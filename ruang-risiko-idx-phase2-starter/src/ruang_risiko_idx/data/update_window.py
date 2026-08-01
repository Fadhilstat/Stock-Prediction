"""Resolve the date range for incremental market data updates."""

from datetime import date, timedelta

import pandas as pd


def resolve_update_start(
    existing: pd.DataFrame,
    default_start: str,
    overlap_days: int,
) -> date:
    """Return a start date that includes a reconciliation overlap."""

    if existing.empty or "trade_date" not in existing:
        return date.fromisoformat(default_start)

    latest_date = pd.to_datetime(existing["trade_date"]).max().date()
    return latest_date - timedelta(days=overlap_days)
