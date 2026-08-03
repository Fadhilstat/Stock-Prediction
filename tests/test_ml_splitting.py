"""Tests for chronological machine learning splits."""

import pandas as pd

from ruang_risiko_idx.ml.splitting import (
    ChronologicalSplitConfig,
    split_ticker_dataset,
)


def test_chronological_split_has_no_overlap() -> None:
    observations = 1_300

    feature_dates = pd.date_range(
        "2020-01-01",
        periods=observations,
        freq="B",
    )

    dataset = pd.DataFrame(
        {
            "ticker": ["AAA"] * observations,
            "trade_date": feature_dates,
            "target_date": (feature_dates + pd.offsets.BDay(1)),
            "target_up_next_day": ([0, 1] * 650),
        }
    )

    config = ChronologicalSplitConfig(
        validation_size=252,
        test_size=252,
        minimum_training_size=750,
    )

    split = split_ticker_dataset(
        ticker_data=dataset,
        config=config,
    )

    assert len(split.train) == 796
    assert len(split.validation) == 252
    assert len(split.test) == 252

    assert split.train["target_date"].max() < split.validation["target_date"].min()

    assert split.validation["target_date"].max() < split.test["target_date"].min()
