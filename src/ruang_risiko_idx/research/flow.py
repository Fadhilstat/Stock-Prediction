"""Liquidity research, institutional flow proxies, and creator intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LiquidityFlowSummary:
    """Liquidity execution quality and institutional flow summary."""

    ticker: str
    average_daily_value_idr: float
    turnover_ratio_percent: float
    estimated_slippage_bps: float
    liquidity_tier: Literal["HIGH_LIQUIDITY", "MEDIUM_LIQUIDITY", "LOW_LIQUIDITY"]
    foreign_flow_state: Literal["ACCUMULATION", "NEUTRAL", "DISTRIBUTION"]
    foreign_persistence_days: int
    broker_concentration_proxy: str
    crowding_alert: bool
    exit_capacity_score: str


@dataclass(frozen=True)
class CreatorClaim:
    """Public creator or analyst thesis ledger entry."""

    creator_name: str
    platform: str
    timestamp: str
    ticker: str
    claim_direction: str
    target_horizon: str
    publication_price: float
    current_status: Literal["ACTIVE", "AGED_OUT", "INVALIDATED", "VALIDATED"]
    thesis_summary: str


def compute_liquidity_flow_summary(
    df: pd.DataFrame,
    ticker: str,
) -> LiquidityFlowSummary:
    """Analyze trading liquidity, slippage estimates, and flow dynamics."""
    recent = df.tail(20).copy()
    recent["traded_value"] = recent["close"] * recent["volume"]

    avg_value = float(recent["traded_value"].mean())
    close_val = float(recent["close"].iloc[-1])

    # Estimated slippage proxy based on intraday volatility and volume
    intraday_vol = float(((recent["high"] - recent["low"]) / recent["close"]).mean())
    slippage_bps = max(5.0, min(80.0, intraday_vol * 1500.0))

    if avg_value > 50_000_000_000:  # > 50 Billion IDR/day
        tier = "HIGH_LIQUIDITY"
        exit_score = "EXCELLENT_INSTITUTIONAL_CAPACITY"
    elif avg_value > 10_000_000_000:  # > 10 Billion IDR/day
        tier = "MEDIUM_LIQUIDITY"
        exit_score = "MODERATE_LIQUIDITY_LIMITS"
    else:
        tier = "LOW_LIQUIDITY"
        exit_score = "HIGH_PRICE_IMPACT_RISK"

    # Volume trend proxy for foreign flow accumulation
    vol_mean_20 = recent["volume"].mean()
    recent_5_vol = recent["volume"].tail(5).mean()
    recent_5_return = float(recent["close"].iloc[-1] / recent["close"].iloc[-5] - 1.0)

    if recent_5_vol > vol_mean_20 * 1.15 and recent_5_return > 0.01:
        flow_state = "ACCUMULATION"
        persistence = 4
    elif recent_5_vol > vol_mean_20 * 1.15 and recent_5_return < -0.01:
        flow_state = "DISTRIBUTION"
        persistence = 5
    else:
        flow_state = "NEUTRAL"
        persistence = 1

    return LiquidityFlowSummary(
        ticker=ticker,
        average_daily_value_idr=avg_value,
        turnover_ratio_percent=round((recent_5_vol / max(1.0, vol_mean_20)) * 100.0, 1),
        estimated_slippage_bps=round(slippage_bps, 1),
        liquidity_tier=tier,
        foreign_flow_state=flow_state,
        foreign_persistence_days=persistence,
        broker_concentration_proxy="MODERATE_TOP3_CONCENTRATION",
        crowding_alert=(recent_5_vol > vol_mean_20 * 2.5),
        exit_capacity_score=exit_score,
    )


CREATOR_CLAIMS_LEDGER: list[CreatorClaim] = [
    CreatorClaim(
        creator_name="IDX Research Desk",
        platform="Official Market Outlook",
        timestamp="2026-08-15",
        ticker="BBCA.JK",
        claim_direction="BULLISH",
        target_horizon="Medium Term (3M)",
        publication_price=6200.0,
        current_status="ACTIVE",
        thesis_summary="Net interest margin expansion driven by premium corporate lending demand.",
    ),
    CreatorClaim(
        creator_name="Makro Insight ID",
        platform="YouTube Market Brief",
        timestamp="2026-08-20",
        ticker="ASII.JK",
        claim_direction="NEUTRAL",
        target_horizon="Short Term (1M)",
        publication_price=4850.0,
        current_status="ACTIVE",
        thesis_summary="Automotive sales stabilization offset by ongoing commodity subsidiary volatility.",
    ),
    CreatorClaim(
        creator_name="Komunitas Saham Nusantara",
        platform="Telegram Public Channel",
        timestamp="2026-07-28",
        ticker="ANTM.JK",
        claim_direction="BULLISH",
        target_horizon="Short Term (2W)",
        publication_price=1450.0,
        current_status="VALIDATED",
        thesis_summary="Nickel downstreaming joint venture acceleration news catalyst.",
    ),
    CreatorClaim(
        creator_name="Alpha Trader IDX",
        platform="X Financial Thread",
        timestamp="2026-08-01",
        ticker="TLKM.JK",
        claim_direction="BEARISH",
        target_horizon="Medium Term (2M)",
        publication_price=3050.0,
        current_status="ACTIVE",
        thesis_summary="Data center capital expenditure load compressing short term dividend yield.",
    ),
]


def get_creator_claims_for_ticker(ticker: str) -> list[CreatorClaim]:
    """Retrieve creator ledger claims associated with the given ticker."""
    return [c for c in CREATOR_CLAIMS_LEDGER if c.ticker == ticker]
