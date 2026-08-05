"""Prepare leakage-safe daily OHLCV windows for Kronos."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

KRONOS_FEATURE_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
)

REQUIRED_MARKET_COLUMNS = (
    "ticker",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True)
class KronosWindow:
    """Store one historical context and its forecast timestamps."""

    ticker: str
    cutoff_date: pd.Timestamp
    context: pd.DataFrame
    context_timestamps: pd.Series
    forecast_timestamps: pd.Series
    actual_future: pd.DataFrame

    @property
    def lookback(self) -> int:
        """Return the number of historical observations."""

        return len(self.context)

    @property
    def pred_len(self) -> int:
        """Return the number of requested forecast observations."""

        return len(self.forecast_timestamps)


def validate_market_data(
    data: pd.DataFrame,
) -> None:
    """Validate columns and values needed by the Kronos adapter."""

    missing_columns = set(REQUIRED_MARKET_COLUMNS).difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Market data is missing columns: {missing_text}")

    if data.empty:
        raise ValueError("Market data must contain at least one row.")

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    if data[numeric_columns].isna().any().any():
        raise ValueError("Market data contains missing OHLCV values.")

    numeric_values = data[numeric_columns].to_numpy(dtype="float64")

    if not np.isfinite(numeric_values).all():
        raise ValueError("Market data contains non-finite OHLCV values.")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Market prices must be positive.")

    if (data["volume"] < 0).any():
        raise ValueError("Market volume cannot be negative.")


def add_kronos_amount_proxy(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Add a transparent traded-value proxy for Kronos.

    The source data does not contain actual traded value. The proxy uses
    closing price multiplied by volume and must not be presented as an
    exchange-reported transaction value.
    """

    result = data.copy()

    result["amount"] = result["close"].astype("float64") * result["volume"].astype("float64")

    return result


def build_kronos_backtest_window(
    data: pd.DataFrame,
    ticker: str,
    cutoff_date: str | pd.Timestamp,
    lookback: int = 400,
    pred_len: int = 1,
) -> KronosWindow:
    """Build a historical Kronos window with known future timestamps.

    Only rows on or before the cutoff date enter the model context.
    Rows after the cutoff are retained solely as evaluation targets.
    """

    if lookback < 2:
        raise ValueError("Kronos lookback must be at least two observations.")

    if pred_len < 1:
        raise ValueError("Kronos prediction length must be positive.")

    validate_market_data(data)

    cutoff = pd.Timestamp(cutoff_date)

    ticker_data = (
        data.loc[
            data["ticker"].eq(ticker),
            list(REQUIRED_MARKET_COLUMNS),
        ]
        .copy()
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    if ticker_data.empty:
        raise ValueError(f"No market data was found for ticker {ticker}.")

    ticker_data["trade_date"] = pd.to_datetime(ticker_data["trade_date"])

    if ticker_data["trade_date"].duplicated().any():
        raise ValueError(f"Ticker {ticker} contains duplicate trade dates.")

    historical = ticker_data.loc[ticker_data["trade_date"].le(cutoff)].tail(lookback)

    future = ticker_data.loc[ticker_data["trade_date"].gt(cutoff)].head(pred_len)

    if len(historical) < lookback:
        raise ValueError(
            f"Ticker {ticker} has only {len(historical)} historical "
            f"rows before the cutoff. Expected {lookback}."
        )

    if len(future) < pred_len:
        raise ValueError(
            f"Ticker {ticker} has only {len(future)} future rows after "
            f"the cutoff. Expected {pred_len}."
        )

    historical = add_kronos_amount_proxy(historical)

    future = add_kronos_amount_proxy(future)

    context = historical[list(KRONOS_FEATURE_COLUMNS)].reset_index(drop=True)

    context_timestamps = historical["trade_date"].reset_index(drop=True).rename("trade_date")

    forecast_timestamps = future["trade_date"].reset_index(drop=True).rename("trade_date")

    actual_future = future[
        [
            "trade_date",
            *KRONOS_FEATURE_COLUMNS,
        ]
    ].reset_index(drop=True)

    if len(context) != len(context_timestamps):
        raise ValueError("Kronos context and historical timestamps have different lengths.")

    if len(forecast_timestamps) != pred_len:
        raise ValueError("Kronos forecast timestamps do not match pred_len.")

    return KronosWindow(
        ticker=ticker,
        cutoff_date=cutoff,
        context=context,
        context_timestamps=context_timestamps,
        forecast_timestamps=forecast_timestamps,
        actual_future=actual_future,
    )
