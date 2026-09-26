"""Unit tests for Corporate Action Risk Engine and Stockbit Stream Sentiment."""

from __future__ import annotations

import pytest

from ruang_risiko_idx.research.corporate_action_risk import (
    evaluate_dividend_action_risk,
)
from ruang_risiko_idx.research.social_stream import (
    get_stream_sentiment,
)


def test_corporate_action_dividend_risk() -> None:
    """Verify dividend trap risk evaluation across canonical tickers."""
    # High risk dividend trap (TLKM or ASII)
    profile_tlkm = evaluate_dividend_action_risk("TLKM.JK", 2900.0)
    assert profile_tlkm.ticker == "TLKM.JK"
    assert profile_tlkm.dividend_yield_percent > 0.0
    assert profile_tlkm.drop_to_yield_ratio > 1.0
    assert profile_tlkm.dividend_trap_risk_state == "HIGH_DIVIDEND_TRAP_RISK"
    assert "Waspada Dividend Trap" in profile_tlkm.action_recommendation

    # Safe carry stock (BBCA)
    profile_bbca = evaluate_dividend_action_risk("BBCA.JK", 10000.0)
    assert profile_bbca.ticker == "BBCA.JK"
    assert profile_bbca.dividend_trap_risk_state == "SAFE_DIVIDEND_CARRY"
    assert profile_bbca.recovery_days_median < 10


def test_social_stream_sentiment_and_fomo() -> None:
    """Verify Stockbit stream sentiment aggregation and FOMO trigger."""
    # Normal stream evaluation
    report = get_stream_sentiment("BBCA.JK", "STRONG_INSTITUTIONAL_ACCUMULATION")
    assert report.ticker == "BBCA.JK"
    assert 0.0 <= report.bullish_percent <= 100.0
    assert 0.0 <= report.bearish_percent <= 100.0
    assert len(report.posts) >= 1
    assert report.herding_state in ["EXTREME_FOMO", "BALANCED_DISCUSSION", "FEAR_PANIC", "QUIET"]

    # FOMO alert condition
    report_fomo = get_stream_sentiment("ANTM.JK", "RETAIL_TRAP_DISTRIBUTION")
    assert report_fomo.fomo_alert is True
