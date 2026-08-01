"""Tests for return correlation analysis."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.eda.correlation import (
    build_correlation_matrix,
    build_rolling_benchmark_correlation,
)


def test_identical_returns_have_perfect_correlation() -> None:
    dates = pd.date_range(
        "2026-01-01",
        periods=4,
        freq="D",
    )

    returns = [
        0.01,
        0.02,
        -0.01,
        0.03,
    ]

    data = pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "AAA",
                "AAA",
                "AAA",
                "^JKSE",
                "^JKSE",
                "^JKSE",
                "^JKSE",
            ],
            "trade_date": list(dates) + list(dates),
            "simple_return": returns + returns,
        }
    )

    matrix = build_correlation_matrix(
        data,
        min_periods=2,
    )

    assert np.isclose(
        matrix.loc["AAA", "^JKSE"],
        1.0,
    )

    rolling = build_rolling_benchmark_correlation(
        data,
        window=3,
        min_periods=3,
    )

    assert np.isclose(
        rolling["rolling_correlation"].dropna().iloc[-1],
        1.0,
    )
