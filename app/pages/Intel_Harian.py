"""Daily intelligence page for Ruang Risiko IDX."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ruang_risiko_idx.dashboard.data_access import DashboardDataError, load_dashboard_data
from ruang_risiko_idx.dashboard.deployment import (
    canonical_runtime_available,
    load_deployment_dashboard_data,
)
from ruang_risiko_idx.dashboard.intelligence import load_runtime_intelligence
from ruang_risiko_idx.dashboard.presentation import format_model_name, get_ticker_row
from ruang_risiko_idx.dashboard.style import apply_app_styles, render_hero, render_state_label

PROJECT_ROOT = Path(__file__).resolve().parents[2]

st.set_page_config(
    page_title="Intel Harian | Ruang Risiko IDX",
    page_icon="🧭",
    layout="wide",
)
apply_app_styles()


@st.cache_data(show_spinner=False)
def load_page_data(project_root: str) -> tuple[object, dict[str, object] | None]:
    """Load validated market data first, then the optional intelligence artifact."""

    root = Path(project_root)
    if canonical_runtime_available(root):
        dashboard_data = load_dashboard_data(root)
    else:
        dashboard_data = load_deployment_dashboard_data(root)

    intelligence = load_runtime_intelligence(
        root,
        latest_date=dashboard_data.latest_date,
        tickers=dashboard_data.tickers,
    )
    return dashboard_data, intelligence


try:
    dashboard_data, intelligence = load_page_data(str(PROJECT_ROOT))
except DashboardDataError:
    render_hero(
        "Intel Harian",
        "Data intelligence belum siap dibaca dengan aman.",
        eyebrow="Status intelligence",
    )
    st.error("Artifact intelligence belum selaras dengan data pasar terbaru.")
    st.write(
        "Dashboard utama tetap dapat digunakan. Halaman ini akan aktif kembali setelah pipeline "
        "menghasilkan artifact yang lolos validasi."
    )
    st.stop()

render_hero(
    "Intel Harian",
    (
        "Ringkasan kondisi pasar dari beberapa sudut yang dapat diperiksa: pasar, risiko, "
        "probabilitas arah, berita, serta audit model dan data."
    ),
    eyebrow="Daily intelligence",
    meta=(
        f"Data dan model: {dashboard_data.latest_date.strftime('%d %b %Y')} | "
        "Tanpa paid language-model API | Bukan rekomendasi investasi"
    ),
)

if intelligence is None:
    st.info(
        "Intel Harian belum tersedia pada bundle ini. Dashboard utama tetap aktif dan pipeline "
        "akan menambahkannya setelah refresh deployment berikutnya."
    )
    st.stop()

selected_ticker = st.sidebar.selectbox(
    "Ticker",
    dashboard_data.tickers,
    help="Pilih satu ticker untuk membaca ringkasan lintas peran.",
)
st.sidebar.caption(
    "Intel Harian membantu membaca konteks. Hasilnya tidak diubah menjadi sinyal transaksi."
)

briefs = intelligence["ticker_briefs"][selected_ticker]
market = briefs["market"]
risk = briefs["risk"]
direction = briefs["direction"]

analytics_rows = dashboard_data.analytics.loc[
    dashboard_data.analytics["ticker"].eq(selected_ticker)
].sort_values("trade_date")
latest_market = analytics_rows.iloc[-1]
risk_row = get_ticker_row(dashboard_data.risk_snapshot, selected_ticker)
direction_row = get_ticker_row(dashboard_data.direction_snapshot, selected_ticker)

st.subheader(f"{selected_ticker} hari ini")
quick_metrics = st.columns(4)
quick_metrics[0].metric("Return harian", f"{float(latest_market['simple_return']):.2%}")
quick_metrics[1].metric(
    "Forecast volatilitas",
    f"{float(risk_row['forecast_volatility']):.2%}",
)
quick_metrics[2].metric("VaR 95%", f"{float(risk_row['var_95']):.2%}")
quick_metrics[3].metric(
    "Probabilitas naik",
    f"{float(direction_row['probability_up']):.1%}",
)

st.markdown("#### Tiga sudut utama")
left, middle, right = st.columns(3)

with left:
    with st.container(border=True):
        st.markdown('<div class="rr-kicker">Analis pasar</div>', unsafe_allow_html=True)
        render_state_label(str(market["state"]))
        st.write(str(market["summary"]))

with middle:
    with st.container(border=True):
        st.markdown('<div class="rr-kicker">Analis risiko</div>', unsafe_allow_html=True)
        render_state_label(str(risk["state"]))
        st.write(str(risk["summary"]))

with right:
    with st.container(border=True):
        st.markdown(
            '<div class="rr-kicker">Analis probabilitas</div>',
            unsafe_allow_html=True,
        )
        render_state_label(str(direction["state"]))
        st.write(str(direction["summary"]))

st.caption(
    "Model arah: "
    f"{format_model_name(str(direction_row['selected_model']))}. "
    "Probabilitas tidak diterjemahkan menjadi keputusan transaksi."
)

st.divider()
macro_news = intelligence["macro_news"]
st.subheader("Makro dan berita")
render_state_label(str(macro_news["state"]))
st.write(str(macro_news["summary"]))

news_items = intelligence.get("news_items", [])
relevant_news = [
    item
    for item in news_items
    if selected_ticker in item.get("tickers", []) or not item.get("tickers", [])
]

if relevant_news:
    st.markdown("#### Sumber terbaru")
    for item in relevant_news[:8]:
        title = str(item["title"])
        url = str(item["url"])
        source = str(item["source_label"])
        published = str(item.get("published_at", ""))
        with st.container(border=True):
            st.write(title)
            detail = source if not published else f"{source} | {published}"
            st.caption(detail)
            st.link_button("Buka sumber", url)
else:
    discovery = intelligence.get("news_discovery", {})
    failed_domains = discovery.get("failed_domains", [])
    st.info(
        "Belum ada artikel baru dari source allowlist yang relevan pada refresh ini. "
        "Ketiadaan berita tidak dipakai sebagai asumsi sentimen pasar."
    )
    if failed_domains:
        st.caption(
            "Discovery belum berhasil untuk sebagian domain sumber pada refresh ini. "
            "Kondisi tersebut dicatat sebagai isu ketersediaan sumber, bukan sinyal pasar."
        )

st.divider()
st.subheader("Audit model dan data")
audit = intelligence["model_audit"]
with st.container(border=True):
    render_state_label(str(audit["state"]))
    st.write(str(audit["summary"]))
    audit_cols = st.columns(2)
    audit_cols[0].metric("Tanggal data", str(audit["latest_trade_date"]))
    audit_cols[1].metric("Convergence warning", int(audit["convergence_warnings"]))

st.subheader("Ringkasan lintas peran")
for sentence in intelligence.get("synthesis", []):
    st.markdown(f"- {sentence}")

st.warning(str(intelligence["disclaimer"]))
st.caption(
    "Berita memakai metadata dan link sumber asli. Baca sumber lengkap sebelum menarik kesimpulan."
)
