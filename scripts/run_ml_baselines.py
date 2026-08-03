"""Run chronological probability baselines for every ticker."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.ml import (
    ChronologicalSplitConfig,
    build_constant_probability_baseline,
    build_split_summary,
    split_ticker_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ml_features.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "ml"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Run constant probability baselines with chronological splits.")
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--validation-size",
        type=int,
        default=252,
    )

    parser.add_argument(
        "--test-size",
        type=int,
        default=252,
    )

    parser.add_argument(
        "--minimum-training-size",
        type=int,
        default=750,
    )

    return parser.parse_args()


def write_parquet_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write Parquet through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    data.to_parquet(
        temporary_path,
        index=False,
    )

    temporary_path.replace(destination)


def main() -> int:
    """Run baselines for validation and test subsets."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"ML feature dataset was not found at {args.input}.")

    dataset = pd.read_parquet(args.input)

    config = ChronologicalSplitConfig(
        validation_size=args.validation_size,
        test_size=args.test_size,
        minimum_training_size=(args.minimum_training_size),
    )

    split_summary = build_split_summary(
        dataset=dataset,
        config=config,
    )

    metric_records: list[dict[str, object]] = []

    prediction_frames: list[pd.DataFrame] = []

    for ticker, group in dataset.groupby(
        "ticker",
        sort=True,
    ):
        split = split_ticker_dataset(
            ticker_data=group,
            config=config,
        )

        validation_probabilities, validation_metrics = build_constant_probability_baseline(
            training_target=split.train["target_up_next_day"],
            evaluation_target=split.validation["target_up_next_day"],
        )

        combined_training_target = pd.concat(
            [
                split.train["target_up_next_day"],
                split.validation["target_up_next_day"],
            ],
            ignore_index=True,
        )

        test_probabilities, test_metrics = build_constant_probability_baseline(
            training_target=combined_training_target,
            evaluation_target=split.test["target_up_next_day"],
        )

        for split_name, metrics in (
            (
                "validation",
                validation_metrics,
            ),
            (
                "test",
                test_metrics,
            ),
        ):
            metric_records.append(
                {
                    "ticker": ticker,
                    "model_name": ("constant_probability"),
                    "split": split_name,
                    **metrics,
                }
            )

        validation_predictions = split.validation[
            [
                "ticker",
                "trade_date",
                "target_date",
                "target_up_next_day",
            ]
        ].copy()

        validation_predictions["split"] = "validation"

        validation_predictions["model_name"] = "constant_probability"

        validation_predictions["probability_up"] = validation_probabilities.to_numpy()

        test_predictions = split.test[
            [
                "ticker",
                "trade_date",
                "target_date",
                "target_up_next_day",
            ]
        ].copy()

        test_predictions["split"] = "test"

        test_predictions["model_name"] = "constant_probability"

        test_predictions["probability_up"] = test_probabilities.to_numpy()

        prediction_frames.extend(
            [
                validation_predictions,
                test_predictions,
            ]
        )

    metrics = (
        pd.DataFrame.from_records(metric_records)
        .sort_values(
            [
                "ticker",
                "split",
            ]
        )
        .reset_index(drop=True)
    )

    predictions = (
        pd.concat(
            prediction_frames,
            ignore_index=True,
        )
        .sort_values(
            [
                "ticker",
                "split",
                "trade_date",
            ]
        )
        .reset_index(drop=True)
    )

    write_parquet_atomic(
        split_summary,
        args.output_dir / "split_summary.parquet",
    )

    write_parquet_atomic(
        metrics,
        args.output_dir / "baseline_metrics.parquet",
    )

    write_parquet_atomic(
        predictions,
        args.output_dir / "baseline_predictions.parquet",
    )

    print("\nChronological split summary:")
    print(split_summary.to_string(index=False))

    print("\nBaseline metrics:")
    print(
        metrics[
            [
                "ticker",
                "split",
                "observations",
                "positive_rate",
                "training_positive_rate",
                "accuracy",
                "balanced_accuracy",
                "roc_auc",
                "brier_score",
                "log_loss",
            ]
        ].to_string(index=False)
    )

    print(f"\nOutputs saved to {args.output_dir}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
