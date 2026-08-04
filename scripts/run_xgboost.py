"""Run XGBoost model selection for every ticker."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.ml.features import FEATURE_COLUMNS
from ruang_risiko_idx.ml.splitting import (
    ChronologicalSplitConfig,
    split_ticker_dataset,
)
from ruang_risiko_idx.ml.xgboost_model import (
    XGBoostSearchConfig,
    train_xgboost_for_ticker,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ml_features.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "ml" / "xgboost"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Select and evaluate XGBoost per ticker.")

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
        "--n-estimators",
        type=int,
        default=300,
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
    """Run XGBoost for all tickers."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"ML feature dataset was not found at {args.input}.")

    dataset = pd.read_parquet(args.input)

    missing_features = set(FEATURE_COLUMNS).difference(dataset.columns)

    if missing_features:
        missing_text = ", ".join(sorted(missing_features))
        raise ValueError(f"ML feature dataset is missing columns: {missing_text}")

    split_config = ChronologicalSplitConfig(
        validation_size=args.validation_size,
        test_size=args.test_size,
        minimum_training_size=args.minimum_training_size,
    )

    model_config = XGBoostSearchConfig(
        n_estimators=args.n_estimators,
    )

    validation_frames: list[pd.DataFrame] = []
    validation_prediction_frames: list[pd.DataFrame] = []
    test_metric_records: list[dict[str, object]] = []
    test_prediction_frames: list[pd.DataFrame] = []
    importance_frames: list[pd.DataFrame] = []

    for ticker, group in dataset.groupby(
        "ticker",
        sort=True,
    ):
        print(f"Training XGBoost for {ticker}.")

        split = split_ticker_dataset(
            ticker_data=group,
            config=split_config,
        )

        result = train_xgboost_for_ticker(
            split=split,
            config=model_config,
        )

        validation = result.validation_results.copy()
        validation.insert(0, "ticker", ticker)
        validation.insert(1, "model_name", "xgboost")
        validation_frames.append(validation)

        validation_predictions = result.validation_predictions.copy()
        validation_predictions["model_name"] = "xgboost"
        validation_prediction_frames.append(validation_predictions)

        test_metric_records.append(
            {
                "ticker": ticker,
                "model_name": "xgboost",
                "split": "test",
                **result.test_metrics,
            }
        )

        test_prediction_frames.append(result.test_predictions)

        importances = result.feature_importances.copy()
        importances.insert(0, "ticker", ticker)
        importances.insert(1, "model_name", "xgboost")
        importance_frames.append(importances)

    validation_metrics = pd.concat(
        validation_frames,
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

    feature_importances = pd.concat(
        importance_frames,
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
        feature_importances,
        args.output_dir / "feature_importances.parquet",
    )

    selected_validation = validation_metrics.loc[
        validation_metrics["validation_rank"].eq(1)
    ].sort_values("ticker")

    print("\nSelected validation results:")
    print(
        selected_validation[
            [
                "ticker",
                "max_depth",
                "learning_rate",
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
                "max_depth",
                "learning_rate",
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
