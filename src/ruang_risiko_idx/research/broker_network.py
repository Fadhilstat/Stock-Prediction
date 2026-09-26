"""Broker Flow Network and Smart Money Classification Matrix for IDX Equities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ruang_risiko_idx.research.broker_summary import BrokerSummarySnapshot, generate_broker_summary


BROKER_TIER_MAP: dict[str, Literal["FOREIGN_INSTITUTIONAL", "DOMESTIC_INSTITUTIONAL", "RETAIL_DOMESTIC"]] = {
    # Foreign Institutional
    "AK": "FOREIGN_INSTITUTIONAL",  # UBS
    "BK": "FOREIGN_INSTITUTIONAL",  # JP Morgan
    "KZ": "FOREIGN_INSTITUTIONAL",  # CLSA
    "ZP": "FOREIGN_INSTITUTIONAL",  # Maybank
    "RX": "FOREIGN_INSTITUTIONAL",  # Macquarie
    "CG": "FOREIGN_INSTITUTIONAL",  # CGS-CIMB
    "CS": "FOREIGN_INSTITUTIONAL",  # Credit Suisse
    # Domestic Institutional
    "CC": "DOMESTIC_INSTITUTIONAL",  # Mandiri Sekuritas
    "NI": "DOMESTIC_INSTITUTIONAL",  # BNI Sekuritas
    "OD": "DOMESTIC_INSTITUTIONAL",  # BRI Danareksa
    "YU": "DOMESTIC_INSTITUTIONAL",  # CGS International
    "LG": "DOMESTIC_INSTITUTIONAL",  # Trimegah
    # Retail Domestic
    "YP": "RETAIL_DOMESTIC",  # Mirae Asset
    "PD": "RETAIL_DOMESTIC",  # Indo Premier
    "XC": "RETAIL_DOMESTIC",  # Ajaib
    "XL": "RETAIL_DOMESTIC",  # Stockbit Sekuritas
    "CP": "RETAIL_DOMESTIC",  # KB Valbury
    "SQ": "RETAIL_DOMESTIC",  # BCA Sekuritas Retail
    "GR": "RETAIL_DOMESTIC",  # Panin Sekuritas
}


@dataclass(frozen=True)
class BrokerNetworkProfile:
    """Consolidated tier classification and smart money index."""

    ticker: str
    smart_money_index: float
    foreign_institutional_net_idr: float
    domestic_institutional_net_idr: float
    retail_domestic_net_idr: float
    regime: Literal[
        "STRONG_INSTITUTIONAL_ACCUMULATION",
        "MODERATE_ACCUMULATION",
        "BALANCED_FLOW",
        "RETAIL_TRAP_DISTRIBUTION",
        "INSTITUTIONAL_OFFLOADING",
    ]
    retail_trap_detected: bool
    summary: str


def analyze_broker_network(broker_summary: BrokerSummarySnapshot) -> BrokerNetworkProfile:
    """Classify broker lines into institutional tiers and compute smart money index."""
    tier_buy_val: dict[str, float] = {
        "FOREIGN_INSTITUTIONAL": 0.0,
        "DOMESTIC_INSTITUTIONAL": 0.0,
        "RETAIL_DOMESTIC": 0.0,
    }
    tier_sell_val: dict[str, float] = {
        "FOREIGN_INSTITUTIONAL": 0.0,
        "DOMESTIC_INSTITUTIONAL": 0.0,
        "RETAIL_DOMESTIC": 0.0,
    }

    for b in broker_summary.top_buyers:
        tier = BROKER_TIER_MAP.get(b.broker_code, "RETAIL_DOMESTIC")
        tier_buy_val[tier] += b.total_value_idr

    for s in broker_summary.top_sellers:
        tier = BROKER_TIER_MAP.get(s.broker_code, "RETAIL_DOMESTIC")
        tier_sell_val[tier] += s.total_value_idr

    f_net = tier_buy_val["FOREIGN_INSTITUTIONAL"] - tier_sell_val["FOREIGN_INSTITUTIONAL"]
    d_net = tier_buy_val["DOMESTIC_INSTITUTIONAL"] - tier_sell_val["DOMESTIC_INSTITUTIONAL"]
    r_net = tier_buy_val["RETAIL_DOMESTIC"] - tier_sell_val["RETAIL_DOMESTIC"]

    smart_money_net = f_net + d_net
    total_institutional_flow = (
        tier_buy_val["FOREIGN_INSTITUTIONAL"]
        + tier_sell_val["FOREIGN_INSTITUTIONAL"]
        + tier_buy_val["DOMESTIC_INSTITUTIONAL"]
        + tier_sell_val["DOMESTIC_INSTITUTIONAL"]
    )
    total_retail_flow = tier_buy_val["RETAIL_DOMESTIC"] + tier_sell_val["RETAIL_DOMESTIC"]
    total_flow = total_institutional_flow + total_retail_flow

    if total_flow > 0:
        base_smai = 50.0 + (smart_money_net / total_flow) * 50.0
        smai = max(0.0, min(100.0, base_smai))
    else:
        smai = 50.0

    # Retail Trap condition: retail is heavy net buying while smart money is net selling
    retail_trap = r_net > 0 and smart_money_net < -1_000_000_000.0

    if retail_trap:
        regime = "RETAIL_TRAP_DISTRIBUTION"
        summary = "Waspada Jebakan Ritel: Broker institusi melakukan distribusi ke broker ritel agresif."
    elif smai >= 65.0:
        regime = "STRONG_INSTITUTIONAL_ACCUMULATION"
        summary = "Akumulasi Institusi Kuat: Smart money mendominasi aliran beli neto."
    elif smai >= 54.0:
        regime = "MODERATE_ACCUMULATION"
        summary = "Akumulasi Moderat: Partisipasi institusional positif."
    elif smai <= 35.0:
        regime = "INSTITUTIONAL_OFFLOADING"
        summary = "Distribusi Institusi: Smart money melepas inventaris."
    else:
        regime = "BALANCED_FLOW"
        summary = "Aliran Seimbang: Tidak ada dominasi signifikan antara ritel dan institusi."

    return BrokerNetworkProfile(
        ticker=broker_summary.ticker,
        smart_money_index=round(smai, 1),
        foreign_institutional_net_idr=round(f_net, 2),
        domestic_institutional_net_idr=round(d_net, 2),
        retail_domestic_net_idr=round(r_net, 2),
        regime=regime,
        retail_trap_detected=retail_trap,
        summary=summary,
    )


def scan_universe_bandarmology(
    tickers: list[str],
    prices: dict[str, float],
    trade_date: str = "2026-09-25",
) -> list[dict[str, object]]:
    """Scan and rank the entire universe by Smart Money Accumulation Index."""
    results = []
    for ticker in tickers:
        p = prices.get(ticker, 5000.0)
        bs = generate_broker_summary(
            ticker=ticker,
            trade_date=trade_date,
            close_price=p,
            total_traded_value_idr=50_000_000_000.0,
            foreign_flow_state="ACCUMULATION" if ticker in ["BBCA.JK", "TLKM.JK"] else "NEUTRAL",
        )
        profile = analyze_broker_network(bs)
        results.append(
            {
                "ticker": ticker,
                "smai": profile.smart_money_index,
                "regime": profile.regime,
                "foreign_net_idr": profile.foreign_institutional_net_idr,
                "retail_net_idr": profile.retail_domestic_net_idr,
                "retail_trap": profile.retail_trap_detected,
                "status": bs.status,
            }
        )

    return sorted(results, key=lambda x: float(x["smai"]), reverse=True)
