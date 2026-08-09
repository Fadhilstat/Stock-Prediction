# Phase 5.4 Final Model Decision Registry

## Decision principle

Ruang Risiko IDX does not use a single leaderboard across all models.

GARCH-family models estimate volatility and tail risk. Classical
machine-learning models estimate daily direction probability. Kronos
and Granite TTM are forecasting benchmarks with different targets.

Because these tasks are different, their metrics are not combined into
one score.

No model was retrained or tuned during Phase 5.4. This phase only
consolidates decisions that were already supported by their original
evaluation protocols.

## Risk and volatility

The GARCH registry keeps its source status exactly as recorded:

`provisional_out_of_sample_selection`

Volatility selection is based primarily on mean QLIKE from a daily
expanding walk-forward evaluation with 252 observations. VaR selection
also considers the reported coverage and independence tests.

| Ticker | Volatility model | VaR model |
| --- | --- | --- |
| ANTM.JK | egarch_normal | egarch_student_t |
| ASII.JK | egarch_student_t | egarch_student_t |
| BBCA.JK | gjr_garch_student_t | gjr_garch_student_t |
| BBRI.JK | gjr_garch_normal | gjr_garch_normal |
| TLKM.JK | egarch_student_t | egarch_student_t |
| ^JKSE | gjr_garch_normal | gjr_garch_student_t |

These selections are used for the risk analytics role while retaining
the provisional status from the source registry.

## Direction probability

Classical model selection uses validation log loss as the primary
metric and validation Brier score as the tie-breaker.

Test results were not used for model selection.

| Ticker | Selected model | Validation log loss | Test ROC AUC |
| --- | --- | ---: | ---: |
| ANTM.JK | logistic_regression | 0.697890 | 0.522303 |
| ASII.JK | random_forest | 0.678386 | 0.543658 |
| BBCA.JK | random_forest | 0.665981 | 0.616697 |
| BBRI.JK | constant_probability | 0.690664 | 0.500000 |
| TLKM.JK | random_forest | 0.687179 | 0.530485 |
| ^JKSE | constant_probability | 0.689175 | 0.500000 |

A simple constant-probability baseline remains selected when it wins
under the frozen validation rule. Model complexity is not treated as
a selection criterion.

## Kronos

Role: `experimental_benchmark`

Production selection: `not_selected`

The full evaluation contained 1,512 rolling
forecasts.

Decision reason:

Random walk produced the lowest close MAE and log-return MAE for all six evaluated market series.

Kronos remains useful as an OHLCV foundation-model benchmark, but it is
not promoted to production forecasting.

## Granite TTM

Role: `experimental_benchmark`

Production selection: `not_selected`

The full evaluation contained 1,260 rolling
forecasts.

Granite beat return persistence on return MAE for
5 of
5 stocks, but beat random walk on
0 of
5 stocks.

Granite therefore remains a return-forecasting benchmark and is not
promoted to production forecasting.

## Final task assignments

Risk and volatility analytics use the ticker-specific GARCH registry.

Direction probability uses the ticker-specific classical validation
registry.

No foundation model is selected as the production OHLCV or return
forecasting model.

Kronos and Granite remain visible in the project as experimental
benchmarks because their evaluations provide useful evidence about the
limits of model complexity.

## Guardrails

The dashboard must not present these models as buy, sell, or target
price recommendations.

Foundation-model test sets remain frozen. Future fine-tuning or
multivariate experiments require a separately defined validation
protocol.

The GARCH registry must continue to be described as provisional until
a later process explicitly changes that status.
