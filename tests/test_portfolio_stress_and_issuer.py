"""Unit tests for Portfolio Stress Testing and Custom Passport Issuer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary
from ruang_risiko_idx.research.fundamentals import get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.passport_issuer import issue_custom_passport
from ruang_risiko_idx.research.portfolio_stress import (
    get_available_stress_scenarios,
    run_portfolio_stress_test,
)
from ruang_risiko_idx.research.risk_engine import evaluate_risk_engine
from ruang_risiko_idx.research.scenarios import compute_horizon_quantiles
from ruang_risiko_idx.research.technical import summarize_technical_state


def test_portfolio_stress_scenarios() -> None:
    """Verify historical crisis scenarios calculation."""
    scenarios = get_available_stress_scenarios()
    assert len(scenarios) >= 3
    scen_ids = [s.scenario_id for s in scenarios]
    assert "PANDEMIC_CIRCUIT_BREAKER_2020" in scen_ids
    assert "TAPER_TANTRUM_2013" in scen_ids

    weights = {"BBCA.JK": 0.40, "BBRI.JK": 0.30, "TLKM.JK": 0.30}
    res = run_portfolio_stress_test(weights, 100_000_000.0, "PANDEMIC_CIRCUIT_BREAKER_2020")
    assert res.portfolio_loss_percent > 15.0
    assert res.monetary_loss_idr > 0.0
    assert res.worst_asset == "BBRI.JK"
    assert res.best_asset == "TLKM.JK"
    assert res.var_99_loss_percent > res.portfolio_loss_percent


def test_custom_passport_issuer(tmp_path) -> None:
    """Verify interactive Pre-Buy Decision Passport generation and signing."""
    dates = pd.bdate_range("2026-01-01", periods=60)
    prices = np.linspace(9500, 10000, 60)
    df = pd.DataFrame(
        {
            "trade_date": dates,
            "ticker": "BBCA.JK",
            "open": prices,
            "high": prices + 50,
            "low": prices - 50,
            "close": prices,
            "adjusted_close": prices,
            "volume": [5_000_000] * 60,
        }
    )

    tech = summarize_technical_state(df, "BBCA.JK")
    ict = evaluate_ict_hypotheses(df, "BBCA.JK")
    fund = get_fundamental_snapshot("BBCA.JK")
    align = compute_market_alignment(df, df, "BBCA.JK")
    liq = compute_liquidity_flow_summary(df, "BBCA.JK")
    risk = evaluate_risk_engine("BBCA.JK", 0.55, 0.015, 0.025, "HIGH_LIQUIDITY", tech.trend_state)
    quantiles = compute_horizon_quantiles(tech.close, 0.015, 0.55)

    base = generate_decision_passport(
        ticker="BBCA.JK",
        company_name=fund.identity.company_name,
        cutoff_date="2026-09-25",
        current_price=tech.close,
        direction_up_prob=0.55,
        direction_model="random_forest",
        volatility_model="garch_normal",
        quantiles_20d=quantiles["20D"],
        technical=tech,
        ict=ict,
        fundamental=fund,
        market_alignment=align,
        liquidity=liq,
        risk_eval=risk,
    )

    custom_pass, path = issue_custom_passport(
        ticker="BBCA.JK",
        company_name=fund.identity.company_name,
        cutoff_date="2026-09-25",
        current_price=tech.close,
        custom_invalidation=9500.0,
        position_size_pct=12.5,
        horizon="Position 20D",
        operator_notes="Thesis validasi kuantitatif.",
        base_passport=base,
    )

    assert custom_pass.ticker == "BBCA.JK"
    assert "12.5%" in custom_pass.markdown_content
    assert path.exists()
    assert "Digital Signature Stamp" in custom_pass.markdown_content
