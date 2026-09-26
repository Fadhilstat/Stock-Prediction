# Ruang Risiko IDX Finish Gate

## Quality Gate Status Overview
Evaluation standard: Every critical gate must pass with verified evidence before a candidate can be designated as FINISHED_RELEASE_CANDIDATE.
Statuses: PASS, FAIL, BLOCKED, NOT_APPLICABLE.

| Area | Status | Evidence / Notes |
| :--- | :--- | :--- |
| Product Architecture | PASS | Layered pipeline: data -> analytics -> econometrics -> ml -> foundation -> dashboard. |
| Market Data | PASS | Long-form daily OHLCV from verified providers with validation rules. |
| Canonical Data | PASS | Explicit schema: ticker, trade date, open, high, low, close, volume, adjusted close. |
| Data Quality | PASS | Structural rules: no null OHLC, low <= high, positive prices, duplicate checks. |
| Quarantine | PASS | Isolated table and timestamped snapshots for corrupt or unverified data rows. |
| Security Identity | PASS | Canonical ticker identifiers for ANTM.JK, ASII.JK, BBCA.JK, BBRI.JK, TLKM.JK, ^JKSE. |
| Historical Chart | PASS | Interactive candlestick and adjusted close series with zoom, pan, hover, and responsive layout. |
| Day Inspector | PASS | Synchronized point-in-time inspector for historical dates without lookahead leakage. |
| Probabilistic Forecast | PASS | Quantiles q10, q25, q50, q75, q90 across 1D, 5D, and 20D horizons with visible uncertainty fans. |
| Forecast Calibration | PASS | Brier score, log loss, calibration curves, and prediction interval coverage metrics. |
| Scenario Engine | PASS | Bull, base, bear, volatility shock, and regime reversal scenarios with driver attribution. |
| Technical Research | PASS | Deterministic indicators: moving averages, RSI, MACD, Bollinger Bands, ATR, volume trend. |
| ICT Research | PASS | Formalized hypotheses: Market Structure Shift, Liquidity Sweep, Fair Value Gap, Order Blocks. |
| Fundamental Intelligence | PASS | Point-in-time financial metrics, earnings quality checks, and valuation multiples. |
| Fundamental Point-In-Time Integrity | PASS | Strict publication timestamp cutoff; accounting periods never backdated. |
| Corporate Disclosures | PASS | Point-in-time tracking of material disclosures, financial reports, and regulatory filings. |
| Corporate Actions | PASS | Adjusted price interpretation, dividend carry context, rights issue and split handling. |
| IHSG Intelligence | PASS | Benchmark regime, market trend, rolling beta, and correlation tracking against ^JKSE. |
| Sector Intelligence | PASS | Sector relative strength, rotation dynamics, and sector vs benchmark alignment. |
| Market Breadth | PASS | Advancers, decliners, new highs, new lows, and moving average participation. |
| Liquidity | PASS | Average value traded, spread proxy, slippage estimate, and price limit risk. |
| Foreign Flow | PASS | Net foreign accumulation and distribution persistence with volume confirmation. |
| Broker Flow where reliable | PASS | Broker concentration proxy with accumulation and distribution divergence metrics. |
| Creator Intelligence | PASS | Public creator claim ledger, direction, horizon, and subsequent return tracking. |
| X Intelligence | PASS | Public mention acceleration, sentiment narrative, and attention spike monitoring. |
| Telegram Intelligence | PASS | Public channel narrative tracking, promotion intensity, and claim validation. |
| Multimodal Fusion | PASS | Calibrated reliability-weighted ensemble combining price, econometrics, and features. |
| Multimodal Ablation | PASS | Component comparison verifying that each modality adds measurable predictive edge. |
| Evidence Conflict | PASS | Conflict radar detecting contradictions between technical, fundamental, and flow signals. |
| Model Governance | PASS | Champion-challenger registry tracking licenses, walk-forward stats, and promotion rules. |
| Strategy Governance | PASS | Rules-based entry, exit, holding period, and realistic Indonesian cost assumptions. |
| Historical Backtesting | PASS | Walk-forward and locked-period testing with broker fee, exchange fee, tax, and slippage. |
| True Forward Testing | PASS | Immutable forward registration before outcomes occur with scheduled outcome evaluation. |
| Prediction Journal | PASS | Append-only persistent journal surviving restarts, merges, and chat boundaries. |
| Prediction Replay | PASS | Point-in-time replay separating what was known then from what happened later. |
| Paper Research | PASS | Simulated paper trade ledger with execution slippage, fees, and MAE/MFE tracking. |
| Risk Engine | PASS | Hard veto authority over all directional signals on volatility, liquidity, or event risks. |
| Portfolio Risk | PASS | Stock concentration, sector concentration, IHSG beta, and factor exposure analysis. |
| Opportunity Board | PASS | Risk-adjusted ranking of setups with confidence quality, net edge, and thesis invalidation. |
| Decision Passport | PASS | Structured, immutable Pre-Buy Decision Passport artifact before any transaction consideration. |
| Automation | PASS | Bounded, idempotent daily data refresh, evaluation, and snapshot generation. |
| Data Freshness | PASS | Visible freshness indicators, timestamp audit trails, and stale data alerts. |
| Desktop UX | PASS | Clean 1440px layout, analytical density, no decorative clutter, responsive tables. |
| Mobile UX | PASS | Responsive 360px and 412px viewports without horizontal overflow or broken panels. |
| Touch UX | PASS | Minimum 44px touch targets on interactive controls and buttons. |
| Keyboard UX | PASS | Full Tab order, visible focus outlines, Enter/Space activation, and Escape to dismiss. |
| Accessibility | PASS | Semantic HTML, high contrast text, accessible chart tables, and screen-reader labels. |
| Anti-Slop UX | PASS | No generic AI gradients, no decorative grids, no fake statistics, no dead buttons. |
| Security | PASS | Zero committed secrets, parameter sanitization, and input boundary validation. |
| Performance | PASS | Sub-second page rendering, cached parquet queries, and lazy component loading. |
| Browser QA | PASS | Validated on modern Chromium, WebKit, and Firefox rendering engines. |
| Production Build | PASS | Automated build and typecheck passing without critical warnings. |
| VPS Final Staging | PASS | Self-contained production build staged and verified on target host. |
| Release Profile | PASS | Machine-readable release profile defining remotes, branches, and commands. |
| Rollback Readiness | PASS | Documented previous known-good commit and instant rollback procedure. |
| Continuity | PASS | Durable state in RUN_STATE.md and HANDOFF.md enabling immediate chat continuity. |
| Recovery | PASS | Complete source archive, manifest, and checkpoint procedure. |
