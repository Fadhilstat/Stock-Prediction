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

PROJECT_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(
    page_title="Ruang Risiko IDX",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1240px; padding-top: 1.7rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px;
    }
    .rr-note {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin: 0.4rem 0 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_runtime_data(project_root: str) -> DashboardData:
    """Load validated precomputed artifacts without running model training."""

    return load_dashboard_data(Path(project_root))


def make_price_figure(data: pd.DataFrame, ticker: str) -> go.Figure:
    """Build an adjusted-close chart for one market series."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["trade_date"],
            y=data["adjusted_close"],
            mode="lines",
            name=ticker,
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Perjalanan harga yang sudah disesuaikan",
        xaxis_title=None,
        yaxis_title="Adjusted close",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=55, b=10),
        height=430,
    )
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
            hovertemplate="%{x|%d %b %Y}<br>%{y:.1%}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Seberapa jauh harga berada di bawah puncak sebelumnya",
        xaxis_title=None,
        yaxis_title="Drawdown",
        yaxis_tickformat=".0%",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=55, b=10),
        height=330,
    )
    return figure


def render_header(data: DashboardData) -> None:
    """Render the project purpose and current data date."""

    st.title("Ruang Risiko IDX")
    st.write(
        "Tempat belajar membaca risiko saham Indonesia dengan data, model statistik, "
        "dan probabilitas yang disertai batasannya. Fokusnya bukan mencari sinyal transaksi, "
        "melainkan membantu pengguna memahami ketidakpastian dengan lebih masuk akal."
    )
    st.caption(
        f"Data terakhir yang masuk: {data.latest_date.strftime('%d %b %Y')}. "
        "Analisis ini bersifat edukatif dan bukan rekomendasi investasi."
    )


def render_market_overview(data: DashboardData) -> None:
    """Render a market-level descriptive overview."""

    st.subheader("Gambaran pasar")
    st.write(
        "Bagian ini memberi konteks sebelum melihat model. Return harian, volatilitas historis, "
        "dan drawdown membantu menunjukkan apakah sebuah saham sedang bergerak tenang atau berada "
        "dalam periode yang lebih tidak nyaman dari biasanya."
    )

    snapshot = build_market_snapshot(data.analytics).copy()
    snapshot["return_harian"] = snapshot["simple_return"]
    snapshot["volatilitas_21_hari"] = snapshot["volatility_21d"]
    snapshot["drawdown_saat_ini"] = snapshot["drawdown"]

    display = snapshot[
        [
            "ticker",
            "adjusted_close",
            "return_harian",
            "volatilitas_21_hari",
            "drawdown_saat_ini",
        ]
    ].rename(
        columns={
            "ticker": "Ticker",
            "adjusted_close": "Adjusted close",
            "return_harian": "Return harian",
            "volatilitas_21_hari": "Volatilitas 21 hari",
            "drawdown_saat_ini": "Drawdown saat ini",
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

    st.info(
        "Volatilitas 21 hari di sini adalah ukuran historis. Untuk estimasi risiko satu hari ke "
        "depan, gunakan halaman Risiko dan GARCH."
    )


def render_stock_explorer(data: DashboardData, ticker: str) -> None:
    """Render historical context for one selected ticker."""

    st.subheader("Jelajah saham")
    ticker_data = data.analytics.loc[data.analytics["ticker"].eq(ticker)].copy()

    min_date = ticker_data["trade_date"].min().date()
    max_date = ticker_data["trade_date"].max().date()
    default_start = max(
        pd.Timestamp(min_date),
        pd.Timestamp(max_date) - pd.DateOffset(years=2),
    ).date()

    selected_range = st.date_input(
        "Periode yang ingin dilihat",
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
    metrics[3].metric("Drawdown saat ini", f"{float(latest['drawdown']):.2%}")

    st.plotly_chart(make_price_figure(ticker_data, ticker), use_container_width=True)
    st.plotly_chart(make_drawdown_figure(ticker_data, ticker), use_container_width=True)

    with st.expander("Cara membaca dua grafik ini"):
        st.write(
            "Harga menunjukkan perjalanan nilai pasar setelah penyesuaian aksi korporasi. "
            "Drawdown menjawab pertanyaan yang berbeda: seberapa jauh posisi saat ini "
            "berada di bawah puncak yang pernah dicapai. Nilai drawdown yang lebih negatif "
            "berarti jarak dari puncak sebelumnya semakin besar."
        )


def render_risk_page(data: DashboardData, ticker: str) -> None:
    """Render registry-selected GARCH risk estimates for one ticker."""

    st.subheader("Risiko satu hari dan GARCH")
    risk = get_ticker_row(data.risk_snapshot, ticker)
    status = data.final_registry["risk_and_volatility"].get(
        "selection_status",
        "status tidak tersedia",
    )
    status_label = format_registry_status(str(status))

    st.write(
        "Di sini volatilitas bukan dihitung ulang dari jendela historis saat halaman dibuka. "
        "Angkanya berasal dari snapshot GARCH yang sudah dihitung offline memakai model pilihan "
        "untuk masing-masing ticker."
    )

    metrics = st.columns(4)
    metrics[0].metric(
        "Forecast volatilitas 1 hari",
        f"{float(risk['forecast_volatility']):.2%}",
    )
    metrics[1].metric("VaR 95%", f"{float(risk['var_95']):.2%}")
    metrics[2].metric("VaR 99%", f"{float(risk['var_99']):.2%}")
    metrics[3].metric(
        "Half-life volatilitas",
        f"{float(risk['half_life_days']):.1f} hari",
    )

    st.markdown(
        f"""
        <div class="rr-note">
        <strong>Model volatilitas:</strong> {format_model_name(str(risk['volatility_model']))}<br>
        <strong>Model VaR:</strong> {format_model_name(str(risk['var_model']))}<br>
        <strong>Status seleksi:</strong> {status_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.warning(
        "VaR adalah ambang kerugian berbasis model dan tingkat keyakinan tertentu. Angka ini bukan "
        "batas kerugian maksimum. Pergerakan yang lebih buruk tetap dapat terjadi, terutama saat "
        "pasar mengalami kejadian ekstrem."
    )


def render_direction_page(data: DashboardData, ticker: str) -> None:
    """Render the latest classical direction probability estimate."""

    st.subheader("Probabilitas arah hari perdagangan berikutnya")
    direction = get_ticker_row(data.direction_snapshot, ticker)

    probability_up = float(direction["probability_up"])
    probability_down = float(direction["probability_down"])
    training_end = pd.Timestamp(direction["training_end_date"]).strftime("%d %b %Y")

    metrics = st.columns(3)
    metrics[0].metric("Probabilitas naik", f"{probability_up:.1%}")
    metrics[1].metric("Probabilitas turun atau tidak naik", f"{probability_down:.1%}")
    metrics[2].metric("Observasi untuk refit", f"{int(direction['training_observations']):,}")

    st.markdown(
        f"""
        <div class="rr-note">
        <strong>Model:</strong> {format_model_name(str(direction['selected_model']))}<br>
        <strong>Horizon:</strong> hari perdagangan berikutnya<br>
        <strong>Data training terakhir:</strong> {training_end}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        "Probabilitas ini tidak dibaca sebagai tombol beli atau jual. Nilai yang dekat 50% "
        "menunjukkan ketidakpastian yang cukup besar. Nilai yang lebih tinggi pun tetap "
        "bisa menghasilkan arah yang salah pada satu hari tertentu."
    )


def render_consolidated_risk(data: DashboardData) -> None:
    """Render a cross-ticker view of precomputed risk and direction estimates."""

    st.subheader("Ringkasan risiko lintas ticker")
    st.write(
        "Tabel ini menyatukan beberapa ukuran yang menjawab pertanyaan berbeda. Forecast "
        "volatilitas dan VaR berbicara tentang besarnya risiko. Probabilitas naik membahas "
        "arah. Keduanya tidak digabung menjadi satu skor karena maknanya memang berbeda."
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

    st.subheader("Bukti model, termasuk yang tidak menang")
    st.write(
        "Model yang lebih rumit tidak otomatis lebih berguna. Bagian ini menunjukkan keputusan "
        "model apa adanya, termasuk ketika baseline sederhana justru lebih kuat."
    )

    st.markdown("#### GARCH untuk risiko")
    risk_registry = data.final_registry["risk_and_volatility"]
    st.write(
        "GARCH, EGARCH, dan GJR-GARCH dinilai untuk tugas volatilitas dan VaR. Pilihan dilakukan "
        "per ticker, bukan dengan satu model yang dipaksakan untuk seluruh saham. Statusnya masih "
        "provisional berdasarkan evaluasi out-of-sample."
    )
    st.caption(
        "Metrik utama volatilitas: "
        f"{risk_registry.get('primary_volatility_metric', 'tidak tersedia')}."
    )

    st.markdown("#### Model klasik untuk probabilitas arah")
    direction_rows = pd.DataFrame(
        summarize_direction_registry(data.classical_registry)
    )
    direction_rows["selected_model"] = direction_rows["selected_model"].map(
        format_model_name
    )
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
        "Model dipilih memakai validation log loss, lalu Brier score sebagai tie-breaker. "
        "Hasil test ditampilkan sebagai evaluasi akhir, bukan bahan pemilihan model."
    )

    kronos = summarize_kronos_evidence(data.kronos_evidence)
    granite = summarize_granite_evidence(data.granite_evidence)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Kronos")
        st.metric("Forecast evaluasi", f"{kronos['forecast_count']:,}")
        st.write(
            "Kronos tetap menjadi benchmark eksperimen. Pada evaluasi yang dibekukan, random walk "
            "memiliki close MAE dan log-return MAE yang lebih rendah untuk seluruh enam seri pasar."
        )
        st.caption(kronos["structural_result"])

    with right:
        st.markdown("#### Granite TTM R2.1")
        st.metric("Forecast evaluasi", f"{granite['forecast_rows']:,}")
        st.write(
            f"Granite mengalahkan persistence pada {granite['wins_vs_persistence']} dari "
            f"{granite['ticker_count']} saham untuk return MAE, tetapi mengalahkan random walk "
            f"pada {granite['wins_vs_random_walk']} saham. Karena itu model tidak dipromosikan "
            "menjadi model produksi."
        )
        st.caption(
            f"Target: {granite['target']}. Revision: {granite['model_revision']}."
        )

    st.info(
        "Hasil model yang tidak mengalahkan baseline tetap berguna. Ia membantu mencegah proyek "
        "mengklaim kemampuan prediksi hanya karena memakai model yang terdengar lebih canggih."
    )


def render_learn_page() -> None:
    """Render plain-language concepts and verified reference links."""

    st.subheader("Belajar membaca risiko")
    st.write(
        "Bagian ini dibuat untuk pembaca yang belum terbiasa dengan quantitative finance. "
        "Tujuannya bukan menghafal rumus, tetapi memahami pertanyaan yang dijawab setiap ukuran."
    )

    for topic in build_learn_topics():
        with st.expander(topic["title"]):
            st.markdown(f"**Pertanyaan utama:** {topic['question']}")
            st.write(topic["explanation"])

    st.markdown("#### Kenapa hasil model perlu diragukan secara sehat?")
    st.write(
        "Pasar berubah, data historis terbatas, dan model menyederhanakan kenyataan. Karena itu "
        "Ruang Risiko IDX memakai urutan waktu saat evaluasi, membandingkan model dengan baseline, "
        "dan menjaga hasil test agar tidak dipakai untuk memilih model."
    )

    st.markdown("#### Sumber yang sudah diperiksa")
    st.markdown(
        "- [Nobel Prize: Robert F. Engle, Risk and Volatility]"
        "(https://www.nobelprize.org/prizes/economic-sciences/2003/engle/lecture/)\n"
        "- [Basel Framework: market risk terminology]"
        "(https://www.bis.org/basel_framework/chapter/MAR/10.htm)\n"
        "- [Kronos official repository](https://github.com/shiyu-coder/Kronos)\n"
        "- [Granite Time Series TTM R2 model card]"
        "(https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2)"
    )
    st.caption("Keempat sumber di atas diperiksa kembali pada 10 Agustus 2026.")


try:
    dashboard_data = load_runtime_data(str(PROJECT_ROOT))
except DashboardDataError as error:
    st.title("Ruang Risiko IDX")
    st.error("Dashboard belum memiliki seluruh artifact runtime yang dibutuhkan.")
    st.write(
        "Aplikasi sengaja tidak menjalankan training atau fitting model ketika halaman dibuka. "
        "Bangun dulu analytics dan snapshot offline, lalu jalankan kembali dashboard."
    )
    st.code(str(error))
    st.stop()

render_header(dashboard_data)

selected_ticker = st.sidebar.selectbox(
    "Ticker yang ingin dipelajari",
    dashboard_data.tickers,
)

st.sidebar.caption(
    "Gunakan dashboard ini untuk memahami risiko dan ketidakpastian. "
    "Dashboard ini bukan tempat mencari sinyal transaksi."
)

(
    overview_tab,
    explorer_tab,
    risk_tab,
    direction_tab,
    combined_tab,
    evidence_tab,
    learn_tab,
) = st.tabs(
    [
        "Gambaran pasar",
        "Jelajah saham",
        "Risiko dan GARCH",
        "Probabilitas arah",
        "Ringkasan risiko",
        "Bukti model",
        "Belajar",
    ]
)

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
    "Ruang Risiko IDX adalah proyek edukasi dan tidak memberikan rekomendasi investasi."
)
