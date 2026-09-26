"""Stockbit-style Broker Summary and Bandarmology intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd


@dataclass(frozen=True)
class BrokerTradeLine:
    """One broker buy or sell line in the summary."""

    broker_code: str
    broker_name: str
    investor_type: Literal["FOREIGN", "DOMESTIC"]
    lot_volume: int
    average_price: float
    total_value_idr: float


@dataclass(frozen=True)
class BrokerSummarySnapshot:
    """Consolidated broker summary and Bandarmology state."""

    ticker: str
    trade_date: str
    status: Literal[
        "BIG_ACCUMULATION",
        "NORMAL_ACCUMULATION",
        "NEUTRAL",
        "DISTRIBUTION",
        "BIG_DISTRIBUTION",
    ]
    top3_buyer_ratio_percent: float
    top3_seller_ratio_percent: float
    foreign_net_value_idr: float
    domestic_net_value_idr: float
    top_buyers: list[BrokerTradeLine]
    top_sellers: list[BrokerTradeLine]


IDX_BROKER_NAMES: dict[str, tuple[str, Literal["FOREIGN", "DOMESTIC"]]] = {
    "AK": ("UBS Sekuritas Indonesia", "FOREIGN"),
    "BK": ("J.P. Morgan Sekuritas Indonesia", "FOREIGN"),
    "KZ": ("CLSA Sekuritas Indonesia", "FOREIGN"),
    "ZP": ("Maybank Sekuritas Indonesia", "FOREIGN"),
    "RX": ("Macquarie Sekuritas Indonesia", "FOREIGN"),
    "CC": ("Mandiri Sekuritas", "DOMESTIC"),
    "YU": ("CGS International Sekuritas", "DOMESTIC"),
    "NI": ("BNI Sekuritas", "DOMESTIC"),
    "PD": ("Indo Premier Sekuritas", "DOMESTIC"),
    "YP": ("Mirae Asset Sekuritas Indonesia", "DOMESTIC"),
    "XC": ("Ajaib Sekuritas Asia", "DOMESTIC"),
    "GR": ("Panin Sekuritas", "DOMESTIC"),
}


def generate_broker_summary(
    ticker: str,
    trade_date: str,
    close_price: float,
    total_traded_value_idr: float,
    foreign_flow_state: str = "ACCUMULATION",
) -> BrokerSummarySnapshot:
    """Generate realistic Stockbit-style broker summary breakdown."""
    base_val = max(10_000_000_000.0, total_traded_value_idr * 0.45)

    if foreign_flow_state == "ACCUMULATION":
        status = "BIG_ACCUMULATION"
        f_net = base_val * 0.35
        buyer_codes = ["AK", "BK", "KZ", "CC", "ZP"]
        seller_codes = ["YP", "PD", "XC", "NI", "GR"]
        buyer_weights = [0.35, 0.25, 0.18, 0.12, 0.10]
        seller_weights = [0.28, 0.24, 0.20, 0.16, 0.12]
    elif foreign_flow_state == "DISTRIBUTION":
        status = "DISTRIBUTION"
        f_net = -base_val * 0.30
        buyer_codes = ["YP", "PD", "XC", "CC", "NI"]
        seller_codes = ["AK", "BK", "ZP", "KZ", "RX"]
        buyer_weights = [0.26, 0.22, 0.20, 0.18, 0.14]
        seller_weights = [0.38, 0.26, 0.16, 0.12, 0.08]
    else:
        status = "NEUTRAL"
        f_net = base_val * 0.02
        buyer_codes = ["CC", "AK", "YU", "NI", "YP"]
        seller_codes = ["BK", "PD", "KZ", "ZP", "XC"]
        buyer_weights = [0.25, 0.22, 0.20, 0.18, 0.15]
        seller_weights = [0.24, 0.22, 0.20, 0.18, 0.16]

    buyers: list[BrokerTradeLine] = []
    sellers: list[BrokerTradeLine] = []

    total_buy_val = base_val * 1.1
    total_sell_val = base_val * 1.05

    for code, w in zip(buyer_codes, buyer_weights):
        val = total_buy_val * w
        avg_p = close_price * (1.0 - 0.003 * (1.0 - w))
        lots = int(val / (avg_p * 100.0))
        name, inv_type = IDX_BROKER_NAMES.get(code, ("Anggota Bursa", "DOMESTIC"))
        buyers.append(
            BrokerTradeLine(
                broker_code=code,
                broker_name=name,
                investor_type=inv_type,
                lot_volume=lots,
                average_price=round(avg_p, 0),
                total_value_idr=val,
            )
        )

    for code, w in zip(seller_codes, seller_weights):
        val = total_sell_val * w
        avg_p = close_price * (1.0 + 0.003 * (1.0 - w))
        lots = int(val / (avg_p * 100.0))
        name, inv_type = IDX_BROKER_NAMES.get(code, ("Anggota Bursa", "DOMESTIC"))
        sellers.append(
            BrokerTradeLine(
                broker_code=code,
                broker_name=name,
                investor_type=inv_type,
                lot_volume=lots,
                average_price=round(avg_p, 0),
                total_value_idr=val,
            )
        )

    top3_buy = sum(b.total_value_idr for b in buyers[:3]) / total_buy_val * 100.0
    top3_sell = sum(s.total_value_idr for s in sellers[:3]) / total_sell_val * 100.0

    return BrokerSummarySnapshot(
        ticker=ticker,
        trade_date=trade_date,
        status=status,
        top3_buyer_ratio_percent=round(top3_buy, 1),
        top3_seller_ratio_percent=round(top3_sell, 1),
        foreign_net_value_idr=f_net,
        domestic_net_value_idr=-f_net,
        top_buyers=buyers,
        top_sellers=sellers,
    )
