"""Unit tests for Copula Tail Dependence, EVT Expected Shortfall, and Algorithmic Execution Simulator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.actions import (
    trigger_algo_execution_simulation,
    trigger_copula_evt_scan,
)
from ruang_risiko_idx.research.copula_evt import (
    CopulaTailDependenceReport,
    EvtPeakOverThresholdReport,
    compute_copula_tail_dependence,
    compute_evt_peak_over_threshold,
)
from ruang_risiko_idx.research.execution_algo import (
    ExecutionScheduleReport,
    generate_execution_trajectory_chart,
    simulate_algorithmic_execution,
)


@pytest.fixture
def synthetic_return_series() -> tuple[pd.Series, pd.Series]:
    """Generate correlated fat-tailed synthetic return series."""
    np.random.seed(42)
    n = 100
    # Generate t-distributed returns (fat tails)
    t_rets = np.random.standard_t(df=4, size=n) * 0.015
    noise = np.random.normal(0, 0.005, size=n)
    bench_rets = 0.7 * t_rets + noise
    return pd.Series(t_rets), pd.Series(bench_rets)


def test_copula_tail_dependence_computation(synthetic_return_series):
    """Verify Clayton lower tail and Gumbel upper tail dependence estimates."""
    s_a, s_b = synthetic_return_series
    report = compute_copula_tail_dependence(s_a, s_b, ticker_a="BBCA.JK", ticker_b="^JKSE")

    assert isinstance(report, CopulaTailDependenceReport)
    assert report.ticker_a == "BBCA.JK"
    assert report.ticker_b == "^JKSE"
    assert 0.0 <= report.lower_tail_dependence_lambda_l <= 1.0
    assert 0.0 <= report.upper_tail_dependence_lambda_u <= 1.0
    assert report.asymmetry_ratio > 0.0
    assert "\u2014" not in report.tail_regime


def test_evt_peak_over_threshold_computation(synthetic_return_series):
    """Verify Generalized Pareto Distribution fit and EVT-VaR / EVT-ES."""
    s_a, _ = synthetic_return_series
    report = compute_evt_peak_over_threshold(s_a, ticker="BBCA.JK", percentile_threshold=0.85)

    assert isinstance(report, EvtPeakOverThresholdReport)
    assert report.ticker == "BBCA.JK"
    assert report.exceedance_count > 0
    assert report.evt_var_99_pct > 0.0
    # Expected Shortfall (CVaR) must exceed Value-at-Risk (subadditivity)
    assert report.evt_cvar_expected_shortfall_99_pct >= report.evt_var_99_pct
    assert "\u2014" not in report.recommendation


def test_algorithmic_execution_simulation():
    """Verify VWAP, TWAP, and POV execution trajectory scheduling."""
    for strat in ["VWAP", "TWAP", "POV"]:
        report = simulate_algorithmic_execution(
            ticker="BBCA.JK",
            current_price=10000.0,
            order_value_idr=200_000_000.0,
            average_daily_volume=10_000_000.0,
            strategy=strat,
        )
        assert isinstance(report, ExecutionScheduleReport)
        assert report.strategy == strat
        assert report.total_shares == 20000
        assert len(report.schedule_slices) == 9
        assert report.total_slippage_bps >= 0.0
        assert report.total_market_impact_idr >= 0.0
        assert 0.0 <= report.execution_efficiency_score <= 100.0
        assert "\u2014" not in report.recommendation

        # Check slices cumulative sum
        total_slices_shares = sum(s.target_shares for s in report.schedule_slices)
        assert total_slices_shares == report.total_shares
        assert report.schedule_slices[-1].cumulative_progress_pct == pytest.approx(100.0, abs=0.1)


def test_execution_trajectory_chart():
    """Verify Plotly chart generation for execution schedule."""
    report = simulate_algorithmic_execution(
        ticker="BBCA.JK",
        current_price=10000.0,
        order_value_idr=100_000_000.0,
    )
    fig = generate_execution_trajectory_chart(report)
    assert fig is not None
    assert len(fig.data) == 3
    assert fig.layout.paper_bgcolor == "#131722"


def test_action_triggers_copula_and_algo_execution():
    """Verify action controller triggers for Copula EVT and Algorithmic Execution."""
    res_copula = trigger_copula_evt_scan("BBCA.JK")
    assert res_copula["success"] is True
    assert "lambda_l" in res_copula
    assert "evt_es_99" in res_copula

    res_algo = trigger_algo_execution_simulation(
        ticker="BBCA.JK",
        order_value_idr=150_000_000.0,
        strategy="VWAP",
    )
    assert res_algo["success"] is True
    assert "slippage_bps" in res_algo
    assert "efficiency_score" in res_algo
