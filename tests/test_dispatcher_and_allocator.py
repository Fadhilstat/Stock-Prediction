"""Tests for Webhook Alert Dispatcher and Portfolio Risk Budget Allocator."""

from __future__ import annotations

import json
import urllib.request
import pytest

from ruang_risiko_idx.research.alert_dispatcher import (
    AlertPayload,
    dispatch_webhook_alert,
    format_discord_payload,
)
from ruang_risiko_idx.research.portfolio_allocator import (
    compute_portfolio_allocation,
    PortfolioAllocationReport,
)


def test_format_discord_payload() -> None:
    alert = AlertPayload(
        event_type="INVALIDATION_BREACH",
        ticker="BBCA.JK",
        current_price=9500.0,
        invalidation_price=9800.0,
        distance_percent=-3.06,
        message="Batas invalidasi tertembus.",
        passport_id="PASSPORT-123",
    )
    discord_data = format_discord_payload(alert)
    assert discord_data["username"] == "Ruang Risiko IDX Watchdog"
    assert len(discord_data["embeds"]) == 1
    embed = discord_data["embeds"][0]
    assert "BBCA.JK" in embed["title"]
    assert len(embed["fields"]) == 4


def test_dispatch_webhook_alert_success(monkeypatch, tmp_path) -> None:
    from ruang_risiko_idx import config

    class MockSettings:
        project_root = tmp_path

    monkeypatch.setattr(config, "ProjectSettings", MockSettings)

    class MockResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=3.0: MockResp())

    alert = AlertPayload(
        event_type="TEST_PING",
        ticker="ANTM.JK",
        current_price=1500.0,
        invalidation_price=1400.0,
        distance_percent=7.14,
        message="Uji konektivitas webhook.",
    )

    res = dispatch_webhook_alert("https://webhook.site/test-uuid", alert)
    assert res["success"] is True
    assert res["status_code"] == 200


def test_dispatch_webhook_invalid_url() -> None:
    alert = AlertPayload(
        event_type="TEST_PING",
        ticker="ANTM.JK",
        current_price=1500.0,
        invalidation_price=1400.0,
        distance_percent=7.14,
        message="Uji konektivitas webhook.",
    )
    res = dispatch_webhook_alert("invalid-url", alert)
    assert res["success"] is False
    assert "Invalid webhook URL" in res["error"]


def test_compute_portfolio_allocation_normal() -> None:
    stocks = [
        {
            "ticker": "BBCA.JK",
            "current_price": 10000.0,
            "garch_vol_daily": 0.012,
            "var_99_daily": 0.028,
            "prob_up": 0.58,
            "reward_risk_ratio": 2.2,
        },
        {
            "ticker": "BBRI.JK",
            "current_price": 5000.0,
            "garch_vol_daily": 0.018,
            "var_99_daily": 0.042,
            "prob_up": 0.52,
            "reward_risk_ratio": 1.8,
        },
    ]

    report = compute_portfolio_allocation(
        total_capital_idr=100_000_000.0,
        daily_risk_budget_pct=2.0,
        max_single_stock_pct=20.0,
        stocks_data=stocks,
    )

    assert isinstance(report, PortfolioAllocationReport)
    assert report.total_capital_idr == 100_000_000.0
    assert report.max_daily_budget_idr == 2_000_000.0
    assert report.allocated_capital_idr > 0.0
    assert report.cash_reserve_idr >= 0.0
    assert len(report.recommendations) == 2

    # Check lot multiples (1 lot = 100 shares)
    for rec in report.recommendations:
        assert rec.allocated_lots >= 0
        expected_val = rec.allocated_lots * rec.current_price * 100.0
        assert rec.allocated_value_idr == expected_val


def test_compute_portfolio_allocation_zero_capital() -> None:
    report = compute_portfolio_allocation(
        total_capital_idr=0.0,
        daily_risk_budget_pct=2.0,
        max_single_stock_pct=20.0,
        stocks_data=[],
    )
    assert report.allocated_capital_idr == 0.0
    assert report.recommendations == []
