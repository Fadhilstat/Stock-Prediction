"""Orderbook Microstructure and Slippage Execution Analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ruang_risiko_idx.research.orderbook import OrderbookSnapshot


@dataclass(frozen=True)
class ExecutionSimulationResult:
    """Quantitative simulation of an order executed against the orderbook."""

    ticker: str
    side: Literal["BUY", "SELL"]
    target_value_idr: float
    total_lots_filled: int
    actual_value_idr: float
    average_fill_price: float
    reference_price: float
    slippage_bps: float
    ticks_traversed: int
    percent_depth_consumed: float
    liquidity_cliff_warning: bool
    rationale: str


@dataclass(frozen=True)
class DepthPressureSummary:
    """Bid-Ask imbalance and structural queue pressure metrics."""

    ticker: str
    bid_ask_imbalance: float
    top3_bid_concentration_percent: float
    top3_offer_concentration_percent: float
    depth_state: Literal["STRONG_BID_SUPPORT", "BALANCED", "HEAVY_OFFER_PRESSURE"]
    phantom_liquidity_risk: bool


def calculate_depth_pressure(orderbook: OrderbookSnapshot) -> DepthPressureSummary:
    """Compute market depth pressure and Bid-Ask Imbalance (BAI)."""
    total_bids = orderbook.total_bid_lots
    total_offers = orderbook.total_offer_lots
    total_lots = total_bids + total_offers

    if total_lots == 0:
        bai = 0.0
    else:
        bai = (total_bids - total_offers) / total_lots

    top3_bid_lots = sum(b.lots for b in orderbook.bids[:3])
    top3_offer_lots = sum(o.lots for o in orderbook.offers[:3])

    top3_bid_conc = (top3_bid_lots / total_bids * 100.0) if total_bids > 0 else 0.0
    top3_offer_conc = (top3_offer_lots / total_offers * 100.0) if total_offers > 0 else 0.0

    if bai > 0.25:
        state = "STRONG_BID_SUPPORT"
    elif bai < -0.25:
        state = "HEAVY_OFFER_PRESSURE"
    else:
        state = "BALANCED"

    # Phantom liquidity risk if bottom 3 levels hold > 60% of volume (potential spoofing)
    bottom3_bid = sum(b.lots for b in orderbook.bids[-3:])
    phantom_risk = (bottom3_bid / total_bids > 0.60) if total_bids > 0 else False

    return DepthPressureSummary(
        ticker=orderbook.ticker,
        bid_ask_imbalance=round(bai, 3),
        top3_bid_concentration_percent=round(top3_bid_conc, 1),
        top3_offer_concentration_percent=round(top3_offer_conc, 1),
        depth_state=state,
        phantom_liquidity_risk=phantom_risk,
    )


def simulate_order_execution(
    orderbook: OrderbookSnapshot,
    side: Literal["BUY", "SELL"],
    order_value_idr: float,
) -> ExecutionSimulationResult:
    """Simulate order execution walking the orderbook depth queue."""
    if order_value_idr <= 0:
        raise ValueError("order_value_idr must be strictly positive.")

    queue = orderbook.offers if side == "BUY" else orderbook.bids
    ref_price = orderbook.offers[0].price if side == "BUY" else orderbook.bids[0].price

    remaining_val = order_value_idr
    total_filled_lots = 0
    total_cost_idr = 0.0
    ticks_traversed = 0

    for level in queue:
        ticks_traversed += 1
        level_max_val = level.price * level.lots * 100.0  # 1 lot = 100 shares

        if remaining_val <= level_max_val:
            lots_needed = int(remaining_val / (level.price * 100.0))
            if lots_needed == 0 and remaining_val > 0:
                lots_needed = 1
            cost = lots_needed * level.price * 100.0
            total_filled_lots += lots_needed
            total_cost_idr += cost
            remaining_val = 0.0
            break
        else:
            total_filled_lots += level.lots
            total_cost_idr += level_max_val
            remaining_val -= level_max_val

    if total_filled_lots > 0:
        avg_price = total_cost_idr / (total_filled_lots * 100.0)
    else:
        avg_price = ref_price

    if side == "BUY":
        slippage_bps = ((avg_price / ref_price) - 1.0) * 10000.0
    else:
        slippage_bps = (1.0 - (avg_price / ref_price)) * 10000.0

    total_queue_lots = orderbook.total_offer_lots if side == "BUY" else orderbook.total_bid_lots
    percent_consumed = (total_filled_lots / total_queue_lots * 100.0) if total_queue_lots > 0 else 100.0
    liquidity_cliff = percent_consumed > 40.0 or remaining_val > 0

    if liquidity_cliff:
        rationale = f"Order Rp {order_value_idr / 1e6:,.0f} Juta menyerap {percent_consumed:.1f}% kedalaman buku; potensi dampak harga tinggi."
    else:
        rationale = f"Order Rp {order_value_idr / 1e6:,.0f} Juta terserap normal pada {ticks_traversed} fraksi harga."

    return ExecutionSimulationResult(
        ticker=orderbook.ticker,
        side=side,
        target_value_idr=order_value_idr,
        total_lots_filled=total_filled_lots,
        actual_value_idr=round(total_cost_idr, 2),
        average_fill_price=round(avg_price, 2),
        reference_price=ref_price,
        slippage_bps=round(max(0.0, slippage_bps), 1),
        ticks_traversed=ticks_traversed,
        percent_depth_consumed=round(percent_consumed, 1),
        liquidity_cliff_warning=liquidity_cliff,
        rationale=rationale,
    )
