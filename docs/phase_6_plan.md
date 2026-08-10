# Phase 6 Dashboard Integration Plan

## Goal

Integrate the completed analytics and model evidence into a Streamlit dashboard that reads precomputed artifacts. Page rendering must not fit GARCH models, train classical models, or load foundation models for inference.

## 6.1 Architecture and data contract

Status: complete.

The dashboard separates committed governance artifacts from generated runtime artifacts.

Committed governance and evidence include model registries, model decisions, and foundation benchmark evidence. Generated runtime artifacts include processed analytics, latest GARCH risk snapshots, and latest direction probability snapshots.

## 6.2 Latest direction snapshot pipeline

Status: complete.

The classical deployment registry freezes ticker-specific model families and reconstructed deployment hyperparameters. The latest probability pipeline refits the frozen configuration on all currently available labeled history and predicts only the latest unlabeled feature row.

Exact Phase 4 metric reproduction is not claimed because the original raw market data and exact dependency lock were not versioned.

## 6.3 Dashboard data access

Status: in progress.

Deliverables:

- one validated loader for analytics, risk snapshot, direction snapshot, model registries, and foundation evidence;
- ticker and date alignment checks across runtime artifacts;
- readable errors for missing or invalid runtime artifacts;
- automated tests for missing files, schema errors, ticker mismatches, stale snapshots, and invalid probabilities;
- GitHub Actions quality gate for Ruff, pytest, and text rules.

## 6.4 Main dashboard pages

Status: planned.

Pages will cover market overview, stock explorer, GARCH and tail-risk evidence, direction probability, and a consolidated risk view. Historical volatility remains descriptive while the risk view uses registry-selected GARCH forecasts and VaR.

## 6.5 Model evidence and Learn

Status: planned.

Kronos and Granite remain visible as experimental benchmarks, including the evidence explaining why they were not promoted to production forecasting. The Learn page will explain return, volatility, drawdown, VaR, model uncertainty, and evaluation limitations.

## 6.6 UX and robustness

Status: planned.

Add clear educational disclaimers, friendly missing-data states, consistent labels, caching for precomputed artifacts, responsive charts, and performance checks. The dashboard must not show BUY, SELL, or target-price language.

## 6.7 Deployment readiness

Status: planned.

Prepare Streamlit Community Cloud deployment, define runtime artifact provisioning, document update operations, and run final acceptance checks.

## Governance guardrails

The GARCH registry remains `provisional_out_of_sample_selection` until a separate process explicitly changes that status.

Classical model selection remains based on validation log loss with Brier score as the tie-breaker. Test results are not used for selection.

Kronos and Granite remain experimental benchmarks. Frozen evaluation sets must not be reused for tuning decisions.
