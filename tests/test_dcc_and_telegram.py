"""Unit tests for DCC-GARCH Contagion Engine and Telegram Notification Dispatcher."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.actions import (
    trigger_dcc_garch_recalculation,
    trigger_telegram_test_dispatch,
)
from ruang_risiko_idx.research.automation_daemon import (
    get_default_scheduled_tasks,
    run_autonomous_full_cycle,
)
from ruang_risiko_idx.research.dcc_garch import (
    compute_dcc_garch_matrix,
    estimate_univariate_garch_volatilities,
    generate_dcc_heatmap_figure,
)
from ruang_risiko_idx.research.telegram_notifier import (
    dispatch_telegram_message,
    format_biweekly_audit_telegram,
    format_dcc_contagion_alert,
    format_morning_briefing_telegram,
    format_trailing_stop_telegram,
)


@pytest.fixture
def synthetic_multi_asset_prices() -> pd.DataFrame:
    """Generate 60 trading days of synthetic close prices for 4 assets."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(60)]
    tickers = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK"]

    records = []
    base_prices = {"BBCA.JK": 10000.0, "BBRI.JK": 5000.0, "TLKM.JK": 3500.0, "ASII.JK": 5200.0}

    for t in tickers:
        p = base_prices[t]
        for d in dates:
            ret = np.random.normal(0.0005, 0.015)
            p = max(100.0, p * (1.0 + ret))
            records.append({
                "ticker": t,
                "trade_date": d,
                "close": p,
                "volume": 10_000_000,
            })

    return pd.DataFrame(records)


def test_univariate_garch_volatilities():
    """Verify univariate GARCH volatility estimates remain positive and bounded."""
    np.random.seed(123)
    rets = pd.Series(np.random.normal(0.0, 0.015, 100))
    vols = estimate_univariate_garch_volatilities(rets)

    assert len(vols) == 100
    assert np.all(vols > 0.0)
    assert np.all(np.isfinite(vols))


def test_dcc_garch_matrix_computation(synthetic_multi_asset_prices):
    """Verify DCC-GARCH output satisfies correlation matrix mathematical axioms."""
    report = compute_dcc_garch_matrix(synthetic_multi_asset_prices, lookback_window=50)

    assert len(report.tickers) == 4
    assert 0.0 <= report.systemic_contagion_index <= 1.0
    assert report.contagion_regime in ["HIGH_SYSTEMIC_SPILLOVER", "MODERATE_COUPLING", "DECOUPLED_RESILIENT"]

    # Verify diagonal is 1.0 and off-diagonals are symmetric within [-1, 1]
    for t1 in report.tickers:
        assert report.correlation_matrix[t1][t1] == pytest.approx(1.0, abs=1e-3)
        for t2 in report.tickers:
            c12 = report.correlation_matrix[t1][t2]
            c21 = report.correlation_matrix[t2][t1]
            assert c12 == pytest.approx(c21, abs=1e-3)
            assert -1.0 <= c12 <= 1.0

    assert report.highest_correlation_pair.current_correlation >= report.lowest_correlation_pair.current_correlation


def test_dcc_heatmap_figure(synthetic_multi_asset_prices):
    """Verify Plotly figure generation for DCC correlation heatmap."""
    report = compute_dcc_garch_matrix(synthetic_multi_asset_prices, lookback_window=40)
    fig = generate_dcc_heatmap_figure(report)

    assert fig is not None
    assert len(fig.data) == 1
    assert fig.layout.paper_bgcolor == "#131722"


def test_telegram_message_formatters():
    """Verify Telegram message markdown formatting generators."""
    # Test morning briefing formatter
    class DummyDigest:
        briefing_date = "2026-09-25"
        market_tone = "BULLISH_OPPORTUNITY"
        top_setups = []

    text_briefing = format_morning_briefing_telegram(DummyDigest())
    assert "MORNING BRIEFING" in text_briefing
    assert "2026-09-25" in text_briefing

    # Test trailing stop alert formatter
    text_trailing = format_trailing_stop_telegram(
        ticker="BBCA.JK",
        current_price=10250.0,
        trailing_price=9850.0,
        stage="BREAKEVEN_LOCKED",
        status="ACTIVE_TRACKING",
    )
    assert "BBCA.JK" in text_trailing
    assert "BREAKEVEN_LOCKED" in text_trailing
    assert "9,850" in text_trailing

    # Test bi-weekly audit formatter
    text_audit = format_biweekly_audit_telegram({
        "cycle_number": 3,
        "brier_score": 0.215,
        "status": "HEALTHY",
        "champion_model": "random_forest",
    })
    assert "BI-WEEKLY" in text_audit
    assert "0.2150" in text_audit

    # Test DCC contagion formatter
    class DummyDcc:
        systemic_contagion_index = 0.68
        contagion_regime = "HIGH_SYSTEMIC_SPILLOVER"
        highest_correlation_pair = None

    text_dcc = format_dcc_contagion_alert(DummyDcc())
    assert "DCC-GARCH CONTAGION" in text_dcc
    assert "0.6800" in text_dcc


def test_telegram_dispatch_simulated():
    """Verify simulated Telegram message dispatch when unconfigured."""
    res = dispatch_telegram_message("Uji pesan otomatis kuantitatif")
    assert res.success is True
    assert res.is_simulated is True
    assert res.status_code == 200
    assert "SIMULATION" in res.summary or "simulated" in res.summary


def test_action_triggers_dcc_and_telegram(synthetic_multi_asset_prices):
    """Verify web action controller integration for DCC and Telegram."""
    res_dcc = trigger_dcc_garch_recalculation()
    assert res_dcc["success"] is True
    assert "sci" in res_dcc

    res_tg = trigger_telegram_test_dispatch(custom_message="Testing action dispatch")
    assert res_tg["success"] is True
    assert res_tg["is_simulated"] is True


def test_automation_tasks_and_full_cycle():
    """Verify automation daemon tasks contain DCC and Telegram, and full cycle completes."""
    tasks = get_default_scheduled_tasks()
    task_ids = [t.task_id for t in tasks]

    assert "TASK-DCC-CONTAGION" in task_ids
    assert "TASK-TELEGRAM-DISPATCH" in task_ids

    cycle_res = run_autonomous_full_cycle(operator="pytest_runner")
    assert "dcc_contagion" in cycle_res.step_results
    assert "telegram_dispatch" in cycle_res.step_results
    assert cycle_res.step_results["dcc_contagion"]["success"] is True
    assert cycle_res.step_results["telegram_dispatch"]["success"] is True
