"""Build exploratory analysis tables from daily analytics data."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ruang_risiko_idx.eda import (
    build_correlation_matrix,
    build_rolling_benchmark_correlation,
    select_extreme_returns,
    summarize_return_statistics,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "eda"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build exploratory analysis outputs.")

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the daily analytics Parquet file.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated EDA outputs.",
    )

    parser.add_argument(
        "--benchmark",
        default="^JKSE",
        help="Ticker used as the market benchmark.",
    )

    return parser.parse_args()


def write_parquet_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write a Parquet file through a temporary path."""

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
    payload: dict[str, Any],
    destination: Path,
) -> None:
    """Write JSON through a temporary path."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(destination)


def build_summary_payload(
    analytics: pd.DataFrame,
    statistics: pd.DataFrame,
    extremes: pd.DataFrame,
) -> dict[str, Any]:
    """Create a compact machine-readable EDA summary."""

    most_volatile = statistics.loc[statistics["annualized_volatility"].idxmax()]

    deepest_drawdown = statistics.loc[statistics["maximum_drawdown"].idxmin()]

    worst_return = extremes.loc[extremes["simple_return"].idxmin()]

    best_return = extremes.loc[extremes["simple_return"].idxmax()]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_start": pd.Timestamp(analytics["trade_date"].min()).date().isoformat(),
        "data_end": pd.Timestamp(analytics["trade_date"].max()).date().isoformat(),
        "row_count": int(len(analytics)),
        "tickers": sorted(analytics["ticker"].astype(str).unique().tolist()),
        "most_volatile_ticker": {
            "ticker": str(most_volatile["ticker"]),
            "annualized_volatility": float(most_volatile["annualized_volatility"]),
        },
        "deepest_drawdown": {
            "ticker": str(deepest_drawdown["ticker"]),
            "maximum_drawdown": float(deepest_drawdown["maximum_drawdown"]),
        },
        "worst_daily_return": {
            "ticker": str(worst_return["ticker"]),
            "trade_date": pd.Timestamp(worst_return["trade_date"]).date().isoformat(),
            "simple_return": float(worst_return["simple_return"]),
        },
        "best_daily_return": {
            "ticker": str(best_return["ticker"]),
            "trade_date": pd.Timestamp(best_return["trade_date"]).date().isoformat(),
            "simple_return": float(best_return["simple_return"]),
        },
    }


def main() -> int:
    """Build and save exploratory analysis outputs."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics data was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    statistics = summarize_return_statistics(analytics)

    correlation_matrix = build_correlation_matrix(
        analytics,
        value_column="simple_return",
        min_periods=60,
    )

    correlation_output = correlation_matrix.rename_axis("ticker").reset_index()

    rolling_correlation = build_rolling_benchmark_correlation(
        analytics,
        benchmark_ticker=args.benchmark,
        window=63,
    )

    extremes = select_extreme_returns(
        analytics,
        top_n=10,
    )

    summary_payload = build_summary_payload(
        analytics=analytics,
        statistics=statistics,
        extremes=extremes,
    )

    write_parquet_atomic(
        statistics,
        args.output_dir / "return_statistics.parquet",
    )

    write_parquet_atomic(
        correlation_output,
        args.output_dir / "correlation_matrix.parquet",
    )

    write_parquet_atomic(
        rolling_correlation,
        args.output_dir / "rolling_benchmark_correlation.parquet",
    )

    write_parquet_atomic(
        extremes,
        args.output_dir / "extreme_returns.parquet",
    )

    write_json_atomic(
        summary_payload,
        args.output_dir / "eda_summary.json",
    )

    print(f"Saved EDA outputs to {args.output_dir}.")

    print("\nReturn statistics:")
    print(
        statistics[
            [
                "ticker",
                "annualized_return",
                "annualized_volatility",
                "maximum_drawdown",
                "positive_return_rate",
            ]
        ].to_string(index=False)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
