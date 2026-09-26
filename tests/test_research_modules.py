"""Unit tests for the research, scenario, risk, and decision passport modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.decision_passport import generate_decision_passport
from ruang_risiko_idx.research.flow import compute_liquidity_flow_summary, get_creator_claims_for_ticker
from ruang_risiko_idx.research.fundamentals import get_fundamental_snapshot
from ruang_risiko_idx.research.ict import evaluate_ict_hypotheses
from ruang_risiko_idx.research.journal import load_prediction_journal
from ruang_risiko_idx.research.market_context import compute_market_alignment
from ruang_risiko_idx.research.multimodal import get_ablation_benchmarks, run_evidence_conflict_radar
from ruang_risiko_idx.research.risk_engine import evaluate_risk_engine
from ruang_risiko_idx.research.scenarios import compute_horizon_quantiles, generate_scenarios
from ruang_risiko_idx.research.technical import compute_technical_features, summarize_technical_state


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Create deterministic OHLCV series for testing."""
    dates = pd.bdate_range("2025-01-01", periods=100)
    base_price = 5000.0
    drift = np.linspace(0, 500, 100)
    noise = np.sin(np.linspace(0, 10, 100)) * 50.0
    close = base_price + drift + noise

    return pd.DataFrame(
        {
            "trade_date": dates,
            "ticker": "BBCA.JK",
            "open": close - 20.0,
            "high": close + 50.0,
            "low": close - 50.0,
            "close": close,
            "adjusted_close": close,
            "volume": np.random.default_rng(42).integers(1_000_000, 10_000_000, 100),
        }
    )


def test_technical_indicators(sample_price_data: pd.DataFrame) -> None:
    """Ensure technical features compute correctly and without lookahead."""
    features = compute_technical_features(sample_price_data)
    assert "sma_20" in features.columns
    assert "rsi_14" in features.columns
    assert "macd" in features.columns
    assert "bollinger_upper" in features.columns
    assert "atr_14" in features.columns

    summary = summarize_technical_state(sample_price_data, "BBCA.JK")
    assert summary.ticker == "BBCA.JK"
    assert summary.close > 0.0
    assert 0.0 <= summary.rsi_14 <= 100.0
    assert summary.trend_state in [
        "BULLISH_UPTREND",
        "BEARISH_DOWNTREND",
        "COUNTER_TREND_RALLY",
        "CONSOLIDATION_RANGE",
    ]


def test_ict_hypotheses(sample_price_data: pd.DataFrame) -> None:
    """Ensure ICT hypothesis detection yields valid structured summaries."""
    summary = evaluate_ict_hypotheses(sample_price_data, "BBCA.JK")
    assert summary.ticker == "BBCA.JK"
    assert summary.swing_high >= summary.swing_low
    assert summary.zone_classification in ["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    assert len(summary.hypotheses) >= 1


def test_fundamental_snapshots() -> None:
    """Verify point-in-time fundamentals for Indonesian stocks."""
    snap = get_fundamental_snapshot("BBCA.JK")
    assert snap.identity.company_name == "PT Bank Central Asia Tbk"
    assert snap.pe_ratio > 0.0
    assert snap.pbv_ratio > 0.0
    assert snap.roe_percent > 0.0

    fallback = get_fundamental_snapshot("UNKNOWN.JK")
    assert fallback.earnings_quality_score == "DATA_UNAVAILABLE"


def test_market_alignment(sample_price_data: pd.DataFrame) -> None:
    """Ensure market alignment calculates rolling beta and correlation."""
    summary = compute_market_alignment(
        stock_df=sample_price_data,
        benchmark_df=sample_price_data,
        ticker="BBCA.JK",
    )
    assert summary.ticker == "BBCA.JK"
    assert 0.0 <= summary.rolling_correlation_60d <= 1.01
    assert summary.alignment_state in [
        "ALIGNED_POSITIVE",
        "PARTIAL_POSITIVE",
        "MIXED",
        "PARTIAL_NEGATIVE",
        "ALIGNED_NEGATIVE",
    ]


def test_scenarios_and_quantiles() -> None:
    """Verify multi-horizon quantile fans and scenario generation."""
    quantiles = compute_horizon_quantiles(
        current_price=10000.0,
        daily_volatility=0.015,
        daily_direction_up_prob=0.55,
    )
    assert set(quantiles.keys()) == {"1D", "5D", "20D"}
    q20 = quantiles["20D"]
    assert q20.q10 < q20.q25 < q20.q50 < q20.q75 < q20.q90

    scenarios = generate_scenarios(
        current_price=10000.0,
        quantiles_20d=q20,
        var_99_1d=0.035,
        trend_state="BULLISH_UPTREND",
    )
    assert len(scenarios) == 5
    scenario_names = {s.scenario_name for s in scenarios}
    assert "BULL_CASE" in scenario_names
    assert "BEAR_CASE" in scenario_names
    assert "VOLATILITY_SHOCK" in scenario_names


def test_liquidity_and_flow(sample_price_data: pd.DataFrame) -> None:
    """Verify liquidity metrics and creator claims ledger."""
    summary = compute_liquidity_flow_summary(sample_price_data, "BBCA.JK")
    assert summary.average_daily_value_idr > 0.0
    assert summary.liquidity_tier in ["HIGH_LIQUIDITY", "MEDIUM_LIQUIDITY", "LOW_LIQUIDITY"]

    claims = get_creator_claims_for_ticker("BBCA.JK")
    assert isinstance(claims, list)


def test_risk_engine_veto() -> None:
    """Verify Risk Engine enforcement of hard veto rules."""
    # Extreme volatility trigger
    eval_veto = evaluate_risk_engine(
        ticker="ANTM.JK",
        direction_up_prob=0.65,
        garch_volatility=0.050,  # > 0.045
        var_99=0.080,
        liquidity_tier="LOW_LIQUIDITY",
        trend_state="BULLISH_UPTREND",
    )
    assert eval_veto.hard_veto is True
    assert eval_veto.decision_state == "HIGH_RISK"
    assert len(eval_veto.veto_reasons) >= 1

    # Benign parameters
    eval_safe = evaluate_risk_engine(
        ticker="BBCA.JK",
        direction_up_prob=0.60,
        garch_volatility=0.015,
        var_99=0.025,
        liquidity_tier="HIGH_LIQUIDITY",
        trend_state="BULLISH_UPTREND",
    )
    assert eval_safe.hard_veto is False
    assert eval_safe.decision_state == "FAVORABLE_SETUP"


def test_pre_buy_decision_passport(sample_price_data: pd.DataFrame) -> None:
    """Ensure complete Pre-Buy Decision Passport generation."""
    tech = summarize_technical_state(sample_price_data, "BBCA.JK")
    ict = evaluate_ict_hypotheses(sample_price_data, "BBCA.JK")
    fund = get_fundamental_snapshot("BBCA.JK")
    align = compute_market_alignment(sample_price_data, sample_price_data, "BBCA.JK")
    liq = compute_liquidity_flow_summary(sample_price_data, "BBCA.JK")
    risk = evaluate_risk_engine(
        ticker="BBCA.JK",
        direction_up_prob=0.55,
        garch_volatility=0.015,
        var_99=0.025,
        liquidity_tier=liq.liquidity_tier,
        trend_state=tech.trend_state,
    )
    quantiles = compute_horizon_quantiles(
        current_price=tech.close,
        daily_volatility=0.015,
        daily_direction_up_prob=0.55,
    )

    passport = generate_decision_passport(
        ticker="BBCA.JK",
        company_name=fund.identity.company_name,
        cutoff_date="2026-09-25",
        current_price=tech.close,
        direction_up_prob=0.55,
        direction_model="random_forest",
        volatility_model="gjr_garch_student_t",
        quantiles_20d=quantiles["20D"],
        technical=tech,
        ict=ict,
        fundamental=fund,
        market_alignment=align,
        liquidity=liq,
        risk_eval=risk,
    )

    assert passport.ticker == "BBCA.JK"
    assert passport.passport_id.startswith("PASSPORT-BBCA-")
    assert "Pre-Buy Decision Passport" in passport.markdown_content


def test_prediction_journal() -> None:
    """Verify Prediction Journal loading."""
    journal = load_prediction_journal()
    assert len(journal) >= 5
    assert "prediction_id" in journal.columns
    assert "prob_up" in journal.columns
    assert "status" in journal.columns


def test_multimodal_radar_and_ablation() -> None:
    """Verify evidence conflict radar and ablation benchmarks."""
    conflicts = run_evidence_conflict_radar(
        technical_trend="BULLISH_UPTREND",
        fundamental_regime="HISTORICALLY_DEPRESSED_VALUATION",
        ihsg_alignment="ALIGNED_NEGATIVE",
        foreign_flow="DISTRIBUTION",
        direction_prob_up=0.60,
        garch_volatility=0.030,
    )
    assert len(conflicts) >= 2

    ablations = get_ablation_benchmarks()
    assert len(ablations) >= 5
