"""Unit tests for Automation Daemon, Dynamic Trailing Ratchet, and Strategy Backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.research.automation_daemon import (
    AutonomousCycleResult,
    get_default_scheduled_tasks,
    load_automation_schedule,
    run_autonomous_full_cycle,
    save_automation_schedule,
)
from ruang_risiko_idx.research.dynamic_trailing import (
    compute_dynamic_trailing_boundary,
    DynamicTrailingSnapshot,
)
from ruang_risiko_idx.research.strategy_backtest import (
    run_strategy_backtest_replay,
    StrategyBacktestReport,
)


def test_dynamic_trailing_boundary_stages():
    """Verify GARCH-ATR dynamic trailing boundary ratcheting stages."""
    # Stage 1: Below target q50
    s1 = compute_dynamic_trailing_boundary(
        ticker="BBCA.JK",
        entry_price=10000.0,
        current_price=10100.0,
        highest_price_since_entry=10150.0,
        static_invalidation=9600.0,
        target_q50=10300.0,
        daily_garch_vol=0.015,
    )
    assert isinstance(s1, DynamicTrailingSnapshot)
    assert s1.ratchet_stage == "INITIAL_DEFENSE"
    assert s1.dynamic_trailing_stop_price >= s1.static_invalidation_price
    assert s1.is_breached is False
    assert "\u2014" not in s1.ratchet_rationale

    # Stage 2: Above target q50, locked breakeven
    s2 = compute_dynamic_trailing_boundary(
        ticker="BBCA.JK",
        entry_price=10000.0,
        current_price=10400.0,
        highest_price_since_entry=10450.0,
        static_invalidation=9600.0,
        target_q50=10300.0,
        daily_garch_vol=0.015,
    )
    assert s2.ratchet_stage == "BREAKEVEN_LOCKED"
    assert s2.dynamic_trailing_stop_price > s2.entry_price

    # Stage 3: Gain >= 8%, profit protection
    s3 = compute_dynamic_trailing_boundary(
        ticker="BBCA.JK",
        entry_price=10000.0,
        current_price=11000.0,
        highest_price_since_entry=11100.0,
        static_invalidation=9600.0,
        target_q50=10300.0,
        daily_garch_vol=0.015,
    )
    assert s3.ratchet_stage == "PROFIT_PROTECTION"
    assert s3.dynamic_trailing_stop_price >= 10400.0

    # Stage 4: Gain >= 15%, trailing tight
    s4 = compute_dynamic_trailing_boundary(
        ticker="BBCA.JK",
        entry_price=10000.0,
        current_price=11800.0,
        highest_price_since_entry=12000.0,
        static_invalidation=9600.0,
        target_q50=10300.0,
        daily_garch_vol=0.015,
    )
    assert s4.ratchet_stage == "TRAILING_TIGHT"
    assert s4.dynamic_trailing_stop_price > 11000.0


def test_strategy_backtest_replay():
    """Verify quantitative strategy historical backtest replay."""
    # Generate synthetic price series for 100 days
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-01-01", periods=100, freq="B").strftime("%Y-%m-%d").tolist()
    rets = rng.normal(0.0008, 0.015, size=100)
    prices = 10000.0 * np.cumprod(1.0 + rets)

    df = pd.DataFrame({"trade_date": dates, "close": prices})
    report = run_strategy_backtest_replay(df, ticker="BBCA.JK", initial_capital_idr=100_000_000.0)

    assert isinstance(report, StrategyBacktestReport)
    assert report.ticker == "BBCA.JK"
    assert report.trading_days == 100
    assert len(report.equity_curve) == 99
    assert report.maximum_drawdown_pct >= 0.0
    assert 0.0 <= report.win_rate_pct <= 100.0
    assert "\u2014" not in report.executive_summary


def test_automation_daemon_schedule_and_cycle():
    """Verify autonomous daemon task management and full cycle execution."""
    tasks = load_automation_schedule()
    assert len(tasks) >= 5
    assert any(t.task_id == "TASK-MARKET-DATA" for t in tasks)
    assert any(t.task_id == "TASK-MORNING-BRIEFING" for t in tasks)

    # Run complete autonomous sequence
    res = run_autonomous_full_cycle(operator="unit_test_runner")
    assert isinstance(res, AutonomousCycleResult)
    assert "CYCLE-" in res.cycle_id
    assert "market_data" in res.step_results
    assert "morning_briefing" in res.step_results
    assert res.total_duration_ms > 0
    assert "\u2014" not in res.summary_message
