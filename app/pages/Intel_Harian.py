"""Daily analyst-role page for Ruang Risiko IDX."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ruang_risiko_idx.dashboard.data_access import DashboardDataError, load_dashboard_data
from ruang_risiko_idx.dashboard.deployment import (
    canonical_runtime_available,
    load_deployment_dashboard_data,
)
from ruang_risiko_idx.dashboard.intelligence import load_runtime_intelligence

PROJECT_ROOT = Path(__file__).resolve().parents[2]

st.set_page_config(
    page_title="Intel Harian | Ruang Risiko IDX",
    page_icon="🧭",
    layout="wide",
)


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
    st.title("Intel Harian")
    st.error("Data intelligence belum siap dibaca dengan aman.")
    st.write(
        "Halaman utama Ruang Risiko IDX tetap dapat digunakan. Intel Harian akan muncul "
        "setelah pipeline berikutnya menghasilkan artifact yang selaras dengan data pasar."
    )
    st.stop()

st.title("Intel Harian")
st.write(
    "Satu tempat untuk membaca kondisi pasar dari beberapa sudut. Setiap role memakai data "
    "atau metadata sumber yang bisa diperiksa, lalu menjelaskan konteksnya tanpa mengubahnya "
    "menjadi rekomendasi transaksi."
)
st.caption(
    "Versi publik ini tidak memanggil OpenAI API atau layanan AI berbayar. Ringkasan dibuat "
    "dengan aturan yang transparan dari artifact proyek dan metadata sumber terverifikasi."
)

if intelligence is None:
    st.info(
        "Intel Harian belum tersedia pada bundle ini. Dashboard utama tetap aktif dan pipeline "
        "akan menambahkan halaman ini setelah refresh deployment berikutnya."
    )
    st.stop()

as_of_date = str(intelligence["as_of_date"])
st.caption(f"Data dan model: {as_of_date}")

selected_ticker = st.sidebar.selectbox(
    "Ticker untuk Intel Harian",
    dashboard_data.tickers,
)

briefs = intelligence["ticker_briefs"][selected_ticker]
market = briefs["market"]
risk = briefs["risk"]
direction = briefs["direction"]

st.subheader(f"{selected_ticker} dari tiga sudut")
left, middle, right = st.columns(3)

with left:
    st.markdown("#### Analis pasar")
    st.caption(str(market["state"]))
    st.write(str(market["summary"]))

with middle:
    st.markdown("#### Analis risiko")
    st.caption(str(risk["state"]))
    st.write(str(risk["summary"]))

with right:
    st.markdown("#### Analis probabilitas")
    st.caption(str(direction["state"]))
    st.write(str(direction["summary"]))

st.divider()
st.subheader("Konteks makro dan berita")
macro_news = intelligence["macro_news"]
st.caption(str(macro_news["state"]))
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
        st.markdown(f"- [{title}]({url})")
        detail = source if not published else f"{source} | {published}"
        st.caption(detail)
else:
    st.info(
        "Belum ada artikel baru dari source allowlist yang relevan pada refresh ini. "
        "Ketiadaan berita tidak diubah menjadi asumsi sentimen pasar."
    )

st.divider()
st.subheader("Auditor model dan data")
audit = intelligence["model_audit"]
st.caption(str(audit["state"]))
st.write(str(audit["summary"]))

st.subheader("Ringkasan lintas peran")
for sentence in intelligence.get("synthesis", []):
    st.markdown(f"- {sentence}")

st.warning(str(intelligence["disclaimer"]))
st.caption(
    "Berita hanya memakai metadata dan link asli. Pengguna tetap diarahkan ke sumber untuk "
    "membaca konteks lengkap dan melakukan penilaian sendiri."
)
