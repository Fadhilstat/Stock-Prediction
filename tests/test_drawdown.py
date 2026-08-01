"""Tests for drawdown analytics."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.analytics.drawdown import (
    add_drawdown_features,
    summarize_drawdowns,
)


def test_drawdown_and_time_under_water() -> None:
    data = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5,
            "trade_date": pd.date_range(
                "2026-01-01",
                periods=5,
                freq="D",
            ),
            "adjusted_close": [
                100.0,
                120.0,
                90.0,
                100.0,
                130.0,
            ],
        }
    )

    result = add_drawdown_features(data)
    summary = summarize_drawdowns(result)

    assert np.isclose(
        result.iloc[2]["drawdown"],
        -0.25,
    )

    assert result["time_under_water"].tolist() == [0, 0, 1, 2, 0]

    assert np.isclose(
        summary.iloc[0]["maximum_drawdown"],
        -0.25,
    )

    assert summary.iloc[0]["maximum_time_under_water"] == 2
