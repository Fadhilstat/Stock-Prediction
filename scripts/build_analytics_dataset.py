"""Build the daily analytics dataset from clean market prices."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.analytics import (
    add_drawdown_features,
    add_return_features,
    add_volatility_features,
    summarize_drawdowns,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "market_prices.parquet"

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "drawdown_summary.parquet"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build daily return and risk analytics.")

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the clean market price Parquet file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the daily analytics Parquet file.",
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help="Path for the drawdown summary Parquet file.",
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
    """Build and save the analytics datasets."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Market data was not found at {args.input}.")

    market_data = pd.read_parquet(args.input)

    analytics = add_return_features(
        data=market_data,
        benchmark_ticker=args.benchmark,
    )

    analytics = add_volatility_features(
        data=analytics,
        windows=(21, 63),
        annualization_factor=252,
    )

    analytics = add_drawdown_features(
        data=analytics,
    )

    duplicate_count = int(analytics.duplicated(["ticker", "trade_date"]).sum())

    if duplicate_count:
        raise ValueError(f"Analytics data contains {duplicate_count} duplicate rows.")

    drawdown_summary = summarize_drawdowns(analytics)

    write_parquet_atomic(
        data=analytics,
        destination=args.output,
    )

    write_parquet_atomic(
        data=drawdown_summary,
        destination=args.summary_output,
    )

    print(f"Saved {len(analytics):,} analytics rows to {args.output}.")

    print(f"Saved {len(drawdown_summary):,} drawdown summaries to {args.summary_output}.")

    print("\nDrawdown summary:")
    print(drawdown_summary.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
