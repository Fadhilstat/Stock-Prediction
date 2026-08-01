"""Validation rules for normalized daily market data."""

from dataclasses import dataclass, field

import pandas as pd


REQUIRED_COLUMNS = {
    "ticker",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "dividends",
    "stock_splits",
    "source",
    "ingested_at",
}


@dataclass
class ValidationReport:
    """Collect blocking errors and non-blocking warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            joined = "\n".join(f"- {message}" for message in self.errors)
            raise MarketDataValidationError(f"Market data validation failed:\n{joined}")


class MarketDataValidationError(ValueError):
    """Raised when market data fails blocking checks."""


def validate_market_data(data: pd.DataFrame) -> ValidationReport:
    """Run structural and financial consistency checks."""

    report = ValidationReport()
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        report.errors.append(
            "Missing required columns: " + ", ".join(sorted(missing_columns))
        )
        return report

    if data.empty:
        report.errors.append("The market data table is empty.")
        return report

    keys = ["ticker", "trade_date"]
    duplicate_count = int(data.duplicated(keys).sum())
    if duplicate_count:
        report.errors.append(f"Found {duplicate_count} duplicate ticker and date rows.")

    if data["ticker"].isna().any() or data["ticker"].astype(str).str.strip().eq("").any():
        report.errors.append("Ticker values cannot be empty.")

    price_columns = ["open", "high", "low", "close", "adjusted_close"]
    missing_price_count = int(data[price_columns].isna().sum().sum())
    if missing_price_count:
        report.errors.append(f"Found {missing_price_count} missing price values.")

    non_positive_count = int((data[price_columns] <= 0).sum().sum())
    if non_positive_count:
        report.errors.append(f"Found {non_positive_count} non-positive price values.")

    invalid_high = data["high"] < data[["open", "low", "close"]].max(axis=1)
    if invalid_high.any():
        report.errors.append(f"Found {int(invalid_high.sum())} rows with an invalid high price.")

    invalid_low = data["low"] > data[["open", "high", "close"]].min(axis=1)
    if invalid_low.any():
        report.errors.append(f"Found {int(invalid_low.sum())} rows with an invalid low price.")

    negative_volume = data["volume"].fillna(0) < 0
    if negative_volume.any():
        report.errors.append(f"Found {int(negative_volume.sum())} rows with negative volume.")

    if data["volume"].isna().any():
        report.warnings.append(
            f"Found {int(data['volume'].isna().sum())} missing volume values."
        )

    for ticker, ticker_data in data.groupby("ticker", sort=False):
        dates = pd.to_datetime(ticker_data["trade_date"], errors="coerce")
        if dates.isna().any():
            report.errors.append(f"Ticker {ticker} contains an invalid trade date.")
            continue
        if not dates.is_monotonic_increasing:
            report.warnings.append(f"Ticker {ticker} is not sorted by trade date.")

        adjusted_returns = ticker_data["adjusted_close"].pct_change(fill_method=None)
        extreme_moves = adjusted_returns.abs() > 0.35
        if extreme_moves.any():
            report.warnings.append(
                f"Ticker {ticker} has {int(extreme_moves.sum())} daily moves above 35 percent."
            )

    return report
