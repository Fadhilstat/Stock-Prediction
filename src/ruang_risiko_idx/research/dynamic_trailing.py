"""GARCH-ATR Dynamic Trailing Boundary and Volatility Ratchet Engine.

Dynamically adapts position stop-loss thresholds using conditional GARCH variance
and Average True Range (ATR), ratcheting stops upward as price surpasses median targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass(frozen=True)
class DynamicTrailingSnapshot:
    """Quantitative trailing stop state for an active position."""

    ticker: str
    entry_price: float
    current_price: float
    unrealized_return_pct: float
    static_invalidation_price: float
    dynamic_trailing_stop_price: float
    ratchet_stage: Literal["INITIAL_DEFENSE", "BREAKEVEN_LOCKED", "PROFIT_PROTECTION", "TRAILING_TIGHT"]
    atr_14: float
    garch_vol_ratio: float
    distance_to_stop_pct: float
    is_breached: bool
    ratchet_rationale: str


def compute_dynamic_trailing_boundary(
    ticker: str,
    entry_price: float,
    current_price: float,
    highest_price_since_entry: float,
    static_invalidation: float,
    target_q50: float,
    daily_garch_vol: float,
    unconditional_vol: float = 0.020,
    atr_14: float | None = None,
    atr_multiplier: float = 2.0,
) -> DynamicTrailingSnapshot:
    """Calculate dynamic trailing stop with volatility-adjusted ratchet mechanics."""
    # Derived ATR if not explicitly provided
    if atr_14 is None:
        effective_atr = current_price * daily_garch_vol * 1.25
    else:
        effective_atr = atr_14

    # Volatility expansion multiplier (widens in high turbulence, tightens in low vol)
    vol_ratio = float(daily_garch_vol / max(1e-4, unconditional_vol))
    vol_scaling = float(np.clip(np.sqrt(vol_ratio), 0.75, 1.50))
    buffer_distance = effective_atr * atr_multiplier * vol_scaling

    unrealized_return = (current_price / entry_price - 1.0) * 100.0

    # Determine ratchet stage
    # Stage 1: Price below median target q50
    if highest_price_since_entry < target_q50:
        raw_stop = highest_price_since_entry - buffer_distance
        trailing_stop = max(static_invalidation, raw_stop)
        stage: Literal["INITIAL_DEFENSE", "BREAKEVEN_LOCKED", "PROFIT_PROTECTION", "TRAILING_TIGHT"] = "INITIAL_DEFENSE"
        rationale = "Posisi masih dalam fase pertahanan awal; batas stop berlabuh pada invalidasi keras."
    # Stage 2: Price surpassed target q50 but unrealized gain < 8%
    elif unrealized_return < 8.0:
        breakeven_plus_fee = entry_price * 1.005  # lock in 0.5% to cover broker fees
        raw_stop = highest_price_since_entry - buffer_distance
        trailing_stop = max(breakeven_plus_fee, raw_stop)
        stage = "BREAKEVEN_LOCKED"
        rationale = "Target q50 terlampaui; batas stop dinaikkan untuk mengunci modal awal dan biaya broker."
    # Stage 3: Unrealized gain between 8% and 15%
    elif unrealized_return < 15.0:
        lock_in_level = entry_price * 1.04  # lock in 4% profit
        raw_stop = highest_price_since_entry - (buffer_distance * 0.85)
        trailing_stop = max(lock_in_level, raw_stop)
        stage = "PROFIT_PROTECTION"
        rationale = "Keuntungan berjalan menguat; batas stop dinaikkan mengunci minimal 4% laba portofolio."
    # Stage 4: Strong trend run (>15% gain)
    else:
        lock_in_level = highest_price_since_entry * 0.93  # lock in within 7% of high
        raw_stop = highest_price_since_entry - (buffer_distance * 0.70)
        trailing_stop = max(lock_in_level, raw_stop)
        stage = "TRAILING_TIGHT"
        rationale = "Tren super-kuat (>15%); trailing stop diperketat menjaga keuntungan maksimal."

    # Round to nearest integer IDR price
    final_stop = round(float(trailing_stop))
    distance_pct = float((current_price - final_stop) / current_price * 100.0)
    is_breached = bool(current_price <= final_stop)

    return DynamicTrailingSnapshot(
        ticker=ticker,
        entry_price=round(entry_price),
        current_price=round(current_price),
        unrealized_return_pct=round(unrealized_return, 2),
        static_invalidation_price=round(static_invalidation),
        dynamic_trailing_stop_price=final_stop,
        ratchet_stage=stage,
        atr_14=round(effective_atr, 1),
        garch_vol_ratio=round(vol_ratio, 2),
        distance_to_stop_pct=round(distance_pct, 2),
        is_breached=is_breached,
        ratchet_rationale=rationale,
    )
