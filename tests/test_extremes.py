"""Tests for extreme return selection."""

import pandas as pd

from ruang_risiko_idx.eda.extremes import (
    select_extreme_returns,
)


def test_select_extreme_returns() -> None:
    data = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5,
            "trade_date": pd.date_range(
                "2026-01-01",
                periods=5,
                freq="D",
            ),
            "simple_return": [
                0.04,
                -0.10,
                0.08,
                -0.03,
                0.01,
            ],
        }
    )

    result = select_extreme_returns(
        data,
        top_n=2,
    )

    negative = result.loc[result["event_type"].eq("negative")]

    positive = result.loc[result["event_type"].eq("positive")]

    assert negative["simple_return"].tolist() == [
        -0.10,
        -0.03,
    ]

    assert positive["simple_return"].tolist() == [
        0.08,
        0.04,
    ]
