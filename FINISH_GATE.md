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
| Orderbook 10-Level Depth | PASS | Official IDX 10-level bid/offer depth queue, lot counts, and ARA/ARB boundary calculation. |
| Bandarmology & Broker Summary | PASS | Stockbit-style top buyer/seller broker breakdown, concentration ratios, and flow status. |
| Creator Intelligence | PASS | Public creator claim ledger, direction, horizon, and subsequent return tracking. |
| Multimodal Fusion | PASS | Calibrated reliability-weighted ensemble combining price, econometrics, and features. |
| Multimodal Ablation | PASS | Component comparison verifying that each modality adds measurable predictive edge. |
| Evidence Conflict | PASS | Conflict radar detecting contradictions between technical, fundamental, and flow signals. |
| Model Governance | PASS | Champion-challenger registry tracking licenses, walk-forward stats, and promotion rules. |
| Strategy Governance | PASS | Rules-based entry, exit, holding period, and realistic Indonesian cost assumptions. |
| Historical Backtesting | PASS | Walk-forward and locked-period testing with broker fee, exchange fee, tax, and slippage. |
| True Forward Testing | PASS | Immutable forward registration before outcomes occur with scheduled outcome evaluation. |
| Prediction Journal | PASS | Append-only persistent journal surviving restarts, merges, and chat boundaries. |
| Risk Engine | PASS | Hard veto authority over all directional signals on volatility, liquidity, or event risks. |
| Decision Passport | PASS | Structured, immutable Pre-Buy Decision Passport artifact before any transaction consideration. |
| Web Action Console | PASS | Live operational control plane for model recalibration, data updates, and runtime tuning. |
| Non-RDC Autonomous Deployment | PASS | Headless Docker Compose and Caddy reverse proxy with automated ACME TLS and healthcheck. |
| Anti-Slop UX | PASS | Stockbit-inspired dark theme, zero generic AI slop, no dead buttons, zero em dash policy. |
| Security | PASS | Zero committed secrets, parameter sanitization, and input boundary validation. |
| Performance | PASS | Sub-second page rendering, cached parquet queries, and lazy component loading. |
| Rollback Readiness | PASS | Documented previous known-good commit and instant rollback procedure. |
| Continuity | PASS | Durable state in RUN_STATE.md and HANDOFF.md enabling immediate chat continuity. |
