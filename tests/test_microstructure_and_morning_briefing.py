"""Unit tests for Orderbook Microstructure Imbalance and Pre-Market Morning Briefing."""

from __future__ import annotations

import pytest

from ruang_risiko_idx.research.orderbook import generate_orderbook
from ruang_risiko_idx.research.microstructure_imbalance import (
    compute_microstructure_imbalance,
    MicrostructureAnalysis,
)
from ruang_risiko_idx.research.morning_briefing import (
    generate_premarket_morning_briefing,
    MorningBriefingDigest,
)
from ruang_risiko_idx.research.actions import (
    trigger_morning_briefing_generation,
    trigger_microstructure_imbalance_scan,
)


def test_microstructure_imbalance_calculation():
    """Verify orderbook microstructure imbalance and order flow delta metrics."""
    ob = generate_orderbook(ticker="BBCA.JK", current_price=10250.0, previous_close=10200.0)
    analysis = compute_microstructure_imbalance(ob)

    assert isinstance(analysis, MicrostructureAnalysis)
    assert analysis.ticker == "BBCA.JK"
    assert -1.0 <= analysis.voi_normalized <= 1.0
    assert analysis.order_flow_regime in ["AGGRESSIVE_BUYING", "BALANCED_FLOW", "AGGRESSIVE_SELLING"]
    assert 0.0 <= analysis.spoofing_probability_score <= 1.0
    assert analysis.absorption_state in ["BID_ABSORPTION", "NEUTRAL_FLOW", "OFFER_ABSORPTION"]
    assert len(analysis.level_breakdowns) == 10
    assert analysis.level_breakdowns[0].step == 1
    assert analysis.level_breakdowns[0].bid_price == ob.bids[0].price
    assert analysis.level_breakdowns[0].offer_price == ob.offers[0].price


def test_morning_briefing_generation():
    """Verify autonomous pre-market morning briefing compilation."""
    digest = generate_premarket_morning_briefing("2026-09-27")

    assert isinstance(digest, MorningBriefingDigest)
    assert digest.briefing_date == "2026-09-27"
    assert len(digest.global_cues) >= 4
    assert len(digest.top_setups) == 3
    assert len(digest.risk_warnings) >= 3
    assert "BRIEF-" in digest.digest_id
    assert "# Ruang Risiko IDX: Pre-Market Morning Briefing" in digest.markdown_content

    # Strict Zero Em Dash check on generated digest content
    assert "\u2014" not in digest.markdown_content


def test_action_triggers_for_new_features():
    """Verify web action controller integration for briefing and microstructure."""
    briefing_res = trigger_morning_briefing_generation()
    assert briefing_res["success"] is True
    assert "digest_id" in briefing_res
    assert len(briefing_res["top_setups"]) == 3

    micro_res = trigger_microstructure_imbalance_scan("BBCA.JK")
    assert micro_res["success"] is True
    assert micro_res["ticker"] == "BBCA.JK"
    assert "voi_lots" in micro_res
