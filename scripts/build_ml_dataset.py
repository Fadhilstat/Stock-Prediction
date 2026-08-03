"""Build the leakage-safe next-day classification dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.ml import (
    FEATURE_COLUMNS,
    build_ml_feature_dataset,
    validate_ml_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ml_features.parquet"

DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "reports" / "ml" / "dataset_summary.json"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Build leakage-safe features for next-day return classification.")
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
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
    """Build and validate the ML feature dataset."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics dataset was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    dataset = build_ml_feature_dataset(
        analytics=analytics,
        drop_incomplete_rows=True,
    )

    summary = validate_ml_dataset(dataset)

    write_parquet_atomic(
        data=dataset,
        destination=args.output,
    )

    args.summary_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_frame = pd.Series(summary)

    args.summary_output.write_text(
        summary_frame.to_json(
            indent=2,
            date_format="iso",
        ),
        encoding="utf-8",
    )

    ticker_summary = (
        dataset.groupby("ticker")
        .agg(
            observations=(
                "target_up_next_day",
                "size",
            ),
            first_feature_date=(
                "trade_date",
                "min",
            ),
            last_feature_date=(
                "trade_date",
                "max",
            ),
            positive_target_rate=(
                "target_up_next_day",
                "mean",
            ),
        )
        .reset_index()
    )

    print("\nML dataset summary:")
    print(pd.Series(summary).to_string())

    print("\nTicker summary:")
    print(ticker_summary.to_string(index=False))

    print("\nFeature columns:")
    for feature_name in FEATURE_COLUMNS:
        print(f"- {feature_name}")

    print(f"\nDataset saved to {args.output}.")

    print(f"Summary saved to {args.summary_output}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
