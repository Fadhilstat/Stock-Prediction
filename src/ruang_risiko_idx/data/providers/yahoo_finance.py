"""Yahoo Finance adapter built on top of yfinance."""

from datetime import UTC, datetime
from typing import Any

import pandas as pd


COLUMN_MAP = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adjusted_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "stock_splits",
}

REQUIRED_PRICE_COLUMNS = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}


class YahooFinanceProvider:
    """Download and normalize daily prices from Yahoo Finance."""

    source_name = "yahoo_finance_via_yfinance"

    def fetch_daily_prices(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Download prices and return a stable long-form schema."""

        if not tickers:
            raise ValueError("At least one ticker must be provided.")

        import yfinance as yf

        raw = yf.download(
            tickers=tickers,
            start=start_date,
            end=end_date,
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=True,
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=30,
        )

        if raw.empty:
            raise RuntimeError(
                "Yahoo Finance returned no data. Check the tickers, dates, and connection."
            )

        return self.normalize_download(raw=raw, requested_tickers=tickers)

    @classmethod
    def normalize_download(
        cls,
        raw: pd.DataFrame,
        requested_tickers: list[str],
        ingested_at: datetime | None = None,
    ) -> pd.DataFrame:
        """Convert yfinance output into one row per ticker and trade date."""

        timestamp = ingested_at or datetime.now(UTC)
        frames: list[pd.DataFrame] = []

        if isinstance(raw.columns, pd.MultiIndex):
            level_zero = set(raw.columns.get_level_values(0).astype(str))
            level_one = set(raw.columns.get_level_values(1).astype(str))

            for ticker in requested_tickers:
                if ticker in level_zero:
                    ticker_frame = raw[ticker].copy()
                elif ticker in level_one:
                    ticker_frame = raw.xs(ticker, axis=1, level=1).copy()
                else:
                    continue
                frames.append(cls._normalize_one_ticker(ticker_frame, ticker, timestamp))
        else:
            if len(requested_tickers) != 1:
                raise ValueError(
                    "Single-level columns can only be normalized for one requested ticker."
                )
            frames.append(cls._normalize_one_ticker(raw.copy(), requested_tickers[0], timestamp))

        if not frames:
            raise RuntimeError("No requested ticker was found in the Yahoo Finance response.")

        normalized = pd.concat(frames, ignore_index=True)
        normalized = normalized.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
        return normalized

    @classmethod
    def _normalize_one_ticker(
        cls,
        frame: pd.DataFrame,
        ticker: str,
        ingested_at: datetime,
    ) -> pd.DataFrame:
        missing = REQUIRED_PRICE_COLUMNS.difference(frame.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing required Yahoo Finance columns for {ticker}: {missing_text}")

        selected = frame.rename(columns=COLUMN_MAP).copy()
        selected.index = pd.to_datetime(selected.index, errors="coerce")
        selected.index.name = "trade_date"
        selected = selected.reset_index()

        for optional_column in ("dividends", "stock_splits"):
            if optional_column not in selected.columns:
                selected[optional_column] = 0.0

        keep_columns = [
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "dividends",
            "stock_splits",
        ]
        selected = selected[keep_columns]
        selected.insert(0, "ticker", ticker)
        selected["source"] = cls.source_name
        selected["ingested_at"] = pd.Timestamp(ingested_at)
        selected = selected.dropna(subset=["trade_date"])
        return selected
