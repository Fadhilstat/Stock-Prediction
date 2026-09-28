"""Autonomous Portfolio Rebalancing Execution Guard for IDX.

Prevents fee drag and excessive portfolio churning by evaluating minimum rebalance
drift thresholds, tax-aware IDX trading commissions (PPh final 0.1%, levy 0.043%),
and Almgren-Chriss market impact penalties for automated portfolio execution.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RebalanceOrderSlice:
    """Individual trade instruction generated for a portfolio rebalancing event."""

    ticker: str
    action: str  # BUY, SELL, HOLD
    current_weight_pct: float
    target_weight_pct: float
    weight_drift_pct: float
    current_value_idr: float
    target_value_idr: float
    trade_value_idr: float
    shares_lots: int
    estimated_commission_idr: float
    estimated_tax_idr: float
    estimated_market_impact_bps: float
    execution_routing: str  # TWAP_3_SLICES, VWAP_PASSIVE, CROSSING_NEGOSIASI

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RebalanceAuditReport:
    """Comprehensive portfolio rebalancing governance and friction audit."""

    timestamp: str
    portfolio_equity_idr: float
    rebalance_triggered: bool
    trigger_reason: str
    max_drift_pct: float
    drift_tolerance_pct: float
    gross_turnover_idr: float
    turnover_ratio_pct: float
    total_commission_idr: float
    total_tax_idr: float
    total_market_impact_idr: float
    net_drag_bps: float
    recommended_orders: list[RebalanceOrderSlice]
    execution_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "portfolio_equity_idr": round(self.portfolio_equity_idr, 2),
            "rebalance_triggered": self.rebalance_triggered,
            "trigger_reason": self.trigger_reason,
            "max_drift_pct": round(self.max_drift_pct, 2),
            "drift_tolerance_pct": round(self.drift_tolerance_pct, 2),
            "gross_turnover_idr": round(self.gross_turnover_idr, 2),
            "turnover_ratio_pct": round(self.turnover_ratio_pct, 2),
            "total_commission_idr": round(self.total_commission_idr, 2),
            "total_tax_idr": round(self.total_tax_idr, 2),
            "total_market_impact_idr": round(self.total_market_impact_idr, 2),
            "net_drag_bps": round(self.net_drag_bps, 2),
            "recommended_orders": [o.to_dict() for o in self.recommended_orders],
            "execution_summary": self.execution_summary,
        }


class RebalanceGuard:
    """Evaluates friction-adjusted rebalancing logic and guards against over-trading."""

    BUY_COMMISSION_RATE = 0.0015  # 0.15%
    SELL_COMMISSION_RATE = 0.0025  # 0.25%
    IDX_LEVY_RATE = 0.00043  # 0.043%
    PPH_FINAL_TAX_RATE = 0.0010  # 0.10% on gross sell

    def evaluate_rebalance(
        self,
        portfolio_equity_idr: float = 100_000_000.0,
        drift_tolerance_pct: float = 2.5,
        holdings: list[dict[str, Any]] | None = None,
    ) -> RebalanceAuditReport:
        """Calculate friction-aware rebalance orders given current vs target weights."""
        default_holdings = [
            {"ticker": "BBCA.JK", "current_weight_pct": 34.0, "target_weight_pct": 28.0, "price": 10425.0},
            {"ticker": "BBRI.JK", "current_weight_pct": 20.0, "target_weight_pct": 25.0, "price": 5125.0},
            {"ticker": "BMRI.JK", "current_weight_pct": 22.0, "target_weight_pct": 20.0, "price": 6850.0},
            {"ticker": "TLKM.JK", "current_weight_pct": 14.0, "target_weight_pct": 17.0, "price": 3120.0},
            {"ticker": "ASII.JK", "current_weight_pct": 10.0, "target_weight_pct": 10.0, "price": 5200.0},
        ]
        active_holdings = holdings or default_holdings

        order_slices: list[RebalanceOrderSlice] = []
        max_drift = 0.0
        gross_turnover = 0.0
        total_comm = 0.0
        total_tax = 0.0
        total_impact = 0.0

        for h in active_holdings:
            ticker = h.get("ticker", "UNKNOWN")
            c_w = float(h.get("current_weight_pct", 0.0))
            t_w = float(h.get("target_weight_pct", 0.0))
            px = float(h.get("price", 5000.0))

            drift = abs(c_w - t_w)
            if drift > max_drift:
                max_drift = drift

            c_val = portfolio_equity_idr * (c_w / 100.0)
            t_val = portfolio_equity_idr * (t_w / 100.0)
            trade_val = abs(t_val - c_val)

            action = "HOLD"
            lots = 0
            comm = 0.0
            tax = 0.0
            impact_bps = 0.0
            routing = "PASSIVE_LIMIT"

            if drift >= drift_tolerance_pct:
                gross_turnover += trade_val
                lots = max(1, int(trade_val / (px * 100.0)))
                actual_trade_idr = lots * px * 100.0

                if t_w > c_w:
                    action = "BUY"
                    comm = actual_trade_idr * (self.BUY_COMMISSION_RATE + self.IDX_LEVY_RATE)
                    tax = 0.0
                    routing = "VWAP_PASSIVE" if lots < 200 else "TWAP_3_SLICES"
                else:
                    action = "SELL"
                    comm = actual_trade_idr * (self.SELL_COMMISSION_RATE + self.IDX_LEVY_RATE)
                    tax = actual_trade_idr * self.PPH_FINAL_TAX_RATE
                    routing = "TWAP_3_SLICES" if lots < 500 else "CROSSING_NEGOSIASI"

                # Almgren-Chriss impact approximation: ~2.5 to 8.0 bps depending on lot size
                impact_bps = round(2.5 + (lots / 100.0) * 0.8, 1)
                impact_idr = actual_trade_idr * (impact_bps / 10000.0)

                total_comm += comm
                total_tax += tax
                total_impact += impact_idr

            order_slices.append(
                RebalanceOrderSlice(
                    ticker=ticker,
                    action=action,
                    current_weight_pct=c_w,
                    target_weight_pct=t_w,
                    weight_drift_pct=round(drift, 2),
                    current_value_idr=round(c_val, 2),
                    target_value_idr=round(t_val, 2),
                    trade_value_idr=round(trade_val, 2),
                    shares_lots=lots,
                    estimated_commission_idr=round(comm, 2),
                    estimated_tax_idr=round(tax, 2),
                    estimated_market_impact_bps=impact_bps,
                    execution_routing=routing,
                )
            )

        triggered = max_drift >= drift_tolerance_pct
        turnover_ratio = (gross_turnover / portfolio_equity_idr) * 100.0
        total_friction = total_comm + total_tax + total_impact
        net_drag_bps = (total_friction / max(1.0, portfolio_equity_idr)) * 10000.0

        if triggered:
            summary = (
                f"Rebalancing Disetujui: Deviasi bobot maksimum {max_drift:.1f}% melebihi ambang batas toleransi "
                f"{drift_tolerance_pct:.1f}%. Estimasi perputaran modal Rp {gross_turnover:,.0f} ({turnover_ratio:.1f}%) "
                f"dengan total friksi (komisi + pajak + dampak pasar) Rp {total_friction:,.0f} ({net_drag_bps:.1f} bps)."
            )
            reason = f"MAX_DRIFT_EXCEEDED ({max_drift:.1f}% >= {drift_tolerance_pct:.1f}%)"
        else:
            summary = (
                f"Rebalancing Ditolak: Deviasi bobot portofolio ({max_drift:.1f}%) masih dalam toleransi aman "
                f"{drift_tolerance_pct:.1f}%. Mencegah churning dan pemborosan komisi/pajak bursa."
            )
            reason = f"DRIFT_WITHIN_TOLERANCE ({max_drift:.1f}% < {drift_tolerance_pct:.1f}%)"

        return RebalanceAuditReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            portfolio_equity_idr=portfolio_equity_idr,
            rebalance_triggered=triggered,
            trigger_reason=reason,
            max_drift_pct=max_drift,
            drift_tolerance_pct=drift_tolerance_pct,
            gross_turnover_idr=gross_turnover,
            turnover_ratio_pct=turnover_ratio,
            total_commission_idr=total_comm,
            total_tax_idr=total_tax,
            total_market_impact_idr=total_impact,
            net_drag_bps=net_drag_bps,
            recommended_orders=order_slices,
            execution_summary=summary,
        )


# Global singleton
rebalance_guard = RebalanceGuard()
