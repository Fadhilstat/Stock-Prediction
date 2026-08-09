"""Build the latest registry-driven direction probability snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.ml.inference import (
    build_latest_direction_snapshot,
    load_classical_deployment_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytics_daily.parquet"
)

DEFAULT_REGISTRY_PATH = (
    PROJECT_ROOT
    / "config"
    / "classical_deployment_registry.yml"
)

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "ml"
    / "latest_direction_snapshot.parquet"
)

DEFAULT_JSON_PATH = (
    PROJECT_ROOT
    / "reports"
    / "ml"
    / "latest_direction_snapshot.json"
)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the latest classical direction probability snapshot."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )

    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_PATH,
    )

    parser.add_argument(
        "--minimum-labeled-observations",
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

    temporary_path = destination.with_name(
        f".{destination.name}.tmp"
    )

    data.to_parquet(
        temporary_path,
        index=False,
    )

    temporary_path.replace(
        destination
    )


def write_json_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write JSON through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(
        f".{destination.name}.tmp"
    )

    json_data = data.copy()

    date_columns = (
        "generated_at_utc",
        "as_of_date",
        "training_start_date",
        "training_end_date",
    )

    for column in date_columns:
        if column in json_data:
            json_data[column] = json_data[
                column
            ].astype(str)

    temporary_path.write_text(
        json_data.to_json(
            orient="records",
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        destination
    )


def validate_snapshot(
    snapshot: pd.DataFrame,
) -> None:
    """Validate the generated direction snapshot."""

    required_columns = {
        "generated_at_utc",
        "ticker",
        "as_of_date",
        "forecast_horizon",
        "selected_model",
        "probability_up",
        "probability_down",
        "training_observations",
        "training_start_date",
        "training_end_date",
        "feature_count",
    }

    missing_columns = required_columns.difference(
        snapshot.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(
                missing_columns
            )
        )

        raise ValueError(
            f"Direction snapshot is missing columns: {missing_text}"
        )

    if snapshot.empty:
        raise ValueError(
            "Direction snapshot cannot be empty."
        )

    if snapshot["ticker"].duplicated().any():
        raise ValueError(
            "Direction snapshot contains duplicate tickers."
        )

    if not snapshot["probability_up"].between(
        0.0,
        1.0,
        inclusive="both",
    ).all():
        raise ValueError(
            "Direction probability_up contains invalid values."
        )

    if not snapshot["probability_down"].between(
        0.0,
        1.0,
        inclusive="both",
    ).all():
        raise ValueError(
            "Direction probability_down contains invalid values."
        )

    probability_sum = (
        snapshot["probability_up"]
        + snapshot["probability_down"]
    )

    if not probability_sum.sub(1.0).abs().lt(
        1e-12
    ).all():
        raise ValueError(
            "Direction probabilities do not sum to one."
        )

    if not (
        snapshot["training_end_date"]
        < snapshot["as_of_date"]
    ).all():
        raise ValueError(
            "Direction training period overlaps the inference date."
        )

    horizons = set(
        snapshot[
            "forecast_horizon"
        ].unique()
    )

    if horizons != {
        "next_trading_day"
    }:
        raise ValueError(
            "Unexpected forecast horizon in direction snapshot."
        )


def main() -> int:
    """Build and save the latest direction snapshot."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Analytics data was not found at {args.input}."
        )

    analytics = pd.read_parquet(
        args.input
    )

    assignments = (
        load_classical_deployment_registry(
            args.registry
        )
    )

    snapshot = build_latest_direction_snapshot(
        analytics=analytics,
        assignments=assignments,
        minimum_labeled_observations=(
            args.minimum_labeled_observations
        ),
    )

    snapshot.insert(
        0,
        "generated_at_utc",
        pd.Timestamp.now(
            tz="UTC"
        ).floor(
            "s"
        ),
    )

    validate_snapshot(
        snapshot
    )

    write_parquet_atomic(
        data=snapshot,
        destination=args.output,
    )

    write_json_atomic(
        data=snapshot,
        destination=args.json_output,
    )

    display_columns = [
        "ticker",
        "as_of_date",
        "selected_model",
        "probability_up",
        "probability_down",
        "training_observations",
        "training_end_date",
    ]

    print(
        "\nLatest direction snapshot:"
    )

    print(
        snapshot[
            display_columns
        ].to_string(
            index=False
        )
    )

    print(
        f"\nParquet saved to {args.output}."
    )

    print(
        f"JSON saved to {args.json_output}."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
