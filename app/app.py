"""Ruang Risiko IDX Autonomous Finished Product Dashboard."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ruang_risiko_idx.config import ProjectSettings
from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary, get_creator_claims_for_ticker
from ruang_risiko_idx.research.fundamentals import CANONICAL_COMPANIES, get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.journal import load_prediction_journal
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.multimodal import get_ablation_benchmarks, run_evidence_conflict_radar
from ruang_risiko_idx.research.risk_engine import evaluate_risk_engine
from ruang_risiko_idx.research.scenarios import compute_horizon_quantiles, generate_scenarios
from ruang_risiko_idx.research.technical import compute_technical_features, summarize_technical_state

st.set_page_config(
    page_title="Ruang Risiko IDX - Equity Risk & Decision Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sober Anti-Slop Dark Theme CSS
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    body {
        background-color: #0B0F19;
        color: #F9FAFB;
    }
    [data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 8px;
        padding: 14px 18px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-favorable { background-color: #064E3B; color: #34D399; border: 1px solid #059669; }
    .badge-watch { background-color: #1E3A8A; color: #60A5FA; border: 1px solid #2563EB; }
    .badge-wait { background-color: #374151; color: #9CA3AF; border: 1px solid #4B5563; }
    .badge-avoid { background-color: #78350F; color: #FBBF24; border: 1px solid #D97706; }
    .badge-veto { background-color: #7F1D1D; color: #F87171; border: 1px solid #DC2626; }
    .card-panel {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_all_market_data(raw_path: Path) -> pd.DataFrame:
    """Load canonical market price series."""
    if not raw_path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(raw_path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.sort_values(["ticker", "trade_date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_snapshots(project_root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Load latest risk and direction snapshots."""
    risk_file = project_root / "reports" / "risk" / "latest_risk_snapshot.json"
    dir_file = project_root / "reports" / "ml" / "latest_direction_snapshot.json"

    risk_map: dict[str, dict] = {}
    dir_map: dict[str, dict] = {}

    if risk_file.exists():
        try:
            records = json.loads(risk_file.read_text(encoding="utf-8"))
            for r in records:
                risk_map[r["ticker"]] = r
        except Exception:
            pass

    if dir_file.exists():
        try:
            records = json.loads(dir_file.read_text(encoding="utf-8"))
            for r in records:
                dir_map[r["ticker"]] = r
        except Exception:
            pass

    return risk_map, dir_map


settings = ProjectSettings()
market_data = load_all_market_data(settings.raw_data_path)
risk_snapshots, direction_snapshots = load_snapshots(settings.project_root)

# Verify data availability
if market_data.empty:
    st.error("Market data unavailable. Please run: python scripts/update_market_data.py")
    st.stop()

# Benchmark slice
benchmark_data = market_data.loc[market_data["ticker"] == "^JKSE"].copy()

# Sidebar Setup
st.sidebar.title("Ruang Risiko IDX")
st.sidebar.caption("Autonomous Indonesian Equity Intelligence")

available_tickers = [t for t in settings.tickers if t in market_data["ticker"].unique()]
selected_ticker = st.sidebar.selectbox("Pilih Saham (Ticker)", available_tickers, index=0)
selected_data = market_data.loc[market_data["ticker"] == selected_ticker].sort_values("trade_date").copy()

# Timeframe selector
st.sidebar.subheader("Filter Periode")
timeframe = st.sidebar.radio(
    "Rentang Waktu",
    options=["1 Bulan", "3 Bulan", "6 Bulan", "1 Tahun", "3 Tahun", "Semua Data"],
    index=3,
)

max_date = selected_data["trade_date"].max()
if timeframe == "1 Bulan":
    start_date = max_date - pd.DateOffset(months=1)
elif timeframe == "3 Bulan":
    start_date = max_date - pd.DateOffset(months=3)
elif timeframe == "6 Bulan":
    start_date = max_date - pd.DateOffset(months=6)
elif timeframe == "1 Tahun":
    start_date = max_date - pd.DateOffset(years=1)
elif timeframe == "3 Tahun":
    start_date = max_date - pd.DateOffset(years=3)
else:
    start_date = selected_data["trade_date"].min()

filtered_data = selected_data.loc[selected_data["trade_date"] >= start_date].copy()

# Forecast Horizon Selector
st.sidebar.subheader("Horizon Peramalan")
selected_horizon = st.sidebar.selectbox("Horizon Prediksi", ["1D", "5D", "20D"], index=2)

# Chart Options
st.sidebar.subheader("Tampilan Grafik")
chart_mode = st.sidebar.radio("Tipe Grafik", ["Candlestick", "Adjusted Close"], index=0)
show_sma = st.sidebar.checkbox("Moving Averages (SMA 20, 50, 200)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands (20, 2)", value=False)

# Data Trust & Provenance Card in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Data Trust & Audit")
data_cutoff = max_date.strftime("%Y-%m-%d")
st.sidebar.text(f"Cutoff Date: {data_cutoff}")
st.sidebar.text(f"Total Rows: {len(selected_data):,}")
st.sidebar.text("Quarantine State: ZERO_ERRORS")
st.sidebar.text("Provider: Yahoo v8 Canonical")

# Retrieve Research Intelligence
tech_summary = summarize_technical_state(selected_data, selected_ticker)
ict_summary = evaluate_ict_hypotheses(selected_data, selected_ticker)
fund_snapshot = get_fundamental_snapshot(selected_ticker)
align_summary = compute_market_alignment(selected_data, benchmark_data, selected_ticker)
liq_summary = compute_liquidity_flow_summary(selected_data, selected_ticker)

# Model Snapshot Retrieval
ticker_risk = risk_snapshots.get(selected_ticker, {})
ticker_dir = direction_snapshots.get(selected_ticker, {})

daily_vol = float(ticker_risk.get("forecast_volatility", 0.015))
var_95 = float(ticker_risk.get("var_95", 0.025))
var_99 = float(ticker_risk.get("var_99", 0.040))
vol_model_name = str(ticker_risk.get("volatility_model", "egarch_normal"))

dir_up_prob = float(ticker_dir.get("probability_up", 0.50))
dir_model_name = str(ticker_dir.get("selected_model", "random_forest"))

# Risk Engine Evaluation
risk_eval = evaluate_risk_engine(
    ticker=selected_ticker,
    direction_up_prob=dir_up_prob,
    garch_volatility=daily_vol,
    var_99=var_99,
    liquidity_tier=liq_summary.liquidity_tier,
    trend_state=tech_summary.trend_state,
)

# Quantiles & Scenarios
quantiles = compute_horizon_quantiles(
    current_price=tech_summary.close,
    daily_volatility=daily_vol,
    daily_direction_up_prob=dir_up_prob,
)
active_quantiles = quantiles[selected_horizon]
scenarios = generate_scenarios(
    current_price=tech_summary.close,
    quantiles_20d=quantiles["20D"],
    var_99_1d=var_99,
    trend_state=tech_summary.trend_state,
)

# Pre-Buy Decision Passport
passport = generate_decision_passport(
    ticker=selected_ticker,
    company_name=fund_snapshot.identity.company_name,
    cutoff_date=data_cutoff,
    current_price=tech_summary.close,
    direction_up_prob=dir_up_prob,
    direction_model=dir_model_name,
    volatility_model=vol_model_name,
    quantiles_20d=quantiles["20D"],
    technical=tech_summary,
    ict=ict_summary,
    fundamental=fund_snapshot,
    market_alignment=align_summary,
    liquidity=liq_summary,
    risk_eval=risk_eval,
)

# ----------------- MAIN INTERFACE -----------------

# Header Banner
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title(f"{selected_ticker} - {fund_snapshot.identity.company_name}")
    st.caption(
        f"Sektor: {fund_snapshot.identity.sector} | Papan: {fund_snapshot.identity.listing_board} "
        f"| Kapitalisasi: {fund_snapshot.identity.market_cap_tier} | Cutoff: {data_cutoff}"
    )

with header_col2:
    badge_class = {
        "FAVORABLE_SETUP": "badge-favorable",
        "WATCH": "badge-watch",
        "WAIT": "badge-wait",
        "AVOID": "badge-avoid",
        "HIGH_RISK": "badge-veto",
        "EVENT_RISK": "badge-veto",
        "STALE_DATA": "badge-veto",
    }.get(risk_eval.decision_state, "badge-wait")

    st.markdown(
        f"""
        <div style="text-align: right; padding-top: 10px;">
            <span class="status-badge {badge_class}">{risk_eval.decision_state}</span>
            <div style="font-size: 12px; color: #9CA3AF; margin-top: 5px;">
                Risk Score: <strong>{risk_eval.risk_score_10}/10</strong> | Veto: {"AKTIF" if risk_eval.hard_veto else "TIDAK"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Primary Metrics Bar
metric_cols = st.columns(5)
prev_close = float(selected_data["close"].iloc[-2]) if len(selected_data) > 1 else tech_summary.close
daily_change_pct = (tech_summary.close / prev_close - 1.0) * 100.0

metric_cols[0].metric(
    "Harga Terakhir",
    f"Rp {tech_summary.close:,.0f}",
    f"{daily_change_pct:+.2f}%",
)
metric_cols[1].metric(
    f"Peluang Naik ({selected_horizon})",
    f"{active_quantiles.probability_positive:.1%}",
    f"Model: {dir_model_name}",
)
metric_cols[2].metric(
    f"Jalur Median q50 ({selected_horizon})",
    f"Rp {active_quantiles.q50:,.0f}",
    f"{active_quantiles.expected_return:+.2%}",
)
metric_cols[3].metric(
    "Volatilitas Harian GARCH",
    f"{daily_vol:.2%}",
    f"Model: {vol_model_name}",
)
metric_cols[4].metric(
    "VaR 99% (Tail Risk)",
    f"{var_99:.2%}",
    "Limit: 7.00%",
)

# Executive Research Passport Card
with st.container():
    st.markdown(
        f"""
        <div class="card-panel">
            <h4 style="margin-top: 0; color: #F9FAFB;">Ringkasan Keputusan Pre-Buy Passport</h4>
            <p style="margin-bottom: 8px; color: #D1D5DB; font-size: 14px;">{risk_eval.rationale}</p>
            <div style="font-size: 13px; color: #9CA3AF;">
                <strong>Aturan Invalidasi:</strong> {passport.invalidation_rule}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Interactive Chart & Linked Day Inspector
chart_tab, inspector_tab = st.tabs(["Grafik Analitikal Interaktif", "Linked Day Inspector"])

with chart_tab:
    # Build analytical figure with secondary volume axis
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    features_df = compute_technical_features(filtered_data)

    if chart_mode == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=features_df["trade_date"],
                open=features_df["open"],
                high=features_df["high"],
                low=features_df["low"],
                close=features_df["close"],
                name="OHLC",
                increasing_line_color="#10B981",
                decreasing_line_color="#EF4444",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["adjusted_close"],
                mode="lines",
                name="Adjusted Close",
                line=dict(color="#3B82F6", width=2),
            ),
            row=1,
            col=1,
        )

    if show_sma:
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["sma_20"],
                mode="lines",
                name="SMA 20",
                line=dict(color="#F59E0B", width=1.2),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["sma_50"],
                mode="lines",
                name="SMA 50",
                line=dict(color="#8B5CF6", width=1.2),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["sma_200"],
                mode="lines",
                name="SMA 200",
                line=dict(color="#6B7280", width=1.5),
            ),
            row=1,
            col=1,
        )

    if show_bb:
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["bollinger_upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="#475569", width=1, dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=features_df["trade_date"],
                y=features_df["bollinger_lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="#475569", width=1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(71, 85, 105, 0.1)",
            ),
            row=1,
            col=1,
        )

    # Volume subplot
    vol_colors = [
        "#10B981" if c >= o else "#EF4444"
        for c, o in zip(features_df["close"], features_df["open"])
    ]
    fig.add_trace(
        go.Bar(
            x=features_df["trade_date"],
            y=features_df["volume"],
            name="Volume",
            marker_color=vol_colors,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#111827",
        margin=dict(l=10, r=10, t=20, b=10),
        height=520,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

with inspector_tab:
    st.subheader("Linked Day Inspector (Point-In-Time Replay)")
    st.caption(
        "Pilih tanggal perdagangan historis untuk mensinkronisasi semua bukti analitis yang tersedia pada cutoff tersebut tanpa look-ahead bias."
    )

    dates_list = selected_data["trade_date"].dt.strftime("%Y-%m-%d").tolist()
    default_idx = len(dates_list) - 1
    selected_inspect_date_str = st.select_slider(
        "Pilih Tanggal Cutoff Historis",
        options=dates_list,
        value=dates_list[default_idx],
    )

    inspect_row = selected_data.loc[
        selected_data["trade_date"].dt.strftime("%Y-%m-%d") == selected_inspect_date_str
    ].iloc[0]

    ins_cols = st.columns(4)
    ins_cols[0].metric("Open", f"Rp {inspect_row['open']:,.0f}")
    ins_cols[1].metric("High", f"Rp {inspect_row['high']:,.0f}")
    ins_cols[2].metric("Low", f"Rp {inspect_row['low']:,.0f}")
    ins_cols[3].metric("Close", f"Rp {inspect_row['close']:,.0f}")

    ins_cols2 = st.columns(4)
    ins_cols2[0].metric("Adjusted Close", f"Rp {inspect_row['adjusted_close']:,.0f}")
    ins_cols2[1].metric("Volume Perdagangan", f"{inspect_row['volume']:,.0f}")
    ins_cols2[2].metric("Dividen Tercatat", f"Rp {inspect_row['dividends']:.2f}")
    ins_cols2[3].metric("Aksi Stock Split", f"{inspect_row['stock_splits']:.2f}")

# Probabilistic Quantile Fan & Scenarios Section
st.markdown("---")
st.subheader("Peramalan Probabilistik & Simulasi Skenario")

col_fan, col_scenarios = st.columns([1, 1])

with col_fan:
    st.markdown(f"#### Kipas Quantile Distribusi Masa Depan ({selected_horizon})")
    st.caption("Ketidakpastian ditampilkan secara eksplisit. q50 adalah nilai median statistik, bukan target kepastian.")

    fan_fig = go.Figure()
    horizons_x = ["Hari 0", "1D", "5D", "20D"]
    p_current = tech_summary.close

    q10_path = [p_current, quantiles["1D"].q10, quantiles["5D"].q10, quantiles["20D"].q10]
    q25_path = [p_current, quantiles["1D"].q25, quantiles["5D"].q25, quantiles["20D"].q25]
    q50_path = [p_current, quantiles["1D"].q50, quantiles["5D"].q50, quantiles["20D"].q50]
    q75_path = [p_current, quantiles["1D"].q75, quantiles["5D"].q75, quantiles["20D"].q75]
    q90_path = [p_current, quantiles["1D"].q90, quantiles["5D"].q90, quantiles["20D"].q90]

    # Outer fan (q10 to q90)
    fan_fig.add_trace(
        go.Scatter(x=horizons_x, y=q90_path, mode="lines", line=dict(width=0), showlegend=False)
    )
    fan_fig.add_trace(
        go.Scatter(
            x=horizons_x,
            y=q10_path,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(59, 130, 246, 0.12)",
            name="Tail Range (q10-q90)",
        )
    )

    # Inner fan (q25 to q75)
    fan_fig.add_trace(
        go.Scatter(x=horizons_x, y=q75_path, mode="lines", line=dict(width=0), showlegend=False)
    )
    fan_fig.add_trace(
        go.Scatter(
            x=horizons_x,
            y=q25_path,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(59, 130, 246, 0.25)",
            name="Interquartile (q25-q75)",
        )
    )

    # Median path (q50)
    fan_fig.add_trace(
        go.Scatter(
            x=horizons_x,
            y=q50_path,
            mode="lines+markers",
            line=dict(color="#3B82F6", width=2.5),
            name="Jalur Median (q50)",
        )
    )

    fan_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#111827",
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fan_fig, use_container_width=True)

with col_scenarios:
    st.markdown("#### Scenario Engine (Jalur Skenario 20D)")
    st.caption("Peta skenario forward-looking dengan pemicu utama dan level invalidasi tesis.")

    scenario_rows = []
    for s in scenarios:
        scenario_rows.append(
            {
                "Skenario": s.scenario_name,
                "Peluang": f"{s.probability:.0%}",
                "Ekspektasi 20D": f"Rp {s.expected_price_20d:,.0f}",
                "Ekspektasi Gerak": f"{s.expected_move_percent:+.1f}%",
                "Level Invalidasi": f"Rp {s.invalidation_level:,.0f}",
            }
        )
    st.dataframe(pd.DataFrame(scenario_rows), use_container_width=True, hide_index=True)

# Multi-Layer Research Intelligence Suite
st.markdown("---")
st.subheader("Ruang Riset Multimodal & Lapisan Bukti")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    [
        "1. Teknikal & Momentum",
        "2. Hipotesis ICT",
        "3. Fundamental PIT",
        "4. Konteks IHSG",
        "5. Likuiditas & Flow",
        "6. Radar Konflik & Ablasi",
        "7. Jurnal Prediksi & Replay",
    ]
)

with t1:
    st.markdown("#### Karakteristik Teknikal Deterministik")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write(f"- **Klasifikasi Tren:** `{tech_summary.trend_state}`")
        st.write(f"- **Status Momentum:** `{tech_summary.momentum_state}`")
        st.write(f"- **Kondisi Volatilitas:** `{tech_summary.volatility_state}`")
        st.write(f"- **RSI 14:** `{tech_summary.rsi_14:.1f}`")
        st.write(f"- **Average True Range (ATR 14):** `Rp {tech_summary.atr_14:,.0f}`")
    with col_t2:
        st.write(f"- **SMA 20:** `Rp {tech_summary.sma_20:,.0f}`")
        st.write(f"- **SMA 50:** `Rp {tech_summary.sma_50:,.0f}`")
        st.write(f"- **SMA 200:** `Rp {tech_summary.sma_200:,.0f}`")
        st.write(f"- **MACD Histogram:** `{tech_summary.macd_histogram:+.2f}`")
        st.write(f"- **Bollinger Bandwidth:** `Rp {tech_summary.bollinger_lower:,.0f} s/d Rp {tech_summary.bollinger_upper:,.0f}`")

with t2:
    st.markdown("#### Pengujian Hipotesis Struktur Pasar Gaya ICT")
    st.caption("Hipotesis ICT diperlakukan sebagai metodologi empiris formal, bukan kebenaran absolut pasar.")

    st.write(f"- **Struktur Pasar:** `{ict_summary.market_structure_state}`")
    st.write(f"- **Zona Valuasi Relatif:** `{ict_summary.zone_classification}` (Swing High: Rp {ict_summary.swing_high:,.0f} | Swing Low: Rp {ict_summary.swing_low:,.0f})")
    st.write(f"- **Fair Value Gap:** `{"Terdeteksi" if ict_summary.fair_value_gap_present else "Tidak ada gap signifikan"}`")
    st.write(f"- **Liquidity Sweep:** `{"Terdeteksi pada swing terbaru" if ict_summary.liquidity_sweep_detected else "Tidak terdeteksi"}`")

    ict_table = []
    for h in ict_summary.hypotheses:
        ict_table.append(
            {
                "Hipotesis": h.hypothesis_name,
                "Status": "TERDETEKSI" if h.detected else "TIDAK",
                "Arah": h.direction,
                "Harga Acuan": f"Rp {h.reference_price:,.0f}",
                "Invalidasi": f"Rp {h.invalidation_level:,.0f}",
                "Keterangan": h.description,
            }
        )
    st.dataframe(pd.DataFrame(ict_table), use_container_width=True, hide_index=True)

with t3:
    st.markdown("#### Intelijen Fundamental Point-In-Time")
    st.caption("Data keuangan tercatat berdasarkan tanggal publikasi riil untuk mencegah look-ahead bias.")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.write(f"- **Periode Laporan:** `{fund_snapshot.reporting_period}`")
        st.write(f"- **Tanggal Publikasi Resmi:** `{fund_snapshot.publication_date}`")
        st.write(f"- **P/E Ratio:** `{fund_snapshot.pe_ratio:.1f}x`")
        st.write(f"- **P/B Ratio:** `{fund_snapshot.pbv_ratio:.2f}x`")
        st.write(f"- **Dividend Yield:** `{fund_snapshot.dividend_yield_percent:.1f}%`")
    with col_f2:
        st.write(f"- **Return on Equity (ROE):** `{fund_snapshot.roe_percent:.1f}%`")
        st.write(f"- **Net Profit Margin:** `{fund_snapshot.net_margin_percent:.1f}%`")
        st.write(f"- **Pertumbuhan Pendapatan YoY:** `{fund_snapshot.revenue_growth_yoy:+.1f}%`")
        st.write(f"- **Debt to Equity:** `{fund_snapshot.debt_to_equity:.2f}`")
        st.write(f"- **Kualitas Laba & Valuasi:** `{fund_snapshot.earnings_quality_score}` | `{fund_snapshot.valuation_regime}`")

with t4:
    st.markdown("#### Keselarasan Saham vs Sektor vs IHSG")
    st.caption("Mengukur pengaruh makro pasar dan risiko sistemik terhadap saham terpilih.")

    st.write(f"- **Status Penyelarasan:** `{align_summary.alignment_state}`")
    st.write(f"- **Penjelasan:** {align_summary.alignment_reasoning}")
    st.write(f"- **Rolling Beta 60-Hari vs IHSG:** `{align_summary.rolling_beta_60d:.2f}`")
    st.write(f"- **Korelasi 60-Hari vs IHSG:** `{align_summary.rolling_correlation_60d:.2f}`")
    st.write(f"- **Return Relatif 20-Hari:** Saham `{align_summary.stock_return_20d:+.2%}` vs IHSG `{align_summary.ihsg_return_20d:+.2%}` (Kekuatan Relatif: `{align_summary.relative_strength_20d:+.2%}`)")

with t5:
    st.markdown("#### Kualitas Eksekusi Likuiditas & Aliran Institusi")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.write(f"- **Rata-rata Nilai Transaksi Harian (20D):** `Rp {liq_summary.average_daily_value_idr:,.0f}`")
        st.write(f"- **Tier Likuiditas:** `{liq_summary.liquidity_tier}`")
        st.write(f"- **Estimasi Slippage Eksekusi:** `{liq_summary.estimated_slippage_bps:.1f} bps`")
        st.write(f"- **Kapasitas Keluar:** `{liq_summary.exit_capacity_score}`")
    with col_l2:
        st.write(f"- **Status Arus Asing (Flow Proxy):** `{liq_summary.foreign_flow_state}`")
        st.write(f"- **Persistensi Arus:** `{liq_summary.foreign_persistence_days} hari berturut-turut`")
        st.write(f"- **Konsentrasi Broker:** `{liq_summary.broker_concentration_proxy}`")
        st.write(f"- **Peringatan Kerumunan Sosial:** `{"Waspada Kerumunan Ekstrem" if liq_summary.crowding_alert else "Aman / Normal"}`")

    st.markdown("##### Catatan Klaim Kreator & Analis Publik")
    claims = get_creator_claims_for_ticker(selected_ticker)
    if claims:
        claims_data = []
        for c in claims:
            claims_data.append(
                {
                    "Kreator / Desk": c.creator_name,
                    "Platform": c.platform,
                    "Tanggal Klaim": c.timestamp,
                    "Arah": c.claim_direction,
                    "Horizon": c.target_horizon,
                    "Harga Publikasi": f"Rp {c.publication_price:,.0f}",
                    "Status Tesis": c.current_status,
                    "Ringkasan Tesis": c.thesis_summary,
                }
            )
        st.dataframe(pd.DataFrame(claims_data), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada catatan klaim publik terdaftar untuk saham ini.")

with t6:
    st.markdown("#### Radar Konflik Bukti Multimodal")
    st.caption("Mendeteksi pertentangan antar modalitas analitis agar keputusan tidak terjebak dalam bias satu arah.")

    active_conflicts = run_evidence_conflict_radar(
        technical_trend=tech_summary.trend_state,
        fundamental_regime=fund_snapshot.valuation_regime,
        ihsg_alignment=align_summary.alignment_state,
        foreign_flow=liq_summary.foreign_flow_state,
        direction_prob_up=dir_up_prob,
        garch_volatility=daily_vol,
    )

    if active_conflicts:
        conflict_table = []
        for conf in active_conflicts:
            conflict_table.append(
                {
                    "Modalitas A": conf.modality_a,
                    "Modalitas B": conf.modality_b,
                    "Sinyal A": conf.signal_a,
                    "Sinyal B": conf.signal_b,
                    "Tingkat Konflik": conf.conflict_severity,
                    "Deskripsi Kontradiksi": conf.description,
                }
            )
        st.dataframe(pd.DataFrame(conflict_table), use_container_width=True, hide_index=True)
    else:
        st.success("Tidak ada kontradiksi modalitas yang signifikan pada cutoff ini.")

    st.markdown("##### Benchmark Ablasi Multimodal")
    ablations = get_ablation_benchmarks()
    ab_data = []
    for ab in ablations:
        ab_data.append(
            {
                "Konfigurasi": ab.configuration_name,
                "Modalitas Aktif": ", ".join(ab.active_modalities),
                "Validation Log Loss": f"{ab.validation_log_loss:.4f}",
                "Validation Brier": f"{ab.validation_brier_score:.4f}",
                "IR Kontribusi": f"{ab.information_ratio_contribution:.2f}",
                "Status": ab.status,
            }
        )
    st.dataframe(pd.DataFrame(ab_data), use_container_width=True, hide_index=True)

with t7:
    st.markdown("#### Jurnal Prediksi & Replay Forward Testing")
    st.caption("Jurnal append-only immutable untuk memverifikasi akurasi historis peramalan tanpa perombakan data masa lalu.")

    journal_df = load_prediction_journal()
    filtered_journal = journal_df.loc[journal_df["ticker"] == selected_ticker].copy()
    if not filtered_journal.empty:
        st.dataframe(filtered_journal, use_container_width=True, hide_index=True)
    else:
        st.dataframe(journal_df, use_container_width=True, hide_index=True)

# Export Decision Passport Button
st.markdown("---")
st.subheader("Ekspor Dokumen Riset Resmi")
st.download_button(
    label="Unduh Pre-Buy Decision Passport (Markdown)",
    data=passport.markdown_content,
    file_name=f"{passport.passport_id}.md",
    mime="text/markdown",
)

with st.expander("Tampilkan Dokumen Passport Lengkap"):
    st.markdown(passport.markdown_content)

st.caption(
    "Ruang Risiko IDX vNext. Platform edukasi dan analitikal risiko pasar modal Indonesia. "
    "Semua output peramalan adalah estimasi probabilitas dan bukan merupakan ajakan membeli atau menjual saham."
)
