from datetime import UTC, datetime

import pandas as pd

from ruang_risiko_idx.data.repository import reconcile_market_data


def make_frame(close_value: float, ingested_at: datetime) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA.JK"],
            "trade_date": pd.to_datetime(["2026-07-31"]),
            "open": [9000.0],
            "high": [9200.0],
            "low": [8950.0],
            "close": [close_value],
            "adjusted_close": [close_value],
            "volume": [100],
            "dividends": [0.0],
            "stock_splits": [0.0],
            "source": ["test"],
            "ingested_at": [ingested_at],
        }
    )


def test_reconcile_keeps_latest_and_records_changes() -> None:
    existing = make_frame(9050.0, datetime(2026, 8, 1, 8, tzinfo=UTC))
    incoming = make_frame(9075.0, datetime(2026, 8, 1, 10, tzinfo=UTC))

    merged, audit = reconcile_market_data(existing, incoming)

    assert len(merged) == 1
    assert merged.loc[0, "close"] == 9075.0
    assert set(audit["column_name"]) == {"close", "adjusted_close"}
