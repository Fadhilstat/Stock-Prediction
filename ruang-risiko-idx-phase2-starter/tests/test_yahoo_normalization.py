from datetime import UTC, datetime

import pandas as pd

from ruang_risiko_idx.data.providers.yahoo_finance import YahooFinanceProvider


def test_normalize_multi_ticker_download() -> None:
    dates = pd.to_datetime(["2026-07-30", "2026-07-31"])
    columns = pd.MultiIndex.from_product(
        [
            ["BBCA.JK", "TLKM.JK"],
            ["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        ]
    )
    raw = pd.DataFrame(
        [
            [9000, 9100, 8950, 9050, 9050, 100, 3000, 3050, 2970, 3010, 3010, 200],
            [9050, 9150, 9000, 9125, 9125, 120, 3010, 3070, 2990, 3060, 3060, 220],
        ],
        index=dates,
        columns=columns,
    )

    result = YahooFinanceProvider.normalize_download(
        raw=raw,
        requested_tickers=["BBCA.JK", "TLKM.JK"],
        ingested_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert len(result) == 4
    assert set(result["ticker"]) == {"BBCA.JK", "TLKM.JK"}
    assert result["adjusted_close"].notna().all()
    assert result["source"].eq("yahoo_finance_via_yfinance").all()
