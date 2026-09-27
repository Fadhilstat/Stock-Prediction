"""Level-2 (L2) 10-Depth Orderbook Microstructure & Spoofing Engine.

Simulates and evaluates 10-level institutional orderbook depth, calculating
bid-ask volume imbalance, cumulative depth pressure, large wall detection,
and algorithmic spoofing risk scores according to IDX tick size rules.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ruang_risiko_idx.research.multimodal_engine import STOCK_CATALOG_MAP


@dataclass
class OrderbookLevel:
    """Individual price level in the orderbook queue."""

    level: int
    price: float
    volume_lots: int
    queue_orders: int
    total_value_idr: float
    depth_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "price": self.price,
            "price_formatted": f"Rp {self.price:,.0f}",
            "volume_lots": self.volume_lots,
            "volume_formatted": f"{self.volume_lots:,} lots",
            "queue_orders": self.queue_orders,
            "total_value_idr": round(self.total_value_idr, 0),
            "depth_pct": round(self.depth_pct, 1),
        }


@dataclass
class OrderbookSnapshot:
    """Consolidated 10-depth orderbook matrix with institutional pressure metrics."""

    ticker: str
    timestamp: str
    last_price: float
    spread_idr: float
    spread_pct: float
    vwap_bid: float
    vwap_ask: float
    total_bid_lots: int
    total_ask_lots: int
    bid_ask_imbalance_ratio: float
    dominant_side: str
    bid_wall_detected: bool
    bid_wall_price: float | None
    ask_wall_detected: bool
    ask_wall_price: float | None
    spoofing_probability_pct: float
    orderbook_health_score: float
    bids: list[OrderbookLevel] = field(default_factory=list)
    asks: list[OrderbookLevel] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "last_price": self.last_price,
            "last_price_formatted": f"Rp {self.last_price:,.0f}",
            "spread_idr": self.spread_idr,
            "spread_pct": round(self.spread_pct, 2),
            "vwap_bid": round(self.vwap_bid, 1),
            "vwap_ask": round(self.vwap_ask, 1),
            "total_bid_lots": self.total_bid_lots,
            "total_ask_lots": self.total_ask_lots,
            "total_bid_formatted": f"{self.total_bid_lots:,} lots",
            "total_ask_formatted": f"{self.total_ask_lots:,} lots",
            "bid_ask_imbalance_ratio": round(self.bid_ask_imbalance_ratio, 3),
            "dominant_side": self.dominant_side,
            "bid_wall_detected": self.bid_wall_detected,
            "bid_wall_price": self.bid_wall_price,
            "ask_wall_detected": self.ask_wall_detected,
            "ask_wall_price": self.ask_wall_price,
            "spoofing_probability_pct": round(self.spoofing_probability_pct, 1),
            "orderbook_health_score": round(self.orderbook_health_score, 1),
            "bids": [b.to_dict() for b in self.bids],
            "asks": [a.to_dict() for a in self.asks],
        }


class OrderbookEngine:
    """Computes realistic 10-level IDX orderbook microstructure."""

    def _get_idx_tick_size(self, price: float) -> float:
        """Return official IDX tick size (fraksi harga BEI)."""
        if price < 200:
            return 1.0
        elif price < 500:
            return 2.0
        elif price < 2000:
            return 5.0
        elif price < 5000:
            return 10.0
        else:
            return 25.0

    def generate_orderbook(self, ticker: str) -> OrderbookSnapshot:
        """Generate high-fidelity L2 10-depth orderbook with spoofing detection."""
        ticker_upper = ticker.upper().strip()
        asset_info = STOCK_CATALOG_MAP.get(ticker_upper, {
            "name": ticker_upper,
            "base_price": 5000.0,
            "volatility": 20.0,
            "sector": "Market Equities",
        })
        base_price = float(asset_info.get("base_price", 5000.0))
        tick = self._get_idx_tick_size(base_price)

        # Pseudorandom seed based on ticker and current minute for realistic stability
        now_dt = datetime.now(timezone.utc)
        seed = sum(ord(c) for c in ticker_upper) + now_dt.minute * 13

        bids: list[OrderbookLevel] = []
        asks: list[OrderbookLevel] = []

        total_bid_lots = 0
        total_ask_lots = 0
        sum_bid_px_vol = 0.0
        sum_ask_px_vol = 0.0

        raw_bids = []
        raw_asks = []

        # 1. Generate 10 levels of Bids (buying interest below last price)
        for i in range(1, 11):
            px = base_price - (i * tick)
            # Volume decays with distance from spread, with occasional institutional wall
            vol_mult = 1.0 + (math.sin((seed + i * 7) % 360) * 0.4)
            base_lot = int(2500 * vol_mult * (1.2 / (1.0 + i * 0.08)))
            
            # Inject institutional wall at level 4 or 5 occasionally
            is_wall = (i == 4 and ((seed % 5) == 0)) or (i == 6 and ((seed % 7) == 0))
            if is_wall:
                base_lot = int(base_lot * 3.8)

            orders = max(12, int(base_lot / 45))
            raw_bids.append((i, px, base_lot, orders))
            total_bid_lots += base_lot
            sum_bid_px_vol += px * base_lot

        # 2. Generate 10 levels of Asks (selling interest above last price)
        for i in range(1, 11):
            px = base_price + (i * tick)
            vol_mult = 1.0 + (math.cos((seed + i * 11) % 360) * 0.45)
            base_lot = int(2400 * vol_mult * (1.2 / (1.0 + i * 0.08)))

            # Inject institutional ask wall at level 3 or 7 occasionally
            is_ask_wall = (i == 3 and ((seed % 4) == 0)) or (i == 7 and ((seed % 6) == 0))
            if is_ask_wall:
                base_lot = int(base_lot * 3.5)

            orders = max(10, int(base_lot / 48))
            raw_asks.append((i, px, base_lot, orders))
            total_ask_lots += base_lot
            sum_ask_px_vol += px * base_lot

        # Convert to structured dataclasses with percentage depth
        bid_wall_detected = False
        bid_wall_price = None
        for lvl, px, lots, ords in raw_bids:
            depth_pct = (lots / total_bid_lots * 100.0) if total_bid_lots > 0 else 10.0
            if depth_pct >= 26.0:
                bid_wall_detected = True
                bid_wall_price = px
            bids.append(OrderbookLevel(
                level=lvl,
                price=px,
                volume_lots=lots,
                queue_orders=ords,
                total_value_idr=px * lots * 100,  # 1 lot = 100 shares in IDX
                depth_pct=depth_pct,
            ))

        ask_wall_detected = False
        ask_wall_price = None
        for lvl, px, lots, ords in raw_asks:
            depth_pct = (lots / total_ask_lots * 100.0) if total_ask_lots > 0 else 10.0
            if depth_pct >= 26.0:
                ask_wall_detected = True
                ask_wall_price = px
            asks.append(OrderbookLevel(
                level=lvl,
                price=px,
                volume_lots=lots,
                queue_orders=ords,
                total_value_idr=px * lots * 100,
                depth_pct=depth_pct,
            ))

        vwap_bid = sum_bid_px_vol / total_bid_lots if total_bid_lots > 0 else base_price
        vwap_ask = sum_ask_px_vol / total_ask_lots if total_ask_lots > 0 else base_price

        # Orderbook Imbalance Ratio: (Bid - Ask) / (Bid + Ask)
        total_vol = total_bid_lots + total_ask_lots
        imbalance = ((total_bid_lots - total_ask_lots) / total_vol) if total_vol > 0 else 0.0

        if imbalance > 0.15:
            dominant = "STRONG_BID_ACCUMULATION"
        elif imbalance > 0.05:
            dominant = "MILD_BID_PRESSURE"
        elif imbalance < -0.15:
            dominant = "STRONG_ASK_DISTRIBUTION"
        elif imbalance < -0.05:
            dominant = "MILD_ASK_PRESSURE"
        else:
            dominant = "BALANCED_EQUILIBRIUM"

        spread_idr = tick
        spread_pct = (spread_idr / base_price) * 100.0

        # Algorithmic Spoofing Risk: high imbalance + large wall + low queue density
        spoofing_score = 15.0
        if bid_wall_detected or ask_wall_detected:
            spoofing_score += 35.0
        if abs(imbalance) >= 0.30:
            spoofing_score += 25.0
        spoofing_score = min(95.0, spoofing_score + ((seed % 15) - 7))

        health_score = max(10.0, min(99.0, 100.0 - (spoofing_score * 0.5) - (spread_pct * 15.0)))

        return OrderbookSnapshot(
            ticker=ticker_upper,
            timestamp=now_dt.isoformat(),
            last_price=base_price,
            spread_idr=spread_idr,
            spread_pct=spread_pct,
            vwap_bid=vwap_bid,
            vwap_ask=vwap_ask,
            total_bid_lots=total_bid_lots,
            total_ask_lots=total_ask_lots,
            bid_ask_imbalance_ratio=imbalance,
            dominant_side=dominant,
            bid_wall_detected=bid_wall_detected,
            bid_wall_price=bid_wall_price,
            ask_wall_detected=ask_wall_detected,
            ask_wall_price=ask_wall_price,
            spoofing_probability_pct=spoofing_score,
            orderbook_health_score=health_score,
            bids=bids,
            asks=asks,
        )


# Global singleton
orderbook_engine = OrderbookEngine()
