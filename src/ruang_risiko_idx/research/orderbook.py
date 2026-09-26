"""Orderbook and market depth simulator following IDX tick size rules."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class OrderbookLevel:
    """One price level in the bid or offer queue."""

    level: int
    price: float
    lots: int
    value_idr: float
    depth_percent: float


@dataclass(frozen=True)
class OrderbookSnapshot:
    """Complete 10-level market depth orderbook snapshot."""

    ticker: str
    current_price: float
    previous_close: float
    ara_price: float
    arb_price: float
    total_bid_lots: int
    total_offer_lots: int
    bid_offer_ratio: float
    bids: list[OrderbookLevel]
    offers: list[OrderbookLevel]


def get_idx_tick_size(price: float) -> int:
    """Return official Indonesia Stock Exchange tick size based on price."""
    if price < 200:
        return 1
    elif price < 500:
        return 2
    elif price < 2000:
        return 5
    elif price < 5000:
        return 10
    else:
        return 25


def calculate_idx_auto_rejection(prev_close: float) -> tuple[float, float]:
    """Calculate official IDX Auto-Rejection Atas (ARA) and Bawah (ARB) limits."""
    if prev_close < 200:
        pct = 0.35
    elif prev_close <= 5000:
        pct = 0.25
    else:
        pct = 0.20

    tick = get_idx_tick_size(prev_close)
    ara_raw = prev_close * (1.0 + pct)
    arb_raw = prev_close * (1.0 - pct)

    ara = round(ara_raw / tick) * tick
    arb = round(arb_raw / tick) * tick
    return float(ara), float(arb)


def generate_orderbook(
    ticker: str,
    current_price: float,
    previous_close: float,
    average_volume: float = 10_000_000,
) -> OrderbookSnapshot:
    """Generate structured 10-level market depth orderbook."""
    ara, arb = calculate_idx_auto_rejection(previous_close)
    tick = get_idx_tick_size(current_price)

    # Base lot scale calibrated to stock liquidity
    rng = np.random.default_rng(int(current_price) + 42)
    base_lots = max(500, int(average_volume / 2000))

    bids: list[OrderbookLevel] = []
    offers: list[OrderbookLevel] = []

    # 10 Bids downwards
    raw_bid_lots = []
    for i in range(1, 11):
        price_i = current_price - (i - 1) * tick
        if price_i < arb:
            price_i = arb
        decay = 1.0 / (1.0 + 0.08 * i)
        lots_i = int(base_lots * decay * rng.uniform(0.7, 1.4))
        raw_bid_lots.append((price_i, lots_i))

    # 10 Offers upwards
    raw_offer_lots = []
    for i in range(1, 11):
        price_i = current_price + i * tick
        if price_i > ara:
            price_i = ara
        decay = 1.0 / (1.0 + 0.08 * i)
        lots_i = int(base_lots * decay * rng.uniform(0.7, 1.4))
        raw_offer_lots.append((price_i, lots_i))

    total_bid = sum(lots for _, lots in raw_bid_lots)
    total_offer = sum(lots for _, lots in raw_offer_lots)
    max_lots = max(max(l for _, l in raw_bid_lots), max(l for _, l in raw_offer_lots))

    for idx, (p, lots) in enumerate(raw_bid_lots, start=1):
        val = p * lots * 100.0  # 1 lot = 100 shares in IDX
        bids.append(
            OrderbookLevel(
                level=idx,
                price=float(p),
                lots=lots,
                value_idr=val,
                depth_percent=round((lots / max_lots) * 100.0, 1),
            )
        )

    for idx, (p, lots) in enumerate(raw_offer_lots, start=1):
        val = p * lots * 100.0
        offers.append(
            OrderbookLevel(
                level=idx,
                price=float(p),
                lots=lots,
                value_idr=val,
                depth_percent=round((lots / max_lots) * 100.0, 1),
            )
        )

    ratio = total_bid / total_offer if total_offer > 0 else 1.0

    return OrderbookSnapshot(
        ticker=ticker,
        current_price=current_price,
        previous_close=previous_close,
        ara_price=ara,
        arb_price=arb,
        total_bid_lots=total_bid,
        total_offer_lots=total_offer,
        bid_offer_ratio=round(ratio, 2),
        bids=bids,
        offers=offers,
    )
