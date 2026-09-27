# RUANG RISIKO IDX (RRIDX) - MASTER CONTEXT HANDOVER & ARCHITECTURE SPECIFICATION
**Version:** 1.13 | **Last Updated:** 2026-09-28 | **Repository:** https://github.com/Fadhilstat/Stock-Prediction.git | **Live Production:** https://rridx.fadhilrusydi.com/

---

## 1. Executive Overview & Mission
Ruang Risiko IDX (RRIDX) is an institutional-grade quantitative risk analysis, time-series forecasting, and automated market microstructure intelligence platform tailored for the Indonesia Stock Exchange (IDX / BEI).
- **Core Paradigm:** Autonomous, non-RDC, high-frequency institutional intelligence engine.
- **Frontend Standard:** Stockbit-style dark theme terminal with interactive financial charts and remote governance console.
- **Backend Standard:** FastAPI asynchronous web engine (`uvicorn`) running in Docker on a Contabo VPS.
- **CI/CD & Deployment:** 100% autonomous. Commits pushed to `origin/main` are pulled, built, and reloaded within 60 seconds by an active systemd timer daemon on the VPS without manual SSH or terminal commands.

---

## 2. Infrastructure & Production Environment
- **Live URL:** `https://rridx.fadhilrusydi.com/` (HTTP/2, SSL via Let's Encrypt automated by Caddy).
- **Server:** Contabo VPS `46.250.231.247` (Hostname: `vmi3564789`).
- **App Path on Server:** `/opt/ruang-risiko-idx`
- **Reverse Proxy Routing:**
  - Container `signalflow-production-caddy-1` routes `rridx.fadhilrusydi.com` to `172.17.0.1:8501`.
  - Application container `ruang_risiko_idx_app` listens on port `8501`.
- **Autonomous Auto-Updater Daemon:**
  - Active systemd service & timer: `rridx-autoupdate.service` / `rridx-autoupdate.timer` (runs every 60s).
  - Skrip: `/opt/ruang-risiko-idx/deploy/auto_update.sh`.
  - When `origin/main` changes, it executes `git reset --hard origin/main`, `docker compose up -d --build app`, connects Docker networks, updates Caddy reverse proxy block, and reloads Caddy.
  - Zero manual deployment is needed from now on.

---

## 3. Directory Structure & Key Components
```text
Stock-Prediction/
├── deploy/
│   ├── auto_update.sh           # Autonomous auto-updater daemon on VPS
│   └── enable_autoupdate.sh     # Systemd installer for continuous 60s auto-deployment
├── src/ruang_risiko_idx/
│   ├── web_server.py            # FastAPI main application with all REST API endpoints
│   ├── web/
│   │   ├── index.html           # Stockbit-style terminal dashboard (Tabbed UI, Action Console)
│   │   ├── app.js               # Dashboard controller, TradingView-style charts, AJAX handlers
│   │   └── style.css            # Dark mode terminal styling, badges, grid layouts
│   └── research/
│       ├── black_litterman.py   # Black-Litterman AI prior views & Sharpe optimization engine
│       ├── alert_dispatcher.py  # Automated institutional anomaly, spoofing & whale accumulation radar
│       ├── stress_testing.py    # Non-linear macro stress testing & orderbook slippage simulator
│       ├── hf_finbert_sentiment.py # FinBERT NLP sentiment entropy & market polarization index
│       ├── hf_foundation_forecaster.py # Chronos-T5, Informer & dynamic ensemble minimum-error tournament
│       ├── broker_network.py    # Institutional broker graph clustering & Smart Money Index (SMI)
│       ├── passport_evaluator.py # Pre-buy institutional risk passport scorecard
│       ├── multimodal_engine.py # Multi-modal synthesis (fundamentals, volatility, momentum)
│       ├── dcc_garch.py         # Dynamic Conditional Correlation GARCH volatility engine
│       ├── copula_evt.py        # Extreme Value Theory (EVT) & Clayton/Gumbel tail risk copula
│       ├── spillover_index.py   # Diebold-Yilmaz 2012 volatility spillover index
│       ├── hmm_regimes.py       # Hidden Markov Model 3-state market regime detector
│       ├── pareto_portfolio.py  # Multi-objective Pareto frontier risk-return optimizer
│       └── actions.py           # Web action executors with audit ledger logging
├── tests/
│   └── test_fastapi_and_innovations.py # Consolidated unit tests
├── Dockerfile                   # Optimized multi-stage build with cached pip dependency layer
├── docker-compose.yml           # Production Docker Compose specification
├── pyproject.toml               # Project package metadata and pytest configurations
└── DESIGN.md                    # Institutional architecture and quant methodology documentation
```

---

## 4. Key Quantitative Engines Implemented
1. **Black-Litterman AI Portfolio Optimizer (`black_litterman.py`):**
   - Combines classical market equilibrium priors with subjective views from Hugging Face Chronos-T5 drift, FinBERT Shannon entropy uncertainty scaling, and Smart Money Index.
   - Solves constrained SLSQP optimization to maximize Sharpe ratio under single-asset limits (default 25%) and VaR 99% risk budgets.
   - Endpoint: `POST /api/v1/portfolio/black-litterman`

2. **Automated Anomaly & Signal Alert Radar (`alert_dispatcher.py`):**
   - Scans IDX equity universe for foreign whale accumulation, orderbook spoofing risk, information entropy discord, and macro stress vulnerability.
   - Categorizes alerts by severity: `CRITICAL`, `WARNING`, `INFO` with actionable steps.
   - Endpoint: `GET /api/v1/alerts/live`

3. **Macro Stress Lab & Non-Linear Slippage Simulator (`stress_testing.py`):**
   - Simulates Fed rate shocks, commodity collapses, liquidity draughts, and currency devaluations.
   - Models square-root orderbook market impact and liquidity exhaustion for institutional execution.
   - Endpoints: `POST /api/v1/risk/stress-test/{ticker}`, `POST /api/v1/risk/liquidity-simulator`

4. **Hugging Face Foundation Model Tournament (`hf_foundation_forecaster.py`):**
   - Automatically benchmarks Hugging Face Chronos-T5, Informer, and Hybrid XGBoost + GJR-GARCH.
   - Selects the champion model with the lowest RMSE, MAE, and MASE, and computes 95% conformal prediction intervals.
   - Endpoint: `GET /api/v1/forecast/foundation/{ticker}`

5. **FinBERT Market Entropy & Polarization (`hf_finbert_sentiment.py`):**
   - Measures institutional news entropy using Shannon Entropy. High entropy indicates deep disagreement among market participants, scaling up volatility multipliers.
   - Endpoint: `GET /api/v1/sentiment/finbert?ticker={ticker}`

6. **Institutional Broker Cluster Matrix (`broker_network.py`):**
   - Tracks foreign institutional broker codes (ZP, BK, AK, CS, CC, RX) vs retail broker flows (PD, XC, YP) to compute the Smart Money Index (SMI) and absorption ratios.
   - Endpoint: `GET /api/v1/market/broker-network/{ticker}`

7. **Web Governance Action Console:**
   - Provides web-based triggers to execute any research, risk recalculation, or optimization job from the browser without opening a terminal.
   - Every execution is recorded in an immutable audit ledger (`reports/audit/action_ledger.json`).
   - Endpoint: `POST /api/v1/actions/execute`

---

## 5. Development & Coding Rules (Mandatory)
1. **CRITICAL HARD CONSTRAINT - ZERO EM DASH:**
   - Never use the em dash character (unicode code point U+2014) in any code, comment, docstring, markdown document, commit message, or conversation response.
   - Always use standard hyphens `-`, colons `:`, parentheses `()`, or rewrite sentences.
2. **Autonomous Push & Merge Flow:**
   - Commit changes to `origin/main` automatically without waiting or prompting the user for confirmation ("APPROVE PUSH & APPROVE MERGE").
   - The VPS will auto-pull and deploy within 60 seconds.
3. **Speed & Testing:**
   - Always run pytest with `-p no:cov` to avoid filesystem crawling hangs:
     `python -m pytest -p no:cov tests/test_fastapi_and_innovations.py`
4. **UI Design Standard:**
   - Adhere strictly to the Stockbit dark terminal aesthetic: deep dark background (`#0b0e14`, `#121824`), crisp borders (`#1e293b`), neon green/cyan indicators (`#00e676`, `#00d2ff`), and clean typography.
