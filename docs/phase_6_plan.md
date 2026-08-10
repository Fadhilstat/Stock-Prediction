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

Status: complete.

The dashboard now has one validated loader for analytics, risk snapshots, direction snapshots, model registries, and foundation evidence. Runtime artifacts are checked for ticker alignment, date alignment, duplicate rows, probability validity, and training boundaries before they reach Streamlit.

Readable errors cover missing or invalid artifacts. Synthetic tests protect the core data contract, and GitHub Actions runs Ruff, pytest, and text rules automatically on pull requests and pushes to `main`.

## 6.4 Main dashboard pages

Status: complete.

The main dashboard now covers market overview, stock exploration, GARCH and tail-risk estimates, direction probability, and a consolidated cross-ticker risk view. Historical volatility remains descriptive, while the risk page reads the precomputed registry-selected GARCH forecast and VaR snapshot.

The interface explains what each metric is trying to answer before presenting the number. Direction probability is kept separate from risk magnitude so users are not encouraged to interpret unrelated outputs as one trading score.

The Streamlit layer does not fit models. Presentation helpers prepare market and risk summaries separately from the page code so the transformation logic can be tested without launching the dashboard.

## 6.5 Model evidence and Learn

Status: complete.

The dashboard now presents the evidence behind each model role rather than showing only the models that performed well. GARCH remains provisional and task-specific. Classical direction models show validation metrics separately from test metrics so the selection process stays visible.

Kronos and Granite remain experimental benchmarks. Their frozen results are shown with the baseline comparisons that prevented promotion to production forecasting. Negative results are treated as useful evidence rather than hidden from the user.

The Learn section explains return, volatility, drawdown, VaR, walk-forward evaluation, and baseline comparisons in plain language. External references used for educational context are recorded in the source registry and rechecked for live access before inclusion.

## 6.6 UX and robustness

Status: complete.

Runtime errors are translated into public-facing guidance that explains what happened and what to do next without exposing local file paths or unnecessary implementation detail. The application still stops when artifact validation fails, because displaying inconsistent data would be worse than showing a clear error state.

GARCH convergence warnings remain visible at ticker level. The dashboard does not hide a warning or discard the output silently. Instead, it keeps the estimate visible and asks the user to interpret it more cautiously.

Precomputed artifacts remain cached, charts use the available container width, and educational disclaimers stay visible throughout the main experience. No buy, sell, target-price, or synthetic trading-score language is introduced.

## 6.7 Deployment readiness

Status: complete.

The public dashboard now has a dedicated deployment bundle instead of depending on ignored local runtime files. The bundle contains only the analytics columns used by the interface, the latest risk snapshot, the latest direction snapshot, and an integrity manifest. Raw market data remains outside the repository.

The deployment loader verifies file checksums, manifest counts, ticker alignment, date alignment, and committed model governance before returning data to Streamlit. Local canonical runtime data still has priority during development, while Community Cloud can fall back to the committed bundle.

GitHub Actions rebuilds the runtime pipeline on relevant changes to `main` and on weekday evenings in the Asia/Jakarta timezone. Only a fully validated bundle is committed. Streamlit Community Cloud dependency and entrypoint requirements are documented separately in `docs/deployment.md`.

## Governance guardrails

The GARCH registry remains `provisional_out_of_sample_selection` until a separate process explicitly changes that status.

Classical model selection remains based on validation log loss with Brier score as the tie-breaker. Test results are not used for selection.

Kronos and Granite remain experimental benchmarks. Frozen evaluation sets must not be reused for tuning decisions.

Project-wide writing, source, and code principles are defined in `docs/project_guidelines.md` and apply to all remaining Phase 6 work.
