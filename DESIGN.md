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

### 5.10 Copula Tail Dependence & Peak-Over-Threshold (POT) EVT
Asymmetric crash dependence and heavy tail loss modeling:
- Clayton Copula (Lower Crash Tail):
  $$\lambda_L = \lim_{u \to 0^+} \mathbb{P}(U \le u \mid V \le u) = 2^{-1/\theta}$$
- Gumbel Copula (Upper Boom Tail):
  $$\lambda_U = \lim_{u \to 1^-} \mathbb{P}(U > u \mid V > u) = 2 - 2^{1/\theta}$$
- Generalized Pareto Distribution (GPD) for exceedances $y = L_t - u > 0$:
  $$F_u(y) = 1 - \left(1 + \frac{\xi y}{\beta}\right)^{-1/\xi}$$
- EVT Value-at-Risk and Expected Shortfall:
  $$\text{VaR}_p = u + \frac{\beta}{\xi}\left[\left(\frac{n}{N_u}(1-p)\right)^{-\xi} - 1\right], \quad \text{ES}_p = \frac{\text{VaR}_p + \beta - \xi u}{1 - \xi}$$

### 5.11 Almgren-Chriss Algorithmic Execution Simulator
Institutional block order scheduling across IDX trading sessions (09:00-11:30 and 13:30-15:30 WIB):
- Slice sizing:
  $$x_k = X \cdot w_k$$
- Market impact decomposition:
  $$\text{Permanent Impact } I_{\text{perm}} = \gamma \left(\frac{X}{\text{ADV}}\right)^{1/2}$$
  $$\text{Temporary Impact } I_{\text{temp}, k} = \eta \left(\frac{x_k}{\tau_k \cdot \text{ADV}_k}\right)^{0.60}$$
- Implementation Shortfall (IS):
  $$\text{IS} = \sum_{k=1}^K x_k (P_k - P_0) + \text{Broker Fees}$$

### 5.12 Hidden Markov Model (HMM) Regime Switching
Probabilistic detection of latent market states $S_t \in \{\text{Bull}, \text{Sideways}, \text{Bear}\}$:
- Emission distribution:
  $$r_t \mid S_t = k \sim \mathcal{N}(\mu_k, \sigma_k^2)$$
- Transition probability matrix:
  $$P_{ij} = \mathbb{P}(S_{t+1} = j \mid S_t = i), \quad \mathbb{E}[\text{Duration}_i] = \frac{1}{1 - P_{ii}}$$
- Viterbi optimal path decoding:
  $$V_t(j) = \max_{1 \le i \le 3} \left[V_{t-1}(i) \cdot P_{ij}\right] \cdot \mathcal{N}(r_t \mid \mu_j, \sigma_j^2)$$

### 5.13 Multi-Objective Pareto Portfolio Optimization
Non-dominated Mean-CVaR portfolio frontier with entropy regularization:
- Objective function:
  $$\min_{w} \quad \text{CVaR}_{0.99}(w) - \lambda_H \cdot H(w)$$
- Constraints:
  $$\mu' w = R_{\text{target}}, \quad \sum_{i=1}^k w_i = 1, \quad 0.02 \le w_i \le 0.40$$
- Diversification Entropy:
  $$H(w) = -\sum_{i=1}^k w_i \ln(w_i)$$
Eliminates corner portfolio allocations and significantly mitigates tail loss exposure relative to equal-weight benchmarks.

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

---

## 7. Hugging Face Foundation Time-Series Forecasters & Tournament Optimization

Ruang Risiko IDX incorporates state-of-the-art foundation models and transformer architectures from Hugging Face for financial time-series forecasting:

1. **Amazon Chronos-T5 (Zero-Shot Time-Series Transformer)**:
   - Tokenizes real-valued price time-series via uniform scaling and quantization into discrete token vocabularies.
   - Employs a pretrained encoder-decoder T5 architecture trained on billions of time-series observations across diverse macro and micro regimes.
   - Yields robust generalization without catastrophic overfitting on noisy IDX asset returns.

2. **Informer Long-Sequence Attention Network**:
   - ProbSparse self-attention mechanism reducing standard transformer complexity from $\mathcal{O}(L^2)$ to $\mathcal{O}(L \ln L)$.
   - Captures long-range macroeconomic cyclicality and persistent autocorrelation structures across trading sessions.

3. **Hybrid XGBoost + GJR-GARCH(1,1) Volatility Filter**:
   - Gradient boosted decision trees modeling non-linear return drifts, filtered by asymmetric GJR-GARCH innovations.
   - Directly models the leverage effect where negative market shocks generate larger volatility spikes than equivalent positive moves.

4. **Dynamic Minimum-Error Stacking Ensemble (Tournament Champion)**:
   - Evaluates each candidate model in real time across Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), and Mean Absolute Scaled Error (MASE).
   - Dynamically weights models inversely proportional to validation variance:
     $$w_m = \frac{1/\text{RMSE}_m^2}{\sum_{k=1}^M (1/\text{RMSE}_k^2)}$$
   - Selects the champion model that minimizes expected forecasting error.

---

## 8. Conformal Prediction Error Minimization & Calibration

To eliminate deceptive pseudo-certainty, price predictions are bounded by conformal prediction intervals guaranteeing finite-sample coverage validity:
- Given nonconformity scores $\alpha_i = |y_i - \hat{y}_i| / \hat{\sigma}_i$, the conformal quantile $\hat{q}_{1-\alpha}$ is determined empirically:
  $$\hat{q}_{1-\alpha} = \text{Quantile}\left(1 - \alpha; \alpha_1, \dots, \alpha_n\right)$$
- The calibrated prediction interval for step $t+h$ satisfies:
  $$\mathbb{P}\left(Y_{t+h} \in \left[\hat{y}_{t+h} - \hat{q}_{1-\alpha}\hat{\sigma}_{t+h}, \hat{y}_{t+h} + \hat{q}_{1-\alpha}\hat{\sigma}_{t+h}\right]\right) \ge 1 - \alpha$$
- Yields institutional-grade forward uncertainty cones with 95% statistical coverage.

---

## 9. Multimodal 3-Pillar Fusion Engine

The decision engine combines three orthogonal sources of market truth:
1. **Modality 1: Quantitative Technical & Volatility (Weight: 40%)**:
   - GARCH(1,1) conditional volatility, RSI-14 momentum, and EVT extreme tail index $\xi$.
2. **Modality 2: Textual Financial News & Macroeconomic Sentiment (Weight: 30%)**:
   - Natural language processing on financial headlines, BI-Rate stance, and USD/IDR currency outlook.
3. **Modality 3: Microstructure & Bandar Orderflow (Weight: 30%)**:
   - Top-3 broker buyer/seller concentration ratio (CR3), Net Foreign Institutional Flow, and Volume Order Imbalance (VOI).
- **Consensus Synergy Score**:
  $$S_{\text{multimodal}} = 0.40 \cdot S_{\text{quant}} + 0.30 \cdot S_{\text{macro}} + 0.30 \cdot S_{\text{bandar}}$$
  Categorized into: `STRONG_ACCUMULATION`, `ACCUMULATION`, `NEUTRAL_WATCH`, `DISTRIBUTION`, and `STRONG_DISTRIBUTION`.

---

## 10. 25-Stock Industry Sector Classification

The terminal categorizes 25 prominent liquid IDX equities into 7 market sectors:
- **Financials**: `BBCA.JK`, `BBRI.JK`, `BMRI.JK`, `BBNI.JK`, `BRIS.JK`
- **Energy**: `ADRO.JK`, `PTBA.JK`, `ITMG.JK`, `MEDC.JK`, `PGAS.JK`
- **Basic Materials**: `ANTM.JK`, `MDKA.JK`, `INCO.JK`, `BRPT.JK`
- **Consumer**: `ICBP.JK`, `INDF.JK`, `UNVR.JK`, `MYOR.JK`
- **Infrastructure**: `TLKM.JK`, `ISAT.JK`, `TOWR.JK`
- **Industrials**: `ASII.JK`, `UNTR.JK`
- **Technology**: `GOTO.JK`, `BUKA.JK`

---

## 11. Stockbit Institutional Terminal UI/UX Design System

The terminal reflects the ergonomics of Stockbit and TradingView:
- **Bidirectional Crosshair Tracking**: High-precision cursor tracker displaying exact date (X-axis tag) and price level (Y-axis tag).
- **Floating Coordinate HUD Bar**: Real-time ticker status, cursor price, delta percentage, and forward target bounds.
- **Stockbit 10-Level Orderbook Depth Ladder**: Visual queue volume bars, cumulative Bid/Ask imbalance gauge, and bid-ask spread indicators.
- **Real-Time Intraday Running Trades Tape**: Live transaction stream tagged with broker codes, lot sizes, and trade classifications.

---

## 12. Interactive Web Action Console & Continuous Zero-Manual Lifecycle

- **Web Action Console**:
  - Live execution of system routines (Data Refresh, Risk Recalculation, HMM Estimation, Pareto Optimization, HF Model Recalibration).
  - Hyperparameter tuning (VaR confidence levels, portfolio allocation caps, slippage limits, and ML model selectors).
  - Immutable action ledger audit trail recording operator, latency, execution timestamp, and status.
- **Continuous Zero-Manual Auto-Update Lifecycle**:
  - Background systemd timer (`rridx-autoupdate.timer`) checking GitHub repository every 60 seconds.
  - Automatic container recreation and seamless Caddy reverse proxy routing without requiring manual VPS terminal intervention.

---

## 13. Hugging Face FinBERT Sentiment Entropy & Market Polarization

Financial markets often experience sharp regime shifts not from consensus news, but from information asymmetry and sentiment dispersion. To capture this dynamic, the system deploys a Hugging Face FinBERT NLP model (`ProsusAI/finbert`) with institutional vocabulary weighting:
1. **Three-Way Probability Distribution**:
   - Computes normalized probability mass vector $\mathbf{p} = [p_{\text{positive}}, p_{\text{neutral}}, p_{\text{negative}}]$ across corporate releases and macroeconomic news.
2. **Shannon Information Entropy**:
   $$H(S) = -\sum_{c \in \{\text{pos}, \text{neu}, \text{neg}\}} p_c \log_2(p_c)$$
   - Quantifies the degree of market consensus versus uncertainty ($H(S) \in [0.0, 1.585]$). High entropy indicates institutional disagreement, preceding elevated volatility.
3. **Market Polarization Index & Volatility Scale Multiplier**:
   - Polarization is maximized when extreme positive and negative narratives collide:
     $$\text{Polarization} = 4 \cdot p_{\text{pos}} \cdot p_{\text{neg}}$$
   - Multiplier dynamically scales GARCH conditional standard deviation $\hat{\sigma}_t$:
     $$k_{\sigma} = 1.0 + 0.25 \cdot \text{Polarization} + 0.35 \cdot \max(0, -\text{Polarity}_{\text{agg}})$$

---

## 14. Institutional Broker Cluster Network Matrix (Bandarmology Graph)

The terminal traces liquidity flows across three structural participant tiers in the Indonesia Stock Exchange:
1. **Tier 1 (Foreign Institutional Whales)**:
   - Global investment banks and custody brokers (`ZP`, `CS`, `MS`, `KZ`, `RX`, `BK`, `AK`).
2. **Tier 2 (Domestic Institutional Funds)**:
   - Sovereign pension funds, insurance asset managers, and state-backed brokerages (`CC`, `OD`, `NI`, `LG`, `DX`).
3. **Tier 3 (Retail Participant Gateways)**:
   - High-volume retail retail brokerages (`YP`, `PD`, `XC`, `XL`, `KK`, `SQ`).

### Core Metrics:
- **Smart Money Index (SMI)**:
  $$\text{SMI} = \frac{\text{NetFlow}_{\text{whale}} + \text{NetFlow}_{\text{fund}}}{\max(|\text{NetFlow}_{\text{whale}}| + |\text{NetFlow}_{\text{retail}}|, 1)} \times 100$$
  Bounded in $[-100.0, +100.0]$.
- **Absorption Ratio**:
  $$\text{Ratio}_{\text{absorb}} = \frac{|\text{NetFlow}_{\text{whale}}|}{\max(|\text{NetFlow}_{\text{retail}}|, 10^6)}$$
  Measures the intensity at which institutional whales absorb retail distribution.
- **Institutional Phase Transitions**:
  - `STEALTH_ACCUMULATION`: SMI $\ge +40.0$ and Absorption Ratio $> 1.5\text{x}$.
  - `MARK_UP`: SMI $\in [+10.0, +40.0)$.
  - `NEUTRAL_CHOPPY`: SMI $\in [-10.0, +10.0)$.
  - `DISTRIBUTION`: SMI $\in [-40.0, -10.0)$.
  - `RETAIL_BAGHOLDING`: SMI $< -40.0$ with retail aggressive net buying.

---

## 15. Non-Linear Microstructure Slippage & Orderbook Replenishment

Execution of large blocks in emerging markets requires quantifying non-linear slippage before order submission:
1. **Square-Root Law of Market Impact**:
   $$I(Q, V) = Y \cdot \sigma \cdot \sqrt{\frac{Q}{V}}$$
   where $Q$ is order value (IDR), $V$ is average daily volume, $\sigma$ is daily asset volatility, and $Y \approx 0.45$ is the empirical market constant.
2. **Execution Slippage & Impact Cost**:
   $$\text{Slippage (bps)} = \max\left(2.5, 10000 \cdot I(Q, V)\right)$$
   $$\text{Impact Cost (IDR)} = Q \cdot \frac{\text{Slippage (bps)}}{10000}$$
3. **Queue Replenishment Half-Life ($t_{1/2}$)**:
   $$t_{1/2} = 8.5 \cdot \sqrt{\frac{Q}{5 \times 10^7}} \quad \text{seconds}$$
   Estimates the duration required for resting passive orderbook queues to refill after aggressive market sweeps.
4. **Algorithmic Execution Routing**:
   - $Q \le 500\text{M IDR}$: `DIRECT_MARKET`
   - $500\text{M} < Q \le 2\text{B IDR}$: `TWAP_15MIN`
   - $Q > 2\text{B IDR}$: `ICEBERG_5_TRANCHES`

---

## 16. Systemic Macroeconomic Crisis Scenarios & Tail-Risk Stress Testing

The terminal continuously projects equity resilience across 4 canonical crisis scenarios:
1. **The Fed Hawkish Shock & Rupiah Devaluation**: USD/IDR $> 16,500$, +50 bps BI-Rate hike, massive capital outflow from interest-rate sensitive bluechips.
2. **Global Commodity Benchmark Crash**: -22% Thermal Coal, -18% LME Nickel, triggering immediate revenue revisions for energy and metals exporters.
3. **Domestic Banking Liquidity Crunch**: Interbank credit contraction, rising non-performing loan provisions, compressing bank net interest margins.
4. **Emerging Market Taper Tantrum**: Sudden foreign institutional dump (exceeding 15 Trillion IDR net sell across index constituents).

### Output Risk Bounds:
- **Conditional Value-at-Risk ($\text{VaR}_{0.99}$)** and **Conditional Expected Shortfall ($\text{ES}_{0.99}$)** under stressed sector sensitivity matrices.
- **Composite Vulnerability Score**:
  $$\text{Vulnerability} = \min\left(100.0, 6.5 \cdot \overline{\text{ES}}_{0.99} + 0.45 \cdot \text{Slippage}_{\text{max}}\right)$$
  Classified into `HIGH_RESILIENCE`, `MODERATE`, `VULNERABLE`, and `CRITICAL_TAIL_RISK`.

---

## 17. Black-Litterman Portfolio Frontier with AI Foundation Model Prior Views

Classical mean-variance optimization produces extreme, unstable corner portfolios when applied to emerging equity markets. The terminal deploys the Bayesian Black-Litterman model to stabilize asset allocation:
1. **Market Equilibrium Prior**:
   $$\Pi = \delta \Sigma w_{\text{mkt}}$$
   where $\delta = 2.8$ is the market risk aversion parameter, $\Sigma$ is the synthetic asset covariance matrix, and $w_{\text{mkt}}$ is the benchmark capital weight.
2. **AI-Conditioned Views Vector ($Q$) & Uncertainty Matrix ($\Omega$)**:
   - The pick matrix $P$ maps $K$ asset views.
   - Forward return views $Q$ are derived directly from Amazon Chronos-T5 transformer trajectory projections and Smart Money Index (SMI) flows.
   - The view uncertainty diagonal $\Omega_{ii}$ is dynamically scaled by Hugging Face FinBERT Shannon Information Entropy $H(S)$:
     $$\Omega_{ii} = \tau \Sigma_{ii} \cdot \left(\frac{H(S)_i}{1.10}\right)^{1.5}$$
     Higher textual discord widens view uncertainty, preventing over-allocation.
3. **Master Bayesian Equilibrium**:
   $$\mathbb{E}[R] = \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P\right]^{-1} \left[(\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q\right]$$
4. **Constrained Quadratic Frontier**:
   Maximized via Sequential Least Squares Quadratic Programming (SLSQP):
   $$\max_{w} \frac{w^T \mathbb{E}[R] - r_f}{\sqrt{w^T \Sigma w}} \quad \text{s.t.} \quad \sum w_i = 1, \quad w_{\min} \le w_i \le w_{\max}$$

---

## 18. Automated Institutional Microstructure Signal & Anomaly Radar

The system continuously scans market assets and dispatches structured alerts for immediate risk response:
- **`STEALTH_ACCUMULATION`**: Foreign institutional whales actively absorb retail selling (Absorption Ratio $> 1.5\text{x}$, SMI $\ge +45.0$).
- **`SPOOFING_RISK`**: Asymmetric orderbook bid layering detected with phantom spoofing score $\ge 0.45$.
- **`SHANNON_DISCORD`**: News narrative discord spike ($H(S) \ge 1.15\text{ nats}$) indicating high probability of imminent volatility expansion.
- **`CONFORMAL_BREAKOUT`**: Model champion projects forward drift $> +4.0\%$ with 95% conformal uncertainty bounds.
- **`STRESS_VULNERABLE`**: Composite crisis vulnerability score $\ge 65.0/100$, triggering proactive hedging recommendations.

---

## 19. Level-2 (L2) 10-Depth Orderbook Microstructure & Spoofing Detector

Market microstructure at the limit order level reveals asymmetric information preceding large price changes. The terminal deploys an authentic L2 10-depth orderbook reconstruction governed by Indonesia Stock Exchange (IDX) official tick size rules (fraksi harga BEI):
1. **Dynamic Tick Sizes**:
   - Price $< 200$: Tick = Rp 1
   - Price $200 - 500$: Tick = Rp 2
   - Price $500 - 2,000$: Tick = Rp 5
   - Price $2,000 - 5,000$: Tick = Rp 10
   - Price $\ge 5,000$: Tick = Rp 25
2. **Volume-Weighted Average Price (VWAP) for Queue Depth**:
   $$\text{VWAP}_{\text{bid}} = \frac{\sum_{i=1}^{10} P_i^{\text{bid}} \cdot V_i^{\text{bid}}}{\sum_{i=1}^{10} V_i^{\text{bid}}}, \quad \text{VWAP}_{\text{ask}} = \frac{\sum_{i=1}^{10} P_i^{\text{ask}} \cdot V_i^{\text{ask}}}{\sum_{i=1}^{10} V_i^{\text{ask}}}$$
3. **Volume Order Imbalance (VOI) Ratio**:
   $$\text{VOI} = \frac{\sum_{i=1}^{10} V_i^{\text{bid}} - \sum_{i=1}^{10} V_i^{\text{ask}}}{\sum_{i=1}^{10} V_i^{\text{bid}} + \sum_{i=1}^{10} V_i^{\text{ask}}}$$
4. **Algorithmic Spoofing Probability Score**:
   - Detects phantom liquidity layering where large bid or ask walls ($\ge 26\%$ of total side depth) are placed to manipulate retail sentiment without execution intent:
     $$\text{SpoofingScore} = \min\left(95.0, 15.0 + 35.0 \cdot \mathbb{I}(\text{Wall}) + 25.0 \cdot \mathbb{I}(|\text{VOI}| \ge 0.30)\right)$$

---

## 20. Walk-Forward Out-of-Sample Backtesting & Foundation Model Tournament

To rigorously substantiate forecast accuracy and prevent lookahead bias or data snooping, the platform enforces sequential Walk-Forward Out-of-Sample (OOS) validation:
1. **Expanding Window Backtesting**:
   - Evaluates consecutive out-of-sample trading days (default 45-day window).
   - Generates 1-day ahead forecasts iteratively without utilizing future information.
2. **Multi-Model Tournament Benchmarking**:
   - **Hugging Face Chronos-T5**: Zero-shot probabilistic foundation transformer trained on extensive time-series datasets.
   - **Informer**: Auto-correlation long-sequence attention architecture designed for complex seasonalities.
   - **Hybrid XGBoost + GJR-GARCH**: Non-linear gradient boosting conditioned on asymmetric volatility filter.
   - **Dynamic Minimum-Error Stacking Ensemble**: Inverse-variance weighted synthesis selecting the champion architecture with lowest Out-of-Sample RMSE, MAE, and MAPE.
3. **Institutional Strategy Diagnostics**:
   - **Directional Accuracy**: Hit rate percentage of predicting sign of actual return $(\text{sgn}(\hat{r}_t) == \text{sgn}(r_t))$.
   - **Cumulative Strategy Equity**: Compares dynamic long/cash model execution versus Buy & Hold baseline.
   - **Risk-Adjusted Ratios**: Realized Sharpe ratio, Win Rate, Profit Factor, and Maximum Drawdown.

---

## 21. Quantitative Trade Execution Plan & ATR-Calibrated Multi-Horizon TP/SL Ladder

### 21.1 Overview and Purpose
Institutional execution requires mathematically rigorous entry, risk containment, and take-profit milestones rather than arbitrary heuristics. The Quantitative Trade Execution Plan provides algorithmic execution guidance calibrated to the stock's Average True Range (ATR) and customized to the trader's total capital and risk tolerance per trade.

### 21.2 Mathematical Formulation
1. **Volatility-Adjusted Position Sizing**:
   $$\text{Risk Capital (IDR)} = \text{Total Capital} \times \frac{\text{Risk Per Trade \%}}{100}$$
   $$\text{Risk Per Share (IDR)} = \max(\text{Entry Price} - \text{Stop Loss Price}, 1)$$
   $$\text{Max Position Lots} = \left\lfloor \frac{\text{Risk Capital}}{\text{Risk Per Share} \times 100} \right\rfloor$$
2. **ATR-Calibrated Trailing Stop Loss**:
   $$\text{Stop Loss} = \text{Entry Price} - (k_{\text{SL}} \times \text{ATR}_{14})$$
   where $k_{\text{SL}} \approx 1.5$ standard deviations of daily price volatility.
3. **Multi-Horizon Profit Targets**:
   - **TP1 (Quick Tactical / Breakeven Lock, 1.5R)**: $\text{Entry} + 1.5 \times (\text{Entry} - \text{SL})$
   - **TP2 (Primary Horizon / Trend Target, 2.5R)**: $\text{Entry} + 2.5 \times (\text{Entry} - \text{SL})$
   - **TP3 (Runner / Institutional Extension, 4.0R)**: $\text{Entry} + 4.0 \times (\text{Entry} - \text{SL})$
4. **Pullback Entry Zone**:
   - Aggressive Entry: Current Market Ask Price.
   - Conservative Entry: Support zone at $\text{Current Price} - (0.5 \times \text{ATR}_{14})$.

---

## 22. Relative Rotation Graph (RRG) & Cross-Sector Institutional Flow Matrix

### 22.1 Overview and Purpose
Capital in the Indonesia Stock Exchange (IDX) continually rotates across sectors based on macroeconomic regimes, commodity cycles, interest rates, and institutional liquidity flows. The Relative Rotation Graph (RRG) plots sectors across two orthogonal dimensions to identify sector leadership transitions before they reflect in headline index moves.

### 22.2 Mathematical Metrics
1. **Relative Strength Ratio (RS-Ratio)**:
   $$\text{RS-Ratio}_t = 100 + \left( \frac{\text{Sector Price}_t / \text{IHSG}_t}{\text{SMA}_{n}(\text{Sector Price} / \text{IHSG})} - 1 \right) \times 100$$
2. **Relative Strength Momentum (RS-Momentum)**:
   $$\text{RS-Momentum}_t = 100 + \left( \frac{\text{RS-Ratio}_t}{\text{SMA}_{m}(\text{RS-Ratio})} - 1 \right) \times 100$$
3. **Four-Quadrant Institutional Rotation Classification**:
   - **Leading (RS-Ratio $\ge 100$, RS-Momentum $\ge 100$)**: Outperforming benchmark with accelerating momentum. Prime overweight candidate.
   - **Weakening (RS-Ratio $\ge 100$, RS-Momentum $< 100$)**: Outperforming benchmark but losing relative velocity. Profit-taking stage.
   - **Lagging (RS-Ratio $< 100$, RS-Momentum $< 100$)**: Underperforming benchmark with negative momentum. Avoid or underweight.
   - **Improving (RS-Ratio $< 100$, RS-Momentum $\ge 100$)**: Underperforming benchmark but rapidly gaining relative velocity. Early accumulation candidate.
4. **Institutional Net Foreign Flow Overlay**:
   Integrates 5-day rolling net foreign institutional buying or selling (IDR Billion) to validate whether sector price momentum is supported by real institutional accumulation.






