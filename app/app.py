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
    trigger_market_data_refresh,
    trigger_risk_recalculation,
    update_runtime_risk_parameters,
)
from ruang_risiko_idx.research.broker_summary import generate_broker_summary
from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary, get_creator_claims_for_ticker
from ruang_risiko_idx.research.fundamentals import CANONICAL_COMPANIES, get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.journal import load_prediction_journal
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.multimodal import get_ablation_benchmarks, run_evidence_conflict_radar
from ruang_risiko_idx.research.orderbook import generate_orderbook
from ruang_risiko_idx.research.risk_engine import evaluate_risk_engine
from ruang_risiko_idx.research.scenarios import compute_horizon_quantiles, generate_scenarios
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
    /* Stockbit Running Ticker Tape */
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
    /* Stockbit Card Panels */
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
    /* Badges */
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

    /* Orderbook Depth Styling */
    .depth-bar-bid {
        background: linear-gradient(90deg, rgba(0, 192, 118, 0.25) 0%, rgba(0, 192, 118, 0.05) 100%);
    }
    .depth-bar-offer {
        background: linear-gradient(270deg, rgba(255, 74, 104, 0.25) 0%, rgba(255, 74, 104, 0.05) 100%);
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
        <div class="tape-item"><span class="tape-label">Status Bursa</span> <span class="tape-val-green">● SESI 2 SELESAI</span></div>
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
    f"Mode: Headless Non-RDC Ready\n"
    f"Engine: Stockbit Hybrid vNext"
)

# Analytics & Models
tech_summary = summarize_technical_state(selected_data, selected_ticker)
ict_summary = evaluate_ict_hypotheses(selected_data, selected_ticker)
fund_snapshot = get_fundamental_snapshot(selected_ticker)
align_summary = compute_market_alignment(selected_data, benchmark_data, selected_ticker)
liq_summary = compute_liquidity_flow_summary(selected_data, selected_ticker)

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
broker_summary = generate_broker_summary(
    ticker=selected_ticker,
    trade_date=data_cutoff,
    close_price=tech_summary.close,
    total_traded_value_idr=liq_summary.average_daily_value_idr,
    foreign_flow_state=liq_summary.foreign_flow_state,
)

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
            ARB: <span style="color: #FF4A68; font-weight: 600;">Rp {orderbook.arb_price:,.0f}</span>
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
    "Bandarmology Status",
    broker_summary.status.replace("_", " "),
    f"Asing: Rp {broker_summary.foreign_net_value_idr / 1e9:+.1f} M",
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
            height=460,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_col2:
        st.markdown("**Orderbook (10-Level Depth)**")
        st.caption(f"Total Bid: {orderbook.total_bid_lots:,} Lot | Total Offer: {orderbook.total_offer_lots:,} Lot")

        # Visual Table for 10-level Bids and Offers
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
                Ratio Bid/Offer: <strong>{orderbook.bid_offer_ratio:.2f}</strong> |
                ARA: <span style="color: #00C076;">Rp {orderbook.ara_price:,.0f}</span> |
                ARB: <span style="color: #FF4A68;">Rp {orderbook.arb_price:,.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# TAB 2: Bandarmology & Broker Summary
with main_tabs[1]:
    st.markdown("#### Broker Summary & Bandarmology Accumulation")
    st.caption("Peta konsentrasi bandar dan aliran modal asing vs domestik.")

    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.metric("Status Bandarmology", broker_summary.status.replace("_", " "))
    b_col2.metric("Top 3 Buyer Concentration", f"{broker_summary.top3_buyer_ratio_percent:.1f}%")
    b_col3.metric("Top 3 Seller Concentration", f"{broker_summary.top3_seller_ratio_percent:.1f}%")

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
    st.caption("Radar sentimen, pengujian hipotesis ICT, dan radar konflik bukti multimodal.")

    stream_col1, stream_col2 = st.columns(2)
    with stream_col1:
        st.markdown("**Hipotesis Struktur Pasar Gaya ICT**")
        st.write(f"- **Struktur Pasar:** `{ict_summary.market_structure_state}`")
        st.write(f"- **Zona Valuasi Relatif:** `{ict_summary.zone_classification}`")
        st.write(f"- **Fair Value Gap:** `{'Terdeteksi' if ict_summary.fair_value_gap_present else 'Tidak ada'}`")
        st.write(f"- **Liquidity Sweep:** `{'Terdeteksi' if ict_summary.liquidity_sweep_detected else 'Tidak ada'}`")

    with stream_col2:
        st.markdown("**Keselarasan vs IHSG**")
        st.write(f"- **Status:** `{align_summary.alignment_state}`")
        st.write(f"- **Rolling Beta 60D:** `{align_summary.rolling_beta_60d:.2f}`")
        st.write(f"- **Korelasi 60D:** `{align_summary.rolling_correlation_60d:.2f}`")
        st.write(f"- **Kekuatan Relatif 20D:** `{align_summary.relative_strength_20d:+.2%}`")

    st.markdown("---")
    st.markdown("**Klaim Kreator & Analis Publik**")
    claims = get_creator_claims_for_ticker(selected_ticker)
    if claims:
        claims_data = []
        for c in claims:
            claims_data.append(
                {
                    "Kreator": c.creator_name,
                    "Platform": c.platform,
                    "Tanggal": c.timestamp,
                    "Arah": c.claim_direction,
                    "Status": c.current_status,
                    "Ringkasan Tesis": c.thesis_summary,
                }
            )
        st.dataframe(pd.DataFrame(claims_data), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada klaim publik terdaftar untuk saham ini.")

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
    st.markdown("##### 📜 Audit Trail & Riwayat Aksi Operasional")
    history_entries = load_action_history(limit=25)
    if history_entries:
        h_df = pd.DataFrame(history_entries)[
            ["action_id", "action_type", "triggered_at", "operator", "status", "summary_message", "duration_ms"]
        ]
        st.dataframe(h_df, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada riwayat aksi operasional tercatat.")

# Footer
st.markdown("---")
st.caption(
    "Ruang Risiko IDX Autonomous Finished Product. "
    "Sistem riset risiko pasar modal Indonesia. Semua output adalah estimasi probabilitas statistik dan bukan ajakan investasi."
)
