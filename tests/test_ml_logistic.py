"""Tests for leakage-safe Logistic Regression training."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.ml.logistic import (
    LogisticSearchConfig,
    build_logistic_pipeline,
    extract_logistic_coefficients,
    select_logistic_regularization,
    train_logistic_for_ticker,
)
from ruang_risiko_idx.ml.splitting import (
    ChronologicalSplitConfig,
    split_ticker_dataset,
)


def make_logistic_dataset(
    observations: int = 1_300,
) -> pd.DataFrame:
    """Create deterministic classification data."""

    generator = np.random.default_rng(42)

    dates = pd.date_range(
        "2020-01-01",
        periods=observations,
        freq="B",
    )

    return_1d = generator.normal(size=observations)

    target = (
        return_1d
        + generator.normal(
            scale=0.7,
            size=observations,
        )
        > 0
    ).astype("int8")

    data = {
        "ticker": ["AAA"] * observations,
        "trade_date": dates,
        "target_date": (dates + pd.offsets.BDay(1)),
        "target_up_next_day": target,
    }

    feature_names = [
        "return_1d",
        "momentum_5d",
        "momentum_21d",
        "benchmark_return_1d",
        "excess_return_1d",
        "volatility_21d",
        "volatility_63d",
        "drawdown",
        "time_under_water",
        "intraday_range",
        "close_location",
        "log_volume",
        "volume_change_1d",
        "volume_zscore_21d",
    ]

    for index, feature_name in enumerate(feature_names):
        if feature_name == "return_1d":
            data[feature_name] = return_1d
        else:
            data[feature_name] = generator.normal(size=observations) + index * 0.001

    return pd.DataFrame(data)


def make_split():
    """Create a chronological model split."""

    dataset = make_logistic_dataset()

    return split_ticker_dataset(
        ticker_data=dataset,
        config=ChronologicalSplitConfig(
            validation_size=252,
            test_size=252,
            minimum_training_size=750,
        ),
    )


def test_logistic_pipeline_predicts_probabilities() -> None:
    split = make_split()

    pipeline = build_logistic_pipeline(c_value=0.1)

    feature_columns = [
        column
        for column in split.train.columns
        if column
        not in {
            "ticker",
            "trade_date",
            "target_date",
            "target_up_next_day",
        }
    ]

    pipeline.fit(
        split.train[feature_columns],
        split.train["target_up_next_day"],
    )

    probabilities = pipeline.predict_proba(split.validation[feature_columns])[:, 1]

    assert np.isfinite(probabilities).all()

    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_regularization_selection() -> None:
    split = make_split()

    selected_c, results, predictions = select_logistic_regularization(
        split=split,
        config=LogisticSearchConfig(
            c_values=(
                0.01,
                0.1,
            )
        ),
    )

    assert selected_c in {
        0.01,
        0.1,
    }

    assert len(results) == 2
    assert results.iloc[0]["validation_rank"] == 1

    assert len(predictions) == (2 * len(split.validation))


def test_full_logistic_workflow() -> None:
    split = make_split()

    result = train_logistic_for_ticker(
        split=split,
        config=LogisticSearchConfig(
            c_values=(
                0.01,
                0.1,
            )
        ),
    )

    assert len(result.test_predictions) == len(split.test)

    assert result.test_predictions["probability_up"].between(0, 1).all()

    assert 0 <= result.test_metrics["roc_auc"] <= 1

    coefficients = extract_logistic_coefficients(result.fitted_pipeline)

    assert len(coefficients) == 14
    assert coefficients["absolute_coefficient"].is_monotonic_decreasing
