"""Identify the largest positive and negative daily returns."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "trade_date",
    "simple_return",
}


def select_extreme_returns(
    data: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Select the strongest positive and negative returns."""

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Extreme return analysis requires columns: {missing_text}")

    if top_n <= 0:
        raise ValueError("The number of extreme observations must be positive.")

    optional_columns = [
        "adjusted_close",
        "benchmark_return",
        "excess_return",
        "volatility_21d",
        "volatility_63d",
        "drawdown",
        "time_under_water",
    ]

    available_columns = [column for column in optional_columns if column in data.columns]

    output_columns = [
        "ticker",
        "trade_date",
        "simple_return",
        *available_columns,
    ]

    frames: list[pd.DataFrame] = []

    for _, ticker_data in data.groupby(
        "ticker",
        sort=True,
    ):
        clean_data = ticker_data.dropna(subset=["simple_return"])

        negative = clean_data.nsmallest(
            top_n,
            "simple_return",
        )[output_columns].copy()

        negative["event_type"] = "negative"
        negative["rank"] = range(
            1,
            len(negative) + 1,
        )

        positive = clean_data.nlargest(
            top_n,
            "simple_return",
        )[output_columns].copy()

        positive["event_type"] = "positive"
        positive["rank"] = range(
            1,
            len(positive) + 1,
        )

        frames.extend(
            [
                negative,
                positive,
            ]
        )

    if not frames:
        return pd.DataFrame(
            columns=[
                *output_columns,
                "event_type",
                "rank",
            ]
        )

    result = pd.concat(
        frames,
        ignore_index=True,
    )

    return result.sort_values(
        [
            "ticker",
            "event_type",
            "rank",
        ]
    ).reset_index(drop=True)
