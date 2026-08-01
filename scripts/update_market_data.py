"""Run the daily yfinance ingestion pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ruang_risiko_idx.config import ProjectSettings
from ruang_risiko_idx.data.providers import YahooFinanceProvider
from ruang_risiko_idx.data.repository import (
    load_market_data,
    reconcile_market_data,
    write_market_data,
)
from ruang_risiko_idx.data.update_window import resolve_update_start
from ruang_risiko_idx.data.validation import validate_market_data


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update daily IDX market data.")
    parser.add_argument("--start", help="Optional inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end", help="Optional exclusive end date in YYYY-MM-DD format.")
    parser.add_argument("--tickers", nargs="+", help="Optional list of Yahoo Finance tickers.")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    settings = ProjectSettings()
    existing = load_market_data(settings.raw_data_path)

    start_date = (
        date.fromisoformat(args.start)
        if args.start
        else resolve_update_start(
            existing=existing,
            default_start=settings.history_start,
            overlap_days=settings.overlap_days,
        )
    )
    end_date = date.fromisoformat(args.end) if args.end else date.today() + timedelta(days=1)
    tickers = args.tickers or list(settings.tickers)

    print(f"Fetching {len(tickers)} tickers from {start_date} to {end_date}.")
    provider = YahooFinanceProvider()
    incoming = provider.fetch_daily_prices(
        tickers=tickers,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    report = validate_market_data(incoming)
    for warning in report.warnings:
        print(f"Warning: {warning}")
    report.raise_for_errors()

    merged, audit = reconcile_market_data(existing=existing, incoming=incoming)
    merged_report = validate_market_data(merged)
    for warning in merged_report.warnings:
        print(f"Warning after merge: {warning}")
    merged_report.raise_for_errors()

    snapshot_path = write_market_data(
        data=merged,
        latest_path=settings.raw_data_path,
        snapshot_dir=settings.snapshot_dir,
        audit=audit,
        audit_path=settings.audit_path,
    )

    latest_date = merged["trade_date"].max()
    print(f"Saved {len(merged):,} rows. Latest trade date: {latest_date:%Y-%m-%d}.")
    print(f"Detected {len(audit):,} revised values in the overlap window.")
    print(f"Snapshot: {snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
