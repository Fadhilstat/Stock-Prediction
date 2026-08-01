"""Descriptive statistics for daily return and risk data."""

from __future__ import annotations

from math import sqrt

import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "trade_date",
    "simple_return",
    "drawdown",
    "time_under_water",
    "volatility_21d",
    "volatility_63d",
}


def _annualized_compound_return(
    returns: pd.Series,
    annualization_factor: int,
) -> float:
    """Annualize the compounded return from available observations."""

    clean_returns = returns.dropna()

    if clean_returns.empty:
        return float("nan")

    gross_return = float((1.0 + clean_returns).prod())

    if gross_return <= 0:
        return float("nan")

    exponent = annualization_factor / len(clean_returns)
    return gross_return**exponent - 1.0


def _last_valid_value(values: pd.Series) -> float:
    """Return the final non-missing value in a series."""

    valid_values = values.dropna()

    if valid_values.empty:
        return float("nan")

    return float(valid_values.iloc[-1])


def summarize_return_statistics(
    data: pd.DataFrame,
    annualization_factor: int = 252,
) -> pd.DataFrame:
    """Create one descriptive statistics row per ticker."""

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Descriptive statistics require columns: {missing_text}")

    if data.empty:
        raise ValueError("Descriptive statistics received an empty table.")

    if annualization_factor <= 0:
        raise ValueError("Annualization factor must be positive.")

    working = data.copy()
    working["trade_date"] = pd.to_datetime(
        working["trade_date"],
        errors="coerce",
    )

    if working["trade_date"].isna().any():
        raise ValueError("Descriptive statistics found an invalid trade date.")

    records: list[dict[str, object]] = []

    for ticker, ticker_data in working.groupby(
        "ticker",
        sort=True,
    ):
        ordered = ticker_data.sort_values("trade_date")
        returns = ordered["simple_return"].dropna()
        daily_volatility = float(returns.std(ddof=1))

        records.append(
            {
                "ticker": ticker,
                "first_date": ordered["trade_date"].min(),
                "last_date": ordered["trade_date"].max(),
                "observations": int(returns.count()),
                "mean_daily_return": float(returns.mean()),
                "median_daily_return": float(returns.median()),
                "daily_volatility": daily_volatility,
                "annualized_return": _annualized_compound_return(
                    returns=returns,
                    annualization_factor=annualization_factor,
                ),
                "annualized_volatility": (daily_volatility * sqrt(annualization_factor)),
                "skewness": float(returns.skew()),
                "excess_kurtosis": float(returns.kurt()),
                "minimum_daily_return": float(returns.min()),
                "return_percentile_01": float(returns.quantile(0.01)),
                "return_percentile_05": float(returns.quantile(0.05)),
                "return_percentile_95": float(returns.quantile(0.95)),
                "return_percentile_99": float(returns.quantile(0.99)),
                "maximum_daily_return": float(returns.max()),
                "positive_return_rate": float(returns.gt(0).mean()),
                "maximum_drawdown": float(ordered["drawdown"].min()),
                "current_drawdown": float(ordered["drawdown"].iloc[-1]),
                "maximum_time_under_water": int(ordered["time_under_water"].max()),
                "latest_volatility_21d": _last_valid_value(ordered["volatility_21d"]),
                "latest_volatility_63d": _last_valid_value(ordered["volatility_63d"]),
            }
        )

    return pd.DataFrame.from_records(records)
