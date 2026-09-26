"""Unit tests for Stockbit-style Orderbook, Broker Summary, and Web Action Controller."""

from __future__ import annotations

import pytest

from ruang_risiko_idx.research.actions import (
    load_action_history,
    load_runtime_config,
    record_action,
    save_runtime_config,
    update_runtime_risk_parameters,
)
from ruang_risiko_idx.research.broker_summary import (
    generate_broker_summary,
)
from ruang_risiko_idx.research.orderbook import (
    calculate_idx_auto_rejection,
    generate_orderbook,
    get_idx_tick_size,
)


def test_idx_tick_sizes() -> None:
    """Verify IDX tick size rules across all price fractions."""
    assert get_idx_tick_size(150.0) == 1
    assert get_idx_tick_size(350.0) == 2
    assert get_idx_tick_size(1500.0) == 5
    assert get_idx_tick_size(3500.0) == 10
    assert get_idx_tick_size(8000.0) == 25


def test_idx_auto_rejection_limits() -> None:
    """Verify official IDX Auto Rejection Atas (ARA) and Bawah (ARB) computation."""
    # Under 200: 35% limit
    ara_low, arb_low = calculate_idx_auto_rejection(100.0)
    assert ara_low == 135.0
    assert arb_low == 65.0

    # 200 - 5000: 25% limit
    ara_mid, arb_mid = calculate_idx_auto_rejection(1000.0)
    assert ara_mid == 1250.0
    assert arb_mid == 750.0

    # > 5000: 20% limit
    ara_high, arb_high = calculate_idx_auto_rejection(10000.0)
    assert ara_high == 12000.0
    assert arb_high == 8000.0


def test_orderbook_generation() -> None:
    """Ensure generated 10-level orderbook has proper structure and tick bounds."""
    book = generate_orderbook(
        ticker="BBCA.JK",
        current_price=10000.0,
        previous_close=9950.0,
        average_volume=15_000_000,
    )
    assert book.ticker == "BBCA.JK"
    assert len(book.bids) == 10
    assert len(book.offers) == 10
    assert book.total_bid_lots > 0
    assert book.total_offer_lots > 0
    assert book.bid_offer_ratio > 0.0
    assert book.ara_price > book.current_price
    assert book.arb_price < book.current_price


def test_broker_summary_generation() -> None:
    """Ensure broker summary outputs top buyers, sellers, and concentration ratio."""
    bs = generate_broker_summary(
        ticker="BBRI.JK",
        trade_date="2026-09-25",
        close_price=4700.0,
        total_traded_value_idr=500_000_000_000.0,
        foreign_flow_state="ACCUMULATION",
    )
    assert bs.ticker == "BBRI.JK"
    assert bs.status == "BIG_ACCUMULATION"
    assert len(bs.top_buyers) == 5
    assert len(bs.top_sellers) == 5
    assert bs.top3_buyer_ratio_percent > 0.0
    assert bs.top3_seller_ratio_percent > 0.0
    assert bs.foreign_net_value_idr > 0.0


def test_web_action_controller() -> None:
    """Ensure web action controller records entries and manages configuration."""
    cfg = load_runtime_config()
    assert "var_confidence_level" in cfg
    assert "max_portfolio_allocation_percent" in cfg

    # Update runtime parameters
    res = update_runtime_risk_parameters(
        var_confidence_level=0.95,
        max_portfolio_allocation_percent=20.0,
        max_slippage_bps=30.0,
        garch_vol_hard_veto_threshold=0.05,
        tail_var99_veto_threshold=0.08,
        active_direction_model="xgboost",
    )
    assert res["success"] is True

    # Check updated config
    updated_cfg = load_runtime_config()
    assert updated_cfg["var_confidence_level"] == 0.95
    assert updated_cfg["active_direction_model"] == "xgboost"

    # Action ledger history
    history = load_action_history(limit=10)
    assert len(history) >= 1
    assert any(h["action_type"] == "RUNTIME_CONFIG_UPDATE" for h in history)
