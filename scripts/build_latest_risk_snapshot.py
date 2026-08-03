"""Build the latest registry-driven GARCH risk snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.econometrics import (
    build_latest_risk_snapshot,
    load_garch_model_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "config" / "garch_model_registry.yml"

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "reports" / "risk" / "latest_risk_snapshot.parquet"

DEFAULT_JSON_PATH = PROJECT_ROOT / "reports" / "risk" / "latest_risk_snapshot.json"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Build the latest GARCH volatility and VaR snapshot.")
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
        "--minimum-observations",
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


def write_json_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write JSON through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    json_data = data.copy()

    for column in (
        "generated_at_utc",
        "as_of_date",
        "data_start_date",
    ):
        if column in json_data:
            json_data[column] = json_data[column].astype(str)

    temporary_path.write_text(
        json_data.to_json(
            orient="records",
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(destination)


def main() -> int:
    """Build and save the latest risk snapshot."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics data was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    assignments = load_garch_model_registry(args.registry)

    snapshot = build_latest_risk_snapshot(
        analytics=analytics,
        assignments=assignments,
        minimum_observations=(args.minimum_observations),
    )

    snapshot.insert(
        0,
        "generated_at_utc",
        pd.Timestamp.now(tz="UTC").floor("s"),
    )

    write_parquet_atomic(
        snapshot,
        args.output,
    )

    write_json_atomic(
        snapshot,
        args.json_output,
    )

    display_columns = [
        "ticker",
        "as_of_date",
        "volatility_model",
        "var_model",
        "forecast_volatility",
        "var_95",
        "var_99",
        "persistence",
        "half_life_days",
        "convergence_flag",
    ]

    print("\nLatest risk snapshot:")
    print(snapshot[display_columns].to_string(index=False))

    print(f"\nParquet saved to {args.output}.")

    print(f"JSON saved to {args.json_output}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
