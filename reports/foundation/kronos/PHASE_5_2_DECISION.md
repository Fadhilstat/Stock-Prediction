# Phase 5.2 Decision: Kronos Rolling Zero-Shot Backtest

## Objective

This experiment evaluated whether Kronos-small could provide useful
one-day-ahead zero-shot forecasts for five Indonesian stocks and the
IDX Composite.

The goal was not to force a foundation model into production. The goal
was to compare it fairly with simple baselines and retain it only when
the evidence supported that decision.

## Evaluation design

The evaluation covered six market series:

- ANTM.JK
- ASII.JK
- BBCA.JK
- BBRI.JK
- TLKM.JK
- ^JKSE

Each series used 252 rolling one-step forecasts with a stride of one
trading day. This produced 1,512 forecasts in total.

Every forecast used 400 historical observations. The Kronos
configuration was frozen before the full evaluation:

- Model: NeoQuasar/Kronos-small
- Tokenizer: NeoQuasar/Kronos-Tokenizer-base
- Prediction length: 1
- Temperature: 1.0
- Top-k: 0
- Top-p: 0.9
- Sample count: 1
- Base seed: 42

Kronos was compared with two naive baselines:

1. Random walk, where the next close equals the latest observed close.
2. Return persistence, where the next log return equals the latest
   observed log return.

## Technical result

The pipeline completed all 1,512 forecasts.

The audit found:

- 0 duplicate forecast windows
- All target dates occurred after their cutoff dates
- All evaluated numeric values were finite
- All actual and predicted close values were positive
- All predicted volume values were nonnegative
- 90.08 percent of predictions had valid OHLC relationships

There were 150 forecasts with invalid OHLC relationships. These raw
outputs were retained without clipping or correction so the model's
limitations remain visible.

## Predictive result

Random walk achieved the lowest close MAE for all six market series.

Random walk also achieved the lowest log-return MAE for all six market
series.

Kronos showed limited directional value for selected series. Its
balanced accuracy and ROC AUC were stronger for some tickers, but the
result was not consistent across the complete evaluation universe.

The directional evidence was not strong enough to offset the larger
price and return errors.

## Decision

Kronos-small is not selected as the production model for one-day-ahead
price forecasting in Ruang Risiko IDX.

It remains in the project as an experimental foundation-model
benchmark.

No Kronos hyperparameters will be tuned using this evaluation set.
This prevents the final evaluation from becoming an informal tuning
dataset.

## Portfolio interpretation

This experiment is useful even though Kronos did not outperform the
simpler baseline.

It demonstrates that the project:

- evaluates complex models against naive alternatives
- uses leakage-safe rolling windows
- checks structural forecast quality
- preserves failed or invalid outputs
- separates technical feasibility from predictive value
- rejects a more complex model when the evidence does not support it

The result supports a risk analytics product that prioritizes
transparent evaluation over model complexity.
