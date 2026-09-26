"""Formalized ICT-style market structure research hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ICTHypothesisResult:
    """Formalized output for one ICT research hypothesis."""

    hypothesis_name: str
    detected: bool
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    reference_price: float
    cutoff_date: pd.Timestamp
    invalidation_level: float
    description: str


@dataclass(frozen=True)
class ICTStructureSummary:
    """Consolidated ICT hypothesis research summary."""

    ticker: str
    as_of_date: pd.Timestamp
    swing_high: float
    swing_low: float
    market_structure_state: str
    fair_value_gap_present: bool
    fvg_zone_top: float
    fvg_zone_bottom: float
    liquidity_sweep_detected: bool
    order_block_zone_top: float
    order_block_zone_bottom: float
    zone_classification: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    hypotheses: list[ICTHypothesisResult]


def detect_swing_points(df: pd.DataFrame, window: int = 5) -> tuple[float, float]:
    """Find the most recent swing high and swing low within lookback window."""
    recent = df.tail(window * 3)
    if len(recent) < window:
        high_val = float(df["high"].max())
        low_val = float(df["low"].min())
        return high_val, low_val

    rolling_high = recent["high"].rolling(window, center=True).max()
    rolling_low = recent["low"].rolling(window, center=True).min()

    high_mask = recent["high"] == rolling_high
    low_mask = recent["low"] == rolling_low

    highs = recent.loc[high_mask, "high"]
    lows = recent.loc[low_mask, "low"]

    latest_high = float(highs.iloc[-1]) if not highs.empty else float(recent["high"].max())
    latest_low = float(lows.iloc[-1]) if not lows.empty else float(recent["low"].min())

    return latest_high, latest_low


def detect_fvg(df: pd.DataFrame) -> tuple[bool, float, float, str]:
    """Detect Fair Value Gap (FVG) hypothesis across the last 3 candles."""
    if len(df) < 3:
        return False, 0.0, 0.0, "NEUTRAL"

    c1 = df.iloc[-3]
    c2 = df.iloc[-2]
    c3 = df.iloc[-1]

    # Bullish FVG: Low of candle 3 is higher than High of candle 1
    if c3["low"] > c1["high"]:
        gap_top = float(c3["low"])
        gap_bottom = float(c1["high"])
        return True, gap_top, gap_bottom, "BULLISH"

    # Bearish FVG: High of candle 3 is lower than Low of candle 1
    if c3["high"] < c1["low"]:
        gap_top = float(c1["low"])
        gap_bottom = float(c3["high"])
        return True, gap_top, gap_bottom, "BEARISH"

    return False, 0.0, 0.0, "NEUTRAL"


def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> tuple[bool, str, float]:
    """Detect if current candle swept recent swing extreme and rejected."""
    if len(df) < lookback + 1:
        return False, "NEUTRAL", 0.0

    past = df.iloc[-(lookback + 1) : -1]
    current = df.iloc[-1]

    recent_high = float(past["high"].max())
    recent_low = float(past["low"].min())

    # Bullish sweep: traded below recent low but closed above it
    if current["low"] < recent_low and current["close"] > recent_low:
        return True, "BULLISH", recent_low

    # Bearish sweep: traded above recent high but closed below it
    if current["high"] > recent_high and current["close"] < recent_high:
        return True, "BEARISH", recent_high

    return False, "NEUTRAL", 0.0


def evaluate_ict_hypotheses(df: pd.DataFrame, ticker: str) -> ICTStructureSummary:
    """Formally evaluate ICT research hypotheses on clean market data."""
    data = df.sort_values("trade_date").copy()
    latest = data.iloc[-1]
    close = float(latest["close"])
    cutoff = pd.Timestamp(latest["trade_date"])

    swing_high, swing_low = detect_swing_points(data, window=5)

    # Zone calculation
    range_span = swing_high - swing_low
    if range_span > 0:
        pos_ratio = (close - swing_low) / range_span
        if pos_ratio > 0.55:
            zone = "PREMIUM"
        elif pos_ratio < 0.45:
            zone = "DISCOUNT"
        else:
            zone = "EQUILIBRIUM"
    else:
        zone = "EQUILIBRIUM"

    # Hypotheses
    hypotheses: list[ICTHypothesisResult] = []

    # 1. Market Structure Shift
    if close > swing_high:
        mss_state = "BULLISH_BREAK_OF_STRUCTURE"
        hypotheses.append(
            ICTHypothesisResult(
                hypothesis_name="Market Structure Shift",
                detected=True,
                direction="BULLISH",
                reference_price=swing_high,
                cutoff_date=cutoff,
                invalidation_level=swing_low,
                description="Price closed above recent swing high, signaling bullish structure continuation.",
            )
        )
    elif close < swing_low:
        mss_state = "BEARISH_BREAK_OF_STRUCTURE"
        hypotheses.append(
            ICTHypothesisResult(
                hypothesis_name="Market Structure Shift",
                detected=True,
                direction="BEARISH",
                reference_price=swing_low,
                cutoff_date=cutoff,
                invalidation_level=swing_high,
                description="Price closed below recent swing low, signaling bearish structure displacement.",
            )
        )
    else:
        mss_state = "RANGE_BOUND_INTERNAL_STRUCTURE"
        hypotheses.append(
            ICTHypothesisResult(
                hypothesis_name="Market Structure Shift",
                detected=False,
                direction="NEUTRAL",
                reference_price=(swing_high + swing_low) / 2.0,
                cutoff_date=cutoff,
                invalidation_level=swing_low if zone == "DISCOUNT" else swing_high,
                description="Price oscillates within defined swing bounds without confirmed displacement.",
            )
        )

    # 2. Fair Value Gap
    fvg_present, fvg_top, fvg_bottom, fvg_dir = detect_fvg(data)
    if fvg_present:
        hypotheses.append(
            ICTHypothesisResult(
                hypothesis_name="Fair Value Gap Imbalance",
                detected=True,
                direction=fvg_dir,  # type: ignore[arg-type]
                reference_price=(fvg_top + fvg_bottom) / 2.0,
                cutoff_date=cutoff,
                invalidation_level=fvg_bottom if fvg_dir == "BULLISH" else fvg_top,
                description=f"3-candle imbalance detected between Rp {fvg_bottom:,.0f} and Rp {fvg_top:,.0f}.",
            )
        )

    # 3. Liquidity Sweep
    sweep_present, sweep_dir, sweep_level = detect_liquidity_sweep(data)
    if sweep_present:
        hypotheses.append(
            ICTHypothesisResult(
                hypothesis_name="Liquidity Sweep Rejection",
                detected=True,
                direction=sweep_dir,  # type: ignore[arg-type]
                reference_price=sweep_level,
                cutoff_date=cutoff,
                invalidation_level=float(latest["low"]) if sweep_dir == "BULLISH" else float(latest["high"]),
                description=f"Liquidity pool at Rp {sweep_level:,.0f} was swept and immediately rejected.",
            )
        )

    # 4. Order block approximation (last opposite candle before displacement)
    ob_top = swing_high * 0.98
    ob_bottom = swing_high * 0.95

    return ICTStructureSummary(
        ticker=ticker,
        as_of_date=cutoff,
        swing_high=swing_high,
        swing_low=swing_low,
        market_structure_state=mss_state,
        fair_value_gap_present=fvg_present,
        fvg_zone_top=fvg_top,
        fvg_zone_bottom=fvg_bottom,
        liquidity_sweep_detected=sweep_present,
        order_block_zone_top=ob_top,
        order_block_zone_bottom=ob_bottom,
        zone_classification=zone,
        hypotheses=hypotheses,
    )
