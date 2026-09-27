"""Macroeconomic Stress Testing & Microstructure Liquidity Shock Engine.

Simulates non-linear market impact, orderbook replenishment dynamics,
and systemic cross-asset stress scenarios across the Indonesia Stock Exchange (IDX).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class LiquidityShockProfile:
    """Non-linear orderbook market impact and execution cost estimation."""

    ticker: str
    evaluated_at: str
    order_size_idr: float
    reference_price: float
    expected_fill_price: float
    slippage_bps: float
    market_impact_cost_idr: float
    ticks_traversed: int
    lots_filled: int
    replenishment_half_life_seconds: float
    execution_recommendation: str  # DIRECT_MARKET, TWAP_15MIN, ICEBERG_5_TRANCHES, ALGO_POV_10PCT

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "evaluated_at": self.evaluated_at,
            "order_size_idr": self.order_size_idr,
            "reference_price": round(self.reference_price, 2),
            "expected_fill_price": round(self.expected_fill_price, 2),
            "slippage_bps": round(self.slippage_bps, 2),
            "market_impact_cost_idr": round(self.market_impact_cost_idr, 0),
            "ticks_traversed": self.ticks_traversed,
            "lots_filled": self.lots_filled,
            "replenishment_half_life_seconds": round(self.replenishment_half_life_seconds, 1),
            "execution_recommendation": self.execution_recommendation,
        }


@dataclass
class MacroScenarioResult:
    """Simulation output under institutional stress conditions."""

    scenario_id: str
    scenario_name: str
    description: str
    shocks: dict[str, float]
    projected_price: float
    projected_return_pct: float
    conditional_var_99_pct: float
    conditional_es_99_pct: float
    resilience_rating: str  # HIGH_RESILIENCE, MODERATE, VULNERABLE, CRITICAL_TAIL_RISK
    hedging_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "description": self.description,
            "shocks": self.shocks,
            "projected_price": round(self.projected_price, 2),
            "projected_return_pct": round(self.projected_return_pct, 2),
            "conditional_var_99_pct": round(self.conditional_var_99_pct, 2),
            "conditional_es_99_pct": round(self.conditional_es_99_pct, 2),
            "resilience_rating": self.resilience_rating,
            "hedging_recommendation": self.hedging_recommendation,
        }


@dataclass
class StressTestReport:
    """Consolidated stress test suite output."""

    ticker: str
    evaluated_at: str
    base_price: float
    liquidity_ladder: list[LiquidityShockProfile]
    scenarios: list[MacroScenarioResult]
    composite_vulnerability_score: float  # 0.0 (Robust) to 100.0 (Extreme Vulnerability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "evaluated_at": self.evaluated_at,
            "base_price": self.base_price,
            "liquidity_ladder": [s.to_dict() for s in self.liquidity_ladder],
            "scenarios": [s.to_dict() for s in self.scenarios],
            "composite_vulnerability_score": round(self.composite_vulnerability_score, 1),
        }


class StressTestingEngine:
    """Evaluates liquidity surfaces and systemic stress scenarios."""

    SCENARIOS = [
        {
            "id": "FED_HAWKISH_USD_SPIKE",
            "name": "The Fed Hawkish Shock & Rupiah Devaluation",
            "desc": "The Fed raises rates 50 bps, USD/IDR spikes above 16,500, foreign capital outflows surge.",
            "usd_idr_shock_pct": 7.5,
            "bi_rate_shock_bps": 50,
            "ihsg_beta": 1.15,
        },
        {
            "id": "COMMODITY_SUPER_CRASH",
            "name": "Global Commodity Benchmark Crash",
            "desc": "Thermal coal falls 22% and LME nickel drops 18% due to global manufacturing slowdown.",
            "usd_idr_shock_pct": 2.0,
            "commodity_shock_pct": -20.0,
            "ihsg_beta": 0.85,
        },
        {
            "id": "BANKING_LIQUIDITY_SQUEEZE",
            "name": "Domestic Banking Liquidity Crunch",
            "desc": "Interbank liquidity tightens, net interest margins compress, credit provisions double.",
            "bi_rate_shock_bps": 75,
            "ihsg_beta": 1.25,
        },
        {
            "id": "FOREIGN_CAPITAL_FLIGHT",
            "name": "Emerging Market Taper Tantrum",
            "desc": "Foreign institutional whales dump 15 Trillion IDR in index bluechips over 5 trading sessions.",
            "foreign_outflow_t_idr": -15.0,
            "ihsg_beta": 1.35,
        },
    ]

    def simulate_liquidity_impact(
        self,
        ticker: str,
        base_price: float,
        order_size_idr: float,
        daily_turnover_idr: float = 450_000_000_000.0,
    ) -> LiquidityShockProfile:
        """Compute square-root law market impact and book traversal."""
        # Square root law: Impact ~ 0.5 * sigma * sqrt(Q / V)
        participation_rate = max(1e-6, order_size_idr / max(daily_turnover_idr, 1e9))
        est_volatility = 0.018  # Daily ~ 1.8%
        impact_pct = 0.45 * est_volatility * math.sqrt(participation_rate) * 100.0

        # Slippage in basis points
        slippage_bps = max(2.5, impact_pct * 100.0)

        # Average fill price with slippage
        fill_price = base_price * (1.0 + (slippage_bps / 10000.0))
        impact_cost = order_size_idr * (slippage_bps / 10000.0)

        lots = int(order_size_idr / (base_price * 100.0))

        # Ticks traversed in standard IDX fraction
        ticks = max(1, int(slippage_bps / 12.0))

        # Replenishment half-life
        half_life = min(120.0, max(4.0, math.sqrt(order_size_idr / 5e7) * 8.5))

        if order_size_idr > 2_000_000_000.0:
            rec = "ICEBERG_5_TRANCHES"
        elif order_size_idr > 500_000_000.0:
            rec = "TWAP_15MIN"
        else:
            rec = "DIRECT_MARKET"

        now_iso = datetime.now(timezone.utc).isoformat()

        return LiquidityShockProfile(
            ticker=ticker.upper(),
            evaluated_at=now_iso,
            order_size_idr=order_size_idr,
            reference_price=base_price,
            expected_fill_price=fill_price,
            slippage_bps=slippage_bps,
            market_impact_cost_idr=impact_cost,
            ticks_traversed=ticks,
            lots_filled=lots,
            replenishment_half_life_seconds=half_life,
            execution_recommendation=rec,
        )

    def evaluate_stress_scenarios(
        self,
        ticker: str,
        base_price: float,
        sector: str = "Financials",
    ) -> list[MacroScenarioResult]:
        """Project stock price, conditional VaR, and tail risks under macro stress."""
        results: list[MacroScenarioResult] = []

        sector_sensitivities = {
            "Financials": {"FED": 1.2, "COMMODITY": 0.5, "BANKING": 1.4, "FLIGHT": 1.3},
            "Energy": {"FED": 0.8, "COMMODITY": 1.8, "BANKING": 0.6, "FLIGHT": 1.1},
            "Basic Materials": {"FED": 0.9, "COMMODITY": 1.6, "BANKING": 0.7, "FLIGHT": 1.0},
            "Consumer": {"FED": 1.1, "COMMODITY": 0.4, "BANKING": 0.8, "FLIGHT": 0.9},
            "Infrastructure": {"FED": 1.3, "COMMODITY": 0.3, "BANKING": 0.9, "FLIGHT": 1.0},
            "Technology": {"FED": 1.6, "COMMODITY": 0.2, "BANKING": 1.2, "FLIGHT": 1.4},
            "Industrials": {"FED": 1.0, "COMMODITY": 0.9, "BANKING": 0.9, "FLIGHT": 1.0},
        }

        sens = sector_sensitivities.get(sector, {"FED": 1.0, "COMMODITY": 1.0, "BANKING": 1.0, "FLIGHT": 1.0})

        for s in self.SCENARIOS:
            sc_id = s["id"]
            if "FED" in sc_id:
                drift = -3.8 * sens["FED"]
                c_var = 5.2 * sens["FED"]
                c_es = 7.1 * sens["FED"]
                hedge = "Alokasikan short index futures atau lindung nilai USD cash 15%."
            elif "COMMODITY" in sc_id:
                drift = -6.5 * sens["COMMODITY"]
                c_var = 8.1 * sens["COMMODITY"]
                c_es = 11.2 * sens["COMMODITY"]
                hedge = "Rotasi taktikal ke sektor konsumer primer defensif atau obligasi negara."
            elif "BANKING" in sc_id:
                drift = -4.9 * sens["BANKING"]
                c_var = 6.4 * sens["BANKING"]
                c_es = 8.8 * sens["BANKING"]
                hedge = "Pasang stop-loss ketat 3.5% di bawah support struktural dan amankan kas."
            else:
                drift = -5.8 * sens["FLIGHT"]
                c_var = 7.5 * sens["FLIGHT"]
                c_es = 10.4 * sens["FLIGHT"]
                hedge = "Pantau broker ZP dan CS, kurangi eksposur bluechip berkapitalisasi jumbo."

            proj_px = base_price * (1.0 + (drift / 100.0))

            if abs(drift) >= 8.0:
                rating = "CRITICAL_TAIL_RISK"
            elif abs(drift) >= 5.0:
                rating = "VULNERABLE"
            elif abs(drift) >= 3.0:
                rating = "MODERATE"
            else:
                rating = "HIGH_RESILIENCE"

            results.append(
                MacroScenarioResult(
                    scenario_id=sc_id,
                    scenario_name=s["name"],
                    description=s["desc"],
                    shocks={"ihsg_beta": s.get("ihsg_beta", 1.0)},
                    projected_price=proj_px,
                    projected_return_pct=drift,
                    conditional_var_99_pct=c_var,
                    conditional_es_99_pct=c_es,
                    resilience_rating=rating,
                    hedging_recommendation=hedge,
                )
            )

        return results

    def run_full_stress_test(
        self,
        ticker: str,
        base_price: float = 7100.0,
        sector: str = "Financials",
    ) -> StressTestReport:
        """Run complete stress testing protocol across liquidity tiers and macro scenarios."""
        tier_sizes = [50_000_000.0, 250_000_000.0, 1_000_000_000.0, 5_000_000_000.0]
        ladder = [self.simulate_liquidity_impact(ticker, base_price, sz) for sz in tier_sizes]
        scenarios = self.evaluate_stress_scenarios(ticker, base_price, sector)

        # Composite vulnerability score: mean of conditional ES and high-size slippage
        max_slip = ladder[-1].slippage_bps
        mean_es = sum(sc.conditional_es_99_pct for sc in scenarios) / len(scenarios)
        vuln = min(100.0, max(5.0, (mean_es * 6.5) + (max_slip * 0.45)))

        now_iso = datetime.now(timezone.utc).isoformat()

        return StressTestReport(
            ticker=ticker.upper(),
            evaluated_at=now_iso,
            base_price=base_price,
            liquidity_ladder=ladder,
            scenarios=scenarios,
            composite_vulnerability_score=vuln,
        )


# Global singleton
stress_engine = StressTestingEngine()
