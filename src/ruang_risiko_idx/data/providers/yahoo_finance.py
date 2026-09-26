"""Yahoo Finance adapter built on top of yfinance."""

from datetime import UTC, datetime

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

        try:
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
                threads=False,
                keepna=True,
                progress=False,
                timeout=30,
            )

            if not raw.empty:
                return self.normalize_download(raw=raw, requested_tickers=tickers)
        except Exception:
            pass

        return self._fetch_via_direct_api(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def _fetch_via_direct_api(
        cls,
        tickers: list[str],
        start_date: str,
        end_date: str,
        ingested_at: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch market data directly from Yahoo Finance v8 chart API."""

        import calendar
        from datetime import datetime as dt
        import requests

        start_dt = dt.fromisoformat(start_date)
        end_dt = dt.fromisoformat(end_date)
        period1 = int(calendar.timegm(start_dt.timetuple()))
        period2 = int(calendar.timegm(end_dt.timetuple()))
        timestamp = ingested_at or datetime.now(UTC)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        frames: list[pd.DataFrame] = []

        for ticker in tickers:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                f"?period1={period1}&period2={period2}&interval=1d&events=div%2Csplit"
            )
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code != 200:
                    continue
                payload = response.json()
            except Exception:
                continue

            results = payload.get("chart", {}).get("result")
            if not results:
                continue

            result = results[0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            adjclose_list = result.get("indicators", {}).get("adjclose", [{}])
            if adjclose_list and "adjclose" in adjclose_list[0]:
                adj_closes = adjclose_list[0]["adjclose"]
            else:
                adj_closes = indicators.get("close", [])

            dates = [
                dt.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
                for ts in timestamps
            ]

            df = pd.DataFrame(
                {
                    "trade_date": pd.to_datetime(dates),
                    "open": indicators.get("open", []),
                    "high": indicators.get("high", []),
                    "low": indicators.get("low", []),
                    "close": indicators.get("close", []),
                    "adjusted_close": adj_closes,
                    "volume": indicators.get("volume", []),
                    "dividends": 0.0,
                    "stock_splits": 0.0,
                }
            )

            df.insert(0, "ticker", ticker)
            df["source"] = cls.source_name
            df["ingested_at"] = pd.Timestamp(timestamp)
            df = df.dropna(subset=["trade_date", "close"])
            frames.append(df)

        if not frames:
            raise RuntimeError(
                "Yahoo Finance returned no data. Check the tickers, dates, and connection."
            )

        normalized = pd.concat(frames, ignore_index=True)
        return normalized.sort_values(["ticker", "trade_date"]).reset_index(drop=True)

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
