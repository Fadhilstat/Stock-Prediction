"""Orderbook Microstructure Imbalance (OMI) and Order Flow Delta Engine.

Analyzes high-frequency queue dynamics, Volume Order Imbalance (VOI),
Cumulative Volume Delta (CVD), and spoofing or phantom depth patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np

from ruang_risiko_idx.research.orderbook import OrderbookSnapshot


@dataclass(frozen=True)
class LevelImbalance:
    """Imbalance metrics at a specific orderbook step."""

    step: int
    bid_price: float
    bid_lots: int
    offer_price: float
    offer_lots: int
    net_level_delta_lots: int
    imbalance_ratio: float


@dataclass(frozen=True)
class MicrostructureAnalysis:
    """Comprehensive orderbook microstructure and order flow delta analysis."""

    ticker: str
    volume_order_imbalance_lots: int
    voi_normalized: float
    cumulative_volume_delta_lots: int
    cvd_nominal_idr: float
    order_flow_regime: Literal["AGGRESSIVE_BUYING", "BALANCED_FLOW", "AGGRESSIVE_SELLING"]
    bid_slope: float
    offer_slope: float
    slope_ratio: float
    spoofing_probability_score: float
    phantom_wall_detected: bool
    absorption_state: Literal["BID_ABSORPTION", "NEUTRAL_FLOW", "OFFER_ABSORPTION"]
    operational_insight: str
    level_breakdowns: list[LevelImbalance]


def compute_microstructure_imbalance(
    orderbook: OrderbookSnapshot,
    historical_trade_delta_lots: int | None = None,
) -> MicrostructureAnalysis:
    """Calculate multi-level volume order imbalance and order flow delta."""
    bids = orderbook.bids
    offers = orderbook.offers
    total_levels = min(len(bids), len(offers))

    level_breakdowns: list[LevelImbalance] = []
    weighted_voi = 0.0
    total_depth_lots = 0

    for i in range(total_levels):
        b = bids[i]
        o = offers[i]
        weight = 1.0 / (i + 1)
        net_delta = b.lots - o.lots
        level_sum = b.lots + o.lots
        ratio = (net_delta / level_sum) if level_sum > 0 else 0.0

        level_breakdowns.append(
            LevelImbalance(
                step=i + 1,
                bid_price=b.price,
                bid_lots=b.lots,
                offer_price=o.price,
                offer_lots=o.lots,
                net_level_delta_lots=net_delta,
                imbalance_ratio=round(ratio, 3),
            )
        )

        weighted_voi += net_delta * weight
        total_depth_lots += level_sum

    raw_voi_lots = int(weighted_voi)
    voi_normalized = float(np.clip(weighted_voi / (total_depth_lots * 0.5 + 1e-6), -1.0, 1.0))

    # Derived or supplied Cumulative Volume Delta (CVD)
    if historical_trade_delta_lots is not None:
        cvd_lots = historical_trade_delta_lots
    else:
        # Calibrated proxy based on top 3 touches and total depth
        top3_bid = sum(b.lots for b in bids[:3])
        top3_offer = sum(o.lots for o in offers[:3])
        cvd_lots = int((top3_bid - top3_offer) * 0.75)

    cvd_nominal_idr = float(cvd_lots * orderbook.current_price * 100)

    if voi_normalized > 0.20 and cvd_lots > 0:
        regime: Literal["AGGRESSIVE_BUYING", "BALANCED_FLOW", "AGGRESSIVE_SELLING"] = "AGGRESSIVE_BUYING"
    elif voi_normalized < -0.20 and cvd_lots < 0:
        regime = "AGGRESSIVE_SELLING"
    else:
        regime = "BALANCED_FLOW"

    # Orderbook Slopes (lots per price step)
    bid_slope = float((bids[-1].lots - bids[0].lots) / max(1, len(bids))) if bids else 0.0
    offer_slope = float((offers[-1].lots - offers[0].lots) / max(1, len(offers))) if offers else 0.0
    denom = abs(offer_slope) if abs(offer_slope) > 1e-4 else 1.0
    slope_ratio = float(abs(bid_slope) / denom)

    # Spoofing & Phantom Wall Detection
    # If levels 7-10 hold > 55% of total side lots while level 1-2 have low depth
    bid_tail_lots = sum(b.lots for b in bids[6:])
    offer_tail_lots = sum(o.lots for o in offers[6:])
    total_bids = orderbook.total_bid_lots or 1
    total_offers = orderbook.total_offer_lots or 1

    phantom_bid_ratio = bid_tail_lots / total_bids
    phantom_offer_ratio = offer_tail_lots / total_offers
    phantom_wall = phantom_bid_ratio > 0.55 or phantom_offer_ratio > 0.55

    spoofing_score = 0.0
    if phantom_bid_ratio > 0.50:
        spoofing_score += 0.40
    if phantom_offer_ratio > 0.50:
        spoofing_score += 0.40
    if abs(voi_normalized) > 0.60:
        spoofing_score += 0.20
    spoofing_score = float(np.clip(spoofing_score, 0.0, 1.0))

    # Absorption state
    if cvd_lots > 0 and voi_normalized < -0.15:
        # High buying into offer wall
        absorption: Literal["BID_ABSORPTION", "NEUTRAL_FLOW", "OFFER_ABSORPTION"] = "OFFER_ABSORPTION"
        insight = "Aliran beli agresif menyerap antrean penawaran (offer absorption) tanpa penurunan harga."
    elif cvd_lots < 0 and voi_normalized > 0.15:
        # High selling absorbed by bid wall
        absorption = "BID_ABSORPTION"
        insight = "Tekanan jual pasar diserap sepenuhnya oleh benteng antrean pembeli (bid absorption)."
    else:
        absorption = "NEUTRAL_FLOW"
        insight = "Antrean bid dan offer berada dalam ekuilibrium mikrostruktur yang wajar."

    return MicrostructureAnalysis(
        ticker=orderbook.ticker,
        volume_order_imbalance_lots=raw_voi_lots,
        voi_normalized=round(voi_normalized, 3),
        cumulative_volume_delta_lots=cvd_lots,
        cvd_nominal_idr=cvd_nominal_idr,
        order_flow_regime=regime,
        bid_slope=round(bid_slope, 2),
        offer_slope=round(offer_slope, 2),
        slope_ratio=round(slope_ratio, 2),
        spoofing_probability_score=round(spoofing_score, 2),
        phantom_wall_detected=phantom_wall,
        absorption_state=absorption,
        operational_insight=insight,
        level_breakdowns=level_breakdowns,
    )
