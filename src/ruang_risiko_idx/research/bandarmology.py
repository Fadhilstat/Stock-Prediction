"""Stockbit Broker Summary and Institutional Flow (Bandarmology) Engine.

Computes top buyer/seller concentration ratios (CR1, CR3, CR5),
broker transaction distribution, and foreign-domestic institutional flow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BrokerEntry:
    """Record of a broker participant buy or sell activity."""

    broker_code: str
    broker_name: str
    lots: int
    value_idr: float
    avg_price: float
    is_foreign: bool


@dataclass(frozen=True)
class BrokerSummaryReport:
    """Complete Stockbit-grade broker summary and accumulation report."""

    ticker: str
    trade_date: str
    regime: str  # BIG_ACCUMULATION, ACCUMULATION, NEUTRAL, DISTRIBUTION, BIG_DISTRIBUTION
    bandar_score: float  # -100 to +100
    concentration_ratio_1: float
    concentration_ratio_3: float
    concentration_ratio_5: float
    net_foreign_flow_idr: float
    total_market_turnover_idr: float
    top_buyers: list[BrokerEntry]
    top_sellers: list[BrokerEntry]
    summary_message: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize broker summary to dictionary."""
        return {
            "ticker": self.ticker,
            "trade_date": self.trade_date,
            "regime": self.regime,
            "bandar_score": round(self.bandar_score, 1),
            "concentration_ratio_1": round(self.concentration_ratio_1, 2),
            "concentration_ratio_3": round(self.concentration_ratio_3, 2),
            "concentration_ratio_5": round(self.concentration_ratio_5, 2),
            "net_foreign_flow_idr": round(self.net_foreign_flow_idr, 0),
            "total_market_turnover_idr": round(self.total_market_turnover_idr, 0),
            "top_buyers": [asdict(b) for b in self.top_buyers],
            "top_sellers": [asdict(s) for s in self.top_sellers],
            "summary_message": self.summary_message,
        }


CANONICAL_BROKERS = {
    "YU": ("CGS International Sekuritas", True),
    "CC": ("Mandiri Sekuritas", False),
    "ZP": ("Maybank Sekuritas", True),
    "RX": ("Macquarie Sekuritas", True),
    "AK": ("UBS Sekuritas Indonesia", True),
    "KZ": ("CLSA Sekuritas Indonesia", True),
    "BK": ("J.P. Morgan Sekuritas", True),
    "PD": ("Indo Premier Sekuritas", False),
    "NI": ("BNI Sekuritas", False),
    "OD": ("BRI Danareksa Sekuritas", False),
    "YP": ("Mirae Asset Sekuritas", False),
    "SQ": ("BCA Sekuritas", False),
    "XC": ("Ajaib Sekuritas", False),
    "XL": ("Stockbit Sekuritas", False),
}


def analyze_broker_summary(
    ticker: str = "BBCA.JK",
    trade_date: str = "2026-09-26",
) -> BrokerSummaryReport:
    """Simulate and compute institutional broker accumulation-distribution metrics."""
    ticker_clean = ticker.upper()
    base_prices = {"BBCA.JK": 10450, "BBRI.JK": 5125, "BMRI.JK": 7100, "TLKM.JK": 3120, "ASII.JK": 5050}
    current_px = base_prices.get(ticker_clean, 5000)

    np.random.seed(abs(hash(ticker_clean + trade_date)) % (2**31))

    # Select random subsets of active brokers
    buyer_codes = ["YU", "ZP", "AK", "KZ", "BK", "CC", "PD"]
    seller_codes = ["YP", "XC", "XL", "NI", "OD", "SQ", "RX"]

    # Generate buy volume
    top_buyers: list[BrokerEntry] = []
    buy_values = []
    for code in buyer_codes:
        name, is_foreign = CANONICAL_BROKERS.get(code, ("Sekuritas", False))
        lots = int(np.random.randint(15000, 120000))
        price_offset = np.random.uniform(-50, 50)
        avg_px = round(current_px + price_offset, 0)
        val = float(lots * 100 * avg_px)
        buy_values.append(val)
        top_buyers.append(
            BrokerEntry(
                broker_code=code,
                broker_name=name,
                lots=lots,
                value_idr=val,
                avg_price=avg_px,
                is_foreign=is_foreign,
            )
        )

    # Sort buyers descending by transaction value
    top_buyers.sort(key=lambda b: b.value_idr, reverse=True)

    # Generate sell volume
    top_sellers: list[BrokerEntry] = []
    sell_values = []
    for code in seller_codes:
        name, is_foreign = CANONICAL_BROKERS.get(code, ("Sekuritas", False))
        lots = int(np.random.randint(10000, 95000))
        price_offset = np.random.uniform(-40, 40)
        avg_px = round(current_px + price_offset, 0)
        val = float(lots * 100 * avg_px)
        sell_values.append(val)
        top_sellers.append(
            BrokerEntry(
                broker_code=code,
                broker_name=name,
                lots=lots,
                value_idr=val,
                avg_price=avg_px,
                is_foreign=is_foreign,
            )
        )

    # Sort sellers descending by transaction value
    top_sellers.sort(key=lambda s: s.value_idr, reverse=True)

    total_buy_val = sum(b.value_idr for b in top_buyers)
    total_sell_val = sum(s.value_idr for s in top_sellers)
    turnover = max(total_buy_val, total_sell_val)

    # Concentration ratios
    cr1 = (top_buyers[0].value_idr / total_buy_val) * 100.0
    cr3 = (sum(b.value_idr for b in top_buyers[:3]) / total_buy_val) * 100.0
    cr5 = (sum(b.value_idr for b in top_buyers[:5]) / total_buy_val) * 100.0

    # Foreign vs domestic flow
    foreign_buy_val = sum(b.value_idr for b in top_buyers if b.is_foreign)
    foreign_sell_val = sum(s.value_idr for s in top_sellers if s.is_foreign)
    net_foreign = foreign_buy_val - foreign_sell_val

    # Bandar score (-100 to +100)
    net_top3_val = sum(b.value_idr for b in top_buyers[:3]) - sum(s.value_idr for s in top_sellers[:3])
    score = float(np.clip((net_top3_val / turnover) * 100.0 * 1.5, -100.0, 100.0))

    if score >= 40.0 and cr3 >= 60.0:
        regime = "BIG_ACCUMULATION"
    elif score >= 15.0:
        regime = "ACCUMULATION"
    elif score <= -40.0:
        regime = "BIG_DISTRIBUTION"
    elif score <= -15.0:
        regime = "DISTRIBUTION"
    else:
        regime = "NEUTRAL"

    summary = (
        f"Bandarmology Status for {ticker_clean}: {regime} (Skor: {score:+.1f}). "
        f"Top 3 Buyer Concentration (CR3) adalah {cr3:.1f}%. "
        f"Net Foreign Flow tercatat Rp {net_foreign / 1e9:+.2f} Miliar."
    )

    return BrokerSummaryReport(
        ticker=ticker_clean,
        trade_date=trade_date,
        regime=regime,
        bandar_score=score,
        concentration_ratio_1=cr1,
        concentration_ratio_3=cr3,
        concentration_ratio_5=cr5,
        net_foreign_flow_idr=net_foreign,
        total_market_turnover_idr=turnover,
        top_buyers=top_buyers[:5],
        top_sellers=top_sellers[:5],
        summary_message=summary,
    )
