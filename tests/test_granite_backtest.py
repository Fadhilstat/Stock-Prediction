"""Tests for the Granite rolling backtest."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.foundation.granite_backtest import (
    GraniteBacktestConfig,
    build_granite_backtest_windows,
    evaluate_granite_prediction,
    summarize_granite_backtest,
)


def make_analytics(
    observations: int = 530,
) -> pd.DataFrame:
    """Create deterministic adjusted-price analytics."""

    dates = pd.bdate_range(
        "2022-01-03",
        periods=observations,
    )

    returns = np.linspace(
        -0.01,
        0.01,
        observations,
        dtype="float64",
    )

    adjusted_close = (
        100.0
        * np.exp(
            np.cumsum(
                returns
            )
        )
    )

    return pd.DataFrame(
        {
            "ticker": "BBCA.JK",
            "trade_date": dates,
            "adjusted_close": adjusted_close,
            "log_return": returns,
        }
    )


def test_build_granite_backtest_windows() -> None:
    """Build the requested recent rolling windows."""

    data = make_analytics()

    config = GraniteBacktestConfig(
        context_length=512,
        evaluation_size=5,
        stride=1,
    )

    windows = build_granite_backtest_windows(
        data=data,
        ticker="BBCA.JK",
        config=config,
    )

    assert len(windows) == 5

    assert all(
        window.context_length == 512
        for window in windows
    )

    assert all(
        window.pred_len == 1
        for window in windows
    )

    target_dates = [
        window.forecast_timestamps.iloc[0]
        for window in windows
    ]

    assert target_dates == sorted(
        target_dates
    )


def test_evaluate_granite_prediction() -> None:
    """Convert a return forecast into adjusted-price metrics."""

    data = make_analytics()

    config = GraniteBacktestConfig(
        context_length=512,
        evaluation_size=1,
    )

    window = build_granite_backtest_windows(
        data=data,
        ticker="BBCA.JK",
        config=config,
    )[0]

    predicted_return = 0.005

    prediction = pd.DataFrame(
        {
            "ticker": ["BBCA.JK"],
            "cutoff_date": [
                window.cutoff_date
            ],
            "trade_date": [
                window.forecast_timestamps.iloc[0]
            ],
            "predicted_log_return": [
                predicted_return
            ],
            "actual_log_return": [
                window.actual_future[
                    "log_return"
                ].iloc[0]
            ],
        }
    )

    result = evaluate_granite_prediction(
        prediction=prediction,
        window=window,
        data=data,
    )

    expected_price = (
        result["last_adjusted_close"]
        * np.exp(
            predicted_return
        )
    )

    assert np.isclose(
        result["predicted_adjusted_close"],
        expected_price,
    )

    assert (
        result["target_date"]
        > result["cutoff_date"]
    )


def test_summarize_granite_backtest() -> None:
    """Summarize Granite and both naive baselines."""

    forecasts = pd.DataFrame(
        {
            "ticker": ["BBCA.JK"] * 4,
            "actual_adjusted_close": [
                101.0,
                99.0,
                102.0,
                98.0,
            ],
            "actual_log_return": [
                0.01,
                -0.01,
                0.02,
                -0.02,
            ],
            "actual_up": [
                1,
                0,
                1,
                0,
            ],
            "predicted_adjusted_close": [
                100.5,
                99.5,
                101.5,
                98.5,
            ],
            "predicted_log_return": [
                0.008,
                -0.005,
                0.015,
                -0.010,
            ],
            "granite_predicted_up": [
                1,
                0,
                1,
                0,
            ],
            "random_walk_adjusted_close": [
                100.0,
                100.0,
                100.0,
                100.0,
            ],
            "random_walk_log_return": [
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            "random_walk_predicted_up": [
                0,
                0,
                0,
                0,
            ],
            "persistence_adjusted_close": [
                100.8,
                99.7,
                101.0,
                99.0,
            ],
            "persistence_log_return": [
                0.007,
                -0.003,
                0.010,
                -0.008,
            ],
            "persistence_predicted_up": [
                1,
                0,
                1,
                0,
            ],
        }
    )

    metrics = summarize_granite_backtest(
        forecasts
    )

    assert len(metrics) == 3

    assert set(metrics["model"]) == {
        "granite_ttm",
        "random_walk",
        "return_persistence",
    }

    assert (
        metrics["observations"]
        .eq(4)
        .all()
    )

    assert (
        metrics["return_mae"]
        .notna()
        .all()
    )

    assert (
        metrics["adjusted_close_mae"]
        .notna()
        .all()
    )
