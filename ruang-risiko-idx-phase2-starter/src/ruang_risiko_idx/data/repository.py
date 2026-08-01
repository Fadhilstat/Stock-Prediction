"""Reconcile market data and write auditable Parquet snapshots."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


KEY_COLUMNS = ["ticker", "trade_date"]
AUDITED_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "dividends",
    "stock_splits",
]


def load_market_data(path: Path) -> pd.DataFrame:
    """Load the latest data file or return an empty table."""

    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def reconcile_market_data(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
    detected_at: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge incoming rows and return a separate change audit."""

    timestamp = pd.Timestamp(detected_at or datetime.now(UTC))
    if existing.empty:
        merged = incoming.sort_values(KEY_COLUMNS).reset_index(drop=True)
        return merged, _empty_audit_frame()

    old = existing.copy()
    new = incoming.copy()
    old["trade_date"] = pd.to_datetime(old["trade_date"])
    new["trade_date"] = pd.to_datetime(new["trade_date"])

    overlap = old.merge(new, on=KEY_COLUMNS, suffixes=("_old", "_new"), how="inner")
    changes: list[dict[str, object]] = []

    for column in AUDITED_COLUMNS:
        old_column = f"{column}_old"
        new_column = f"{column}_new"
        if old_column not in overlap or new_column not in overlap:
            continue

        changed = ~overlap[old_column].fillna(0).eq(overlap[new_column].fillna(0))
        for row in overlap.loc[changed, KEY_COLUMNS + [old_column, new_column]].itertuples(
            index=False
        ):
            changes.append(
                {
                    "ticker": row[0],
                    "trade_date": row[1],
                    "column_name": column,
                    "old_value": row[2],
                    "new_value": row[3],
                    "detected_at": timestamp,
                }
            )

    combined = pd.concat([old, new], ignore_index=True)
    combined = combined.sort_values("ingested_at")
    combined = combined.drop_duplicates(KEY_COLUMNS, keep="last")
    combined = combined.sort_values(KEY_COLUMNS).reset_index(drop=True)

    audit = pd.DataFrame(changes) if changes else _empty_audit_frame()
    return combined, audit


def write_market_data(
    data: pd.DataFrame,
    latest_path: Path,
    snapshot_dir: Path,
    audit: pd.DataFrame | None = None,
    audit_path: Path | None = None,
) -> Path:
    """Write the latest data atomically and keep a timestamped snapshot."""

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = snapshot_dir / f"market_prices_{timestamp}.parquet"
    temporary_path = latest_path.with_suffix(".tmp.parquet")

    data.to_parquet(temporary_path, index=False)
    temporary_path.replace(latest_path)
    data.to_parquet(snapshot_path, index=False)

    if audit is not None and not audit.empty and audit_path is not None:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        existing_audit = pd.read_parquet(audit_path) if audit_path.exists() else pd.DataFrame()
        combined_audit = pd.concat([existing_audit, audit], ignore_index=True)
        combined_audit.to_parquet(audit_path, index=False)

    return snapshot_path


def _empty_audit_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "ticker",
            "trade_date",
            "column_name",
            "old_value",
            "new_value",
            "detected_at",
        ]
    )
