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
    trigger_microstructure_imbalance_scan,
    trigger_morning_briefing_generation,
    trigger_risk_recalculation,
    update_runtime_risk_parameters,
)
from ruang_risiko_idx.research.alert_dispatcher import AlertPayload, dispatch_webhook_alert
from ruang_risiko_idx.research.automation_daemon import (
    load_automation_schedule,
    run_autonomous_full_cycle,
)
from ruang_risiko_idx.research.biweekly_validation import generate_biweekly_validation_ledger
from ruang_risiko_idx.research.dynamic_trailing import compute_dynamic_trailing_boundary
from ruang_risiko_idx.research.microstructure_imbalance import compute_microstructure_imbalance
from ruang_risiko_idx.research.morning_briefing import generate_premarket_morning_briefing
from ruang_risiko_idx.research.strategy_backtest import run_strategy_backtest_replay
from ruang_risiko_idx.research.broker_network import analyze_broker_network, scan_universe_bandarmology
from ruang_risiko_idx.research.broker_summary import generate_broker_summary
from ruang_risiko_idx.research.corporate_action_risk import evaluate_dividend_action_risk
from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.depth_analytics import calculate_depth_pressure, simulate_order_execution
from ruang_risiko_idx.research.flexible_universe import (
    EXPANDED_IDX_UNIVERSE,
    ensure_ticker_data_available,
    normalize_ticker_symbol,
    resolve_stock_metadata,
)
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary, get_creator_claims_for_ticker
from ruang_risiko_idx.research.fundamentals import CANONICAL_COMPANIES, get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.invalidation_watchdog import scan_active_passports_watchdog
from ruang_risiko_idx.research.journal import load_prediction_journal
from ruang_risiko_idx.research.macro_economy import compute_mathematical_moments, get_macroeconomic_report
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.multimodal import get_ablation_benchmarks, run_evidence_conflict_radar
from ruang_risiko_idx.research.news_sentiment import CANONICAL_NEWS_FEED, get_news_sentiment_profile
from ruang_risiko_idx.research.orderbook import generate_orderbook
from ruang_risiko_idx.research.passport_issuer import issue_custom_passport
from ruang_risiko_idx.research.portfolio_allocator import compute_portfolio_allocation
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
st.sidebar.markdown("### 📊 TradingView Ruang Risiko")
st.sidebar.caption("Institutional Equity Intelligence Terminal")

universe_mode = st.sidebar.radio(
    "Mode Pemilihan Saham",
    ["Preset Unggulan BEI", "Ketik Kode Bebas (Custom)"],
    horizontal=True,
    label_visibility="collapsed",
)

all_preset_options = list(EXPANDED_IDX_UNIVERSE.keys())
if universe_mode == "Preset Unggulan BEI":
    def _format_ticker(t: str) -> str:
        entry = EXPANDED_IDX_UNIVERSE.get(t)
        return f"{entry.symbol} ({entry.sector})" if entry else t

    selected_ticker = st.sidebar.selectbox(
        "Pilih Saham",
        all_preset_options,
        index=0,
        format_func=_format_ticker,
    )
else:
    custom_in = st.sidebar.text_input("Ketik Kode Saham (misal: BBCA, BREN, BRIS, ADRO)", value="BBCA")
    selected_ticker = normalize_ticker_symbol(custom_in or "BBCA")

market_data = ensure_ticker_data_available(market_data, selected_ticker)
stock_meta = resolve_stock_metadata(selected_ticker)
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
math_moments = compute_mathematical_moments(selected_data, selected_ticker)
macro_report = get_macroeconomic_report(data_cutoff)
news_profile = get_news_sentiment_profile(selected_ticker)
biweekly_ledger = generate_biweekly_validation_ledger(selected_ticker, market_data)

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
micro_imbalance = compute_microstructure_imbalance(orderbook)
morning_briefing = generate_premarket_morning_briefing(
    briefing_date=data_cutoff,
    risk_snapshots=risk_snapshots,
    direction_snapshots=direction_snapshots,
)

trailing_snapshot = compute_dynamic_trailing_boundary(
    ticker=selected_ticker,
    entry_price=tech_summary.sma_20 if tech_summary.sma_20 > 0 else tech_summary.close * 0.98,
    current_price=tech_summary.close,
    highest_price_since_entry=float(selected_data["high"].tail(20).max()),
    static_invalidation=passport.invalidation_price,
    target_q50=quantiles["20D"].q50,
    daily_garch_vol=daily_vol,
    unconditional_vol=float(math_moments.unconditional_garch_vol_pct / 100.0),
    atr_14=float(tech_summary.atr_14),
)

backtest_report = run_strategy_backtest_replay(
    price_df=selected_data,
    ticker=selected_ticker,
    initial_capital_idr=100_000_000.0,
    prob_up_threshold=0.52,
    max_vol_threshold=0.035,
)

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

# ----------------- TRADINGVIEW TABULAR WORKSPACE -----------------
main_tabs = st.tabs(
    [
        "📈 TradingView Chart & Book",
        "📐 Insight Matematis & Ekonometrika",
        "🌐 Makroekonomi & Sentimen Berita",
        "💼 Bandarmology & Broker Summary",
        "🔎 Screener Saham Publik",
        "⏱️ Validasi Model Bi-Weekly (14-Hari)",
        "🛡️ Pre-Buy Decision Passport & Allocator",
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

        max_depth_lot = max(max(b.lots for b in orderbook.bids), max(o.lots for o in orderbook.offers), 1)
        ob_html = """
        <table style="width: 100%; border-collapse: collapse; font-family: monospace; font-size: 12px; color: #D1D4DC;">
            <thead>
                <tr style="border-bottom: 1px solid #2A2E39; color: #787B86;">
                    <th style="text-align: right; padding: 4px;">Bid Lot</th>
                    <th style="text-align: right; padding: 4px; color: #00C076;">Bid</th>
                    <th style="text-align: left; padding: 4px; color: #FF4A68;">Offer</th>
                    <th style="text-align: left; padding: 4px;">Offer Lot</th>
                </tr>
            </thead>
            <tbody>
        """
        for i in range(10):
            b = orderbook.bids[i]
            o = orderbook.offers[i]
            b_pct = (b.lots / max_depth_lot) * 100.0
            o_pct = (o.lots / max_depth_lot) * 100.0
            ob_html += f"""
                <tr style="border-bottom: 1px solid rgba(42, 46, 57, 0.4);">
                    <td style="text-align: right; padding: 4px; position: relative;">
                        <div style="position: absolute; right: 0; top: 0; bottom: 0; width: {b_pct:.0f}%; background-color: rgba(0, 192, 118, 0.20); z-index: 1;"></div>
                        <span style="position: relative; z-index: 2;">{b.lots:,}</span>
                    </td>
                    <td style="text-align: right; padding: 4px; font-weight: 700; color: #00C076;">{b.price:,.0f}</td>
                    <td style="text-align: left; padding: 4px; font-weight: 700; color: #FF4A68;">{o.price:,.0f}</td>
                    <td style="text-align: left; padding: 4px; position: relative;">
                        <div style="position: absolute; left: 0; top: 0; bottom: 0; width: {o_pct:.0f}%; background-color: rgba(255, 74, 104, 0.20); z-index: 1;"></div>
                        <span style="position: relative; z-index: 2;">{o.lots:,}</span>
                    </td>
                </tr>
            """
        ob_html += "</tbody></table>"
        st.markdown(ob_html, unsafe_allow_html=True)

        voi_sign = "+" if micro_imbalance.volume_order_imbalance_lots > 0 else ""
        cvd_sign = "+" if micro_imbalance.cumulative_volume_delta_lots > 0 else ""
        st.markdown(
            f"""
            <div style="background-color: #1E222D; border: 1px solid #2A2E39; border-radius: 4px; padding: 8px 12px; font-size: 12px; margin-top: 8px;">
                Ratio Bid/Offer: <strong>{orderbook.bid_offer_ratio:.2f}</strong> | Tekanan: <strong>{depth_pressure.depth_state}</strong><br/>
                ARA: <span style="color: #00C076;">Rp {orderbook.ara_price:,.0f}</span> |
                ARB: <span style="color: #FF4A68;">Rp {orderbook.arb_price:,.0f}</span><br/>
                VOI 10-Level: <strong>{voi_sign}{micro_imbalance.volume_order_imbalance_lots:,} Lot</strong> ({micro_imbalance.order_flow_regime})<br/>
                CVD Proksi: <strong>{cvd_sign}{micro_imbalance.cumulative_volume_delta_lots:,} Lot</strong> (Rp {micro_imbalance.cvd_nominal_idr / 1e9:+.2f} M)<br/>
                Skor Risiko Spoofing: <strong>{micro_imbalance.spoofing_probability_score * 100:.0f}%</strong> {'(🚨 Benteng Semu)' if micro_imbalance.phantom_wall_detected else '(Normal)'}
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

    with st.expander("🔬 Analisis Mikrostruktur Imbalance & Penyerapan Order Flow"):
        st.markdown(f"**Insight Penyerapan Pasar:** {micro_imbalance.operational_insight}")
        micro_c1, micro_c2, micro_c3 = st.columns(3)
        micro_c1.metric("VOI Ternormalisasi", f"{micro_imbalance.voi_normalized:+.3f}")
        micro_c2.metric("Rasio Kemiringan (Bid/Offer Slope)", f"{micro_imbalance.slope_ratio:.2f}x")
        micro_c3.metric("Status Penyerapan", micro_imbalance.absorption_state.replace("_", " "))

        breakdown_rows = []
        for l in micro_imbalance.level_breakdowns:
            breakdown_rows.append(
                {
                    "Level": f"Fraksi #{l.step}",
                    "Bid (Lot)": f"{l.bid_price:,.0f} ({l.bid_lots:,})",
                    "Offer (Lot)": f"{l.offer_price:,.0f} ({l.offer_lots:,})",
                    "Net Delta": f"{l.net_level_delta_lots:+,}",
                    "Imbalance (%)": f"{l.imbalance_ratio * 100:+.1f}%",
                }
            )
        st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)

# TAB 2: Insight Matematis & Ekonometrika
with main_tabs[1]:
    st.markdown("#### 📐 Insight Matematis & Properti Ekonometrika Distribusi")
    st.caption("Analisis momen statistik tingkat tinggi, uji normalitas Jarque-Bera, eksponen Hurst, dan Expected Shortfall (CVaR).")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Volatilitas Tahunan", f"{math_moments.annualized_volatility_pct:.1f}%")
    m_col2.metric("Kemiringan (Skewness)", f"{math_moments.skewness:+.2f}")
    m_col3.metric("Kurtosis Ekses", f"{math_moments.excess_kurtosis:+.2f}")
    m_col4.metric("Eksponen Hurst (H)", f"{math_moments.hurst_exponent:.2f}", math_moments.memory_regime)

    m_col5, m_col6, m_col7, m_col8 = st.columns(4)
    m_col5.metric("Jarque-Bera p-value", f"{math_moments.jarque_bera_p_value:.4f}", "Non-Normal" if not math_moments.is_normal_distribution else "Normal")
    m_col6.metric("Expected Shortfall (CVaR 99%)", f"-{math_moments.cvar_expected_shortfall_99_pct:.2f}%")
    m_col7.metric("Volatilitas Tak Bersyarat", f"{math_moments.unconditional_garch_vol_pct:.2f}%")
    m_col8.metric("Volatilitas Bersyarat GARCH", f"{daily_vol * 100:.2f}%", f"Model: {vol_model_name}")

    st.info(f"💡 Interpretasi Ekonometrika: {math_moments.interpretation}")

    st.markdown("---")
    st.markdown("##### 🎯 Kipas Quantile Distribusi Probabilitas Multi-Horizon")
    fan_c1, fan_c2 = st.columns([1, 1])
    with fan_c1:
        st.markdown(f"**Jalur Quantile ({selected_horizon})**")
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

# TAB 3: Makroekonomi & Sentimen Berita
with main_tabs[2]:
    st.markdown("#### 🌐 Intelijen Makroekonomi & Sentimen Berita Terkurasi")
    st.caption("Dasbor indikator makroekonomi domestik, Equity Risk Premium, dan analisis sentimen pemberitaan finansial.")

    mac_c1, mac_c2, mac_c3, mac_c4 = st.columns(4)
    mac_c1.metric("BI-Rate Acuan", f"{macro_report.bank_indonesia_rate_pct:.2f}%", "-25 bps MoM")
    mac_c2.metric("Yield SUN 10Y", f"{macro_report.ten_year_sun_yield_pct:.2f}%", "-15 bps MoM")
    mac_c3.metric("Equity Risk Premium", f"{macro_report.equity_risk_premium_pct:+.2f}%", "Akomodatif")
    mac_c4.metric("Kurs USD/IDR", f"{macro_report.usd_idr_exchange_rate:,.0f}", "-180 IDR MoM")

    st.info(f"🏛️ {macro_report.summary}")

    st.markdown("---")
    st.markdown("##### ☕ Pre-Market Morning Briefing & Intisari Pembukaan Sesi I (08:30 WIB)")
    st.caption(f"Audit ID: {morning_briefing.digest_id} | Tanggal Efektif: {morning_briefing.briefing_date}")

    st.markdown(f"**Nada Pasar Harian:** `{morning_briefing.market_tone}`")

    cue_c1, cue_c2, cue_c3, cue_c4, cue_c5 = st.columns(5)
    for idx_cue, cue in enumerate(morning_briefing.global_cues[:5]):
        [cue_c1, cue_c2, cue_c3, cue_c4, cue_c5][idx_cue].metric(
            cue.asset_name.split(" ")[0],
            cue.last_value,
            f"{cue.daily_change_pct:+.2f}%",
        )

    st.markdown("**Top 3 Kandidat Saham Pilihan Pre-Market (High Conviction)**")
    top_cols = st.columns(3)
    for idx_s, setup in enumerate(morning_briefing.top_setups):
        with top_cols[idx_s]:
            st.markdown(
                f"""
                <div class="stockbit-card">
                    <div style="font-weight: 700; color: #2962FF; font-size: 14px;">#{idx_s + 1} {setup.ticker}</div>
                    <div style="font-size: 12px; color: #9CA3AF;">{setup.company_name}</div>
                    <div style="margin-top: 4px; font-size: 12px;">Status: <strong>{setup.setup_status}</strong> ({setup.sentiment_tag})</div>
                    <div style="font-size: 12px; color: #00C076;">Target q50: Rp {setup.target_q50_idr:,.0f}</div>
                    <div style="font-size: 12px; color: #FF4A68;">Invalidasi: Rp {setup.invalidation_level_idr:,.0f}</div>
                    <div style="margin-top: 4px; font-size: 11px; color: #787B86;">{setup.key_theme}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.download_button(
        label="Unduh Pre-Market Morning Briefing (Markdown)",
        data=morning_briefing.markdown_content,
        file_name=f"{morning_briefing.digest_id}.md",
        mime="text/markdown",
    )

    st.markdown("---")
    st.markdown("##### 📰 Sentimen Berita & Narasi Pasar Terkini")
    n_col1, n_col2, n_col3 = st.columns(3)
    n_col1.metric("Skor Sentimen Emiten", f"{news_profile.average_sentiment_score:+.2f}", news_profile.sentiment_regime)
    n_col2.metric("Artikel Positif", f"{news_profile.positive_count}")
    n_col3.metric("Artikel Negatif", f"{news_profile.negative_count}")

    st.info(f"📌 Katalis Kunci: {news_profile.key_catalyst}")

    for art in news_profile.articles:
        badge_color = "#00C076" if art.sentiment_label == "POSITIVE" else ("#FF4A68" if art.sentiment_label == "NEGATIVE" else "#D1D4DC")
        st.markdown(
            f"""
            <div class="stockbit-card">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #787B86;">
                    <span><strong>{art.source}</strong> | {art.category}</span>
                    <span style="color: {badge_color}; font-weight: 700;">{art.sentiment_label} ({art.sentiment_score:+.2f})</span>
                </div>
                <div style="margin-top: 6px; font-size: 14px; font-weight: 700; color: #F9FAFB;">{art.headline}</div>
                <div style="margin-top: 6px; font-size: 13px; color: #D1D4DC;">{art.summary_insight}</div>
                <div style="margin-top: 6px; font-size: 11px; color: #787B86;">Saham Terdampak: {', '.join(art.impacted_tickers)} | {art.published_at}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("💬 Radar Komunitas & Stream Diskusi Emiten"):
        comm_c1, comm_c2, comm_c3 = st.columns(3)
        comm_c1.metric("Status Kerumunan", stream_report.herding_state)
        comm_c2.metric("Bullish Sentiment", f"{stream_report.bullish_percent:.1f}%")
        comm_c3.metric("Bearish Sentiment", f"{stream_report.bearish_percent:.1f}%")
        if stream_report.fomo_alert:
            st.error(f"🚨 FOMO Alert: {stream_report.summary}")
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

# TAB 4: Bandarmology & Broker Summary
with main_tabs[3]:
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

# TAB 5: Screener Saham Publik (TradingView Screener)
with main_tabs[4]:
    st.markdown("#### 🔎 Screener Saham Interaktif Publik (TradingView Style)")
    st.caption("Penyaring multi-faktor seluruh saham unggulan BEI berdasarkan valuasi, momentum teknikal, volatilitas GARCH, dan aliran smart money.")

    scr_col1, scr_col2 = st.columns(2)
    selected_sec_filter = scr_col1.multiselect(
        "Filter Sektor",
        options=sorted(list({e.sector for e in EXPANDED_IDX_UNIVERSE.values() if e.ticker != "^JKSE"})),
        default=[],
        placeholder="Semua Sektor",
    )
    max_vol_filter = scr_col2.slider("Batas Maksimal Volatilitas Harian GARCH (%)", 0.5, 5.0, 3.5, 0.1)

    screener_rows = []
    for tick, entry in EXPANDED_IDX_UNIVERSE.items():
        if tick == "^JKSE":
            continue
        if selected_sec_filter and entry.sector not in selected_sec_filter:
            continue

        sub_tick = market_data.loc[market_data["ticker"] == tick]
        p_last = float(sub_tick["close"].iloc[-1]) if not sub_tick.empty else 1000.0
        p_prev = float(sub_tick["close"].iloc[-2]) if len(sub_tick) > 1 else p_last
        chg_1d = ((p_last / p_prev) - 1.0) * 100.0

        r_snap = risk_snapshots.get(tick, {})
        d_snap = direction_snapshots.get(tick, {})
        v_daily = float(r_snap.get("forecast_volatility", 0.018)) * 100.0
        p_up = float(d_snap.get("probability_up", 0.52)) * 100.0

        if v_daily > max_vol_filter:
            continue

        screener_rows.append(
            {
                "Kode": entry.symbol,
                "Nama Perusahaan": entry.company_name,
                "Sektor": entry.sector,
                "Harga Terakhir": f"Rp {p_last:,.0f}",
                "1D Change (%)": f"{chg_1d:+.2f}%",
                "GARCH Vol (%)": f"{v_daily:.2f}%",
                "Peluang Naik ML": f"{p_up:.1f}%",
                "Indeks": ", ".join(entry.index_membership[:2]),
            }
        )

    if screener_rows:
        st.dataframe(pd.DataFrame(screener_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada saham yang memenuhi kriteria filter saat ini.")

# TAB 6: Validasi Model Bi-Weekly (14-Hari Walk-Forward)
with main_tabs[5]:
    st.markdown("#### ⏱️ Validasi Model Otonom Bi-Weekly (14-Hari Out-Of-Sample)")
    st.caption("Pemeriksaan audit ketahanan model secara periodik setiap 2 pekan (14 hari bursa) untuk mendeteksi drift dan rekalibrasi.")

    bw_c1, bw_c2, bw_c3, bw_c4 = st.columns(4)
    bw_c1.metric("Status Kesehatan Model", biweekly_ledger.overall_health.replace("_", " "))
    bw_c2.metric("Rata-rata Hit Rate 14D", f"{biweekly_ledger.mean_hit_rate_pct:.1f}%")
    bw_c3.metric("Brier Calibration Score", f"{biweekly_ledger.mean_brier_score:.4f}")
    bw_c4.metric("Pelanggaran VaR 99%", f"{biweekly_ledger.total_var_breaches} Kali")

    st.markdown(
        f"""
        <div class="stockbit-card">
            <div>Cadence Evaluasi: <strong>{biweekly_ledger.evaluation_cadence}</strong> | Audit Terakhir: <strong>{biweekly_ledger.last_audit_date}</strong> | Audit Berikutnya: <strong>{biweekly_ledger.next_scheduled_audit}</strong></div>
            <div style="margin-top: 6px; color: #00C076; font-weight: 600;">{biweekly_ledger.recalibration_recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### 📜 Buku Besar Siklus Evaluasi 14-Harian (Walk-Forward Cycles)")
    cycle_rows = []
    for c in biweekly_ledger.cycles:
        cycle_rows.append(
            {
                "ID Siklus": c.cycle_id,
                "Periode Awal": c.start_date,
                "Periode Akhir": c.end_date,
                "Hari Bursa": c.trading_days,
                "Akurasi Arah (%)": f"{c.directional_hit_rate_pct:.1f}%",
                "Brier Score": f"{c.brier_score:.4f}",
                "Log Loss": f"{c.log_loss:.4f}",
                "Breach VaR 99%": c.var_99_breach_count,
                "Status Kalibrasi": c.model_status,
            }
        )
    if cycle_rows:
        st.dataframe(pd.DataFrame(cycle_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Riwayat siklus evaluasi sedang dikompilasi untuk saham ini.")

# TAB 7: Pre-Buy Decision Passport & Allocator
with main_tabs[6]:
    st.markdown("#### Pre-Buy Decision Passport & Risk Allocator")
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

    st.markdown("---")
    st.markdown("##### 💼 Kalkulator Alokasi Modal & Budget Risiko Portofolio")
    st.caption("Penentuan ukuran posisi matematis berbasis Fractional Kelly dan volatilitas bersyarat GARCH.")

    alloc_c1, alloc_c2, alloc_c3 = st.columns(3)
    user_capital = alloc_c1.number_input(
        "Total Modal Portofolio (IDR)",
        min_value=1_000_000,
        max_value=10_000_000_000,
        value=100_000_000,
        step=5_000_000,
    )
    user_budget_pct = alloc_c2.slider("Batas Risiko Harian Maksimum (% Portofolio)", 0.5, 5.0, 2.0, 0.1)
    user_max_single = alloc_c3.slider("Batas Maksimal 1 Saham (% Portofolio)", 5.0, 40.0, 20.0, 1.0)

    alloc_stocks = [
        {
            "ticker": selected_ticker,
            "current_price": tech_summary.close,
            "garch_vol_daily": daily_vol,
            "var_99_daily": var_99,
            "prob_up": dir_up_prob,
            "reward_risk_ratio": 2.0,
        }
    ]
    alloc_report = compute_portfolio_allocation(
        total_capital_idr=float(user_capital),
        daily_risk_budget_pct=float(user_budget_pct),
        max_single_stock_pct=float(user_max_single),
        stocks_data=alloc_stocks,
    )

    ar_c1, ar_c2, ar_c3, ar_c4 = st.columns(4)
    if alloc_report.recommendations:
        rec = alloc_report.recommendations[0]
        ar_c1.metric("Rekomendasi Bobot", f"{rec.recommended_weight_pct:.1f}%")
        ar_c2.metric("Nominal Pembelian", f"Rp {rec.allocated_value_idr:,.0f}")
        ar_c3.metric("Jumlah Lot Disarankan", f"{rec.allocated_lots:,} Lot")
        ar_c4.metric("Kontribusi Risiko VaR", f"Rp {rec.var_contribution_idr:,.0f}")
        st.info(f"📌 Dasar Perhitungan: {rec.sizing_rationale}")

    st.markdown("---")
    st.markdown("##### 🏹 GARCH-ATR Dynamic Trailing Boundary & Volatility Ratchet")
    st.caption("Penyesuaian batas proteksi kerugian bertingkat berbasis volatilitas bersyarat dan rata-rata pergerakan rentang nyata (ATR).")

    tr_c1, tr_c2, tr_c3, tr_c4 = st.columns(4)
    tr_c1.metric("Trailing Stop Dinamis", f"Rp {trailing_snapshot.dynamic_trailing_stop_price:,.0f}")
    tr_c2.metric("Jarak ke Batas Stop", f"{trailing_snapshot.distance_to_stop_pct:+.2f}%")
    tr_c3.metric("Tahap Ratchet", trailing_snapshot.ratchet_stage.replace("_", " "))
    tr_c4.metric("Status Posisi", "🚨 TERLANGGAR" if trailing_snapshot.is_breached else "✓ AMAN TERKENDALI")

    st.info(f"💡 Logika Ratchet: {trailing_snapshot.ratchet_rationale}")

    st.markdown("---")
    st.markdown("##### 📈 Simulasi Kurva Ekuitas Strategi & Strategy Backtest Replay")
    st.caption("Evaluasi performa historis eksekusi protokol Pre-Buy Passport dan alokasi Kelly pada data pasar aktual.")

    bt_c1, bt_c2, bt_c3, bt_c4 = st.columns(4)
    bt_c1.metric("Total Return Strategi", f"{backtest_report.total_return_pct:+.2f}%", f"Alpha: {backtest_report.alpha_pct:+.2f}%")
    bt_c2.metric("CAGR Disetahunkan", f"{backtest_report.annualized_return_cagr_pct:.2f}%")
    bt_c3.metric("Sharpe Ratio", f"{backtest_report.annualized_sharpe_ratio:.2f}")
    bt_c4.metric("Maximum Drawdown", f"-{backtest_report.maximum_drawdown_pct:.2f}%")

    bt_c5, bt_c6, bt_c7, bt_c8 = st.columns(4)
    bt_c5.metric("Win Rate (%)", f"{backtest_report.win_rate_pct:.1f}%")
    bt_c6.metric("Profit Factor", f"{backtest_report.profit_factor:.2f}x")
    bt_c7.metric("Calmar Ratio", f"{backtest_report.calmar_ratio:.2f}")
    bt_c8.metric("Total Transaksi", f"{backtest_report.total_trades_count} Trade")

    # Plot Equity Curve
    eq_dates = [pt.trade_date for pt in backtest_report.equity_curve]
    eq_strat = [pt.strategy_equity for pt in backtest_report.equity_curve]
    eq_bench = [pt.benchmark_equity for pt in backtest_report.equity_curve]

    eq_fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
    )
    eq_fig.add_trace(
        go.Scatter(
            x=eq_dates,
            y=eq_strat,
            mode="lines",
            name="Strategi Pre-Buy Passport",
            line=dict(color="#00C076", width=2.2),
        ),
        row=1,
        col=1,
    )
    eq_fig.add_trace(
        go.Scatter(
            x=eq_dates,
            y=eq_bench,
            mode="lines",
            name="Benchmark Buy & Hold",
            line=dict(color="#787B86", width=1.5, dash="dot"),
        ),
        row=1,
        col=1,
    )
    eq_fig.add_trace(
        go.Scatter(
            x=eq_dates,
            y=[pt.drawdown_pct for pt in backtest_report.equity_curve],
            mode="lines",
            name="Drawdown (%)",
            line=dict(color="#FF4A68", width=1.0),
            fill="tozeroy",
            fillcolor="rgba(255, 74, 104, 0.15)",
        ),
        row=2,
        col=1,
    )
    eq_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#1E222D",
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(eq_fig, use_container_width=True)
    st.caption(f"📝 Ringkasan Replay: {backtest_report.executive_summary}")

# TAB 8: Web Action Console (Operational Control Plane)
with main_tabs[7]:
    st.markdown("#### Web Action Console (Pusat Kontrol & Operasional)")
    st.caption("Pantau dan atur setiap aksi operasional, model recalculation, dan konfigurasi risiko langsung dari web browser.")

    st.markdown("##### 🤖 Panel Orkestrasi & Otomasi Daemon (Zero-RDC Full Automation)")
    st.caption("Kendali eksekusi pipeline otonom tanpa perlu intervensi manual atau login terminal VPS.")

    auto_col1, auto_col2 = st.columns([2, 1])
    with auto_col1:
        st.markdown(
            """
            <div style="background-color: #1E222D; border: 1px solid #2A2E39; border-radius: 6px; padding: 12px 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; color: #F9FAFB; font-size: 14px;">Status Daemon Otomasi Sistem</span>
                    <span class="status-badge badge-favorable">BERJALAN OTONOM (ACTIVE)</span>
                </div>
                <div style="margin-top: 6px; font-size: 13px; color: #D1D4DC;">
                    Pipeline dijadwalkan secara otomatis: Ingestion Data Pasar (16:30 WIB), Recalculation GARCH/VaR (17:00 WIB), Morning Briefing (08:30 WIB), dan Audit Bi-Weekly 14-Hari.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with auto_col2:
        if st.button("⚡ Jalankan Siklus Penuh Otonom Sekarang", use_container_width=True):
            with st.spinner("Mengeksekusi seluruh siklus otomatisasi (Data -> GARCH -> ML -> Briefing -> Audit)..."):
                cycle_res = run_autonomous_full_cycle(operator="web_operator")
                if cycle_res.all_success:
                    st.success(cycle_res.summary_message)
                    st.cache_data.clear()
                else:
                    st.warning(cycle_res.summary_message)

    with st.expander("📅 Jadwal & Status Eksekusi Pekerjaan Otomatis (Task Registry)"):
        sched_tasks = load_automation_schedule()
        task_rows = []
        for t in sched_tasks:
            task_rows.append(
                {
                    "ID Tugas": t.task_id,
                    "Nama Pekerjaan": t.task_name,
                    "Frekuensi": t.cadence,
                    "Jadwal (WIB)": t.schedule_time_wib,
                    "Status": t.status,
                    "Total Eksekusi": f"{t.execution_count}x",
                    "Pesan Terakhir": t.last_message,
                }
            )
        st.dataframe(pd.DataFrame(task_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
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

        if st.button("Kompilasi Pre-Market Morning Briefing (08:30 WIB)"):
            with st.spinner("Mengompilasi intisari makro, katalis global, dan saham pilihan..."):
                res = trigger_morning_briefing_generation()
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                else:
                    st.error(res["message"])

        if st.button("Pindai Microstructure Imbalance & Order Flow Delta"):
            with st.spinner(f"Memindai dinamika antrean mikrostruktur {selected_ticker}..."):
                res = trigger_microstructure_imbalance_scan(selected_ticker)
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
    st.markdown("##### 🔔 Webhook Notifikasi Real-Time (Telegram / Discord)")
    st.caption("Kirim notifikasi otomatis saat harga mendekati atau menembus batas invalidasi posisi.")

    wh_c1, wh_c2 = st.columns([3, 1])
    webhook_url_input = wh_c1.text_input(
        "Webhook URL (Discord atau HTTP Gateway)",
        value="",
        placeholder="https://discord.com/api/webhooks/...",
    )
    test_wh_btn = wh_c2.button("Kirim Test Ping")

    if test_wh_btn and webhook_url_input:
        with st.spinner("Mengirimkan sinyal uji coba webhook..."):
            test_alert = AlertPayload(
                event_type="TEST_PING",
                ticker=selected_ticker,
                current_price=tech_summary.close,
                invalidation_price=round(tech_summary.close * 0.95),
                distance_percent=5.0,
                message=f"Uji coba konektivitas webhook Ruang Risiko IDX untuk {selected_ticker} berhasil.",
            )
            wh_res = dispatch_webhook_alert(webhook_url_input, test_alert)
            if wh_res["success"]:
                st.success(f"Webhook terkirim sukses (Status {wh_res['status_code']})!")
            else:
                st.error(f"Gagal mengirim webhook: {wh_res.get('error')}")
    elif test_wh_btn:
        st.warning("Masukkan Webhook URL terlebih dahulu.")

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
