# Phase 5.3 Granite TTM Decision

## Scope

Granite TTM R2.1 was evaluated as a zero-shot univariate
forecasting baseline for daily log returns.

Model revision: `512-48-ft-r2.1`

Context length: 512 observations

Forecast horizon: one trading day

Evaluation: 252 recent targets for each of five IDX stocks

Total forecasts: 1,260

The evaluation was frozen before the full run. No configuration
changes or fine-tuning were selected using these test results.

## Leakage and execution audit

The full run produced 1,260 forecasts with 252 observations for
each ticker. There were no duplicate ticker and target-date
windows. Every target date occurred after its context cutoff, and
all required numeric outputs were finite.

The full run completed in 45.62 seconds
on CPU.

## Return MAE

| Ticker | Granite TTM | Random walk | Return persistence |
| --- | ---: | ---: | ---: |
| ANTM.JK | 0.028038 | 0.025821 | 0.039749 |
| ASII.JK | 0.020156 | 0.018425 | 0.030770 |
| BBCA.JK | 0.016736 | 0.015551 | 0.022969 |
| BBRI.JK | 0.015555 | 0.014928 | 0.020661 |
| TLKM.JK | 0.020523 | 0.019618 | 0.027828 |

Granite TTM did not beat the zero-return random-walk baseline on
return MAE for any of the five stocks.

Granite TTM did beat the return-persistence baseline on return MAE
for all five stocks.

Directional metrics were generally close to chance. The results
do not provide sufficiently consistent evidence for promoting
Granite TTM to a production forecasting model.

## Decision

Granite TTM R2.1 remains an experimental foundation-model
benchmark.

It is not selected for production forecasting in Ruang Risiko IDX.

The model is retained because it provides a reproducible
foundation-model comparison and performs better than the return
persistence baseline, while still demonstrating the importance of
testing complex models against simple baselines.

No fine-tuning will be performed against this frozen 252-day test
set. Any future multivariate or channel-mixing experiment must use
a separately defined validation protocol and must preserve this
test set as untouched final evidence.
