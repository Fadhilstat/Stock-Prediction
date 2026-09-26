"""Risk Engine with final hard veto authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RiskEngineEvaluation:
    """Final output from the autonomous Risk Engine."""

    ticker: str
    risk_score_10: float
    hard_veto: bool
    veto_reasons: list[str]
    volatility_risk_state: str
    liquidity_risk_state: str
    tail_risk_state: str
    data_trust_state: str
    decision_state: Literal[
        "FAVORABLE_SETUP",
        "WATCH",
        "WAIT",
        "AVOID",
        "HIGH_RISK",
        "EVENT_RISK",
        "STALE_DATA",
    ]
    rationale: str


def evaluate_risk_engine(
    ticker: str,
    direction_up_prob: float,
    garch_volatility: float,
    var_99: float,
    liquidity_tier: str,
    trend_state: str,
    data_staleness_days: int = 0,
) -> RiskEngineEvaluation:
    """Execute risk evaluation with non-negotiable veto controls."""
    veto_reasons: list[str] = []
    hard_veto = False
    base_risk = 2.5

    # 1. Extreme volatility veto
    if garch_volatility > 0.045:  # > 4.5% daily volatility
        hard_veto = True
        veto_reasons.append("Extreme daily volatility exceeds safety threshold (4.5%).")
        base_risk += 3.0
        vol_state = "EXTREME_VOLATILITY"
    elif garch_volatility > 0.025:
        base_risk += 1.5
        vol_state = "ELEVATED_VOLATILITY"
    else:
        vol_state = "CONTROLLED_VOLATILITY"

    # 2. Tail risk (VaR 99%)
    if var_99 > 0.07:  # > 7% 1-day 99% VaR
        hard_veto = True
        veto_reasons.append("Daily 99% Value at Risk exceeds 7.0% tail loss limit.")
        base_risk += 2.0
        tail_state = "SEVERE_TAIL_EXPOSURE"
    elif var_99 > 0.04:
        base_risk += 1.0
        tail_state = "MODERATE_TAIL_RISK"
    else:
        tail_state = "NORMAL_TAIL_RISK"

    # 3. Liquidity risk
    if liquidity_tier == "LOW_LIQUIDITY":
        hard_veto = True
        veto_reasons.append("Low liquidity tier triggers exit capacity constraint.")
        base_risk += 2.5
        liq_state = "RESTRICTED_EXIT_CAPACITY"
    elif liquidity_tier == "MEDIUM_LIQUIDITY":
        base_risk += 0.5
        liq_state = "ACCEPTABLE_EXIT_CAPACITY"
    else:
        liq_state = "DEEP_INSTITUTIONAL_LIQUIDITY"

    # 4. Data staleness
    if data_staleness_days > 3:
        hard_veto = True
        veto_reasons.append(f"Market data is stale ({data_staleness_days} days without update).")
        data_trust = "STALE_DATA_ALERT"
    else:
        data_trust = "VERIFIED_FRESH"

    final_score = float(min(10.0, max(1.0, base_risk)))

    # Determine decision state
    if hard_veto:
        if data_staleness_days > 3:
            dec_state = "STALE_DATA"
        else:
            dec_state = "HIGH_RISK"
        rationale = "Hard veto enforced by Risk Engine: " + "; ".join(veto_reasons)
    else:
        if direction_up_prob > 0.58 and "BULLISH" in trend_state and final_score <= 4.5:
            dec_state = "FAVORABLE_SETUP"
            rationale = "Probabilistic edge supported by favorable technical trend and benign risk metrics."
        elif direction_up_prob > 0.50 and final_score <= 6.0:
            dec_state = "WATCH"
            rationale = "Modest statistical edge observed; monitor for liquidity confirmation."
        elif direction_up_prob < 0.45 or "BEARISH" in trend_state:
            dec_state = "AVOID"
            rationale = "Negative direction probability or dominant bearish trend structure."
        else:
            dec_state = "WAIT"
            rationale = "Uncertain statistical edge; wait for market structure clarification."

    return RiskEngineEvaluation(
        ticker=ticker,
        risk_score_10=round(final_score, 1),
        hard_veto=hard_veto,
        veto_reasons=veto_reasons,
        volatility_risk_state=vol_state,
        liquidity_risk_state=liq_state,
        tail_risk_state=tail_state,
        data_trust_state=data_trust,
        decision_state=dec_state,
        rationale=rationale,
    )
