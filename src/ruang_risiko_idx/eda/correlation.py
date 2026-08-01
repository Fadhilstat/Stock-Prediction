"""Cross-asset and benchmark correlation analysis."""

from __future__ import annotations

import pandas as pd


def build_correlation_matrix(
    data: pd.DataFrame,
    value_column: str = "simple_return",
    min_periods: int = 60,
) -> pd.DataFrame:
    """Calculate a return correlation matrix across tickers."""

    required_columns = {
        "ticker",
        "trade_date",
        value_column,
    }

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Correlation calculation requires columns: {missing_text}")

    if min_periods < 2:
        raise ValueError("Correlation requires at least two observations.")

    wide_returns = data.pivot(
        index="trade_date",
        columns="ticker",
        values=value_column,
    ).sort_index()

    return wide_returns.corr(
        min_periods=min_periods,
    )


def build_rolling_benchmark_correlation(
    data: pd.DataFrame,
    benchmark_ticker: str = "^JKSE",
    window: int = 63,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Calculate rolling correlation against the benchmark."""

    required_columns = {
        "ticker",
        "trade_date",
        "simple_return",
    }

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Rolling correlation requires columns: {missing_text}")

    if window < 2:
        raise ValueError("Rolling correlation window must be at least two.")

    required_observations = min_periods if min_periods is not None else window

    if required_observations < 2:
        raise ValueError("Minimum observations must be at least two.")

    if required_observations > window:
        raise ValueError("Minimum observations cannot exceed the window.")

    wide_returns = data.pivot(
        index="trade_date",
        columns="ticker",
        values="simple_return",
    ).sort_index()

    if benchmark_ticker not in wide_returns.columns:
        raise ValueError(f"Benchmark ticker {benchmark_ticker} was not found.")

    frames: list[pd.DataFrame] = []

    for ticker in sorted(wide_returns.columns):
        if ticker == benchmark_ticker:
            continue

        aligned = wide_returns[[ticker, benchmark_ticker]].dropna()

        rolling_values = (
            aligned[ticker]
            .rolling(
                window=window,
                min_periods=required_observations,
            )
            .corr(aligned[benchmark_ticker])
        )

        frames.append(
            pd.DataFrame(
                {
                    "trade_date": aligned.index,
                    "ticker": ticker,
                    "benchmark_ticker": benchmark_ticker,
                    "window": window,
                    "rolling_correlation": rolling_values.to_numpy(),
                }
            )
        )

    if not frames:
        return pd.DataFrame(
            columns=[
                "trade_date",
                "ticker",
                "benchmark_ticker",
                "window",
                "rolling_correlation",
            ]
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )
