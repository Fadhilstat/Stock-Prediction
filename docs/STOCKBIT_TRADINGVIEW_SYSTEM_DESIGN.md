# Ruang Risiko IDX: Stockbit & TradingView Terminal Architecture Design

## 1. Executive Summary

This document specifies the institutional architectural overhaul of **Ruang Risiko IDX**, transitioning away from Streamlit to a high-concurrency **FastAPI + Vanilla JS Single Page Application (SPA)** terminal inspired by TradingView and Stockbit.

The redesigned platform achieves:
1. **Zero-Flicker Execution**: Client-side reactive DOM rendering replaces Streamlit whole-script re-runs, eliminating UI lag, WebSocket disconnects, and layout jitter.
2. **Autonomous Continuous Auto-Deployment**: A dedicated background systemd timer daemon (`rridx-autoupdate.timer`) and REST webhook endpoints (`/api/v1/system/auto-update`, `/api/v1/system/webhook-update`) poll `origin/main` every 60 seconds, autonomously applying Git updates without manual SSH or terminal commands.
3. **Web-Based Action Console**: Complete operational control (data ingestion, model recalculations, regime classifications, portfolio optimizations, and server updates) executable via asynchronous REST calls from the web interface.
4. **Institutional Quantitative Intelligence**: Integrates GARCH, HMM 3-State Regime Switching, DCC-GARCH Dynamic Contagion, Copula EVT Tail Risk, Pareto Multi-Objective Optimization, Almgren-Chriss Algorithmic Execution, and Diebold-Yilmaz Volatility Spillover Index.

---

## 2. Architecture Comparison: Streamlit vs. FastAPI SPA

| Architectural Layer | Legacy Architecture (Streamlit) | Modern Architecture (FastAPI + SPA) |
| :--- | :--- | :--- |
| **Execution Paradigm** | Full script re-execution on every click | Event-driven asynchronous REST API |
| **Frontend Rendering** | Server-side DOM re-render with WebSocket sync | Client-side reactive Vanilla JS |
| **State Management** | Ephemeral `st.session_state` prone to drops | In-memory reactive state object (`state`) |
| **Chart Interactions** | Static Plotly iframe rebuilds | Responsive SVG Area Spline with hover crosshair |
| **Orderbook Microstructure** | Tabular markdown or static Streamlit tables | Animated 10-level Bid/Ask depth ladder with VOI |
| **Update Mechanism** | Manual SSH / bash script trigger | Autonomous 60s background daemon + 1-click web action |
| **Memory Footprint** | ~350MB+ base per active session | < 85MB base, non-blocking asynchronous event loop |

---

## 3. Microstructure & Visual Interface Design (Stockbit & TradingView Theme)

### 3.1 Dark Institutional Color Palette
- **Background Root**: `#131722` (TradingView Dark Canvas)
- **Panel Containers**: `#1e222d` with `#2a2e39` structural borders
- **Card Backgrounds**: `#262b3e`
- **Bullish / Inflow / Bid**: `#089981` (Accent: `rgba(8, 153, 129, 0.15)`)
- **Bearish / Outflow / Ask**: `#f23645` (Accent: `rgba(242, 54, 69, 0.15)`)
- **Primary Electric Accent**: `#2962ff` (Brand Identity)
- **Warning / Moderate Alert**: `#f5a623`

### 3.2 Key Frontend Components
1. **World Indices Ticker Ribbon**: Top-level header streaming IHSG, LQ45, S&P 500, Nikkei 225, and USD/IDR exchange rates.
2. **Watchlist Sidebar**: Instant emiten filter across IDX blue-chips with price changes and mini sparkline metrics.
3. **TradingView Area Spline Chart**: Smooth cubic bezier curve rendering with high/low bounds, right-hand dynamic price badges, and crosshair inspect.
4. **Stockbit 10-Level Orderbook Ladder**: Proportional depth bars visualising queued lots and Volume Order Imbalance (VOI).
5. **Running Trade Tape**: Real-time intraday tick feed with buy/sell flags.
6. **Quantitative Intelligence Suite**: Modular tabbed panels providing deep analytical insights without page reloading.

---

## 4. Quantitative Engine Specification

### 4.1 Diebold-Yilmaz (2012) Volatility Spillover Index
Measures systemic connectedness across Indonesian financial institutions and global benchmarks:
- **Vector Autoregression**: Fits a VAR(p) model via Ordinary Least Squares on daily returns.
- **GFEVD Formulation**: Employs Koop-Pesaran-Potter / Pesaran-Shin invariant Generalized Forecast Error Variance Decomposition.
- **Directional Connectedness**: Computes gross volatility transmitted (TO), received (FROM), and net directional spillovers (NET = TO - FROM).

### 4.2 Hidden Markov Model (HMM) Regime Switching
- Models market returns via 3 Gaussian mixtures:
  - State 0: Bullish Expansion (positive mean drift, low volatility)
  - State 1: Sideways Consolidation (near-zero drift, moderate volatility)
  - State 2: Bearish Crash (negative drift, extreme volatility)
- Decodes hidden sequence via the Viterbi path algorithm.

### 4.3 Multi-Objective Pareto Portfolio Allocator
Balances three objectives:
1. Maximize Annualized Return $\mu^T w$
2. Minimize Expected Shortfall $\text{CVaR}_{99\%}(w)$
3. Maximize Diversification Entropy $H(w) = -\sum_{i=1}^N w_i \ln(w_i)$

---

## 5. Autonomous Zero-Touch Auto-Deployment Protocol

To achieve 100% automated updates without human intervention:

```
[Git Push to origin/main]
          |
          v
[VPS Systemd Timer (Every 60s)] ---> [deploy/auto_update.sh]
          |                                   |
          |                                   v
          |------------------------> [git fetch origin main]
          |                                   |
          |                      (Is Local HEAD == Remote HEAD?)
          |                                   |
          |                            No: New commit!
          |                                   |
          |                       [git reset --hard origin/main]
          |                                   |
          |                       [docker compose up -d --build]
          |                                   |
          |------------------------> [Log to /var/log/rridx-autoupdate.log]
```

### 5.1 Redundancy Options
- **Option A (Systemd Timer)**: Runs on the host OS every 60s (`rridx-autoupdate.timer`). Installed turnkey via `deploy/enable_autoupdate.sh`.
- **Option B (In-Container Poller)**: `BackgroundAutoUpdatePoller` daemon thread runs inside the FastAPI process, polling every 120s.
- **Option C (Web Action Console)**: Clicking `Cek & Terapkan Pembaruan GitHub` on the web interface triggers an immediate deployment check via REST API.
- **Option D (GitHub Webhook)**: POST `/api/v1/system/webhook-update` enables instant deployment on push.

---

## 6. Verification and Compliance

- **Style Rule**: Zero em dash characters throughout the entire codebase.
- **Healthcheck**: Universal endpoints at `/health` and `/_stcore/health` for Caddy and Docker integration.
- **Port Compatibility**: Bound to port 8501 inside the container, preserving existing Caddy reverse proxy mappings seamlessly.
