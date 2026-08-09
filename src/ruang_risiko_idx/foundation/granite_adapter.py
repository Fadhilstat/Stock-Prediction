"""Prepare leakage-safe return windows for Granite TTM."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

GRANITE_TARGET_COLUMN = "log_return"

REQUIRED_GRANITE_COLUMNS = (
    "ticker",
    "trade_date",
    GRANITE_TARGET_COLUMN,
)


@dataclass(frozen=True)
class GraniteWindow:
    """Store one historical return context and its evaluation target."""

    ticker: str
    cutoff_date: pd.Timestamp
    context: pd.DataFrame
    context_timestamps: pd.Series
    forecast_timestamps: pd.Series
    actual_future: pd.DataFrame

    @property
    def context_length(self) -> int:
        """Return the number of historical observations."""

        return len(self.context)

    @property
    def pred_len(self) -> int:
        """Return the number of requested forecast observations."""

        return len(self.forecast_timestamps)


def validate_granite_data(
    data: pd.DataFrame,
) -> None:
    """Validate columns needed by the Granite adapter."""

    missing_columns = set(REQUIRED_GRANITE_COLUMNS).difference(
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

    if data.empty:
        raise ValueError(
            "Analytics data must contain at least one row."
        )


def _prepare_ticker_returns(
    data: pd.DataFrame,
    ticker: str,
) -> pd.DataFrame:
    """Prepare one ordered ticker return series."""

    ticker_data = (
        data.loc[
            data["ticker"].eq(ticker),
            list(REQUIRED_GRANITE_COLUMNS),
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
        errors="coerce",
    )

    if ticker_data["trade_date"].isna().any():
        raise ValueError(
            f"Ticker {ticker} contains invalid trade dates."
        )

    if ticker_data["trade_date"].duplicated().any():
        raise ValueError(
            f"Ticker {ticker} contains duplicate trade dates."
        )

    returns = pd.to_numeric(
        ticker_data[GRANITE_TARGET_COLUMN],
        errors="coerce",
    )

    infinite_mask = np.isinf(
        returns.to_numpy(dtype="float64")
    )

    if infinite_mask.any():
        raise ValueError(
            f"Ticker {ticker} contains non-finite log returns."
        )

    valid_positions = np.flatnonzero(
        returns.notna().to_numpy()
    )

    if len(valid_positions) == 0:
        raise ValueError(
            f"Ticker {ticker} does not contain valid log returns."
        )

    first_valid_position = int(valid_positions[0])

    if returns.iloc[first_valid_position:].isna().any():
        raise ValueError(
            f"Ticker {ticker} contains missing log returns "
            "after the return series begins."
        )

    ticker_data = (
        ticker_data.iloc[first_valid_position:]
        .copy()
        .reset_index(drop=True)
    )

    ticker_data[GRANITE_TARGET_COLUMN] = (
        ticker_data[GRANITE_TARGET_COLUMN]
        .astype("float64")
    )

    return ticker_data


def build_granite_backtest_window(
    data: pd.DataFrame,
    ticker: str,
    cutoff_date: str | pd.Timestamp,
    context_length: int = 512,
    pred_len: int = 1,
) -> GraniteWindow:
    """Build a leakage-safe Granite return window.

    Only observations on or before the cutoff enter the model
    context. Later observations are retained only for evaluation.
    """

    if context_length < 2:
        raise ValueError(
            "Granite context length must be at least two observations."
        )

    if pred_len < 1:
        raise ValueError(
            "Granite prediction length must be positive."
        )

    validate_granite_data(data)

    cutoff = pd.Timestamp(
        cutoff_date
    )

    ticker_data = _prepare_ticker_returns(
        data=data,
        ticker=ticker,
    )

    historical = (
        ticker_data.loc[
            ticker_data["trade_date"].le(cutoff)
        ]
        .tail(context_length)
        .copy()
    )

    future = (
        ticker_data.loc[
            ticker_data["trade_date"].gt(cutoff)
        ]
        .head(pred_len)
        .copy()
    )

    if len(historical) < context_length:
        raise ValueError(
            f"Ticker {ticker} has only {len(historical)} "
            "historical return rows before the cutoff. "
            f"Expected {context_length}."
        )

    if len(future) < pred_len:
        raise ValueError(
            f"Ticker {ticker} has only {len(future)} "
            "future return rows after the cutoff. "
            f"Expected {pred_len}."
        )

    context = (
        historical[
            [GRANITE_TARGET_COLUMN]
        ]
        .reset_index(drop=True)
    )

    context_timestamps = (
        historical["trade_date"]
        .reset_index(drop=True)
        .rename("trade_date")
    )

    forecast_timestamps = (
        future["trade_date"]
        .reset_index(drop=True)
        .rename("trade_date")
    )

    actual_future = (
        future[
            [
                "trade_date",
                GRANITE_TARGET_COLUMN,
            ]
        ]
        .reset_index(drop=True)
    )

    if len(context) != len(context_timestamps):
        raise ValueError(
            "Granite context and timestamps have different lengths."
        )

    if len(forecast_timestamps) != pred_len:
        raise ValueError(
            "Granite forecast timestamps do not match pred_len."
        )

    if not (
        forecast_timestamps.min()
        > context_timestamps.max()
    ):
        raise ValueError(
            "Granite forecast timestamps must be after the context."
        )

    return GraniteWindow(
        ticker=ticker,
        cutoff_date=cutoff,
        context=context,
        context_timestamps=context_timestamps,
        forecast_timestamps=forecast_timestamps,
        actual_future=actual_future,
    )
