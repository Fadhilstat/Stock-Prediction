"""Unit tests for Hidden Markov Model (HMM) Regime Switching and Pareto Portfolio Optimizer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.actions import (
    trigger_auto_update_check,
    trigger_hmm_regime_detection,
    trigger_pareto_portfolio_optimization,
)
from ruang_risiko_idx.research.hmm_regime import (
    HmmRegimeReport,
    compute_hmm_regime_classification,
    decode_viterbi_path,
    fit_gaussian_hmm_3state,
)
from ruang_risiko_idx.research.pareto_portfolio import (
    ParetoPortfolioReport,
    compute_portfolio_cvar_99,
    generate_pareto_frontier_chart,
    optimize_pareto_portfolio_frontier,
)


@pytest.fixture
def synthetic_regime_prices() -> pd.Series:
    """Generate 120 days of multi-regime price series."""
    np.random.seed(42)
    # 40 days bull, 40 days bear, 40 days sideways
    rets_bull = np.random.normal(0.0015, 0.008, 40)
    rets_bear = np.random.normal(-0.002, 0.025, 40)
    rets_side = np.random.normal(0.0001, 0.010, 40)
    all_rets = np.concatenate([rets_bull, rets_bear, rets_side])
    prices = 10000.0 * np.cumprod(1.0 + all_rets)
    return pd.Series(prices)


@pytest.fixture
def synthetic_multi_asset_df() -> pd.DataFrame:
    """Generate 100 days of price data for 4 assets."""
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    records = []
    tickers = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK"]
    for t in tickers:
        p = 10000.0
        for d in dates:
            p *= (1.0 + np.random.normal(0.0005, 0.015))
            records.append({"trade_date": d, "ticker": t, "close": p})
    return pd.DataFrame(records)


def test_hmm_regime_fitting_and_viterbi(synthetic_regime_prices):
    """Verify EM parameter estimation and Viterbi path decoding."""
    rets = synthetic_regime_prices.pct_change().dropna()
    means, variances, trans, gamma = fit_gaussian_hmm_3state(rets, max_iter=20)

    assert len(means) == 3
    assert len(variances) == 3
    assert trans.shape == (3, 3)
    assert np.all(variances > 0.0)
    # Row sum of transition matrix must equal 1.0
    assert np.allclose(np.sum(trans, axis=1), 1.0, atol=1e-3)

    viterbi_states = decode_viterbi_path(rets, means, variances, trans)
    assert len(viterbi_states) == len(rets)
    assert all(s in ["BULLISH_TREND", "SIDEWAYS_COMPRESSION", "HIGH_VOLATILITY_BEAR"] for s in viterbi_states)


def test_hmm_regime_classification_report(synthetic_regime_prices):
    """Verify HMM classification report generation and state profiles."""
    report = compute_hmm_regime_classification(synthetic_regime_prices, ticker="BBCA.JK")

    assert isinstance(report, HmmRegimeReport)
    assert report.ticker == "BBCA.JK"
    assert report.current_regime in ["BULLISH_TREND", "SIDEWAYS_COMPRESSION", "HIGH_VOLATILITY_BEAR"]
    assert 0.0 <= report.current_regime_probability <= 1.0
    assert len(report.states) == 3
    assert "\u2014" not in report.regime_interpretation


def test_pareto_portfolio_optimization(synthetic_multi_asset_df):
    """Verify Mean-CVaR Pareto frontier generation and tangency portfolio."""
    report = optimize_pareto_portfolio_frontier(synthetic_multi_asset_df, num_points=10)

    assert isinstance(report, ParetoPortfolioReport)
    assert len(report.tickers) == 4
    assert len(report.frontier_points) == 10
    assert report.optimal_tangency_point.sharpe_ratio >= report.minimum_cvar_point.sharpe_ratio
    assert report.diversification_gain_pct >= 0.0
    assert "\u2014" not in report.recommendation

    # Check sum of optimal weights equals 100%
    total_weights = sum(report.optimal_tangency_point.weights.values())
    assert total_weights == pytest.approx(100.0, abs=0.5)


def test_pareto_frontier_chart(synthetic_multi_asset_df):
    """Verify Plotly figure generation for Pareto efficient frontier."""
    report = optimize_pareto_portfolio_frontier(synthetic_multi_asset_df, num_points=8)
    fig = generate_pareto_frontier_chart(report)

    assert fig is not None
    assert len(fig.data) == 2
    assert fig.layout.paper_bgcolor == "#131722"


def test_action_triggers_hmm_and_pareto():
    """Verify action controller triggers for HMM and Pareto optimization."""
    res_hmm = trigger_hmm_regime_detection("BBCA.JK")
    assert res_hmm["success"] is True
    assert "current_regime" in res_hmm
    assert "probability" in res_hmm

    res_pareto = trigger_pareto_portfolio_optimization()
    assert res_pareto["success"] is True
    assert "sharpe" in res_pareto
    assert "optimal_weights" in res_pareto

    res_update = trigger_auto_update_check()
    assert res_update["success"] is True
    assert "Auto-updater" in res_update["message"] or "completed" in res_update["message"]
