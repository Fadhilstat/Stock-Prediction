from datetime import UTC, datetime

import pandas as pd

from ruang_risiko_idx.data.validation import validate_market_data


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA.JK", "BBCA.JK"],
            "trade_date": pd.to_datetime(["2026-07-30", "2026-07-31"]),
            "open": [9000.0, 9050.0],
            "high": [9100.0, 9150.0],
            "low": [8950.0, 9000.0],
            "close": [9050.0, 9125.0],
            "adjusted_close": [9050.0, 9125.0],
            "volume": [100, 120],
            "dividends": [0.0, 0.0],
            "stock_splits": [0.0, 0.0],
            "source": ["test", "test"],
            "ingested_at": [datetime(2026, 8, 1, tzinfo=UTC)] * 2,
        }
    )


def test_valid_market_data_passes() -> None:
    report = validate_market_data(valid_frame())
    assert report.is_valid


def test_invalid_high_is_blocking() -> None:
    data = valid_frame()
    data.loc[0, "high"] = 8900.0

    report = validate_market_data(data)

    assert not report.is_valid
    assert any("invalid high" in error for error in report.errors)
