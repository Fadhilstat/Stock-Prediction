"""Tests for leakage-safe Random Forest training."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.ml.features import (
    FEATURE_COLUMNS,
)
from ruang_risiko_idx.ml.random_forest import (
    RandomForestSearchConfig,
    build_random_forest_model,
    select_random_forest_parameters,
    train_random_forest_for_ticker,
)
from ruang_risiko_idx.ml.splitting import (
    ChronologicalSplitConfig,
    split_ticker_dataset,
)


def make_random_forest_split():
    """Create a deterministic chronological split."""

    generator = np.random.default_rng(42)
    observations = 1_300

    dates = pd.date_range(
        "2020-01-01",
        periods=observations,
        freq="B",
    )

    signal = generator.normal(size=observations)

    target = (
        signal
        + generator.normal(
            scale=0.8,
            size=observations,
        )
        > 0
    ).astype("int8")

    data: dict[str, object] = {
        "ticker": ["AAA"] * observations,
        "trade_date": dates,
        "target_date": (dates + pd.offsets.BDay(1)),
        "target_up_next_day": target,
    }

    for feature_name in FEATURE_COLUMNS:
        if feature_name == "return_1d":
            data[feature_name] = signal
        else:
            data[feature_name] = generator.normal(size=observations)

    dataset = pd.DataFrame(data)

    return split_ticker_dataset(
        ticker_data=dataset,
        config=ChronologicalSplitConfig(
            validation_size=252,
            test_size=252,
            minimum_training_size=750,
        ),
    )


def test_random_forest_probability_output() -> None:
    split = make_random_forest_split()

    model = build_random_forest_model(
        n_estimators=50,
        max_depth=3,
        min_samples_leaf=10,
        n_jobs=1,
    )

    model.fit(
        split.train[list(FEATURE_COLUMNS)],
        split.train["target_up_next_day"],
    )

    probabilities = model.predict_proba(split.validation[list(FEATURE_COLUMNS)])[:, 1]

    assert np.isfinite(probabilities).all()

    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_random_forest_selection() -> None:
    split = make_random_forest_split()

    selected, results, predictions = select_random_forest_parameters(
        split=split,
        config=RandomForestSearchConfig(
            n_estimators=50,
            max_depth_values=(3,),
            min_samples_leaf_values=(
                10,
                25,
            ),
            n_jobs=1,
        ),
    )

    assert selected["min_samples_leaf"] in {10, 25}

    assert len(results) == 2

    assert results.iloc[0]["validation_rank"] == 1

    assert len(predictions) == (2 * len(split.validation))


def test_full_random_forest_workflow() -> None:
    split = make_random_forest_split()

    result = train_random_forest_for_ticker(
        split=split,
        config=RandomForestSearchConfig(
            n_estimators=50,
            max_depth_values=(3,),
            min_samples_leaf_values=(10,),
            n_jobs=1,
        ),
    )

    assert len(result.test_predictions) == len(split.test)

    assert result.test_predictions["probability_up"].between(0, 1).all()

    assert len(result.feature_importances) == len(FEATURE_COLUMNS)

    assert np.isclose(
        result.feature_importances["importance"].sum(),
        1.0,
    )
