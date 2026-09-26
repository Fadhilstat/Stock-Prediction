# Ruang Risiko IDX Durable Architecture and Engineering Handoff

## 1. Product Mission and Positioning
Ruang Risiko IDX is an Indonesian equity research, risk quantification, probabilistic forecasting, and pre-buy decision-support platform.
It serves as an analytical research cockpit for investors and researchers evaluating Bursa Efek Indonesia (IDX) stocks.
The platform emphasizes point-in-time safety, visible forecast uncertainty, realistic Indonesian market friction, and a strict Risk Engine hard veto.

## 2. Market Universe and Canonical Data Architecture
- Core Universe: ANTM.JK, ASII.JK, BBCA.JK, BBRI.JK, TLKM.JK, and the benchmark index ^JKSE.
- Canonical Schema: Long-form daily records containing ticker, trade_date, open, high, low, close, volume, and adjusted_close.
- Strict Ingestion Pipeline:
  Provider (yfinance) -> Raw Validation -> Quarantine Isolation -> Canonical Merging -> Audit Trail.
  Any row failing price sanity checks (negative price, low > high, missing OHLC) is quarantined into an append-only audit snapshot.

## 3. Econometric Volatility and Tail Risk (GARCH)
- Modeling Framework: ARCH, GARCH, EGARCH, and GJR-GARCH with normal and Student-t innovations.
- Selection Standard: Minimum QLIKE loss in expanding walk-forward out-of-sample evaluation (252 observations) alongside Kupiec POF and Christoffersen independence tests for Value at Risk (VaR).
- Selected Volatility Models:
  - ANTM.JK: EGARCH Normal
  - ASII.JK: EGARCH Student-t
  - BBCA.JK: GJR-GARCH Student-t
  - BBRI.JK: GJR-GARCH Normal
  - TLKM.JK: EGARCH Student-t
  - ^JKSE: GJR-GARCH Normal

## 4. Machine Learning Direction Probability
- Modeling Framework: Logistic Regression, Random Forest, XGBoost, and naive Constant Probability baseline.
- Validation Rule: Model selection strictly based on out-of-fold validation log loss and Brier score.
- Model Assignments:
  - ANTM.JK: Logistic Regression (C=0.01)
  - ASII.JK: Random Forest (n_estimators=400, min_samples_leaf=10)
  - BBCA.JK: Random Forest (n_estimators=400, min_samples_leaf=10)
  - BBRI.JK: Constant Probability baseline
  - TLKM.JK: Random Forest (n_estimators=400, min_samples_leaf=25)
  - ^JKSE: Constant Probability baseline

## 5. Foundation Models Benchmarks (Kronos and Granite TTM)
- Evaluations in Phase 5 demonstrated that simple random walk baselines outperformed foundation models in Indonesian equity price forecasting.
- Kronos-small and Granite TTM R2 remain in the codebase as empirical research benchmarks to prevent over-promising complexity.

## 6. Multi-Horizon Probabilistic Forecasting and Scenarios
- Horizons: 1 trading day (1D), 5 trading days (5D), 20 trading days (20D).
- Quantiles: Explicit probability distributions across q10, q25, q50, q75, and q90.
- Scenario Engine: Generates bull, base, bear, volatility shock, and regime reversal paths with transparent driver attribution.

## 7. Research Layers
- Technical Indicators: Trend moving averages (20, 50, 200), RSI-14, MACD, Bollinger Bands, ATR.
- ICT Hypotheses: Market Structure Shift (MSS), Liquidity Sweep, Fair Value Gap (FVG), Order Blocks.
- Fundamental Point-in-Time Intelligence: Financial ratios, margins, earnings quality checks, and valuation percentiles.
- Flow Evidence: Foreign net accumulation/distribution persistence, broker concentration proxies.
- Social & Creator Intelligence: Public creator claim ledgers, thesis aging, and narrative acceleration.
- Multimodal Fusion & Conflict Radar: Explicitly highlights disagreements between technical, fundamental, and flow signals.

## 8. Pre-Buy Decision Passport and Risk Engine
- Decision States: FAVORABLE_SETUP, WATCH, WAIT, AVOID, HIGH_RISK, EVENT_RISK, INSUFFICIENT_DATA.
- Final Veto: The Risk Engine overrides all directional forecasts if volatility spikes, liquidity drops, or event risk is elevated.
- Passport Artifact: Structured summary capturing all cutoff evidence, forecast distributions, invalidation rules, and execution notes.

## 9. Design System and Anti-Slop Policy
- Theme: Analytical dark theme (#0B0F19 background, #111827 surfaces, #1F2937 borders).
- Semantics: Green (#10B981) for bullish, red (#EF4444) for bearish, amber (#F59E0B) for caution.
- Strict Anti-Slop: Zero generic AI gradients, zero decorative grids, zero dead controls, and zero em dashes.

## 10. Operations, CI/CD, and Release Profile
- Git Authority: Forgejo VPS (primary), GitLab CI/CD with Contabo runner (automation), Google Drive (rolling checkpoint).
- Release Lifecycle: Develop -> Test -> Lint -> Validate -> Staging -> APPROVE PUSH -> Push -> CI -> APPROVE MERGE -> Merge -> Deploy.
- Exact Next Step: Complete dashboard interactive experience and execute end-to-end integration validation.
