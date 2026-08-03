"""Run Logistic Regression model selection for every ticker."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.ml import (
    ChronologicalSplitConfig,
    LogisticSearchConfig,
    split_ticker_dataset,
    train_logistic_for_ticker,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ml_features.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "ml" / "logistic"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Select and evaluate Logistic Regression per ticker.")
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

    parser.add_argument(
        "--c-values",
        nargs="+",
        type=float,
        default=[
            0.01,
            0.1,
            1.0,
            10.0,
        ],
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
    """Run Logistic Regression for all tickers."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"ML feature dataset was not found at {args.input}.")

    dataset = pd.read_parquet(args.input)

    split_config = ChronologicalSplitConfig(
        validation_size=args.validation_size,
        test_size=args.test_size,
        minimum_training_size=(args.minimum_training_size),
    )

    model_config = LogisticSearchConfig(c_values=tuple(args.c_values))

    validation_metric_frames: list[pd.DataFrame] = []

    validation_prediction_frames: list[pd.DataFrame] = []

    test_metric_records: list[dict[str, object]] = []

    test_prediction_frames: list[pd.DataFrame] = []

    coefficient_frames: list[pd.DataFrame] = []

    for ticker, group in dataset.groupby(
        "ticker",
        sort=True,
    ):
        print(f"Training Logistic Regression for {ticker}.")

        split = split_ticker_dataset(
            ticker_data=group,
            config=split_config,
        )

        result = train_logistic_for_ticker(
            split=split,
            config=model_config,
        )

        validation_metrics = result.validation_results.copy()

        validation_metrics.insert(
            0,
            "ticker",
            ticker,
        )

        validation_metrics.insert(
            1,
            "model_name",
            "logistic_regression",
        )

        validation_metric_frames.append(validation_metrics)

        validation_predictions = result.validation_predictions.copy()

        validation_predictions["model_name"] = "logistic_regression"

        validation_prediction_frames.append(validation_predictions)

        test_metric_records.append(
            {
                "ticker": ticker,
                "model_name": ("logistic_regression"),
                "split": "test",
                **result.test_metrics,
            }
        )

        test_prediction_frames.append(result.test_predictions)

        coefficients = result.coefficients.copy()

        coefficients.insert(
            0,
            "ticker",
            ticker,
        )

        coefficients.insert(
            1,
            "model_name",
            "logistic_regression",
        )

        coefficients.insert(
            2,
            "selected_c",
            result.selected_c,
        )

        coefficient_frames.append(coefficients)

    validation_metrics = pd.concat(
        validation_metric_frames,
        ignore_index=True,
    )

    validation_predictions = pd.concat(
        validation_prediction_frames,
        ignore_index=True,
    )

    test_metrics = (
        pd.DataFrame.from_records(test_metric_records).sort_values("ticker").reset_index(drop=True)
    )

    test_predictions = pd.concat(
        test_prediction_frames,
        ignore_index=True,
    )

    coefficients = pd.concat(
        coefficient_frames,
        ignore_index=True,
    )

    write_parquet_atomic(
        validation_metrics,
        args.output_dir / "validation_metrics.parquet",
    )

    write_parquet_atomic(
        validation_predictions,
        args.output_dir / "validation_predictions.parquet",
    )

    write_parquet_atomic(
        test_metrics,
        args.output_dir / "test_metrics.parquet",
    )

    write_parquet_atomic(
        test_predictions,
        args.output_dir / "test_predictions.parquet",
    )

    write_parquet_atomic(
        coefficients,
        args.output_dir / "coefficients.parquet",
    )

    selected_validation = validation_metrics.loc[
        validation_metrics["validation_rank"].eq(1)
    ].sort_values("ticker")

    print("\nSelected validation results:")
    print(
        selected_validation[
            [
                "ticker",
                "c_value",
                "accuracy",
                "balanced_accuracy",
                "roc_auc",
                "brier_score",
                "log_loss",
            ]
        ].to_string(index=False)
    )

    print("\nTest results:")
    print(
        test_metrics[
            [
                "ticker",
                "selected_c",
                "accuracy",
                "balanced_accuracy",
                "roc_auc",
                "brier_score",
                "log_loss",
                "predicted_positive_rate",
            ]
        ].to_string(index=False)
    )

    print(f"\nOutputs saved to {args.output_dir}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
