"""Tests for the Granite TTM data adapter."""

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.foundation.granite_adapter import (
    GRANITE_TARGET_COLUMN,
    build_granite_backtest_window,
    validate_granite_data,
)


def make_analytics(
    observations: int = 530,
) -> pd.DataFrame:
    """Create deterministic analytics rows for one ticker."""

    dates = pd.bdate_range(
        "2020-01-01",
        periods=observations,
    )

    returns = np.linspace(
        -0.02,
        0.02,
        observations,
        dtype="float64",
    )

    return pd.DataFrame(
        {
            "ticker": "BBCA.JK",
            "trade_date": dates,
            "log_return": returns,
        }
    )


def test_build_granite_backtest_window() -> None:
    """Build an exact leakage-safe context and future target."""

    data = make_analytics()

    cutoff = data["trade_date"].iloc[-2]

    window = build_granite_backtest_window(
        data=data,
        ticker="BBCA.JK",
        cutoff_date=cutoff,
        context_length=512,
        pred_len=1,
    )

    assert window.ticker == "BBCA.JK"
    assert window.context_length == 512
    assert window.pred_len == 1

    assert list(window.context.columns) == [
        GRANITE_TARGET_COLUMN
    ]

    assert (
        window.context_timestamps.iloc[-1]
        == cutoff
    )

    assert (
        window.forecast_timestamps.iloc[0]
        > window.context_timestamps.iloc[-1]
    )

    assert (
        window.actual_future["trade_date"].iloc[0]
        == data["trade_date"].iloc[-1]
    )


def test_granite_adapter_allows_leading_missing_return() -> None:
    """Allow the expected first missing return from return creation."""

    data = make_analytics()

    data.loc[
        data.index[0],
        "log_return",
    ] = np.nan

    cutoff = data["trade_date"].iloc[-2]

    window = build_granite_backtest_window(
        data=data,
        ticker="BBCA.JK",
        cutoff_date=cutoff,
        context_length=512,
        pred_len=1,
    )

    assert window.context_length == 512


def test_granite_adapter_rejects_internal_missing_return() -> None:
    """Reject a missing value after the return series has started."""

    data = make_analytics()

    data.loc[
        data.index[100],
        "log_return",
    ] = np.nan

    with pytest.raises(
        ValueError,
        match="missing log returns",
    ):
        build_granite_backtest_window(
            data=data,
            ticker="BBCA.JK",
            cutoff_date=data["trade_date"].iloc[-2],
        )


def test_granite_adapter_rejects_non_finite_return() -> None:
    """Reject infinite return values."""

    data = make_analytics()

    data.loc[
        data.index[100],
        "log_return",
    ] = np.inf

    with pytest.raises(
        ValueError,
        match="non-finite log returns",
    ):
        build_granite_backtest_window(
            data=data,
            ticker="BBCA.JK",
            cutoff_date=data["trade_date"].iloc[-2],
        )


def test_granite_adapter_rejects_duplicate_dates() -> None:
    """Reject duplicate trading dates for one ticker."""

    data = make_analytics()

    data.loc[
        data.index[1],
        "trade_date",
    ] = data.loc[
        data.index[0],
        "trade_date",
    ]

    with pytest.raises(
        ValueError,
        match="duplicate trade dates",
    ):
        build_granite_backtest_window(
            data=data,
            ticker="BBCA.JK",
            cutoff_date=data["trade_date"].iloc[-2],
        )


def test_granite_adapter_requires_full_context() -> None:
    """Reject a window that lacks enough history."""

    data = make_analytics(
        observations=300,
    )

    with pytest.raises(
        ValueError,
        match="historical return rows",
    ):
        build_granite_backtest_window(
            data=data,
            ticker="BBCA.JK",
            cutoff_date=data["trade_date"].iloc[-2],
            context_length=512,
        )


def test_validate_granite_data_requires_columns() -> None:
    """Reject analytics data that lacks the target column."""

    data = make_analytics().drop(
        columns=["log_return"]
    )

    with pytest.raises(
        ValueError,
        match="Analytics data is missing columns",
    ):
        validate_granite_data(
            data
        )
