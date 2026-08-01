"""Drawdown and time-under-water analytics."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "trade_date",
    "adjusted_close",
}


def _underwater_streak(
    drawdown: pd.Series,
) -> pd.Series:
    """Count consecutive observations below the previous peak."""

    underwater = drawdown.lt(0)
    recovery_groups = (~underwater).cumsum()

    return underwater.groupby(recovery_groups).cumsum().astype("int64")


def add_drawdown_features(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate wealth, running peak, drawdown, and duration."""

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Drawdown calculation requires columns: {missing_text}")

    if data.empty:
        raise ValueError("Drawdown calculation received an empty table.")

    result = data.copy()
    result = result.sort_values(["ticker", "trade_date"]).reset_index(drop=True)

    grouped_prices = result.groupby(
        "ticker",
        sort=False,
    )["adjusted_close"]

    result["wealth_index"] = grouped_prices.transform(lambda values: values / values.iloc[0])

    result["running_peak"] = result.groupby(
        "ticker",
        sort=False,
    )["wealth_index"].cummax()

    result["drawdown"] = result["wealth_index"] / result["running_peak"] - 1.0

    result["time_under_water"] = result.groupby(
        "ticker",
        sort=False,
    )["drawdown"].transform(_underwater_streak)

    return result


def summarize_drawdowns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Create one drawdown summary row per ticker."""

    required_columns = {
        "ticker",
        "trade_date",
        "drawdown",
        "time_under_water",
    }

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Drawdown summary requires columns: {missing_text}")

    ordered = data.sort_values(["ticker", "trade_date"])

    return ordered.groupby(
        "ticker",
        as_index=False,
    ).agg(
        first_date=("trade_date", "min"),
        last_date=("trade_date", "max"),
        maximum_drawdown=("drawdown", "min"),
        current_drawdown=("drawdown", "last"),
        maximum_time_under_water=(
            "time_under_water",
            "max",
        ),
    )
