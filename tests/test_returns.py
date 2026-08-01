"""Tests for return feature engineering."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.analytics.returns import (
    add_return_features,
)


def test_add_return_features() -> None:
    data = pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "AAA",
                "AAA",
                "^JKSE",
                "^JKSE",
                "^JKSE",
            ],
            "trade_date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                ]
            ),
            "adjusted_close": [
                100.0,
                110.0,
                99.0,
                100.0,
                102.0,
                101.0,
            ],
        }
    )

    result = add_return_features(data)
    stock = result.loc[result["ticker"].eq("AAA")]

    assert np.isnan(stock.iloc[0]["simple_return"])
    assert np.isclose(
        stock.iloc[1]["simple_return"],
        0.10,
    )
    assert np.isclose(
        stock.iloc[1]["log_return"],
        np.log(1.10),
    )
    assert np.isclose(
        stock.iloc[-1]["cumulative_return"],
        -0.01,
    )
    assert np.isclose(
        stock.iloc[1]["excess_return"],
        0.08,
    )
