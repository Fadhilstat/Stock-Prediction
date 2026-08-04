"""Tests for leakage-safe XGBoost training."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.ml.features import FEATURE_COLUMNS
from ruang_risiko_idx.ml.splitting import (
    ChronologicalSplitConfig,
    split_ticker_dataset,
)
from ruang_risiko_idx.ml.xgboost_model import (
    XGBoostSearchConfig,
    build_xgboost_model,
    select_xgboost_parameters,
    train_xgboost_for_ticker,
)


def make_xgboost_split():
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
        "target_date": dates + pd.offsets.BDay(1),
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


def test_xgboost_probability_output() -> None:
    split = make_xgboost_split()

    model = build_xgboost_model(
        n_estimators=50,
        max_depth=2,
        learning_rate=0.05,
        n_jobs=1,
    )

    model.fit(
        split.train[list(FEATURE_COLUMNS)],
        split.train["target_up_next_day"],
    )

    probabilities = model.predict_proba(split.validation[list(FEATURE_COLUMNS)])[:, 1]

    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_xgboost_selection() -> None:
    split = make_xgboost_split()

    selected, results, predictions = select_xgboost_parameters(
        split=split,
        config=XGBoostSearchConfig(
            n_estimators=50,
            max_depth_values=(2,),
            learning_rate_values=(
                0.01,
                0.05,
            ),
            n_jobs=1,
        ),
    )

    assert selected["learning_rate"] in {
        0.01,
        0.05,
    }

    assert len(results) == 2
    assert results.iloc[0]["validation_rank"] == 1

    assert len(predictions) == (2 * len(split.validation))


def test_full_xgboost_workflow() -> None:
    split = make_xgboost_split()

    result = train_xgboost_for_ticker(
        split=split,
        config=XGBoostSearchConfig(
            n_estimators=50,
            max_depth_values=(2,),
            learning_rate_values=(0.05,),
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
