"""Market Making & Level-2 Limit Order Queue Position Simulator.

Models passive limit order execution probability, adverse selection risk,
and expected time-to-fill across the 10-depth orderbook using Poisson trade
arrivals and queue depletion dynamics on the Indonesia Stock Exchange (IDX).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ruang_risiko_idx.research.orderbook_engine import orderbook_engine


@dataclass
class QueueLevelAnalysis:
    """Microstructure execution probability at a single tick depth."""

    level: int
    side: str  # BID or ASK
    price_idr: float
    existing_queue_lots: int
    order_size_lots: int
    total_queue_ahead_lots: int
    estimated_trade_rate_lots_per_min: float
    expected_time_to_fill_min: float
    fill_prob_1m_pct: float
    fill_prob_3m_pct: float
    fill_prob_5m_pct: float
    fill_prob_15m_pct: float
    adverse_selection_risk: str  # LOW, MODERATE, HIGH

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueueSimulationReport:
    """Consolidated limit order queue telemetry and execution guidance."""

    ticker: str
    timestamp: str
    current_bid_price: float
    current_ask_price: float
    spread_idr: float
    simulated_order_size_lots: int
    bid_queue_levels: list[QueueLevelAnalysis]
    ask_queue_levels: list[QueueLevelAnalysis]
    optimal_bid_placement: QueueLevelAnalysis
    optimal_ask_placement: QueueLevelAnalysis
    queue_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "current_bid_price": self.current_bid_price,
            "current_ask_price": self.current_ask_price,
            "spread_idr": self.spread_idr,
            "simulated_order_size_lots": self.simulated_order_size_lots,
            "bid_queue_levels": [b.to_dict() for b in self.bid_queue_levels],
            "ask_queue_levels": [a.to_dict() for a in self.ask_queue_levels],
            "optimal_bid_placement": self.optimal_bid_placement.to_dict(),
            "optimal_ask_placement": self.optimal_ask_placement.to_dict(),
            "queue_verdict": self.queue_verdict,
        }


class OrderQueueSimulator:
    """Simulates queue progression and adverse selection for passive orders."""

    def simulate_queue(
        self,
        ticker: str = "BBCA.JK",
        order_size_lots: int = 100,
    ) -> QueueSimulationReport:
        """Evaluate fill dynamics at each depth level of the orderbook."""
        ob = orderbook_engine.generate_orderbook(ticker)
        bids = ob.bids
        asks = ob.asks

        best_bid = bids[0].price if bids else 10000.0
        best_ask = asks[0].price if asks else 10025.0
        spread = best_ask - best_bid

        # Depletion rate: base Poisson trade arrival rate (lots/min)
        base_depletion_rate = max(150.0, float(bids[0].volume_lots) * 0.12)

        def analyze_side(levels: list[Any], side_name: str) -> list[QueueLevelAnalysis]:
            results: list[QueueLevelAnalysis] = []
            cum_lots_ahead = 0

            for idx, lvl in enumerate(levels[:5]):
                depth_factor = 1.0 / (idx + 1.0)
                effective_rate = max(20.0, base_depletion_rate * depth_factor)
                queue_ahead = cum_lots_ahead + lvl.volume_lots
                cum_lots_ahead += lvl.volume_lots

                # Expected time to fill = Total lots ahead / rate
                expected_min = queue_ahead / max(1.0, effective_rate)

                # Poisson probability: P(Fill <= T) = 1 - exp(- (effective_rate * T) / queue_ahead)
                def calc_prob(t_min: float) -> float:
                    ratio = (effective_rate * t_min) / max(1.0, queue_ahead)
                    return round((1.0 - math.exp(-ratio)) * 100.0, 1)

                p1 = calc_prob(1.0)
                p3 = calc_prob(3.0)
                p5 = calc_prob(5.0)
                p15 = calc_prob(15.0)

                adv = "LOW" if idx >= 2 else ("MODERATE" if idx == 1 else "HIGH")

                results.append(
                    QueueLevelAnalysis(
                        level=idx + 1,
                        side=side_name,
                        price_idr=lvl.price,
                        existing_queue_lots=lvl.volume_lots,
                        order_size_lots=order_size_lots,
                        total_queue_ahead_lots=queue_ahead,
                        estimated_trade_rate_lots_per_min=round(effective_rate, 1),
                        expected_time_to_fill_min=round(expected_min, 2),
                        fill_prob_1m_pct=p1,
                        fill_prob_3m_pct=p3,
                        fill_prob_5m_pct=p5,
                        fill_prob_15m_pct=p15,
                        adverse_selection_risk=adv,
                    )
                )

            return results

        bid_analysis = analyze_side(bids, "BID")
        ask_analysis = analyze_side(asks, "ASK")

        # Optimal placement: level 2 balances fill rate and adverse selection
        opt_bid = bid_analysis[1] if len(bid_analysis) > 1 else bid_analysis[0]
        opt_ask = ask_analysis[1] if len(ask_analysis) > 1 else ask_analysis[0]

        verdict = (
            f"Simulasi Antrean {ticker.upper()} (Ukuran Order: {order_size_lots} Lot): "
            f"Penempatan Bid optimal pada Level {opt_bid.level} (Rp {opt_bid.price_idr:,.0f}) "
            f"dengan estimasi waktu antrean {opt_bid.expected_time_to_fill_min:.1f} menit "
            f"(Peluang terisi 5m: {opt_bid.fill_prob_5m_pct}%). "
            f"Penempatan Offer optimal pada Level {opt_ask.level} (Rp {opt_ask.price_idr:,.0f})."
        )

        return QueueSimulationReport(
            ticker=ticker.upper(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_bid_price=best_bid,
            current_ask_price=best_ask,
            spread_idr=spread,
            simulated_order_size_lots=order_size_lots,
            bid_queue_levels=bid_analysis,
            ask_queue_levels=ask_analysis,
            optimal_bid_placement=opt_bid,
            optimal_ask_placement=opt_ask,
            queue_verdict=verdict,
        )


# Global singleton
queue_simulator = OrderQueueSimulator()
