"""IHSG benchmark context, sector intelligence, and market alignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MarketAlignmentSummary:
    """Stock vs Sector vs IHSG benchmark alignment."""

    ticker: str
    benchmark_ticker: str
    rolling_beta_60d: float
    rolling_correlation_60d: float
    stock_return_20d: float
    ihsg_return_20d: float
    relative_strength_20d: float
    alignment_state: Literal[
        "ALIGNED_POSITIVE",
        "PARTIAL_POSITIVE",
        "MIXED",
        "PARTIAL_NEGATIVE",
        "ALIGNED_NEGATIVE",
    ]
    alignment_reasoning: str


def compute_market_alignment(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    ticker: str,
    benchmark_ticker: str = "^JKSE",
) -> MarketAlignmentSummary:
    """Compute rolling beta, correlation, and market alignment against IHSG."""
    stock = stock_df.sort_values("trade_date").set_index("trade_date")
    bench = benchmark_df.sort_values("trade_date").set_index("trade_date")

    merged = pd.DataFrame(
        {
            "stock_close": stock["adjusted_close"],
            "bench_close": bench["adjusted_close"],
        }
    ).dropna()

    if len(merged) < 25:
        return MarketAlignmentSummary(
            ticker=ticker,
            benchmark_ticker=benchmark_ticker,
            rolling_beta_60d=1.0,
            rolling_correlation_60d=0.5,
            stock_return_20d=0.0,
            ihsg_return_20d=0.0,
            relative_strength_20d=0.0,
            alignment_state="MIXED",
            alignment_reasoning="Insufficient overlapping trading history for robust alignment.",
        )

    merged["stock_ret"] = np.log(merged["stock_close"]).diff()
    merged["bench_ret"] = np.log(merged["bench_close"]).diff()
    merged = merged.dropna()

    # 60-day rolling beta and correlation
    recent = merged.tail(60)
    cov = float(recent["stock_ret"].cov(recent["bench_ret"]))
    bench_var = float(recent["bench_ret"].var())
    beta = cov / bench_var if bench_var > 0 else 1.0
    corr = float(recent["stock_ret"].corr(recent["bench_ret"]))

    # 20-day returns
    stock_ret_20d = float(
        merged["stock_close"].iloc[-1] / merged["stock_close"].iloc[-20] - 1.0
    ) if len(merged) >= 20 else 0.0

    bench_ret_20d = float(
        merged["bench_close"].iloc[-1] / merged["bench_close"].iloc[-20] - 1.0
    ) if len(merged) >= 20 else 0.0

    relative_strength = stock_ret_20d - bench_ret_20d

    if stock_ret_20d > 0.02 and bench_ret_20d > 0.01:
        state = "ALIGNED_POSITIVE"
        reason = "Both stock and IHSG benchmark are advancing with positive relative strength."
    elif stock_ret_20d > 0.0 and bench_ret_20d <= 0.0:
        state = "PARTIAL_POSITIVE"
        reason = "Stock is showing idiosyncratic resilience despite weak or negative IHSG context."
    elif stock_ret_20d < -0.02 and bench_ret_20d < -0.01:
        state = "ALIGNED_NEGATIVE"
        reason = "Stock and IHSG are both in synchronized decline, elevating market-wide drawdown risk."
    elif stock_ret_20d < 0.0 and bench_ret_20d >= 0.0:
        state = "PARTIAL_NEGATIVE"
        reason = "Stock is lagging and underperforming while the broader market benchmark holds firm."
    else:
        state = "MIXED"
        reason = "Balanced or range-bound moves across stock and benchmark without clear directional trend."

    return MarketAlignmentSummary(
        ticker=ticker,
        benchmark_ticker=benchmark_ticker,
        rolling_beta_60d=beta,
        rolling_correlation_60d=corr,
        stock_return_20d=stock_ret_20d,
        ihsg_return_20d=bench_ret_20d,
        relative_strength_20d=relative_strength,
        alignment_state=state,
        alignment_reasoning=reason,
    )
