"""Dynamic Capital and Risk Budget Allocator (Volatility-Adjusted Fractional Kelly)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StockAllocationRecommendation:
    """Individual stock sizing recommendation within portfolio risk constraints."""

    ticker: str
    current_price: float
    garch_vol_pct: float
    var_99_pct: float
    prob_up: float
    recommended_weight_pct: float
    allocated_value_idr: float
    allocated_lots: int
    var_contribution_idr: float
    sizing_rationale: str


@dataclass(frozen=True)
class PortfolioAllocationReport:
    """Consolidated portfolio capital and risk budget sizing report."""

    total_capital_idr: float
    allocated_capital_idr: float
    cash_reserve_idr: float
    portfolio_var_99_idr: float
    portfolio_var_99_pct: float
    max_daily_budget_idr: float
    budget_utilized_pct: float
    recommendations: list[StockAllocationRecommendation]


def compute_portfolio_allocation(
    total_capital_idr: float,
    daily_risk_budget_pct: float,
    max_single_stock_pct: float,
    stocks_data: list[dict[str, Any]],
) -> PortfolioAllocationReport:
    """Compute risk-constrained capital allocation across candidate stocks."""
    if total_capital_idr <= 0 or not stocks_data:
        return PortfolioAllocationReport(
            total_capital_idr=max(0.0, total_capital_idr),
            allocated_capital_idr=0.0,
            cash_reserve_idr=max(0.0, total_capital_idr),
            portfolio_var_99_idr=0.0,
            portfolio_var_99_pct=0.0,
            max_daily_budget_idr=0.0,
            budget_utilized_pct=0.0,
            recommendations=[],
        )

    max_budget_idr = total_capital_idr * (daily_risk_budget_pct / 100.0)

    # 1. Compute raw score based on directional edge and inverse volatility
    scored_stocks: list[dict[str, Any]] = []
    for item in stocks_data:
        ticker = item["ticker"]
        price = float(item.get("current_price", 1000.0))
        vol = max(0.005, float(item.get("garch_vol_daily", 0.02)))
        var99 = max(0.01, float(item.get("var_99_daily", vol * 2.33)))
        prob_up = float(item.get("prob_up", 0.50))
        reward_risk = max(1.0, float(item.get("reward_risk_ratio", 2.0)))

        # Half-Kelly calculation
        b = reward_risk
        p = prob_up
        q = 1.0 - p
        kelly_full = (p * b - q) / b
        kelly_half = max(0.0, kelly_full * 0.5)

        # Volatility penalty
        vol_adjusted_score = kelly_half / (vol * 100.0)
        scored_stocks.append({
            "ticker": ticker,
            "price": price,
            "vol": vol,
            "var99": var99,
            "prob_up": prob_up,
            "raw_score": vol_adjusted_score,
        })

    total_score = sum(s["raw_score"] for s in scored_stocks)
    recommendations: list[StockAllocationRecommendation] = []
    total_allocated_idr = 0.0
    total_var_contribution = 0.0

    for s in scored_stocks:
        if total_score > 0:
            target_weight = min(max_single_stock_pct, (s["raw_score"] / total_score) * 80.0)
        else:
            target_weight = 0.0

        target_value = total_capital_idr * (target_weight / 100.0)
        # Lot sizing: 1 lot = 100 shares
        share_price = s["price"]
        lot_cost = share_price * 100.0
        lots = int(target_value // lot_cost) if lot_cost > 0 else 0
        actual_val = lots * lot_cost
        actual_weight = (actual_val / total_capital_idr) * 100.0 if total_capital_idr > 0 else 0.0
        stock_var_idr = actual_val * s["var99"]

        total_allocated_idr += actual_val
        total_var_contribution += stock_var_idr

        if lots > 0:
            rationale = (
                f"Alokasi {actual_weight:.1f}% ({lots:,} lot) didasarkan pada probabilitas naik {s['prob_up']:.1%} "
                f"dan volatilitas terkontrol {s['vol']:.2%}."
            )
        else:
            rationale = "Alokasi 0 lot: Probabilitas tidak memberikan edge matematis atau volatilitas terlalu tinggi."

        recommendations.append(
            StockAllocationRecommendation(
                ticker=s["ticker"],
                current_price=share_price,
                garch_vol_pct=round(s["vol"] * 100.0, 2),
                var_99_pct=round(s["var99"] * 100.0, 2),
                prob_up=round(s["prob_up"] * 100.0, 1),
                recommended_weight_pct=round(actual_weight, 2),
                allocated_value_idr=actual_val,
                allocated_lots=lots,
                var_contribution_idr=round(stock_var_idr, 2),
                sizing_rationale=rationale,
            )
        )

    cash_reserve = max(0.0, total_capital_idr - total_allocated_idr)
    port_var_pct = (total_var_contribution / total_capital_idr) * 100.0 if total_capital_idr > 0 else 0.0
    budget_util = (total_var_contribution / max_budget_idr) * 100.0 if max_budget_idr > 0 else 0.0

    return PortfolioAllocationReport(
        total_capital_idr=total_capital_idr,
        allocated_capital_idr=total_allocated_idr,
        cash_reserve_idr=cash_reserve,
        portfolio_var_99_idr=round(total_var_contribution, 2),
        portfolio_var_99_pct=round(port_var_pct, 2),
        max_daily_budget_idr=round(max_budget_idr, 2),
        budget_utilized_pct=round(budget_util, 1),
        recommendations=recommendations,
    )
