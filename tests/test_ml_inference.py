"""Tests for registry-driven direction inference."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.ml.inference import (
    DirectionModelAssignment,
    build_ticker_direction_snapshot,
)


def build_synthetic_analytics(
    ticker: str = "TEST.JK",
    observations: int = 320,
) -> pd.DataFrame:
    """Build deterministic analytics data for inference tests."""

    dates = pd.bdate_range(
        start="2024-01-02",
        periods=observations,
    )

    index = np.arange(
        observations,
        dtype="float64",
    )

    log_return = (
        0.012 * np.sin(index / 4.0)
        + 0.004 * np.cos(index / 11.0)
    )

    benchmark_return = (
        0.006 * np.sin(index / 5.0)
    )

    close = (
        100.0
        * np.exp(
            np.cumsum(log_return)
        )
    )

    high = close * 1.01
    low = close * 0.99

    volume = (
        1_000_000
        + 50_000
        * np.sin(index / 7.0)
        + index * 100
    )

    wealth = np.exp(
        np.cumsum(log_return)
    )

    running_peak = np.maximum.accumulate(
        wealth
    )

    drawdown = (
        wealth / running_peak - 1.0
    )

    return pd.DataFrame(
        {
            "ticker": ticker,
            "trade_date": dates,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "log_return": log_return,
            "benchmark_return": benchmark_return,
            "excess_return": (
                log_return
                - benchmark_return
            ),
            "volatility_21d": 0.20,
            "volatility_63d": 0.22,
            "drawdown": drawdown,
            "time_under_water": (
                drawdown < 0.0
            ).astype("int64"),
        }
    )


@pytest.mark.parametrize(
    ("model", "parameters"),
    [
        (
            "logistic_regression",
            {
                "C": 0.01,
                "maximum_iterations": 2_000,
                "random_state": 42,
            },
        ),
        (
            "random_forest",
            {
                "n_estimators": 50,
                "max_depth": 3,
                "min_samples_leaf": 10,
                "max_features": "sqrt",
                "random_state": 42,
                "n_jobs": 1,
            },
        ),
        (
            "constant_probability",
            {
                "probability_rule": (
                    "full_labeled_history_positive_rate"
                ),
            },
        ),
    ],
)
def test_latest_direction_snapshot_supports_all_models(
    model: str,
    parameters: dict[str, object],
) -> None:
    """Every supported model should produce a valid latest probability."""

    ticker = "TEST.JK"

    analytics = build_synthetic_analytics(
        ticker=ticker,
    )

    assignment = DirectionModelAssignment(
        ticker=ticker,
        model=model,
        parameters=parameters,
    )

    snapshot = build_ticker_direction_snapshot(
        ticker_data=analytics,
        assignment=assignment,
        minimum_labeled_observations=250,
    )

    assert snapshot["ticker"] == ticker
    assert snapshot["selected_model"] == model

    assert snapshot["as_of_date"] == pd.Timestamp(
        analytics["trade_date"].max()
    )

    assert snapshot["forecast_horizon"] == (
        "next_trading_day"
    )

    assert 0.0 <= snapshot["probability_up"] <= 1.0
    assert 0.0 <= snapshot["probability_down"] <= 1.0

    assert np.isclose(
        snapshot["probability_up"]
        + snapshot["probability_down"],
        1.0,
    )

    assert snapshot["training_end_date"] < snapshot["as_of_date"]
    assert snapshot["training_observations"] >= 250


def test_constant_probability_uses_labeled_history_rate() -> None:
    """Baseline inference should equal the usable labeled positive rate."""

    from ruang_risiko_idx.ml.features import (
        FEATURE_COLUMNS,
        build_ticker_ml_features,
    )

    ticker = "TEST.JK"

    analytics = build_synthetic_analytics(
        ticker=ticker,
    )

    assignment = DirectionModelAssignment(
        ticker=ticker,
        model="constant_probability",
        parameters={
            "probability_rule": (
                "full_labeled_history_positive_rate"
            ),
        },
    )

    snapshot = build_ticker_direction_snapshot(
        ticker_data=analytics,
        assignment=assignment,
        minimum_labeled_observations=250,
    )

    features = build_ticker_ml_features(
        ticker_data=analytics,
    )

    usable_labeled = features.dropna(
        subset=[
            *FEATURE_COLUMNS,
            "target_up_next_day",
        ]
    ).copy()

    expected = float(
        usable_labeled[
            "target_up_next_day"
        ]
        .astype("int8")
        .mean()
    )

    assert np.isclose(
        snapshot["probability_up"],
        expected,
    )

    assert snapshot["training_observations"] == len(
        usable_labeled
    )


def test_ticker_assignment_must_match_data() -> None:
    """Inference should reject data from another ticker."""

    analytics = build_synthetic_analytics(
        ticker="TEST.JK",
    )

    assignment = DirectionModelAssignment(
        ticker="OTHER.JK",
        model="constant_probability",
        parameters={},
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        build_ticker_direction_snapshot(
            ticker_data=analytics,
            assignment=assignment,
            minimum_labeled_observations=250,
        )
