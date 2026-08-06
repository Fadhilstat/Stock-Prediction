"""Build and evaluate leakage-safe rolling Kronos forecasts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

from ruang_risiko_idx.foundation.kronos_adapter import (
    KronosWindow,
    build_kronos_backtest_window,
)


@dataclass(frozen=True)
class KronosBacktestConfig:
    """Configure a rolling Kronos backtest."""

    lookback: int = 400
    evaluation_size: int = 20
    stride: int = 5
    pred_len: int = 1

    def validate(self) -> None:
        """Validate rolling backtest settings."""

        if self.lookback < 2:
            raise ValueError("Kronos lookback must be at least two observations.")

        if self.evaluation_size < 1:
            raise ValueError("Kronos evaluation size must be positive.")

        if self.stride < 1:
            raise ValueError("Kronos backtest stride must be positive.")

        if self.pred_len != 1:
            raise ValueError("The current rolling backtest supports pred_len=1.")


def derive_window_seed(
    base_seed: int,
    ticker: str,
    cutoff_date: str | pd.Timestamp,
) -> int:
    """Derive a stable random seed for one forecast window."""

    cutoff_text = pd.Timestamp(cutoff_date).strftime("%Y-%m-%d")

    seed_text = f"{base_seed}|{ticker}|{cutoff_text}"

    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()

    return int.from_bytes(
        digest[:4],
        byteorder="big",
        signed=False,
    )


def build_kronos_backtest_windows(
    data: pd.DataFrame,
    ticker: str,
    config: KronosBacktestConfig,
) -> list[KronosWindow]:
    """Build recent rolling windows for one ticker."""

    config.validate()

    required_columns = {
        "ticker",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Market data is missing columns: {missing_text}")

    ticker_data = (
        data.loc[data["ticker"].eq(ticker)].copy().sort_values("trade_date").reset_index(drop=True)
    )

    if ticker_data.empty:
        raise ValueError(f"No market data was found for ticker {ticker}.")

    ticker_data["trade_date"] = pd.to_datetime(ticker_data["trade_date"])

    eligible_target_positions = np.arange(
        config.lookback,
        len(ticker_data),
        dtype="int64",
    )

    selected_positions = eligible_target_positions[::-1][:: config.stride][
        : config.evaluation_size
    ][::-1]

    if len(selected_positions) < config.evaluation_size:
        raise ValueError(
            f"Ticker {ticker} has only "
            f"{len(selected_positions)} eligible rolling windows. "
            f"Expected {config.evaluation_size}."
        )

    windows: list[KronosWindow] = []

    for target_position in selected_positions:
        cutoff_date = ticker_data.loc[
            target_position - 1,
            "trade_date",
        ]

        window = build_kronos_backtest_window(
            data=data,
            ticker=ticker,
            cutoff_date=cutoff_date,
            lookback=config.lookback,
            pred_len=config.pred_len,
        )

        windows.append(window)

    return windows


def evaluate_kronos_prediction(
    prediction: pd.DataFrame,
    window: KronosWindow,
    window_seed: int,
) -> dict[str, object]:
    """Evaluate one Kronos prediction and naive baselines."""

    if len(prediction) != 1:
        raise ValueError("Rolling evaluation expects one prediction row.")

    if len(window.actual_future) != 1:
        raise ValueError("Rolling evaluation expects one actual row.")

    if len(window.context) < 2:
        raise ValueError("Rolling evaluation needs at least two context rows.")

    required_prediction_columns = {
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    }

    missing_columns = required_prediction_columns.difference(prediction.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Kronos prediction is missing columns: {missing_text}")

    predicted = prediction.iloc[0]
    actual = window.actual_future.iloc[0]

    predicted_target_date = pd.Timestamp(predicted["trade_date"])

    actual_target_date = pd.Timestamp(actual["trade_date"])

    if predicted_target_date != actual_target_date:
        raise ValueError("Prediction and actual target dates do not match.")

    previous_close = float(window.context["close"].iloc[-2])

    last_close = float(window.context["close"].iloc[-1])

    predicted_close = float(predicted["close"])

    actual_close = float(actual["close"])

    if previous_close <= 0:
        raise ValueError("Previous close must be positive.")

    if last_close <= 0:
        raise ValueError("Last close must be positive.")

    if predicted_close <= 0:
        raise ValueError("Kronos predicted close must be positive.")

    if actual_close <= 0:
        raise ValueError("Actual close must be positive.")

    predicted_log_return = float(np.log(predicted_close / last_close))

    actual_log_return = float(np.log(actual_close / last_close))

    persistence_log_return = float(np.log(last_close / previous_close))

    random_walk_close = last_close

    persistence_close = float(last_close * np.exp(persistence_log_return))

    predicted_open = float(predicted["open"])

    predicted_high = float(predicted["high"])

    predicted_low = float(predicted["low"])

    predicted_volume = float(predicted["volume"])

    predicted_amount = float(predicted["amount"])

    predicted_values = np.array(
        [
            predicted_open,
            predicted_high,
            predicted_low,
            predicted_close,
            predicted_volume,
            predicted_amount,
        ],
        dtype="float64",
    )

    if not np.isfinite(predicted_values).all():
        raise ValueError("Kronos prediction contains non-finite values.")

    ohlc_is_valid = bool(
        predicted_high
        >= max(
            predicted_open,
            predicted_close,
        )
        and predicted_low
        <= min(
            predicted_open,
            predicted_close,
        )
        and predicted_high >= predicted_low
    )

    volume_is_nonnegative = bool(predicted_volume >= 0)

    return {
        "ticker": window.ticker,
        "cutoff_date": pd.Timestamp(window.cutoff_date),
        "target_date": actual_target_date,
        "window_seed": int(window_seed),
        "previous_close": previous_close,
        "last_close": last_close,
        "actual_close": actual_close,
        "actual_log_return": actual_log_return,
        "actual_up": int(actual_log_return > 0),
        "predicted_open": predicted_open,
        "predicted_high": predicted_high,
        "predicted_low": predicted_low,
        "predicted_close": predicted_close,
        "predicted_volume": predicted_volume,
        "predicted_amount": predicted_amount,
        "predicted_log_return": (predicted_log_return),
        "kronos_predicted_up": int(predicted_log_return > 0),
        "random_walk_close": (random_walk_close),
        "random_walk_log_return": 0.0,
        "random_walk_predicted_up": 0,
        "persistence_close": (persistence_close),
        "persistence_log_return": (persistence_log_return),
        "persistence_predicted_up": int(persistence_log_return > 0),
        "ohlc_is_valid": ohlc_is_valid,
        "volume_is_nonnegative": (volume_is_nonnegative),
    }


def _safe_classification_metrics(
    actual_up: pd.Series,
    predicted_up: pd.Series,
    prediction_score: pd.Series,
) -> tuple[float, float, float]:
    """Calculate classification metrics with one-class protection."""

    actual_values = actual_up.to_numpy(dtype="int64")

    predicted_values = predicted_up.to_numpy(dtype="int64")

    direction_accuracy = float(np.mean(actual_values == predicted_values))

    if actual_up.nunique() < 2:
        return (
            direction_accuracy,
            float("nan"),
            float("nan"),
        )

    balanced_accuracy = float(
        balanced_accuracy_score(
            actual_up,
            predicted_up,
        )
    )

    roc_auc = float(
        roc_auc_score(
            actual_up,
            prediction_score,
        )
    )

    return (
        direction_accuracy,
        balanced_accuracy,
        roc_auc,
    )


def summarize_kronos_backtest(
    forecasts: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize Kronos and naive baseline performance."""

    required_columns = {
        "ticker",
        "actual_close",
        "actual_log_return",
        "actual_up",
        "predicted_close",
        "predicted_log_return",
        "kronos_predicted_up",
        "random_walk_close",
        "random_walk_log_return",
        "random_walk_predicted_up",
        "persistence_close",
        "persistence_log_return",
        "persistence_predicted_up",
        "ohlc_is_valid",
        "volume_is_nonnegative",
    }

    missing_columns = required_columns.difference(forecasts.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Kronos forecast data is missing columns: {missing_text}")

    if forecasts.empty:
        raise ValueError("Kronos forecast data must not be empty.")

    model_columns = {
        "kronos": {
            "close": "predicted_close",
            "return": "predicted_log_return",
            "direction": "kronos_predicted_up",
        },
        "random_walk": {
            "close": "random_walk_close",
            "return": "random_walk_log_return",
            "direction": "random_walk_predicted_up",
        },
        "return_persistence": {
            "close": "persistence_close",
            "return": "persistence_log_return",
            "direction": "persistence_predicted_up",
        },
    }

    records: list[dict[str, object]] = []

    for ticker, ticker_data in forecasts.groupby(
        "ticker",
        sort=True,
    ):
        ticker_data = ticker_data.reset_index(drop=True)

        for (
            model_name,
            columns,
        ) in model_columns.items():
            predicted_close = ticker_data[columns["close"]].astype("float64")

            predicted_return = ticker_data[columns["return"]].astype("float64")

            predicted_direction = ticker_data[columns["direction"]].astype("int64")

            actual_close = ticker_data["actual_close"].astype("float64")

            actual_return = ticker_data["actual_log_return"].astype("float64")

            actual_direction = ticker_data["actual_up"].astype("int64")

            close_error = predicted_close - actual_close

            return_error = predicted_return - actual_return

            (
                direction_accuracy,
                balanced_accuracy,
                roc_auc,
            ) = _safe_classification_metrics(
                actual_up=actual_direction,
                predicted_up=predicted_direction,
                prediction_score=predicted_return,
            )

            record: dict[str, object] = {
                "ticker": ticker,
                "model_name": model_name,
                "observations": int(len(ticker_data)),
                "close_mae": float(close_error.abs().mean()),
                "close_rmse": float(np.sqrt(np.mean(np.square(close_error.to_numpy())))),
                "close_mape": float((close_error.abs() / actual_close).mean()),
                "log_return_mae": float(return_error.abs().mean()),
                "log_return_bias": float(return_error.mean()),
                "direction_accuracy": (direction_accuracy),
                "balanced_accuracy": (balanced_accuracy),
                "roc_auc": roc_auc,
                "ohlc_valid_rate": (
                    float(ticker_data["ohlc_is_valid"].mean())
                    if model_name == "kronos"
                    else float("nan")
                ),
                "nonnegative_volume_rate": (
                    float(ticker_data["volume_is_nonnegative"].mean())
                    if model_name == "kronos"
                    else float("nan")
                ),
            }

            records.append(record)

    return (
        pd.DataFrame.from_records(records)
        .sort_values(
            [
                "ticker",
                "model_name",
            ]
        )
        .reset_index(drop=True)
    )
