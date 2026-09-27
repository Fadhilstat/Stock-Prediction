# Ruang Risiko IDX Design System: TradingView Terminal Specification & Mathematical Architecture

## 1. Product Identity and Design Philosophy
Ruang Risiko IDX is an audit-grade Indonesian equity risk intelligence and quantitative decision research terminal.
Its user interface combines the visual ergonomics of TradingView dark mode with the deep orderbook and Bandarmology mechanics native to the Indonesia Stock Exchange (IDX / BEI).

### Core Philosophy
1. **TradingView Dark Ergonomics**: High-contrast, fatigue-free terminal palette (`#131722`, `#1E222D`, `#2A2E39`, `#2962FF`) with responsive multi-pane layout, toolbar pills, and crosshairs.
2. **Quantitative Rigor without Slop**: Beneath familiar retail charts lies an institutional statistical engine: GARCH(1,1) volatility forecasting, parametric and Cornish-Fisher Value-at-Risk (VaR), Expected Shortfall (CVaR 99%), Hurst Exponent memory classification, Jarque-Bera normality testing, and Machine Learning directional quantiles.
3. **Public-Facing Financial Inclusion**: Powerful tools (Multi-Factor Screener, Macroeconomic Barometer, Curated Financial News Sentiment) accessible to both institutional analysts and public retail investors.
4. **Flexible Equity Universe**: Built-in 14 flagship IDX tickers spanning Banking, Telco, Automotive, Mining, Consumer Goods, Technology, and IHSG benchmark, plus arbitrary custom ticker entry with real-time normalization (`.JK`).
5. **Continuous Out-Of-Sample Validation**: Autonomous bi-weekly (14 trading days) walk-forward model evaluation tracking directional hit rate, Brier calibration score, log loss, and VaR 99% breach counts.
6. **Web-Based Operational Sovereignty**: Every critical system action (data updates, model recalculation, risk tolerance tuning, and passport issuance) can be monitored and controlled directly through the browser without RDC or terminal commands.

---

## 2. Anti-Slop UX Mandates
- **Zero Generic AI Slop**: No decorative neon gradients, pulsing borders, or floating particles.
- **Zero Decorative Placeholders**: Every button, slider, and selector executes verified computational routines and records immutable audit entries.
- **Zero Pseudo-Certainty**: Predictions are rendered strictly as quantile probability distributions (q10 to q90), never as deterministic price guarantees.
- **Zero Look-Ahead Bias**: Historical inspection and fundamental data enforce strict Point-In-Time reporting dates.
- **Zero Em Dash Policy**: Absolute prohibition of the em dash character (`\u2014`) across all UI copy, labels, tooltips, code comments, and documentation.

---

## 3. Design Tokens and Theme Architecture

### Color Palette (TradingView Institutional Dark)
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `color-bg-base` | `#131722` | Terminal deep charcoal background |
| `color-bg-surface` | `#1E222D` | Cards, panels, orderbook background, and sidebar |
| `color-border-subtle` | `#2A2E39` | Clean structural dividing borders |
| `color-accent-blue` | `#2962FF` | TradingView brand blue for active states, tabs, and median paths |
| `color-idx-green` | `#00C076` | IDX bullish price movement, bid queue, ARA limit, positive sentiment |
| `color-idx-red` | `#FF4A68` | IDX bearish price movement, offer queue, ARB limit, negative sentiment |
| `color-warning-amber` | `#F59E0B` | Watch setups, event risks, moderate volatility warnings |
| `color-veto-crimson` | `#DC2626` | Hard veto triggers, tail risk breaches, circuit breaker limits |
| `color-text-primary` | `#F9FAFB` | Primary headings, asset prices, and critical figures |
| `color-text-secondary` | `#D1D4DC` | Standard body copy, table figures, and active labels |
| `color-text-muted` | `#787B86` | Micro captions, audit metadata, and inactive headers |

### Typography and Tabular Alignment
- **Sans-Serif System Font**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` for clean legibility.
- **Monospace Tabular Font**: `SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace` for 10-level orderbook depth, broker lots, prices, and timestamped audit logs.

---

## 4. Eight-Tab TradingView Workspace Specification

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Ticker Tape: IHSG 7,812.35 (+0.42%) | LQ45 982.10 | USD/IDR 15,420 | Net Foreign│
├─────────────────────────────────────────────────────────────────────────────────┤
│ Header: BBCA.JK | Rp 10,250 (+0.49%) | ARA: Rp 12,300 | ARB: Rp 8,200 | [STATUS]│
├─────────────────────────────────────────────────────────────────────────────────┤
│ Metrics: Prob Up: 58.4% | Median q50: Rp 10,280 | GARCH Vol: 1.5% | VaR 99: 4.0%│
├─────────────────────────────────────────────────────────────────────────────────┤
│ Navigation Tabs:                                                                │
│ [1. Chart & Book] [2. Math & Econometrics] [3. Macro & News] [4. Bandarmology]  │
│ [5. Public Screener] [6. Bi-Weekly Valid] [7. Pre-Buy Passport] [8. Web Console]│
│                                                                                 │
│ Active Workspace Panel                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Tab 1: TradingView Chart and 10-Level Orderbook
- **Interactive Multi-Pane Chart**: Candlestick and OHLC display with moving averages (SMA 20, SMA 50, SMA 200), Bollinger Bands, and volume histogram.
- **Stockbit-Style Visual Orderbook Depth Queue**: Real-time 10-level bid and offer ladders with horizontal colored depth progress bars proportional to lot volume, ARA/ARB limits, and bid/offer ratio.
- **Microstructure Imbalance and Order Flow Delta**:
  - Volume Order Imbalance (VOI) weighted across 10 depth tiers.
  - Cumulative Volume Delta (CVD) proxy quantifying aggressive buy vs sell market absorption.
  - Order flow regime classification (`AGGRESSIVE_BUYING`, `BALANCED_FLOW`, `AGGRESSIVE_SELLING`).
  - Spoofing & Phantom Wall detector flagging asymmetric phantom liquidity far from the touch.
- **Slippage and Depth Simulator**: Computes volume-weighted average fill price (VWAP), slippage in basis points (bps), and orderbook ticks consumed for custom transaction sizes.

### Tab 2: Insight Matematis and Ekonometrika
- **Higher-Order Distributional Moments**:
  - Sample Mean ($\mu$) and Daily Return Standard Deviation ($\sigma$).
  - Skewness ($S$): Quantifies upside vs downside return asymmetry.
  - Excess Kurtosis ($\kappa - 3$): Quantifies fat-tail leptokurtic probability.
  - Jarque-Bera Test: Statistical hypothesis testing for normality; reports test statistic and p-value.
- **Long-Memory and Regime Persistence**:
  - Hurst Exponent ($H$): Rescaled range analysis ($R/S$) classifying series as mean-reverting ($H < 0.45$), random walk Brownian ($0.45 \le H \le 0.55$), or trend persistent ($H > 0.55$).
- **Extreme Tail Risk Metrics**:
  - Parametric and Cornish-Fisher Value-at-Risk (VaR 99%).
  - Expected Shortfall (CVaR 99%): Average conditional loss beyond the 99th percentile cutoff.
  - Conditional vs Unconditional Variance: Ratio of current GARCH conditional variance ($\sigma_t^2$) to long-run unconditional variance ($\sigma^2$).
- **Multi-Horizon Quantile Fan Chart**: Visualizes forecast dispersion across 1-day, 5-day, and 20-day horizons with q10, q25, q50, q75, and q90 paths.
- **Scenario and Crisis Stress Testing**: Simulates portfolio drawdown under historical BEI market shocks (COVID-19 Crash March 2020, Subprime 2008, Fed Taper Tantrum 2013).

### Tab 3: Makroekonomi and Sentimen Berita
- **Macroeconomic Barometer**:
  - Bank Indonesia Policy Rate (BI-Rate).
  - 10-Year Surat Berharga Negara (SUN 10Y) benchmark yield.
  - Domestic Equity Risk Premium (ERP): Calculated as Earnings Yield minus SUN 10Y Yield.
  - USD/IDR Foreign Exchange Spot Rate.
- **Pre-Market Morning Briefing (08:30 WIB Digest)**:
  - Daily opening briefing synthesizing overnight global cues (Brent Oil, Nickel, Coal, Gold, S&P 500).
  - Top 3 Pre-Market High-Conviction Setups with invalidation boundaries and expected target levels.
  - Operational risk execution warnings and 1-click Markdown digest download.
- **Curated Financial News Sentiment**:
  - Real-time news aggregation categorized by Macro, Banking, Energy, and Regulatory domains.
  - Natural language sentiment scoring (-1.0 to +1.0) with sentiment labels (POSITIVE, NEUTRAL, NEGATIVE).
  - Identification of impacted tickers and key forward catalysts.
- **Community Radar and Stockbit Stream**:
  - Community crowd sentiment metrics (% Bullish vs % Bearish).
  - Retail Herding and FOMO early warning alerts.
  - Sector Rotation Compass: 4-quadrant momentum map (Leading, Weakening, Lagging, Improving) and market breadth (% stocks above SMA 20, 50, 200).

### Tab 4: Bandarmology and Broker Summary
- **Broker Transaction Summary**: Top 5 Buyer brokers vs Top 5 Seller brokers with volume in lots, average prices, and net IDR transaction values.
- **Three-Tier Investor Flow**: Net flows segregated by Foreign Institutional, Domestic Institutional, and Retail Domestic.
- **Smart Money Accumulation Index (SMAI)**: Normalized index (0% to 100%) indicating institutional accumulation pressure.
- **Retail Trap Alert**: Automated warning when retail brokers dominate net purchases into falling prices.
- **Dividend and Corporate Action Trap Risk**: Historical ex-date drop analysis and recovery duration.

### Tab 5: Screener Saham Publik (TradingView Style)
- **Multi-Factor Public Screener**: Interactive filtering across all monitored Indonesian equities.
- **Filter Controls**: Multi-sector selector and maximum daily GARCH volatility threshold slider.
- **Tabular Indicators**: Last price, 1-day percentage change, daily GARCH volatility, machine learning directional probability (% Up), and index membership (LQ45, IDX30, Kompas100).

### Tab 6: Validasi Model Bi-Weekly (14-Hari Walk-Forward)
- **Rolling Out-Of-Sample Validation**: Evaluates predictive stability over 14-day rolling trading windows.
- **Performance Metrics**:
  - Directional Hit Rate (%): Proportion of correct daily price movement directions.
  - Brier Calibration Score: Mean squared error of probabilistic forecasts (lower is better calibrated).
  - Log Loss (Cross-Entropy Loss): Penalizes overconfident wrong predictions.
  - VaR 99% Tail Breach Count: Frequency of realized daily losses exceeding the 99% VaR threshold.
- **Automated Drift Detection and Recalibration Recommendation**: Recommends `MAINTAIN_CURRENT_MODEL`, `RECALIBRATE_VOLATILITY`, or `RETRAIN_DIRECTION_MODEL` based on empirical breach thresholds.

### Tab 7: Pre-Buy Decision Passport and Allocator
- **Institutional Decision Passport**: Formal GO / NO-GO research certificate with hard veto rationale and invalidation rules.
- **Markdown Export**: One-click download of the cryptographic and digital audit passport document.
- **Dynamic Capital and Risk Budget Allocator**:
  - Volatility-adjusted Fractional Kelly sizing.
  - Position sizing constrained by maximum single-stock allocation, daily portfolio risk budget, and IDX 100-share lot minimums.
  - Exact IDR Value-at-Risk contribution calculation.
- **GARCH-ATR Dynamic Trailing Boundary and Volatility Ratchet**:
  - Continuous stop-loss tightening driven by conditional GARCH volatility and ATR multiples.
  - 4-stage ratchet mechanism: Initial Defense, Breakeven Locked (covers fees upon reaching q50), Profit Protection (locks 4% profit upon 8% gain), and Trailing Tight (locks within 7% of high upon 15% run).
- **Strategy Backtest Replay and Interactive Equity Curve**:
  - Historical simulation comparing strategy return vs Benchmark Buy & Hold across empirical trading days.
  - Performance metrics: CAGR (%), Alpha (%), Annualized Sharpe Ratio, Maximum Drawdown (%), Calmar Ratio, Win Rate (%), and Profit Factor.
  - Interactive Plotly multi-pane equity curve with historical drawdown visualization.

### Tab 8: Web Action Console (Operational Control Plane)
- **Autonomous Task Daemon and Orchestration Panel**:
  - End-to-end autonomous background job coordinator eliminating need for command-line or RDC intervention.
  - Master Execution Trigger: 1-click execution of the entire pipeline sequence (Data Ingestion, GARCH/VaR Recalculation, ML Direction Refit, Morning Briefing Compilation, Bi-Weekly Model Audit).
  - Live Task Schedule Registry: Monitored status, execution frequency, next scheduled run, and audit logs.
- **Real-Time Action Triggers**:
  - Refresh market data ingestion.
  - Recalculate GARCH volatility and VaR snapshots.
  - Retrain and re-score machine learning directional models.
  - Compile Pre-Market Morning Briefing (08:30 WIB) digest.
  - Run Microstructure Imbalance & Order Flow Delta scans.
- **Runtime Risk Configuration**:
  - Slider adjustments for VaR confidence level, maximum single-stock allocation %, and execution slippage limits.
  - Active model selector (Random Forest, Logistic Regression, XGBoost, Ensemble).
- **Chronological Audit Ledger**: Transparent browser display of recent operational commands, execution durations, operator identities, and status outcomes.

---

## 5. Mathematical and Econometric Formulations

### 5.1 Higher-Order Distributional Moments
For a time series of daily log returns $r_t = \ln(P_t / P_{t-1})$ with sample mean $\hat{\mu}$ and standard deviation $\hat{\sigma}$:

$$\text{Skewness } S = \frac{\frac{1}{T} \sum_{t=1}^T (r_t - \hat{\mu})^3}{\hat{\sigma}^3}$$

$$\text{Excess Kurtosis } K = \frac{\frac{1}{T} \sum_{t=1}^T (r_t - \hat{\mu})^4}{\hat{\sigma}^4} - 3$$

$$\text{Jarque-Bera Statistic } JB = \frac{T}{6} \left( S^2 + \frac{K^2}{4} \right) \sim \chi^2(2)$$

### 5.2 Hurst Exponent Memory Analysis
The Hurst Exponent $H$ is estimated via rescaled range analysis across sub-series lengths $n$:

$$\mathbb{E}[(R/S)_n] = C \cdot n^H \quad \implies \quad \ln(R/S)_n = \ln(C) + H \ln(n)$$

- $H < 0.45$: Mean-reverting regime (anti-persistent, suitable for mean-reversion strategies).
- $0.45 \le H \le 0.55$: Geometric Brownian motion (random walk, efficient market).
- $H > 0.55$: Trend-persistent regime (momentum-driven institutional flow).

### 5.3 Conditional vs Unconditional Variance
Under the GARCH(1,1) specification $\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$:

$$\text{Unconditional Variance } \sigma_{\text{long-run}}^2 = \frac{\omega}{1 - (\alpha + \beta)}$$

$$\text{Variance Ratio } = \frac{\sigma_t^2}{\sigma_{\text{long-run}}^2}$$

### 5.4 Expected Shortfall (CVaR 99%)
Expected Shortfall measures the expected return conditional on exceeding the 99% Value-at-Risk threshold:

$$\text{CVaR}_{0.99} = -\mathbb{E}[r_t \mid r_t < -\text{VaR}_{0.99}]$$

### 5.5 Volume Order Imbalance (VOI) and Cumulative Volume Delta (CVD)
Multi-level queue imbalance aggregates weighted net depth across $K=10$ levels:

$$\text{VOI} = \sum_{k=1}^K w_k \cdot (V_k^{\text{bid}} - V_k^{\text{offer}}), \quad w_k = \frac{1}{k}$$

Cumulative Volume Delta proxy quantifies net market order aggression:

$$\text{CVD} = \int (\text{Market Buys} - \text{Market Sells}) \, dt \approx 0.75 \cdot \left(\sum_{k=1}^3 V_k^{\text{bid}} - \sum_{k=1}^3 V_k^{\text{offer}}\right)$$

### 5.6 GARCH-ATR Dynamic Trailing Boundary
The adaptive stop-loss boundary scales dynamically with conditional volatility:

$$\text{Trailing Stop}_t = \max\left(\text{Stop}_{t-1}, P_{\text{high}} - k \cdot \text{ATR}_{14} \cdot \sqrt{\frac{\sigma_t^2}{\sigma_{\text{long-run}}^2}}\right)$$

### 5.7 Strategy Performance Metrics
The annualized Sharpe Ratio incorporates the risk-free rate (BI-Rate $R_f = 6.0\%$):

$$\text{Sharpe} = \frac{\bar{R}_p - R_f}{\sigma_p} \cdot \sqrt{252}, \quad \text{Calmar} = \frac{\text{CAGR}}{\text{Maximum Drawdown}}$$

### 5.8 Dynamic Conditional Correlation (DCC-GARCH)
Following Engle (2002), time-varying covariance matrices are decomposed into conditional variances and dynamic correlations:

$$H_t = D_t R_t D_t, \quad D_t = \text{diag}(\sigma_{1,t}, \dots, \sigma_{k,t})$$

Quasi-correlation recursion:
$$Q_t = (1 - \alpha - \beta)\bar{Q} + \alpha (\epsilon_{t-1} \epsilon_{t-1}') + \beta Q_{t-1}$$

Dynamic correlation matrix:
$$R_t = \text{diag}(Q_t)^{-1/2} Q_t \text{diag}(Q_t)^{-1/2}$$

Systemic Contagion Index (SCI):
$$\text{SCI}_t = \frac{2}{k(k-1)} \sum_{i < j} |\rho_{ij,t}|$$

When $\text{SCI}_t \ge 0.60$, market co-movement indicates systemic contagion and portfolio diversification breakdown.

### 5.9 Autonomous Telegram Webhook Dispatcher
Automated dispatch engine for real-time mobile investor alerts:
- Premarket Morning Briefing (08:35 WIB).
- Dynamic Trailing Stop Ratchet trigger events.
- Bi-Weekly 14-day model validation Brier score audits.
- DCC Contagion Risk Spikes.
Operates with dual-mode reliability: zero-dependency live HTTPS transmission via Telegram Bot API, with automated non-blocking fallback to audit-logged simulation in test/offline environments.

---

## 6. Flexible Equity Universe Specification
The system supports both built-in core tickers and user-specified custom tickers:
- **Core Universe (14 Assets)**:
  - Banking: `BBCA.JK`, `BBRI.JK`, `BMRI.JK`, `BBNI.JK`
  - Telco & Infrastructure: `TLKM.JK`
  - Conglomerate & Automotive: `ASII.JK`
  - Energy & Metals: `ANTM.JK`, `ADRO.JK`, `PTBA.JK`, `AMMN.JK`
  - Consumer Goods: `ICBP.JK`, `UNVR.JK`
  - Technology: `GOTO.JK`
  - Benchmark Index: `^JKSE` (IHSG)
- **Arbitrary Custom Ticker Handler**:
  - Automatically appends `.JK` if omitted.
  - Dynamically synthesizes market data baselines, technical indicators, and quantile projections for newly evaluated tickers.

