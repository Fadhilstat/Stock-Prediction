"""Tests for the chronological baseline workflow."""

import pandas as pd

from ruang_risiko_idx.ml import (
    ChronologicalSplitConfig,
    build_constant_probability_baseline,
    split_ticker_dataset,
)


def test_test_baseline_uses_train_and_validation_history() -> None:
    observations = 1_300

    dates = pd.date_range(
        "2020-01-01",
        periods=observations,
        freq="B",
    )

    target = pd.Series(
        [0] * 796 + [1] * 252 + [0, 1] * 126,
        dtype="int8",
    )

    dataset = pd.DataFrame(
        {
            "ticker": ["AAA"] * observations,
            "trade_date": dates,
            "target_date": (dates + pd.offsets.BDay(1)),
            "target_up_next_day": target,
        }
    )

    split = split_ticker_dataset(
        ticker_data=dataset,
        config=ChronologicalSplitConfig(
            validation_size=252,
            test_size=252,
            minimum_training_size=750,
        ),
    )

    combined_training_target = pd.concat(
        [
            split.train["target_up_next_day"],
            split.validation["target_up_next_day"],
        ],
        ignore_index=True,
    )

    probabilities, metrics = build_constant_probability_baseline(
        training_target=combined_training_target,
        evaluation_target=split.test["target_up_next_day"],
    )

    expected_rate = float(combined_training_target.mean())

    assert metrics["training_positive_rate"] == expected_rate

    assert probabilities.eq(expected_rate).all()
