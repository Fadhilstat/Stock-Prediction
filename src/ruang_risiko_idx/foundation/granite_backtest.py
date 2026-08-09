"""Build and evaluate leakage-safe rolling Granite TTM forecasts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

from ruang_risiko_idx.foundation.granite_adapter import (
    GraniteWindow,
    build_granite_backtest_window,
)


@dataclass(frozen=True)
class GraniteBacktestConfig:
    """Configure a rolling Granite TTM backtest."""

    context_length: int = 512
    evaluation_size: int = 252
    stride: int = 1
    pred_len: int = 1

    def validate(self) -> None:
        """Validate rolling backtest settings."""

        if self.context_length < 2:
            raise ValueError(
                "Granite context length must be at least two observations."
            )

        if self.evaluation_size < 1:
            raise ValueError(
                "Granite evaluation size must be positive."
            )

        if self.stride < 1:
            raise ValueError(
                "Granite backtest stride must be positive."
            )

        if self.pred_len != 1:
            raise ValueError(
                "The current Granite backtest supports pred_len=1."
            )


def build_granite_backtest_windows(
    data: pd.DataFrame,
    ticker: str,
    config: GraniteBacktestConfig,
) -> list[GraniteWindow]:
    """Build recent leakage-safe Granite windows for one ticker."""

    config.validate()

    required_columns = {
        "ticker",
        "trade_date",
        "log_return",
    }

    missing_columns = required_columns.difference(
        data.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Analytics data is missing columns: "
            + missing_text
        )

    ticker_data = (
        data.loc[
            data["ticker"].eq(ticker),
            [
                "ticker",
                "trade_date",
                "log_return",
            ],
        ]
        .copy()
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    if ticker_data.empty:
        raise ValueError(
            f"No analytics data was found for ticker {ticker}."
        )

    ticker_data["trade_date"] = pd.to_datetime(
        ticker_data["trade_date"],
        errors="raise",
    )

    ticker_data = (
        ticker_data.dropna(
            subset=["log_return"]
        )
        .reset_index(drop=True)
    )

    eligible_target_positions = np.arange(
        config.context_length,
        len(ticker_data),
        dtype="int64",
    )

    selected_positions = (
        eligible_target_positions[::-1]
        [:: config.stride]
        [: config.evaluation_size]
        [::-1]
    )

    if len(selected_positions) < config.evaluation_size:
        raise ValueError(
            f"Ticker {ticker} has only "
            f"{len(selected_positions)} eligible rolling windows. "
            f"Expected {config.evaluation_size}."
        )

    windows: list[GraniteWindow] = []

    for target_position in selected_positions:
        cutoff_date = ticker_data.loc[
            target_position - 1,
            "trade_date",
        ]

        window = build_granite_backtest_window(
            data=data,
            ticker=ticker,
            cutoff_date=cutoff_date,
            context_length=config.context_length,
            pred_len=config.pred_len,
        )

        windows.append(
            window
        )

    return windows


def _lookup_adjusted_close(
    data: pd.DataFrame,
    ticker: str,
    trade_date: pd.Timestamp,
) -> float:
    """Read one adjusted close from the analytics dataset."""

    required_columns = {
        "ticker",
        "trade_date",
        "adjusted_close",
    }

    missing_columns = required_columns.difference(
        data.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Adjusted close lookup is missing columns: "
            + missing_text
        )

    dates = pd.to_datetime(
        data["trade_date"],
        errors="coerce",
    )

    matched = data.loc[
        data["ticker"].eq(ticker)
        & dates.eq(pd.Timestamp(trade_date)),
        "adjusted_close",
    ]

    if len(matched) != 1:
        raise ValueError(
            f"Expected one adjusted close for {ticker} "
            f"on {pd.Timestamp(trade_date).date()}."
        )

    value = float(
        matched.iloc[0]
    )

    if not np.isfinite(value) or value <= 0:
        raise ValueError(
            "Adjusted close must be finite and positive."
        )

    return value


def evaluate_granite_prediction(
    prediction: pd.DataFrame,
    window: GraniteWindow,
    data: pd.DataFrame,
) -> dict[str, object]:
    """Evaluate one Granite forecast and two naive baselines."""

    if len(prediction) != 1:
        raise ValueError(
            "Rolling evaluation expects one prediction row."
        )

    if len(window.actual_future) != 1:
        raise ValueError(
            "Rolling evaluation expects one actual row."
        )

    if len(window.context) < 2:
        raise ValueError(
            "Rolling evaluation requires at least two context rows."
        )

    required_prediction_columns = {
        "ticker",
        "cutoff_date",
        "trade_date",
        "predicted_log_return",
        "actual_log_return",
    }

    missing_columns = required_prediction_columns.difference(
        prediction.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Granite prediction is missing columns: "
            + missing_text
        )

    predicted = prediction.iloc[0]

    target_date = pd.Timestamp(
        window.forecast_timestamps.iloc[0]
    )

    predicted_target_date = pd.Timestamp(
        predicted["trade_date"]
    )

    if predicted_target_date != target_date:
        raise ValueError(
            "Prediction and actual target dates do not match."
        )

    cutoff_date = pd.Timestamp(
        window.context_timestamps.iloc[-1]
    )

    if not target_date > cutoff_date:
        raise ValueError(
            "Granite target date must be after the cutoff."
        )

    predicted_log_return = float(
        predicted["predicted_log_return"]
    )

    actual_log_return = float(
        window.actual_future["log_return"].iloc[0]
    )

    reported_actual_return = float(
        predicted["actual_log_return"]
    )

    if not np.isclose(
        actual_log_return,
        reported_actual_return,
        rtol=1e-10,
        atol=1e-12,
    ):
        raise ValueError(
            "Prediction output and window actual return do not match."
        )

    persistence_log_return = float(
        window.context["log_return"].iloc[-1]
    )

    return_values = np.array(
        [
            predicted_log_return,
            actual_log_return,
            persistence_log_return,
        ],
        dtype="float64",
    )

    if not np.isfinite(return_values).all():
        raise ValueError(
            "Granite evaluation contains non-finite returns."
        )

    last_adjusted_close = _lookup_adjusted_close(
        data=data,
        ticker=window.ticker,
        trade_date=cutoff_date,
    )

    actual_adjusted_close = _lookup_adjusted_close(
        data=data,
        ticker=window.ticker,
        trade_date=target_date,
    )

    predicted_adjusted_close = float(
        last_adjusted_close
        * np.exp(predicted_log_return)
    )

    random_walk_adjusted_close = (
        last_adjusted_close
    )

    persistence_adjusted_close = float(
        last_adjusted_close
        * np.exp(persistence_log_return)
    )

    return {
        "ticker": window.ticker,
        "cutoff_date": cutoff_date,
        "target_date": target_date,
        "last_adjusted_close": last_adjusted_close,
        "actual_adjusted_close": actual_adjusted_close,
        "actual_log_return": actual_log_return,
        "actual_up": int(
            actual_log_return > 0
        ),
        "predicted_log_return": predicted_log_return,
        "granite_predicted_up": int(
            predicted_log_return > 0
        ),
        "predicted_adjusted_close": (
            predicted_adjusted_close
        ),
        "random_walk_log_return": 0.0,
        "random_walk_predicted_up": 0,
        "random_walk_adjusted_close": (
            random_walk_adjusted_close
        ),
        "persistence_log_return": (
            persistence_log_return
        ),
        "persistence_predicted_up": int(
            persistence_log_return > 0
        ),
        "persistence_adjusted_close": (
            persistence_adjusted_close
        ),
    }


def _safe_classification_metrics(
    actual_up: pd.Series,
    predicted_up: pd.Series,
    prediction_score: pd.Series,
) -> tuple[float, float, float]:
    """Calculate direction metrics with one-class protection."""

    actual_values = actual_up.to_numpy(
        dtype="int64"
    )

    predicted_values = predicted_up.to_numpy(
        dtype="int64"
    )

    direction_accuracy = float(
        np.mean(
            actual_values == predicted_values
        )
    )

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


def summarize_granite_backtest(
    forecasts: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize Granite and naive baseline performance."""

    required_columns = {
        "ticker",
        "actual_adjusted_close",
        "actual_log_return",
        "actual_up",
        "predicted_adjusted_close",
        "predicted_log_return",
        "granite_predicted_up",
        "random_walk_adjusted_close",
        "random_walk_log_return",
        "random_walk_predicted_up",
        "persistence_adjusted_close",
        "persistence_log_return",
        "persistence_predicted_up",
    }

    missing_columns = required_columns.difference(
        forecasts.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Granite forecast data is missing columns: "
            + missing_text
        )

    if forecasts.empty:
        raise ValueError(
            "Granite forecast data must not be empty."
        )

    model_columns = {
        "granite_ttm": {
            "price": "predicted_adjusted_close",
            "return": "predicted_log_return",
            "direction": "granite_predicted_up",
        },
        "random_walk": {
            "price": "random_walk_adjusted_close",
            "return": "random_walk_log_return",
            "direction": "random_walk_predicted_up",
        },
        "return_persistence": {
            "price": "persistence_adjusted_close",
            "return": "persistence_log_return",
            "direction": "persistence_predicted_up",
        },
    }

    records: list[dict[str, object]] = []

    for ticker, ticker_data in forecasts.groupby(
        "ticker",
        sort=True,
    ):
        actual_return = ticker_data[
            "actual_log_return"
        ].astype("float64")

        actual_price = ticker_data[
            "actual_adjusted_close"
        ].astype("float64")

        for model_name, columns in model_columns.items():
            predicted_return = ticker_data[
                columns["return"]
            ].astype("float64")

            predicted_price = ticker_data[
                columns["price"]
            ].astype("float64")

            return_error = (
                predicted_return - actual_return
            )

            price_error = (
                predicted_price - actual_price
            )

            (
                direction_accuracy,
                balanced_accuracy,
                roc_auc,
            ) = _safe_classification_metrics(
                actual_up=ticker_data["actual_up"],
                predicted_up=ticker_data[
                    columns["direction"]
                ],
                prediction_score=predicted_return,
            )

            records.append(
                {
                    "ticker": ticker,
                    "model": model_name,
                    "observations": int(
                        len(ticker_data)
                    ),
                    "return_mae": float(
                        np.mean(
                            np.abs(return_error)
                        )
                    ),
                    "return_rmse": float(
                        np.sqrt(
                            np.mean(
                                np.square(
                                    return_error
                                )
                            )
                        )
                    ),
                    "return_bias": float(
                        np.mean(
                            return_error
                        )
                    ),
                    "adjusted_close_mae": float(
                        np.mean(
                            np.abs(price_error)
                        )
                    ),
                    "adjusted_close_mape": float(
                        np.mean(
                            np.abs(
                                price_error
                                / actual_price
                            )
                        )
                    ),
                    "direction_accuracy": (
                        direction_accuracy
                    ),
                    "balanced_accuracy": (
                        balanced_accuracy
                    ),
                    "roc_auc": roc_auc,
                }
            )

    return pd.DataFrame.from_records(
        records
    )
