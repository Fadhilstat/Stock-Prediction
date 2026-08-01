"""Return and benchmark-relative feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "trade_date",
    "adjusted_close",
}


def add_return_features(
    data: pd.DataFrame,
    benchmark_ticker: str = "^JKSE",
) -> pd.DataFrame:
    """Calculate daily and benchmark-relative return features."""

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Return calculation requires columns: {missing_text}")

    if data.empty:
        raise ValueError("Return calculation received an empty table.")

    result = data.copy()
    result["trade_date"] = pd.to_datetime(
        result["trade_date"],
        errors="coerce",
    )

    if result["trade_date"].isna().any():
        raise ValueError("Return calculation found an invalid trade date.")

    if result["adjusted_close"].isna().any():
        raise ValueError("Adjusted close cannot contain missing values.")

    if result["adjusted_close"].le(0).any():
        raise ValueError("Adjusted close must contain positive values.")

    result = result.sort_values(["ticker", "trade_date"]).reset_index(drop=True)

    grouped_prices = result.groupby(
        "ticker",
        sort=False,
    )["adjusted_close"]

    result["simple_return"] = grouped_prices.pct_change(fill_method=None)

    result["log_return"] = grouped_prices.transform(lambda values: np.log(values).diff())

    result["cumulative_return"] = grouped_prices.transform(
        lambda values: values / values.iloc[0] - 1.0
    )

    benchmark = result.loc[
        result["ticker"].eq(benchmark_ticker),
        ["trade_date", "simple_return"],
    ].rename(
        columns={
            "simple_return": "benchmark_return",
        }
    )

    if benchmark.empty:
        raise ValueError(f"Benchmark ticker {benchmark_ticker} was not found.")

    if benchmark["trade_date"].duplicated().any():
        raise ValueError("Benchmark contains duplicate trade dates.")

    result = result.merge(
        benchmark,
        on="trade_date",
        how="left",
        validate="many_to_one",
    )

    result["excess_return"] = result["simple_return"] - result["benchmark_return"]

    return result.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
