"""Build a validated, lightweight bundle for the public dashboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.dashboard.data_access import (
    load_analytics,
    load_direction_snapshot,
    load_risk_snapshot,
    validate_runtime_alignment,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ANALYTICS = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"
DEFAULT_RISK = PROJECT_ROOT / "reports" / "risk" / "latest_risk_snapshot.json"
DEFAULT_DIRECTION = PROJECT_ROOT / "reports" / "ml" / "latest_direction_snapshot.json"
DEFAULT_INTELLIGENCE = (
    PROJECT_ROOT / "reports" / "intelligence" / "latest_daily_intelligence.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "deployment"

ANALYTICS_COLUMNS = (
    "ticker",
    "trade_date",
    "adjusted_close",
    "simple_return",
    "log_return",
    "benchmark_return",
    "excess_return",
    "volatility_21d",
    "volatility_63d",
    "drawdown",
    "time_under_water",
)


def parse_arguments() -> argparse.Namespace:
    """Parse deployment bundle paths."""

    parser = argparse.ArgumentParser(
        description="Build validated precomputed artifacts for dashboard deployment."
    )
    parser.add_argument("--analytics", type=Path, default=DEFAULT_ANALYTICS)
    parser.add_argument("--risk", type=Path, default=DEFAULT_RISK)
    parser.add_argument("--direction", type=Path, default=DEFAULT_DIRECTION)
    parser.add_argument("--intelligence", type=Path, default=DEFAULT_INTELLIGENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return a stable SHA-256 digest for one generated file."""

    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(payload: object, destination: Path) -> None:
    """Write JSON through a temporary file before replacing the destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def copy_atomic(source: Path, destination: Path) -> None:
    """Copy a validated text artifact without leaving a partial destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def build_deployment_bundle(
    analytics_path: Path,
    risk_path: Path,
    direction_path: Path,
    output_dir: Path,
    intelligence_path: Path | None = None,
) -> dict[str, object]:
    """Validate runtime artifacts and publish the subset needed by Streamlit."""

    analytics = load_analytics(analytics_path)
    risk_snapshot = load_risk_snapshot(risk_path)
    direction_snapshot = load_direction_snapshot(direction_path)

    validate_runtime_alignment(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    analytics_output = output_dir / "analytics_daily.parquet"
    risk_output = output_dir / "latest_risk_snapshot.json"
    direction_output = output_dir / "latest_direction_snapshot.json"

    temporary_analytics = analytics_output.with_name(
        f".{analytics_output.name}.tmp"
    )
    analytics.loc[:, ANALYTICS_COLUMNS].to_parquet(
        temporary_analytics,
        index=False,
    )
    temporary_analytics.replace(analytics_output)

    copy_atomic(risk_path, risk_output)
    copy_atomic(direction_path, direction_output)

    file_hashes = {
        analytics_output.name: sha256_file(analytics_output),
        risk_output.name: sha256_file(risk_output),
        direction_output.name: sha256_file(direction_output),
    }

    if intelligence_path is not None and intelligence_path.exists():
        intelligence_output = output_dir / "latest_daily_intelligence.json"
        copy_atomic(intelligence_path, intelligence_output)
        file_hashes[intelligence_output.name] = sha256_file(intelligence_output)

    latest_date = pd.Timestamp(analytics["trade_date"].max())
    manifest = {
        "schema_version": 1,
        "latest_trade_date": latest_date.date().isoformat(),
        "analytics_rows": int(len(analytics)),
        "ticker_count": int(analytics["ticker"].nunique()),
        "files": file_hashes,
    }

    write_json_atomic(manifest, output_dir / "manifest.json")
    return manifest


def main() -> int:
    """Build the deployment bundle and print a compact audit summary."""

    args = parse_arguments()
    manifest = build_deployment_bundle(
        analytics_path=args.analytics,
        risk_path=args.risk,
        direction_path=args.direction,
        intelligence_path=args.intelligence,
        output_dir=args.output_dir,
    )

    print("Deployment bundle built successfully.")
    print(f"Latest trade date: {manifest['latest_trade_date']}")
    print(f"Analytics rows: {manifest['analytics_rows']:,}")
    print(f"Tickers: {manifest['ticker_count']}")
    print(f"Bundle files: {len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
