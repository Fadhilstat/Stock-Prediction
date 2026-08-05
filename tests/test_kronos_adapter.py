"""Tests for leakage-safe Kronos data preparation."""

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.foundation.kronos_adapter import (
    KRONOS_FEATURE_COLUMNS,
    add_kronos_amount_proxy,
    build_kronos_backtest_window,
    validate_market_data,
)


def make_market_data(
    observations: int = 500,
) -> pd.DataFrame:
    """Create deterministic daily OHLCV data."""

    dates = pd.bdate_range(
        "2024-01-02",
        periods=observations,
    )

    close = np.linspace(
        100.0,
        150.0,
        observations,
    )

    return pd.DataFrame(
        {
            "ticker": ["AAA"] * observations,
            "trade_date": dates,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.arange(
                1_000,
                1_000 + observations,
            ),
        }
    )


def test_amount_proxy_uses_close_times_volume() -> None:
    data = make_market_data(observations=5)

    result = add_kronos_amount_proxy(data)

    expected = result["close"] * result["volume"]

    assert np.allclose(
        result["amount"],
        expected,
    )


def test_build_kronos_window_is_leakage_safe() -> None:
    data = make_market_data()

    cutoff_date = data.loc[
        449,
        "trade_date",
    ]

    window = build_kronos_backtest_window(
        data=data,
        ticker="AAA",
        cutoff_date=cutoff_date,
        lookback=400,
        pred_len=3,
    )

    assert window.lookback == 400
    assert window.pred_len == 3

    assert window.context_timestamps.max() <= cutoff_date

    assert window.forecast_timestamps.min() > cutoff_date

    assert list(window.context.columns) == list(KRONOS_FEATURE_COLUMNS)

    assert len(window.actual_future) == 3


def test_window_uses_actual_future_trade_dates() -> None:
    data = make_market_data()

    cutoff_date = data.loc[
        449,
        "trade_date",
    ]

    expected_dates = data.loc[
        450:451,
        "trade_date",
    ].reset_index(drop=True)

    window = build_kronos_backtest_window(
        data=data,
        ticker="AAA",
        cutoff_date=cutoff_date,
        lookback=400,
        pred_len=2,
    )

    pd.testing.assert_series_equal(
        window.forecast_timestamps,
        expected_dates.rename("trade_date"),
    )


def test_window_rejects_insufficient_history() -> None:
    data = make_market_data(observations=100)

    with pytest.raises(
        ValueError,
        match="historical rows",
    ):
        build_kronos_backtest_window(
            data=data,
            ticker="AAA",
            cutoff_date=data["trade_date"].iloc[-2],
            lookback=400,
            pred_len=1,
        )


def test_validation_rejects_missing_values() -> None:
    data = make_market_data(observations=10)

    data.loc[
        4,
        "close",
    ] = np.nan

    with pytest.raises(
        ValueError,
        match="missing OHLCV",
    ):
        validate_market_data(data)
