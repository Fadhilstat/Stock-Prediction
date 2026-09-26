"""Multi-horizon probabilistic forecast quantiles and scenario engine."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class HorizonQuantiles:
    """Probabilistic quantiles for one trading horizon."""

    horizon_days: int
    horizon_label: str
    current_price: float
    q10: float
    q25: float
    q50: float
    q75: float
    q90: float
    expected_return: float
    probability_positive: float
    probability_negative: float
    volatility_projected: float


@dataclass(frozen=True)
class ScenarioDefinition:
    """Detailed research scenario path."""

    scenario_name: Literal[
        "BULL_CASE",
        "BASE_CASE",
        "BEAR_CASE",
        "VOLATILITY_SHOCK",
        "REGIME_REVERSAL",
    ]
    probability: float
    expected_price_20d: float
    expected_move_percent: float
    drivers: list[str]
    supporting_evidence: str
    contradicting_evidence: str
    invalidation_level: float


def compute_horizon_quantiles(
    current_price: float,
    daily_volatility: float,
    daily_direction_up_prob: float,
    historical_drift: float = 0.0003,
) -> dict[str, HorizonQuantiles]:
    """Compute explicit probabilistic distribution quantiles across 1D, 5D, and 20D horizons."""
    horizons = [(1, "1D"), (5, "5D"), (20, "20D")]
    results: dict[str, HorizonQuantiles] = {}

    for days, label in horizons:
        sigma_t = daily_volatility * sqrt(days)
        # Shift drift based on directional model probability
        directional_bias = (daily_direction_up_prob - 0.5) * 0.01 * days
        mu_t = historical_drift * days + directional_bias

        # Standard normal inverse quantiles
        z10 = -1.28155
        z25 = -0.67449
        z50 = 0.0
        z75 = 0.67449
        z90 = 1.28155

        q10 = current_price * exp(mu_t + z10 * sigma_t)
        q25 = current_price * exp(mu_t + z25 * sigma_t)
        q50 = current_price * exp(mu_t + z50 * sigma_t)
        q75 = current_price * exp(mu_t + z75 * sigma_t)
        q90 = current_price * exp(mu_t + z90 * sigma_t)

        prob_pos = float(
            np.clip(daily_direction_up_prob + (0.02 if days > 1 else 0.0), 0.05, 0.95)
        )
        prob_neg = 1.0 - prob_pos
        exp_ret = (q50 / current_price) - 1.0

        results[label] = HorizonQuantiles(
            horizon_days=days,
            horizon_label=label,
            current_price=current_price,
            q10=round(q10, 0),
            q25=round(q25, 0),
            q50=round(q50, 0),
            q75=round(q75, 0),
            q90=round(q90, 0),
            expected_return=exp_ret,
            probability_positive=prob_pos,
            probability_negative=prob_neg,
            volatility_projected=sigma_t,
        )

    return results


def generate_scenarios(
    current_price: float,
    quantiles_20d: HorizonQuantiles,
    var_99_1d: float,
    trend_state: str,
) -> list[ScenarioDefinition]:
    """Generate structured multi-case research scenarios."""
    scenarios: list[ScenarioDefinition] = [
        ScenarioDefinition(
            scenario_name="BULL_CASE",
            probability=round(quantiles_20d.probability_positive * 0.5, 2),
            expected_price_20d=quantiles_20d.q90,
            expected_move_percent=round(((quantiles_20d.q90 / current_price) - 1.0) * 100.0, 1),
            drivers=[
                "Sustained institutional flow accumulation",
                "Favorable sector rotation momentum",
                "Breakout above immediate resistance band",
            ],
            supporting_evidence="Positive momentum indicator alignment and robust volume participation.",
            contradicting_evidence="High valuation multiples or overbought oscillator readings.",
            invalidation_level=round(quantiles_20d.q25, 0),
        ),
        ScenarioDefinition(
            scenario_name="BASE_CASE",
            probability=0.45,
            expected_price_20d=quantiles_20d.q50,
            expected_move_percent=round(((quantiles_20d.q50 / current_price) - 1.0) * 100.0, 1),
            drivers=[
                "Stable earnings yield continuation",
                "Range-bound benchmark market conditions",
                "Balanced order book liquidity",
            ],
            supporting_evidence="Mean reversion tendencies within recent 60-day price channel.",
            contradicting_evidence="Macroeconomic interest rate shifts or unexpected regulatory disclosures.",
            invalidation_level=round(quantiles_20d.q10, 0),
        ),
        ScenarioDefinition(
            scenario_name="BEAR_CASE",
            probability=round(quantiles_20d.probability_negative * 0.5, 2),
            expected_price_20d=quantiles_20d.q10,
            expected_move_percent=round(((quantiles_20d.q10 / current_price) - 1.0) * 100.0, 1),
            drivers=[
                "Foreign net outflow persistence",
                "Breakdown below major structural support",
                "IHSG benchmark risk-off liquidity drain",
            ],
            supporting_evidence="Weak market breadth participation and bearish moving average alignment.",
            contradicting_evidence="Defensive cash flow yield attracting value-oriented domestic capital.",
            invalidation_level=round(quantiles_20d.q75, 0),
        ),
        ScenarioDefinition(
            scenario_name="VOLATILITY_SHOCK",
            probability=0.10,
            expected_price_20d=round(current_price * (1.0 - var_99_1d * 3.0), 0),
            expected_move_percent=round(-var_99_1d * 3.0 * 100.0, 1),
            drivers=[
                "Global equity liquidity contagion",
                "Emerging market currency depreciation pressure",
                "Exchange price limit (Auto Rejection Bawah) clustering",
            ],
            supporting_evidence="Historical VaR 99% tail exceedance cluster.",
            contradicting_evidence="Domestic institutional stabilization intervention.",
            invalidation_level=round(current_price * 0.95, 0),
        ),
        ScenarioDefinition(
            scenario_name="REGIME_REVERSAL",
            probability=0.15,
            expected_price_20d=round(
                quantiles_20d.q75 if "DOWNTREND" in trend_state else quantiles_20d.q25, 0
            ),
            expected_move_percent=round(
                (
                    (quantiles_20d.q75 if "DOWNTREND" in trend_state else quantiles_20d.q25)
                    / current_price
                    - 1.0
                )
                * 100.0,
                1,
            ),
            drivers=[
                "Aggressive mean reversion after extreme sentiment exhaustion",
                "Unexpected monetary policy easing or dividend surprise",
            ],
            supporting_evidence="Extreme oscillator divergence and historical swing boundaries.",
            contradicting_evidence="Strong institutional trend persistence.",
            invalidation_level=round(quantiles_20d.q50, 0),
        ),
    ]
    return scenarios
