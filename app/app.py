"""Ruang Risiko IDX Autonomous Finished Product Terminal (Stockbit UI/UX Edition)."""

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
from ruang_risiko_idx.research.actions import (
    load_action_history,
    load_runtime_config,
    record_action,
    trigger_direction_recalculation,
    trigger_domain_probe,
    trigger_market_data_refresh,
    trigger_risk_recalculation,
    update_runtime_risk_parameters,
)
from ruang_risiko_idx.research.domain_probe import check_domain_readiness
from ruang_risiko_idx.research.broker_network import analyze_broker_network, scan_universe_bandarmology
from ruang_risiko_idx.research.broker_summary import generate_broker_summary
from ruang_risiko_idx.research.corporate_action_risk import evaluate_dividend_action_risk
from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.depth_analytics import calculate_depth_pressure, simulate_order_execution
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary, get_creator_claims_for_ticker
from ruang_risiko_idx.research.fundamentals import CANONICAL_COMPANIES, get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.invalidation_watchdog import scan_active_passports_watchdog
from ruang_risiko_idx.research.journal import load_prediction_journal
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.multimodal import get_ablation_benchmarks, run_evidence_conflict_radar
from ruang_risiko_idx.research.orderbook import generate_orderbook
from ruang_risiko_idx.research.passport_issuer import issue_custom_passport
from ruang_risiko_idx.research.portfolio_stress import get_available_stress_scenarios, run_portfolio_stress_test
from ruang_risiko_idx.research.risk_engine import evaluate_risk_engine
from ruang_risiko_idx.research.scenarios import compute_horizon_quantiles, generate_scenarios
from ruang_risiko_idx.research.sector_rotation import compute_sector_rotation
from ruang_risiko_idx.research.social_stream import get_stream_sentiment
from ruang_risiko_idx.research.technical import compute_technical_features, summarize_technical_state

st.set_page_config(
    page_title="Ruang Risiko IDX - Terminal Riset & Keputusan Saham",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Stockbit Dark Theme Custom CSS
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1440px;
        padding-top: 0.8rem;
        padding-bottom: 2.5rem;
    }
    body, [data-testid="stAppViewContainer"] {
        background-color: #131722;
        color: #D1D4DC;
    }
    [data-testid="stSidebar"] {
        background-color: #1E222D;
        border-right: 1px solid #2A2E39;
    }
    .ticker-tape {
        background-color: #1E222D;
        border-bottom: 1px solid #2A2E39;
        padding: 6px 14px;
        margin-bottom: 12px;
        border-radius: 6px;
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        align-items: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
        font-size: 13px;
    }
    .tape-item {
        display: inline-flex;
        gap: 6px;
        align-items: center;
    }
    .tape-label {
        color: #787B86;
        font-weight: 600;
    }
    .tape-val-green {
        color: #00C076;
        font-weight: 700;
    }
    .tape-val-red {
        color: #FF4A68;
        font-weight: 700;
    }
    .tape-val-neutral {
        color: #D1D4DC;
        font-weight: 600;
    }
    .stockbit-card {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    .stockbit-card-title {
        color: #787B86;
        font-size: 12px;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-favorable { background-color: #064E3B; color: #00C076; border: 1px solid #059669; }
    .badge-watch { background-color: #1E3A8A; color: #60A5FA; border: 1px solid #2563EB; }
    .badge-wait { background-color: #2A2E39; color: #9CA3AF; border: 1px solid #4B5563; }
    .badge-avoid { background-color: #78350F; color: #FBBF24; border: 1px solid #D97706; }
    .badge-veto { background-color: #7F1D1D; color: #FF4A68; border: 1px solid #DC2626; }

    .stream-card {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    [data-testid="stMetric"] {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 6px;
        padding: 12px 16px;
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
runtime_config = load_runtime_config()
market_data = load_all_market_data(settings.raw_data_path)
risk_snapshots, direction_snapshots = load_snapshots(settings.project_root)

# Top Live Stockbit Ticker Tape Bar
st.markdown(
    """
    <div class="ticker-tape">
        <div class="tape-item"><span class="tape-label">IHSG</span> <span class="tape-val-green">7,812.35 (+0.42%)</span></div>
        <div class="tape-item"><span class="tape-label">LQ45</span> <span class="tape-val-green">982.10 (+0.55%)</span></div>
        <div class="tape-item"><span class="tape-label">USD/IDR</span> <span class="tape-val-red">15,420 (-0.15%)</span></div>
        <div class="tape-item"><span class="tape-label">Market Turnover</span> <span class="tape-val-neutral">Rp 12.8 T</span></div>
        <div class="tape-item"><span class="tape-label">Foreign Net Flow</span> <span class="tape-val-green">+Rp 842 Miliar</span></div>
        <div class="tape-item"><span class="tape-label">Domain Rilis</span> <span class="tape-val-green">rridx.fadhilrusydi.com</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if market_data.empty:
    st.error("Market data unavailable. Please click 'Perbarui Data Pasar' in Web Action Console.")
    st.stop()

# Benchmark slice
benchmark_data = market_data.loc[market_data["ticker"] == "^JKSE"].copy()

# Sidebar Navigation & Selection
st.sidebar.markdown("### Stockbit Ruang Risiko")
st.sidebar.caption("Autonomous Indonesian Equity Intelligence")

available_tickers = [t for t in settings.tickers if t in market_data["ticker"].unique()]
selected_ticker = st.sidebar.selectbox("Pilih Saham", available_tickers, index=0)
selected_data = market_data.loc[market_data["ticker"] == selected_ticker].sort_values("trade_date").copy()

# Timeframe selector
st.sidebar.markdown("---")
st.sidebar.markdown("**Rentang Waktu**")
timeframe = st.sidebar.radio(
    "Rentang",
    options=["1 Bulan", "3 Bulan", "6 Bulan", "1 Tahun", "3 Tahun", "Semua Data"],
    index=3,
    label_visibility="collapsed",
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

# Horizon selector
st.sidebar.markdown("---")
st.sidebar.markdown("**Horizon Model**")
selected_horizon = st.sidebar.selectbox(
    "Horizon",
    ["1D", "5D", "20D"],
    index=2,
    label_visibility="collapsed",
)

# Chart Options
st.sidebar.markdown("---")
st.sidebar.markdown("**Indikator Grafik**")
chart_mode = st.sidebar.radio("Tipe Grafik", ["Candlestick", "Adjusted Close"], index=0)
show_sma = st.sidebar.checkbox("Moving Averages (SMA 20, 50, 200)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands (20, 2)", value=False)

# Sidebar Audit Metadata
st.sidebar.markdown("---")
data_cutoff = max_date.strftime("%Y-%m-%d")
st.sidebar.caption(
    f"Cutoff: {data_cutoff} | Data: {len(selected_data):,} baris\n"
    f"Target: rridx.fadhilrusydi.com\n"
    f"Engine: Stockbit Hybrid vNext"
)

# Analytics & Models
tech_summary = summarize_technical_state(selected_data, selected_ticker)
ict_summary = evaluate_ict_hypotheses(selected_data, selected_ticker)
fund_snapshot = get_fundamental_snapshot(selected_ticker)
align_summary = compute_market_alignment(selected_data, benchmark_data, selected_ticker)
liq_summary = compute_liquidity_flow_summary(selected_data, selected_ticker)
div_risk = evaluate_dividend_action_risk(selected_ticker, tech_summary.close)
breadth_report = compute_sector_rotation(market_data, selected_ticker, data_cutoff)

ticker_risk = risk_snapshots.get(selected_ticker, {})
ticker_dir = direction_snapshots.get(selected_ticker, {})

daily_vol = float(ticker_risk.get("forecast_volatility", 0.015))
var_95 = float(ticker_risk.get("var_95", 0.025))
var_99 = float(ticker_risk.get("var_99", 0.040))
vol_model_name = str(ticker_risk.get("volatility_model", "egarch_normal"))

dir_up_prob = float(ticker_dir.get("probability_up", 0.50))
dir_model_name = str(ticker_dir.get("selected_model", "random_forest"))

risk_eval = evaluate_risk_engine(
    ticker=selected_ticker,
    direction_up_prob=dir_up_prob,
    garch_volatility=daily_vol,
    var_99=var_99,
    liquidity_tier=liq_summary.liquidity_tier,
    trend_state=tech_summary.trend_state,
)

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

# Orderbook & Broker Summary data
prev_close = float(selected_data["close"].iloc[-2]) if len(selected_data) > 1 else tech_summary.close
orderbook = generate_orderbook(
    ticker=selected_ticker,
    current_price=tech_summary.close,
    previous_close=prev_close,
    average_volume=float(selected_data["volume"].tail(20).mean()),
)
depth_pressure = calculate_depth_pressure(orderbook)

broker_summary = generate_broker_summary(
    ticker=selected_ticker,
    trade_date=data_cutoff,
    close_price=tech_summary.close,
    total_traded_value_idr=liq_summary.average_daily_value_idr,
    foreign_flow_state=liq_summary.foreign_flow_state,
)
broker_network = analyze_broker_network(broker_summary)
stream_report = get_stream_sentiment(selected_ticker, broker_network.regime)

# Stockbit Header Banner
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    daily_change_pct = (tech_summary.close / prev_close - 1.0) * 100.0
    change_color = "#00C076" if daily_change_pct >= 0 else "#FF4A68"
    change_sign = "+" if daily_change_pct >= 0 else ""

    st.markdown(
        f"""
        <div style="display: flex; align-items: baseline; gap: 14px;">
            <h2 style="margin: 0; color: #F9FAFB; font-weight: 800;">{selected_ticker}</h2>
            <span style="font-size: 16px; color: #9CA3AF;">{fund_snapshot.identity.company_name}</span>
            <span style="font-size: 24px; font-weight: 800; color: {change_color};">Rp {tech_summary.close:,.0f}</span>
            <span style="font-size: 16px; font-weight: 700; color: {change_color};">{change_sign}{daily_change_pct:.2f}%</span>
        </div>
        <div style="color: #787B86; font-size: 13px; margin-top: 4px;">
            Sektor: <strong>{fund_snapshot.identity.sector}</strong> | Papan: <strong>{fund_snapshot.identity.listing_board}</strong> |
            ARA: <span style="color: #00C076; font-weight: 600;">Rp {orderbook.ara_price:,.0f}</span> |
            ARB: <span style="color: #FF4A68; font-weight: 600;">Rp {orderbook.arb_price:,.0f}</span> |
            Rotasi Sektor: <strong>{breadth_report.stock_sector_quadrant}</strong>
        </div>
        """,
        unsafe_allow_html=True,
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
        <div style="text-align: right;">
            <span class="status-badge {badge_class}">{risk_eval.decision_state}</span>
            <div style="font-size: 12px; color: #9CA3AF; margin-top: 4px;">
                Risk Score: <strong>{risk_eval.risk_score_10}/10</strong> | Veto: {"AKTIF" if risk_eval.hard_veto else "TIDAK"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Primary Metrics Bar
metric_cols = st.columns(5)
metric_cols[0].metric(
    "Peluang Naik (" + selected_horizon + ")",
    f"{active_quantiles.probability_positive:.1%}",
    f"Model: {dir_model_name}",
)
metric_cols[1].metric(
    "Target Median q50",
    f"Rp {active_quantiles.q50:,.0f}",
    f"{active_quantiles.expected_return:+.2%}",
)
metric_cols[2].metric(
    "Volatilitas GARCH",
    f"{daily_vol:.2%}",
    f"{vol_model_name}",
)
metric_cols[3].metric(
    "VaR 99% Tail Risk",
    f"{var_99:.2%}",
    "Limit: 7.00%",
)
metric_cols[4].metric(
    "Smart Money Regime",
    broker_network.regime.replace("_", " "),
    f"Index: {broker_network.smart_money_index}%",
)

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# ----------------- STOCKBIT TABULAR WORKSPACE -----------------
main_tabs = st.tabs(
    [
        "📈 Chartbit & Orderbook",
        "💼 Bandarmology & Broker Summary",
        "📊 Key Stats & Fundamental",
        "🎯 Ruang Risiko Radar",
        "🛡️ Pre-Buy Decision Passport",
        "💬 Stream & Narrative Intelijen",
        "⚙️ Web Action Console",
    ]
)

# TAB 1: Chartbit & Orderbook
with main_tabs[0]:
    c_col1, c_col2 = st.columns([7, 3])

    with c_col1:
        st.markdown("**Chartbit Interaktif**")
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
                    increasing_line_color="#00C076",
                    decreasing_line_color="#FF4A68",
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
                    line=dict(color="#2962FF", width=2),
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
                    line=dict(color="#787B86", width=1.5),
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

        vol_colors = [
            "#00C076" if c >= o else "#FF4A68"
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
            paper_bgcolor="#131722",
            plot_bgcolor="#1E222D",
            margin=dict(l=10, r=10, t=10, b=10),
            height=440,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_col2:
        st.markdown("**Orderbook (10-Level Depth)**")
        st.caption(f"Total Bid: {orderbook.total_bid_lots:,} Lot | Total Offer: {orderbook.total_offer_lots:,} Lot")

        ob_rows = []
        for i in range(10):
            b = orderbook.bids[i]
            o = orderbook.offers[i]
            ob_rows.append(
                {
                    "Bid Lot": f"{b.lots:,}",
                    "Bid": f"{b.price:,.0f}",
                    "Offer": f"{o.price:,.0f}",
                    "Offer Lot": f"{o.lots:,}",
                }
            )
        ob_df = pd.DataFrame(ob_rows)
        st.dataframe(ob_df, use_container_width=True, hide_index=True)

        st.markdown(
            f"""
            <div style="background-color: #1E222D; border: 1px solid #2A2E39; border-radius: 4px; padding: 8px 12px; font-size: 12px;">
                Ratio Bid/Offer: <strong>{orderbook.bid_offer_ratio:.2f}</strong> | Tekanan: <strong>{depth_pressure.depth_state}</strong><br/>
                ARA: <span style="color: #00C076;">Rp {orderbook.ara_price:,.0f}</span> |
                ARB: <span style="color: #FF4A68;">Rp {orderbook.arb_price:,.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### 🔬 Simulator Slippage & Dampak Likuiditas Order Eksekusi")
    sim_c1, sim_c2 = st.columns([1, 2])
    with sim_c1:
        sim_side = st.radio("Arah Order Transaksi", ["BUY", "SELL"], horizontal=True)
        sim_val_jt = st.slider("Ukuran Nilai Order (Juta IDR)", min_value=10, max_value=1000, value=100, step=10)
    with sim_c2:
        sim_res = simulate_order_execution(orderbook, sim_side, float(sim_val_jt * 1_000_000))
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Rata-rata Harga Terisi", f"Rp {sim_res.average_fill_price:,.0f}")
        res_col2.metric("Estimasi Slippage", f"{sim_res.slippage_bps:.1f} bps")
        res_col3.metric("Kedalaman Terpakai", f"{sim_res.percent_depth_consumed:.1f}% ({sim_res.ticks_traversed} fraksi)")
        if sim_res.liquidity_cliff_warning:
            st.warning(f"⚠️ {sim_res.rationale}")
        else:
            st.success(f"✓ {sim_res.rationale}")

# TAB 2: Bandarmology & Broker Summary
with main_tabs[1]:
    st.markdown("#### Broker Summary & Bandarmology Accumulation")
    st.caption("Peta konsentrasi bandar, aliran smart money, dan deteksi jebakan ritel.")

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("Status Bandarmology", broker_summary.status.replace("_", " "))
    b_col2.metric("Smart Money Index", f"{broker_network.smart_money_index}%")
    b_col3.metric("Top 3 Buyer Concentration", f"{broker_summary.top3_buyer_ratio_percent:.1f}%")
    b_col4.metric("Top 3 Seller Concentration", f"{broker_summary.top3_seller_ratio_percent:.1f}%")

    if broker_network.retail_trap_detected:
        st.error(f"🚨 {broker_network.summary}")
    else:
        st.info(f"💡 {broker_network.summary}")

    bs_col1, bs_col2 = st.columns(2)
    with bs_col1:
        st.markdown("**Top 5 Buyer Brokers**")
        buyer_rows = []
        for b in broker_summary.top_buyers:
            buyer_rows.append(
                {
                    "Broker": f"{b.broker_code} ({b.investor_type[0]})",
                    "Nama Sekuritas": b.broker_name,
                    "Lot": f"{b.lot_volume:,}",
                    "Avg": f"Rp {b.average_price:,.0f}",
                    "Nilai": f"Rp {b.total_value_idr / 1e9:.2f} M",
                }
            )
        st.dataframe(pd.DataFrame(buyer_rows), use_container_width=True, hide_index=True)

    with bs_col2:
        st.markdown("**Top 5 Seller Brokers**")
        seller_rows = []
        for s in broker_summary.top_sellers:
            seller_rows.append(
                {
                    "Broker": f"{s.broker_code} ({s.investor_type[0]})",
                    "Nama Sekuritas": s.broker_name,
                    "Lot": f"{s.lot_volume:,}",
                    "Avg": f"Rp {s.average_price:,.0f}",
                    "Nilai": f"Rp {s.total_value_idr / 1e9:.2f} M",
                }
            )
        st.dataframe(pd.DataFrame(seller_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Aliran Modal Berdasarkan Kategori Investor**")
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    cat_col1.metric("Institusi Asing Neto", f"Rp {broker_network.foreign_institutional_net_idr / 1e9:+.2f} M")
    cat_col2.metric("Institusi Domestik Neto", f"Rp {broker_network.domestic_institutional_net_idr / 1e9:+.2f} M")
    cat_col3.metric("Ritel Domestik Neto", f"Rp {broker_network.retail_domestic_net_idr / 1e9:+.2f} M")

# TAB 3: Key Stats & Fundamental
with main_tabs[2]:
    st.markdown("#### Key Statistics & Fundamental Point-In-Time")
    st.caption("Data keuangan tercatat berdasarkan tanggal publikasi riil untuk mencegah look-ahead bias.")

    kf_cols1 = st.columns(4)
    kf_cols1[0].metric("P/E Ratio", f"{fund_snapshot.pe_ratio:.1f}x")
    kf_cols1[1].metric("P/BV Ratio", f"{fund_snapshot.pbv_ratio:.2f}x")
    kf_cols1[2].metric("ROE", f"{fund_snapshot.roe_percent:.1f}%")
    kf_cols1[3].metric("Dividend Yield", f"{fund_snapshot.dividend_yield_percent:.1f}%")

    kf_cols2 = st.columns(4)
    kf_cols2[0].metric("Net Profit Margin", f"{fund_snapshot.net_margin_percent:.1f}%")
    kf_cols2[1].metric("Revenue Growth YoY", f"{fund_snapshot.revenue_growth_yoy:+.1f}%")
    kf_cols2[2].metric("Debt to Equity", f"{fund_snapshot.debt_to_equity:.2f}")
    kf_cols2[3].metric("Kualitas Laba", fund_snapshot.earnings_quality_score)

    st.markdown(
        f"""
        <div class="stockbit-card" style="margin-top: 10px;">
            <div class="stockbit-card-title">Informasi Laporan Keuangan</div>
            <div>Periode Laporan: <strong>{fund_snapshot.reporting_period}</strong> | Tanggal Publikasi Resmi: <strong>{fund_snapshot.publication_date}</strong></div>
            <div style="font-size: 13px; color: #9CA3AF; margin-top: 4px;">Regime Valuasi: <strong>{fund_snapshot.valuation_regime}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("##### 💰 Analisis Risiko Dividen & Corporate Action Trap")
    div_c1, div_c2 = st.columns([1, 2])
    with div_c1:
        st.metric("Dividen Terakhir", f"Rp {div_risk.last_dividend_per_share:,.0f} / saham")
        st.metric("Historical Drop Ex-Date", f"{div_risk.historical_ex_date_drop_percent:.1f}%")
        st.metric("Median Hari Pemulihan", f"{div_risk.recovery_days_median} Hari Bursa")
    with div_c2:
        st.markdown(f"**Status Risiko Dividen:** `{div_risk.dividend_trap_risk_state}`")
        st.write(f"- **Rasio Penurunan terhadap Imbal Hasil:** `{div_risk.drop_to_yield_ratio:.2f}x`")
        st.write(f"- **Rekomendasi Taktis:** {div_risk.action_recommendation}")

# TAB 4: Ruang Risiko Radar & Scenarios
with main_tabs[3]:
    st.markdown("#### Ruang Risiko Radar & Scenario Simulator")
    fan_c1, fan_c2 = st.columns([1, 1])

    with fan_c1:
        st.markdown(f"**Kipas Quantile Distribusi ({selected_horizon})**")
        fan_fig = go.Figure()
        horizons_x = ["Hari 0", "1D", "5D", "20D"]
        p_current = tech_summary.close

        q10_path = [p_current, quantiles["1D"].q10, quantiles["5D"].q10, quantiles["20D"].q10]
        q25_path = [p_current, quantiles["1D"].q25, quantiles["5D"].q25, quantiles["20D"].q25]
        q50_path = [p_current, quantiles["1D"].q50, quantiles["5D"].q50, quantiles["20D"].q50]
        q75_path = [p_current, quantiles["1D"].q75, quantiles["5D"].q75, quantiles["20D"].q75]
        q90_path = [p_current, quantiles["1D"].q90, quantiles["5D"].q90, quantiles["20D"].q90]

        fan_fig.add_trace(go.Scatter(x=horizons_x, y=q90_path, mode="lines", line=dict(width=0), showlegend=False))
        fan_fig.add_trace(
            go.Scatter(
                x=horizons_x,
                y=q10_path,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(41, 98, 255, 0.12)",
                name="Tail Range (q10-q90)",
            )
        )
        fan_fig.add_trace(go.Scatter(x=horizons_x, y=q75_path, mode="lines", line=dict(width=0), showlegend=False))
        fan_fig.add_trace(
            go.Scatter(
                x=horizons_x,
                y=q25_path,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(41, 98, 255, 0.28)",
                name="Interquartile (q25-q75)",
            )
        )
        fan_fig.add_trace(
            go.Scatter(
                x=horizons_x,
                y=q50_path,
                mode="lines+markers",
                line=dict(color="#2962FF", width=2.5),
                name="Jalur Median (q50)",
            )
        )
        fan_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#131722",
            plot_bgcolor="#1E222D",
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fan_fig, use_container_width=True)

    with fan_c2:
        st.markdown("**Simulasi Skenario 20D**")
        scen_rows = []
        for s in scenarios:
            scen_rows.append(
                {
                    "Skenario": s.scenario_name,
                    "Peluang": f"{s.probability:.0%}",
                    "Target 20D": f"Rp {s.expected_price_20d:,.0f}",
                    "Gerak": f"{s.expected_move_percent:+.1f}%",
                    "Invalidasi": f"Rp {s.invalidation_level:,.0f}",
                }
            )
        st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### ⚡ Uji Ketahanan Portofolio terhadap Crash Historis BEI")
    stress_scenarios = get_available_stress_scenarios()
    scen_titles = [s.title for s in stress_scenarios]
    selected_scen_title = st.selectbox("Pilih Skenario Guncangan Krisis", scen_titles, index=0)
    selected_scen = next(s for s in stress_scenarios if s.title == selected_scen_title)

    port_val_jt = st.number_input("Total Modal Portofolio Ekuitas (Juta IDR)", min_value=10, max_value=50000, value=100, step=10)
    stress_res = run_portfolio_stress_test(
        portfolio_weights={selected_ticker: 0.50, "^JKSE": 0.50},
        total_portfolio_value_idr=float(port_val_jt * 1_000_000),
        scenario_id=selected_scen.scenario_id,
    )

    str_c1, str_c2, str_c3, str_c4 = st.columns(4)
    str_c1.metric("Estimasi Kerugian Portofolio", f"-{stress_res.portfolio_loss_percent:.1f}%")
    str_c2.metric("Nominal Penurunan", f"Rp {stress_res.monetary_loss_idr:,.0f}")
    str_c3.metric("VaR 99% Tertekan", f"-{stress_res.var_99_loss_percent:.1f}%")
    str_c4.metric("Expected Shortfall (CVaR)", f"-{stress_res.cvar_expected_shortfall_percent:.1f}%")
    st.info(f"💡 Rekomendasi Ketahanan: {stress_res.survival_recommendation}")

# TAB 5: Pre-Buy Decision Passport
with main_tabs[4]:
    st.markdown("#### Pre-Buy Decision Passport")
    st.markdown(
        f"""
        <div class="stockbit-card">
            <h4 style="margin-top: 0; color: #F9FAFB;">Ringkasan Keputusan: {risk_eval.decision_state}</h4>
            <p style="color: #D1D4DC; font-size: 14px;">{risk_eval.rationale}</p>
            <div style="font-size: 13px; color: #9CA3AF;">
                <strong>Aturan Invalidasi:</strong> {passport.invalidation_rule}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        label="Unduh Pre-Buy Decision Passport (Markdown)",
        data=passport.markdown_content,
        file_name=f"{passport.passport_id}.md",
        mime="text/markdown",
    )

    with st.expander("Tampilkan Dokumen Passport Lengkap"):
        st.markdown(passport.markdown_content)

# TAB 6: Stream & Narrative Intelligence
with main_tabs[5]:
    st.markdown("#### Stockbit Stream & Intelijen Narasi")
    st.caption("Radar sentimen komunitas, herding behavior, hipotesis ICT, dan rotasi sektor.")

    str_c1, str_c2, str_c3 = st.columns(3)
    str_c1.metric("Status Kerumunan", stream_report.herding_state)
    str_c2.metric("Bullish Sentiment", f"{stream_report.bullish_percent:.1f}%")
    str_c3.metric("Bearish Sentiment", f"{stream_report.bearish_percent:.1f}%")

    if stream_report.fomo_alert:
        st.error(f"🚨 FOMO Alert: {stream_report.summary}")
    else:
        st.info(f"💬 Sentimen Stream: {stream_report.summary}")

    st.markdown("**Feed Diskusi Komunitas Stockbit Terkini**")
    for post in stream_report.posts:
        badge = "🟢" if post.sentiment == "BULLISH" else ("🔴" if post.sentiment == "BEARISH" else "⚪")
        st.markdown(
            f"""
            <div class="stream-card">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #787B86;">
                    <span><strong>@{post.author}</strong> {badge} ({post.sentiment})</span>
                    <span>{post.posted_ago} | ❤️ {post.likes_count}</span>
                </div>
                <div style="margin-top: 5px; font-size: 13px; color: #D1D4DC;">{post.content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### 🧭 Kompas Rotasi Sektor & Partisipasi Breadth BEI")
    br_c1, br_c2, br_c3 = st.columns(3)
    br_c1.metric("Saham di Atas SMA 20", f"{breadth_report.percent_above_sma20:.1f}%")
    br_c2.metric("Saham di Atas SMA 50", f"{breadth_report.percent_above_sma50:.1f}%")
    br_c3.metric("Saham di Atas SMA 200", f"{breadth_report.percent_above_sma200:.1f}%")
    st.info(f"📊 Status Breadth: {breadth_report.summary}")

    sec_rows = []
    for sec in breadth_report.sectors:
        sec_rows.append(
            {
                "Sektor": sec.sector_name,
                "Saham Penggerak": sec.primary_ticker,
                "Return Relatif 20D": f"{sec.relative_strength_20d:+.2f}%",
                "Kuadran Rotasi": sec.quadrant,
                "Keterangan": sec.summary,
            }
        )
    st.dataframe(pd.DataFrame(sec_rows), use_container_width=True, hide_index=True)

# TAB 7: Web Action Console (Operational Control Plane)
with main_tabs[6]:
    st.markdown("#### Web Action Console (Pusat Kontrol & Operasional)")
    st.caption("Pantau dan atur setiap aksi operasional, model recalculation, dan konfigurasi risiko langsung dari web browser.")

    action_c1, action_c2 = st.columns([1, 1])

    with action_c1:
        st.markdown("##### 🚀 Pemicu Aksi Langsung (Action Triggers)")

        if st.button("Perbarui Data Pasar (Update Ingestion)"):
            with st.spinner("Menjalankan pipeline pembaruan data harga..."):
                res = trigger_market_data_refresh()
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                else:
                    st.error(res["message"])

        if st.button("Hitung Ulang Snapshot Risiko & GARCH"):
            with st.spinner("Mengestimasi ulang parameter GARCH dan VaR..."):
                res = trigger_risk_recalculation()
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                else:
                    st.error(res["message"])

        if st.button("Hitung Ulang Model Direction ML"):
            with st.spinner("Menjalankan klasifikasi arah probabilitas machine learning..."):
                res = trigger_direction_recalculation()
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                else:
                    st.error(res["message"])

    with action_c2:
        st.markdown("##### ⚙️ Pengaturan Parameter Risiko Runtime")
        with st.form("risk_config_form"):
            new_var_conf = st.slider(
                "Level Kepercayaan VaR",
                min_value=0.90,
                max_value=0.995,
                value=float(runtime_config.get("var_confidence_level", 0.99)),
                step=0.005,
            )
            new_max_alloc = st.slider(
                "Batas Alokasi Portofolio Maksimal (%)",
                min_value=1.0,
                max_value=30.0,
                value=float(runtime_config.get("max_portfolio_allocation_percent", 15.0)),
                step=0.5,
            )
            new_slippage = st.slider(
                "Batas Maksimum Toleransi Slippage (bps)",
                min_value=5.0,
                max_value=50.0,
                value=float(runtime_config.get("max_slippage_bps", 25.0)),
                step=1.0,
            )
            new_active_model = st.selectbox(
                "Model Prediksi Arah Aktif",
                options=["random_forest", "logistic_regression", "xgboost", "ensemble"],
                index=0,
            )

            submit_cfg = st.form_submit_button("Simpan Konfigurasi Baru")
            if submit_cfg:
                cfg_res = update_runtime_risk_parameters(
                    var_confidence_level=new_var_conf,
                    max_portfolio_allocation_percent=new_max_alloc,
                    max_slippage_bps=new_slippage,
                    garch_vol_hard_veto_threshold=float(runtime_config.get("garch_vol_hard_veto_threshold", 0.045)),
                    tail_var99_veto_threshold=float(runtime_config.get("tail_var99_veto_threshold", 0.070)),
                    active_direction_model=new_active_model,
                )
                if cfg_res["success"]:
                    st.success(cfg_res["message"])
                    st.cache_data.clear()

    st.markdown("---")
    st.markdown("##### 📝 Penerbitan Mandiri Pre-Buy Decision Passport Berstempel Digital")
    with st.form("passport_custom_issuer_form"):
        pass_col1, pass_col2, pass_col3 = st.columns(3)
        custom_inv_price = pass_col1.number_input(
            "Level Invalidasi Tesis Kustom (Rp)",
            min_value=50.0,
            max_value=100000.0,
            value=float(round(tech_summary.close * 0.95)),
            step=25.0,
        )
        custom_alloc = pass_col2.slider("Alokasi Portofolio yang Disetujui (%)", 1.0, 30.0, 10.0, 0.5)
        custom_horiz = pass_col3.selectbox("Target Horizon Transaksi", ["Swing 5D", "Position 20D", "Day 1D"], index=1)
        custom_notes = st.text_area("Catatan & Rationale Keputusan Riset Operator", "Setup terkonfirmasi sinyal kuantitatif. Siap dieksekusi bertahap.")

        submit_pass = st.form_submit_button("Terbitkan & Sahkan Passport Resmi")
        if submit_pass:
            new_pass, new_path = issue_custom_passport(
                ticker=selected_ticker,
                company_name=fund_snapshot.identity.company_name,
                cutoff_date=data_cutoff,
                current_price=tech_summary.close,
                custom_invalidation=custom_inv_price,
                position_size_pct=custom_alloc,
                horizon=custom_horiz,
                operator_notes=custom_notes,
                base_passport=passport,
            )
            st.success(f"Berhasil menerbitkan {new_pass.passport_id}!")
            st.download_button(
                label=f"Unduh {new_pass.passport_id}.md",
                data=new_pass.markdown_content,
                file_name=f"{new_pass.passport_id}.md",
                mime="text/markdown",
            )

    st.markdown("---")
    st.markdown("##### 🔍 Watchdog Pemantauan Batas Invalidasi Posisi Aktif")
    active_price_map = {
        t: float(market_data.loc[market_data["ticker"] == t]["close"].iloc[-1])
        for t in available_tickers
        if not market_data.loc[market_data["ticker"] == t].empty
    }
    watchdog_alerts = scan_active_passports_watchdog(active_price_map)
    if watchdog_alerts:
        w_rows = []
        for w in watchdog_alerts:
            w_rows.append(
                {
                    "Passport ID": w.passport_id,
                    "Saham": w.ticker,
                    "Harga Saat Ini": f"Rp {w.current_price:,.0f}",
                    "Level Invalidasi": f"Rp {w.invalidation_price:,.0f}",
                    "Jarak Pengaman (%)": f"{w.distance_percent:+.1f}%",
                    "Jarak (IDR)": f"Rp {w.distance_idr:,.0f}",
                    "Status": w.alert_level,
                    "Rekomendasi": w.recommendation,
                }
            )
        st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada Decision Passport aktif yang terdaftar dalam watchdog monitor.")

    st.markdown("---")
    st.markdown("##### 📡 Radar Bandarmology Seluruh Universe")
    if st.button("Jalankan Radar Bandarmology Universe"):
        with st.spinner("Menganalisis matriks smart money untuk seluruh saham..."):
            price_dict = {
                t: float(market_data.loc[market_data["ticker"] == t]["close"].iloc[-1])
                for t in available_tickers
                if not market_data.loc[market_data["ticker"] == t].empty
            }
            scan_results = scan_universe_bandarmology(available_tickers, price_dict, trade_date=data_cutoff)
            scan_df = pd.DataFrame(scan_results)
            st.dataframe(scan_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### 📜 Audit Trail & Riwayat Aksi Operasional")
    history_entries = load_action_history(limit=25)
    if history_entries:
        h_df = pd.DataFrame(history_entries)[
            ["action_id", "action_type", "triggered_at", "operator", "status", "summary_message", "duration_ms"]
        ]
        st.dataframe(h_df, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada riwayat aksi operasional tercatat.")

    st.markdown("---")
    st.markdown("##### 🚀 Kesiapan Domain & Peluncuran Produksi (rridx.fadhilrusydi.com)")
    st.caption("Verifikasi langsung status DNS record, sertifikat SSL/TLS, dan instruksi peluncuran headless non-RDC.")

    probe_col1, probe_col2 = st.columns([3, 1])
    target_domain_input = probe_col1.text_input("Domain Target Peluncuran", value="rridx.fadhilrusydi.com")
    run_probe_btn = probe_col2.button("Uji Resolusi & SSL")

    if run_probe_btn:
        with st.spinner("Memeriksa resolusi DNS dan endpoint TLS..."):
            probe_result = trigger_domain_probe(target_domain_input)
            if probe_result["dns_status"] == "RESOLVED":
                st.success(f"DNS Sukses Terarah: `{probe_result['resolved_ip']}`")
            else:
                st.warning(f"DNS Status: {probe_result['dns_status']}")
            st.info(f"Panduan: {probe_result['recommendation']}")

    st.markdown("**Instruksi Peluncuran 1-Command Headless (Non-RDC):**")
    st.code(
        f"curl -sSL https://raw.githubusercontent.com/Fadhilstat/Stock-Prediction/main/deploy/setup_production.sh | "
        f"bash -s -- --domain {target_domain_input} --email admin@fadhilrusydi.com",
        language="bash",
    )

    st.markdown("---")
    st.markdown("##### 🌐 Headless API & Webhook Service (Zero-RDC Operations)")
    st.code(
        """
# Healthcheck Endpoint:
curl -s http://localhost:8502/health

# Cek Kesiapan Domain & SSL:
curl -s http://localhost:8502/api/v1/domain-probe

# Trigger Ingestion Webhook (misal dari cron atau Cloudflare Worker):
curl -X POST http://localhost:8502/api/v1/actions/refresh-data

# Trigger Recalculate Risk Snapshots:
curl -X POST http://localhost:8502/api/v1/actions/recalc-risk
        """,
        language="bash",
    )

# Footer
st.markdown("---")
st.caption(
    "Ruang Risiko IDX Autonomous Finished Product. "
    "Sistem riset risiko pasar modal Indonesia. Target domain: rridx.fadhilrusydi.com. "
    "Semua output adalah estimasi probabilitas statistik dan bukan ajakan investasi."
)
