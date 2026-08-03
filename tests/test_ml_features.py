"""Tests for leakage-safe ML feature engineering."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.ml.features import (
    FEATURE_COLUMNS,
    build_ml_feature_dataset,
    build_ticker_ml_features,
    validate_ml_dataset,
)


def make_analytics_fixture(
    observations: int = 90,
) -> pd.DataFrame:
    """Create deterministic analytics data for testing."""

    dates = pd.date_range(
        "2025-01-01",
        periods=observations,
        freq="B",
    )

    returns = np.linspace(
        -0.02,
        0.02,
        observations,
    )

    close = 100.0 * np.exp(np.cumsum(returns))

    return pd.DataFrame(
        {
            "ticker": ["AAA"] * observations,
            "trade_date": dates,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.arange(
                1_000,
                1_000 + observations,
            ),
            "log_return": returns,
            "benchmark_return": (returns * 0.5),
            "excess_return": (returns * 0.5),
            "volatility_21d": (pd.Series(returns).rolling(21).std().to_numpy()),
            "volatility_63d": (pd.Series(returns).rolling(63).std().to_numpy()),
            "drawdown": np.minimum(
                returns,
                0.0,
            ),
            "time_under_water": np.arange(observations),
        }
    )


def test_target_uses_following_observation() -> None:
    analytics = make_analytics_fixture()

    features = build_ticker_ml_features(analytics)

    assert (
        features.loc[
            0,
            "target_date",
        ]
        == analytics.loc[
            1,
            "trade_date",
        ]
    )

    assert np.isclose(
        features.loc[
            0,
            "target_return_next_day",
        ],
        analytics.loc[
            1,
            "log_return",
        ],
    )


def test_last_row_has_no_target() -> None:
    analytics = make_analytics_fixture()

    features = build_ticker_ml_features(analytics)

    last_row = features.iloc[-1]

    assert pd.isna(last_row["target_return_next_day"])

    assert pd.isna(last_row["target_up_next_day"])


def test_features_do_not_use_future_return() -> None:
    analytics = make_analytics_fixture()

    original = build_ticker_ml_features(analytics)

    changed = analytics.copy()

    changed.loc[
        changed.index[-1],
        "log_return",
    ] = 99.0

    modified = build_ticker_ml_features(changed)

    comparison_columns = list(FEATURE_COLUMNS)

    pd.testing.assert_frame_equal(
        original.loc[
            :-2,
            comparison_columns,
        ],
        modified.loc[
            :-2,
            comparison_columns,
        ],
    )


def test_combined_dataset_is_complete() -> None:
    analytics = make_analytics_fixture()

    dataset = build_ml_feature_dataset(analytics)

    summary = validate_ml_dataset(dataset)

    assert not dataset.empty
    assert summary["tickers"] == 1
    assert summary["missing_feature_values"] == 0

    assert (dataset["target_date"] > dataset["trade_date"]).all()
