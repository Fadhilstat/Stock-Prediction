"""Shared contract for market data providers."""

from typing import Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    """Define the minimum interface for daily market data."""

    def fetch_daily_prices(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Return normalized daily prices for the requested period."""
