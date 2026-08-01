"""Tests for descriptive return statistics."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.eda.descriptive import (
    summarize_return_statistics,
)


def test_summarize_return_statistics() -> None:
    data = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4,
            "trade_date": pd.date_range(
                "2026-01-01",
                periods=4,
                freq="D",
            ),
            "simple_return": [
                np.nan,
                0.10,
                -0.10,
                0.05,
            ],
            "drawdown": [
                0.0,
                0.0,
                -0.10,
                0.0,
            ],
            "time_under_water": [
                0,
                0,
                1,
                0,
            ],
            "volatility_21d": [
                np.nan,
                np.nan,
                0.20,
                0.18,
            ],
            "volatility_63d": [
                np.nan,
                np.nan,
                np.nan,
                0.16,
            ],
        }
    )

    result = summarize_return_statistics(data)
    row = result.iloc[0]

    assert row["observations"] == 3
    assert np.isclose(
        row["maximum_drawdown"],
        -0.10,
    )
    assert np.isclose(
        row["positive_return_rate"],
        2 / 3,
    )
    assert np.isclose(
        row["latest_volatility_21d"],
        0.18,
    )
