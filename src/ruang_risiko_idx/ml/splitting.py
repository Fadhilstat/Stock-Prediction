"""Chronological dataset splitting for machine learning."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ChronologicalSplitConfig:
    """Configure train, validation, and test periods."""

    validation_size: int = 252
    test_size: int = 252
    minimum_training_size: int = 750

    def validate(self) -> None:
        """Validate chronological split settings."""

        if self.validation_size < 1:
            raise ValueError("Validation size must be positive.")

        if self.test_size < 1:
            raise ValueError("Test size must be positive.")

        if self.minimum_training_size < 250:
            raise ValueError("Minimum training size must be at least 250.")


@dataclass
class TickerDatasetSplit:
    """Store chronological subsets for one ticker."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def split_ticker_dataset(
    ticker_data: pd.DataFrame,
    config: ChronologicalSplitConfig,
) -> TickerDatasetSplit:
    """Split one ticker without shuffling observations."""

    config.validate()

    required_columns = {
        "ticker",
        "trade_date",
        "target_date",
        "target_up_next_day",
    }

    missing_columns = required_columns.difference(ticker_data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Ticker dataset is missing columns: {missing_text}")

    ordered = ticker_data.copy().sort_values("trade_date").reset_index(drop=True)

    if ordered.empty:
        raise ValueError("Ticker dataset cannot be empty.")

    if ordered["ticker"].nunique() != 1:
        raise ValueError("Ticker split requires exactly one ticker.")

    required_total = config.minimum_training_size + config.validation_size + config.test_size

    if len(ordered) < required_total:
        raise ValueError(
            f"Ticker dataset has {len(ordered)} rows, but at least {required_total} are required."
        )

    test_start = len(ordered) - config.test_size

    validation_start = test_start - config.validation_size

    train = ordered.iloc[:validation_start].copy()

    validation = ordered.iloc[validation_start:test_start].copy()

    test = ordered.iloc[test_start:].copy()

    if len(train) < config.minimum_training_size:
        raise ValueError("Training subset is smaller than required.")

    if not (train["target_date"].max() < validation["target_date"].min()):
        raise ValueError("Training and validation target periods overlap.")

    if not (validation["target_date"].max() < test["target_date"].min()):
        raise ValueError("Validation and test target periods overlap.")

    return TickerDatasetSplit(
        train=train,
        validation=validation,
        test=test,
    )


def build_split_summary(
    dataset: pd.DataFrame,
    config: ChronologicalSplitConfig,
) -> pd.DataFrame:
    """Summarize chronological subsets for every ticker."""

    records: list[dict[str, object]] = []

    for ticker, group in dataset.groupby(
        "ticker",
        sort=True,
    ):
        split = split_ticker_dataset(
            ticker_data=group,
            config=config,
        )

        for split_name, subset in (
            ("train", split.train),
            ("validation", split.validation),
            ("test", split.test),
        ):
            records.append(
                {
                    "ticker": ticker,
                    "split": split_name,
                    "observations": int(len(subset)),
                    "first_feature_date": (subset["trade_date"].min()),
                    "last_feature_date": (subset["trade_date"].max()),
                    "first_target_date": (subset["target_date"].min()),
                    "last_target_date": (subset["target_date"].max()),
                    "positive_target_rate": float(subset["target_up_next_day"].mean()),
                }
            )

    return (
        pd.DataFrame.from_records(records)
        .sort_values(
            [
                "ticker",
                "split",
            ]
        )
        .reset_index(drop=True)
    )
