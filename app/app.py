"""Main Streamlit dashboard for Ruang Risiko IDX."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ruang_risiko_idx.dashboard.data_access import (
    DashboardData,
    DashboardDataError,
    load_dashboard_data,
)
from ruang_risiko_idx.dashboard.deployment import (
    canonical_runtime_available,
    deployment_bundle_available,
    load_deployment_dashboard_data,
)
from ruang_risiko_idx.dashboard.evidence import (
    build_learn_topics,
    summarize_direction_registry,
    summarize_granite_evidence,
    summarize_kronos_evidence,
)
from ruang_risiko_idx.dashboard.presentation import (
    build_market_snapshot,
    build_risk_overview,
    format_model_name,
    format_registry_status,
    get_ticker_row,
)
from ruang_risiko_idx.dashboard.style import apply_app_styles, render_hero
from ruang_risiko_idx.dashboard.ux import explain_data_error, ticker_has_convergence_warning

PROJECT_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(
    page_title="Ruang Risiko IDX",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_app_styles()


@st.cache_data(show_spinner=False)
def load_runtime_data(project_root: str) -> DashboardData:
    """Load local runtime first, then use the committed deployment bundle."""

    root = Path(project_root)
    if canonical_runtime_available(root):
        return load_dashboard_data(root)
    if deployment_bundle_available(root):
        return load_deployment_dashboard_data(root)
    return load_dashboard_data(root)


def make_price_figure(data: pd.DataFrame, ticker: str) -> go.Figure:
    """Build a restrained adjusted-close chart for one market series."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["trade_date"],
            y=data["adjusted_close"],
            mode="lines",
            name=ticker,
            line={"color": "#1F4E79", "width": 2},
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Harga yang sudah disesuaikan",
        xaxis_title=None,
        yaxis_title="Adjusted close",
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 8, "t": 54, "b": 8},
        height=410,
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#E9EEF5", zeroline=False)
    return figure


def make_drawdown_figure(data: pd.DataFrame, ticker: str) -> go.Figure:
    """Build a drawdown chart that emphasizes distance from prior peaks."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["trade_date"],
            y=data["drawdown"],
            mode="lines",
            name=ticker,
            line={"color": "#9F3A46", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(159,58,70,0.08)",
            hovertemplate="%{x|%d %b %Y}<br>%{y:.1%}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Jarak dari puncak sebelumnya",
        xaxis_title=None,
        yaxis_title="Drawdown",
        yaxis_tickformat=".0%",
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 8, "t": 54, "b": 8},
        height=320,
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#E9EEF5", zeroline=False)
    return figure


def render_header(data: DashboardData) -> None:
    """Render the project purpose and current data date."""

    render_hero(
        "Ruang Risiko IDX",
        (
            "Dashboard edukasi untuk membaca return, volatilitas, drawdown, VaR, dan probabilitas "
            "arah saham Indonesia tanpa mengubah ketidakpastian menjadi sinyal transaksi."
        ),
        eyebrow="Risk analytics untuk pasar Indonesia",
        meta=(
            f"Data terakhir: {data.latest_date.strftime('%d %b %Y')} | "
            "Model dihitung offline | Bukan rekomendasi investasi"
        ),
    )


def render_market_overview(data: DashboardData) -> None:
    """Render a market-level descriptive overview."""

    st.subheader("Gambaran pasar")
    st.write(
        "Mulai dari kondisi yang terlihat di data sebelum masuk ke model. Return, volatilitas "
        "historis, dan drawdown memberi konteks tentang ritme pasar saat ini."
    )

    snapshot = build_market_snapshot(data.analytics).copy()
    benchmark = snapshot.loc[snapshot["ticker"].eq("^JKSE")]
    risk_overview = build_risk_overview(data.risk_snapshot, data.direction_snapshot)
    highest_risk = risk_overview.sort_values("forecast_volatility", ascending=False).iloc[0]

    if not benchmark.empty:
        row = benchmark.iloc[0]
        metric_cols = st.columns(4)
        metric_cols[0].metric("Return JKSE", f"{float(row['simple_return']):.2%}")
        metric_cols[1].metric("Volatilitas JKSE 21 hari", f"{float(row['volatility_21d']):.2%}")
        metric_cols[2].metric("Drawdown JKSE", f"{float(row['drawdown']):.2%}")
        metric_cols[3].metric(
            "Risiko model tertinggi",
            str(highest_risk["ticker"]),
            help=(
                "Ticker dengan forecast volatilitas satu hari tertinggi pada snapshot model "
                "terbaru. Ini bukan peringkat kualitas investasi."
            ),
        )

    display = snapshot[
        ["ticker", "adjusted_close", "simple_return", "volatility_21d", "drawdown"]
    ].rename(
        columns={
            "ticker": "Ticker",
            "adjusted_close": "Adjusted close",
            "simple_return": "Return harian",
            "volatility_21d": "Volatilitas 21 hari",
            "drawdown": "Drawdown saat ini",
        }
    )

    st.dataframe(
        display.style.format(
            {
                "Adjusted close": "{:,.2f}",
                "Return harian": "{:.2%}",
                "Volatilitas 21 hari": "{:.2%}",
                "Drawdown saat ini": "{:.2%}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Volatilitas 21 hari adalah ukuran historis. Forecast risiko satu hari tersedia di tab Risiko."
    )


def render_stock_explorer(data: DashboardData, ticker: str) -> None:
    """Render historical context for one selected ticker."""

    st.subheader("Jelajah saham")
    st.write("Lihat perjalanan harga dan tekanan drawdown pada satu ticker dalam periode pilihanmu.")

    ticker_data = data.analytics.loc[data.analytics["ticker"].eq(ticker)].copy()
    min_date = ticker_data["trade_date"].min().date()
    max_date = ticker_data["trade_date"].max().date()
    default_start = max(
        pd.Timestamp(min_date),
        pd.Timestamp(max_date) - pd.DateOffset(years=2),
    ).date()

    selected_range = st.date_input(
        "Periode",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
        key="stock_period",
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
        ticker_data = ticker_data.loc[
            ticker_data["trade_date"].dt.date.between(start_date, end_date)
        ]

    if ticker_data.empty:
        st.warning("Tidak ada observasi pada periode yang dipilih.")
        return

    latest = ticker_data.iloc[-1]
    metrics = st.columns(4)
    metrics[0].metric("Adjusted close", f"{float(latest['adjusted_close']):,.2f}")
    metrics[1].metric("Return harian", f"{float(latest['simple_return']):.2%}")
    metrics[2].metric("Volatilitas 21 hari", f"{float(latest['volatility_21d']):.2%}")
    metrics[3].metric("Drawdown", f"{float(latest['drawdown']):.2%}")

    st.plotly_chart(make_price_figure(ticker_data, ticker), use_container_width=True)
    st.plotly_chart(make_drawdown_figure(ticker_data, ticker), use_container_width=True)

    with st.expander("Cara membaca grafik"):
        st.write(
            "Harga menunjukkan perjalanan nilai setelah penyesuaian aksi korporasi. Drawdown "
            "menunjukkan seberapa jauh harga berada di bawah puncak yang pernah dicapai pada "
            "riwayat yang tersedia."
        )


def render_risk_page(data: DashboardData, ticker: str) -> None:
    """Render registry-selected GARCH risk estimates for one ticker."""

    st.subheader("Risiko satu hari")
    st.write(
        "Angka di bawah berasal dari snapshot GARCH yang dihitung offline. Model dipilih per ticker "
        "dan status seleksinya tetap ditampilkan agar keterbatasan tidak hilang dari layar."
    )

    risk = get_ticker_row(data.risk_snapshot, ticker)
    status = data.final_registry["risk_and_volatility"].get(
        "selection_status",
        "status tidak tersedia",
    )

    if ticker_has_convergence_warning(data.risk_snapshot, ticker):
        st.warning(
            "Estimasi ticker ini melaporkan convergence warning. Angka tetap ditampilkan, tetapi "
            "perlu dibaca dengan lebih hati-hati."
        )

    metrics = st.columns(4)
    metrics[0].metric("Forecast volatilitas", f"{float(risk['forecast_volatility']):.2%}")
    metrics[1].metric("VaR 95%", f"{float(risk['var_95']):.2%}")
    metrics[2].metric("VaR 99%", f"{float(risk['var_99']):.2%}")
    metrics[3].metric("Half-life", f"{float(risk['half_life_days']):.1f} hari")

    st.markdown(
        (
            '<div class="rr-note">'
            f"<strong>Model volatilitas:</strong> {format_model_name(str(risk['volatility_model']))}<br>"
            f"<strong>Model VaR:</strong> {format_model_name(str(risk['var_model']))}<br>"
            f"<strong>Status:</strong> {format_registry_status(str(status))}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.warning(
        "VaR adalah ambang kerugian berbasis model pada tingkat keyakinan tertentu, bukan batas "
        "kerugian maksimum. Pergerakan yang lebih buruk tetap dapat terjadi."
    )


def render_direction_page(data: DashboardData, ticker: str) -> None:
    """Render the latest classical direction probability estimate."""

    st.subheader("Probabilitas arah")
    st.write(
        "Model memberi probabilitas untuk hari perdagangan berikutnya. Angka ini menunjukkan "
        "ketidakpastian model dan tidak diterjemahkan menjadi tombol beli atau jual."
    )

    direction = get_ticker_row(data.direction_snapshot, ticker)
    metrics = st.columns(3)
    metrics[0].metric("Probabilitas naik", f"{float(direction['probability_up']):.1%}")
    metrics[1].metric("Turun atau tidak naik", f"{float(direction['probability_down']):.1%}")
    metrics[2].metric("Observasi refit", f"{int(direction['training_observations']):,}")

    training_end = pd.Timestamp(direction["training_end_date"]).strftime("%d %b %Y")
    st.markdown(
        (
            '<div class="rr-note">'
            f"<strong>Model:</strong> {format_model_name(str(direction['selected_model']))}<br>"
            "<strong>Horizon:</strong> hari perdagangan berikutnya<br>"
            f"<strong>Training terakhir:</strong> {training_end}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_consolidated_risk(data: DashboardData) -> None:
    """Render a cross-ticker view of precomputed risk and direction estimates."""

    st.subheader("Ringkasan lintas ticker")
    st.write(
        "Volatilitas, VaR, dan probabilitas arah menjawab pertanyaan yang berbeda. Karena itu "
        "mereka dibandingkan berdampingan dan tidak dicampur menjadi satu skor sintetis."
    )

    overview = build_risk_overview(data.risk_snapshot, data.direction_snapshot)
    display = overview[
        [
            "ticker",
            "forecast_volatility",
            "var_95",
            "var_99",
            "probability_up",
            "volatility_model_label",
            "direction_model_label",
        ]
    ].rename(
        columns={
            "ticker": "Ticker",
            "forecast_volatility": "Forecast volatilitas",
            "var_95": "VaR 95%",
            "var_99": "VaR 99%",
            "probability_up": "Probabilitas naik",
            "volatility_model_label": "Model volatilitas",
            "direction_model_label": "Model arah",
        }
    )
    st.dataframe(
        display.style.format(
            {
                "Forecast volatilitas": "{:.2%}",
                "VaR 95%": "{:.2%}",
                "VaR 99%": "{:.2%}",
                "Probabilitas naik": "{:.1%}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_model_evidence(data: DashboardData) -> None:
    """Render why each model family received its current project role."""

    st.subheader("Bukti model")
    st.write(
        "Model yang lebih rumit tidak otomatis lebih berguna. Bagian ini menyimpan keputusan model, "
        "baseline, dan hasil eksperimen yang tidak menang."
    )

    risk_registry = data.final_registry["risk_and_volatility"]
    with st.container(border=True):
        st.markdown("#### GARCH untuk risiko")
        st.write(
            "GARCH, EGARCH, dan GJR-GARCH dinilai per ticker untuk volatilitas dan VaR. Statusnya "
            "masih provisional berdasarkan evaluasi out-of-sample."
        )
        st.caption(
            "Metrik utama volatilitas: "
            f"{risk_registry.get('primary_volatility_metric', 'tidak tersedia')}."
        )

    st.markdown("#### Model klasik untuk probabilitas arah")
    direction_rows = pd.DataFrame(summarize_direction_registry(data.classical_registry))
    direction_rows["selected_model"] = direction_rows["selected_model"].map(format_model_name)
    direction_rows = direction_rows.rename(
        columns={
            "ticker": "Ticker",
            "selected_model": "Model terpilih",
            "validation_log_loss": "Validation log loss",
            "validation_brier": "Validation Brier",
            "test_log_loss": "Test log loss",
        }
    )
    st.dataframe(
        direction_rows.style.format(
            {
                "Validation log loss": "{:.4f}",
                "Validation Brier": "{:.4f}",
                "Test log loss": "{:.4f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Pemilihan memakai validation log loss lalu Brier score. Test dipakai untuk evaluasi akhir, "
        "bukan untuk memilih model."
    )

    kronos = summarize_kronos_evidence(data.kronos_evidence)
    granite = summarize_granite_evidence(data.granite_evidence)
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### Kronos")
            st.metric("Forecast evaluasi", f"{kronos['forecast_count']:,}")
            st.write(
                "Random walk memiliki close MAE dan log-return MAE yang lebih rendah pada enam seri "
                "pasar. Kronos tetap menjadi benchmark eksperimen."
            )
    with right:
        with st.container(border=True):
            st.markdown("#### Granite TTM R2.1")
            st.metric("Forecast evaluasi", f"{granite['forecast_rows']:,}")
            st.write(
                f"Granite menang melawan persistence pada {granite['wins_vs_persistence']} dari "
                f"{granite['ticker_count']} saham, tetapi menang melawan random walk pada "
                f"{granite['wins_vs_random_walk']} saham."
            )


def render_learn_page() -> None:
    """Render plain-language concepts and verified reference links."""

    st.subheader("Belajar membaca risiko")
    st.write(
        "Penjelasan singkat untuk pembaca yang belum terbiasa dengan quantitative finance. Fokusnya "
        "adalah pertanyaan yang dijawab setiap ukuran, bukan menghafal rumus."
    )

    for topic in build_learn_topics():
        with st.expander(topic["title"]):
            st.markdown(f"**Pertanyaan utama:** {topic['question']}")
            st.write(topic["explanation"])

    st.markdown("#### Kenapa model perlu diragukan secara sehat?")
    st.write(
        "Pasar berubah, data historis terbatas, dan model menyederhanakan kenyataan. Proyek ini "
        "menjaga urutan waktu saat evaluasi, membandingkan model dengan baseline, dan tidak memakai "
        "test set untuk memilih model."
    )

    st.markdown("#### Sumber utama")
    st.markdown(
        "- [Nobel Prize: Robert F. Engle, Risk and Volatility]"
        "(https://www.nobelprize.org/prizes/economic-sciences/2003/engle/lecture/)\n"
        "- [Basel Framework: market risk terminology]"
        "(https://www.bis.org/basel_framework/chapter/MAR/10.htm)\n"
        "- [Kronos official repository](https://github.com/shiyu-coder/Kronos)\n"
        "- [Granite Time Series TTM R2 model card]"
        "(https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2)"
    )
    st.caption("Tanggal verifikasi setiap sumber dicatat di references/source_registry.yaml.")


try:
    dashboard_data = load_runtime_data(str(PROJECT_ROOT))
except DashboardDataError as error:
    guidance = explain_data_error(error)
    render_hero(
        "Ruang Risiko IDX",
        "Data dashboard belum dapat dibaca dengan aman.",
        eyebrow="Status data",
    )
    st.error(guidance.title)
    st.write(guidance.explanation)
    st.info(guidance.action)
    st.stop()

render_header(dashboard_data)

st.sidebar.markdown("### Ruang Risiko IDX")
selected_ticker = st.sidebar.selectbox(
    "Ticker",
    dashboard_data.tickers,
    help="Pilihan ini dipakai pada tab saham, risiko, dan arah.",
)
st.sidebar.caption(
    "Gunakan dashboard untuk memahami risiko dan ketidakpastian. Tidak ada sinyal transaksi."
)

(
    overview_tab,
    explorer_tab,
    risk_tab,
    direction_tab,
    combined_tab,
    evidence_tab,
    learn_tab,
) = st.tabs(["Pasar", "Saham", "Risiko", "Arah", "Ringkasan", "Model", "Belajar"])

with overview_tab:
    render_market_overview(dashboard_data)
with explorer_tab:
    render_stock_explorer(dashboard_data, selected_ticker)
with risk_tab:
    render_risk_page(dashboard_data, selected_ticker)
with direction_tab:
    render_direction_page(dashboard_data, selected_ticker)
with combined_tab:
    render_consolidated_risk(dashboard_data)
with evidence_tab:
    render_model_evidence(dashboard_data)
with learn_tab:
    render_learn_page()

st.divider()
st.caption(
    "Sumber data pasar: Yahoo Finance melalui yfinance. Model dan snapshot dihitung offline. "
    "Ruang Risiko IDX adalah proyek edukasi dan bukan rekomendasi investasi."
)
