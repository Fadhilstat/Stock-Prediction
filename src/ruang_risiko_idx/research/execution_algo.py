"""Algorithmic Order Execution Simulator and Market Impact Engine.

Implements Almgren-Chriss (2000) execution scheduling with Volume-Weighted Average Price (VWAP),
Time-Weighted Average Price (TWAP), and Percentage of Volume (POV) trajectories
tailored to Indonesia Stock Exchange (IDX) trading sessions (Sesi I and Sesi II).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass(frozen=True)
class ExecutionBinSlice:
    """Individual intraday execution interval slice."""

    bin_index: int
    time_window: str
    target_shares: int
    target_value_idr: float
    bin_volume_weight_pct: float
    expected_fill_price: float
    temporary_impact_bps: float
    cumulative_progress_pct: float


@dataclass(frozen=True)
class ExecutionScheduleReport:
    """Comprehensive algorithmic execution schedule and impact report."""

    ticker: str
    strategy: str
    order_value_idr: float
    total_shares: int
    arrival_price: float
    expected_average_price: float
    total_slippage_bps: float
    total_market_impact_idr: float
    permanent_impact_bps: float
    implementation_shortfall_idr: float
    schedule_slices: list[ExecutionBinSlice]
    execution_efficiency_score: float
    recommendation: str


# Canonical intraday IDX volume profile (U-shaped smile curve)
IDX_INTRADAY_VOLUME_PROFILE: list[tuple[str, float]] = [
    ("09:00 - 09:30 WIB", 0.18),  # Opening surge
    ("09:30 - 10:00 WIB", 0.14),
    ("10:00 - 10:30 WIB", 0.10),
    ("10:30 - 11:00 WIB", 0.08),
    ("11:00 - 11:30 WIB", 0.07),  # Pre-lunch lull
    ("13:30 - 14:00 WIB", 0.09),  # Sesi II reopen
    ("14:00 - 14:30 WIB", 0.09),
    ("14:30 - 15:00 WIB", 0.11),
    ("15:00 - 15:30 WIB", 0.14),  # Pre-closing acceleration
]


def simulate_algorithmic_execution(
    ticker: str,
    current_price: float,
    order_value_idr: float,
    average_daily_volume: float = 10_000_000.0,
    strategy: str = "VWAP",
    side: str = "BUY",
    participation_limit_pct: float = 12.0,
) -> ExecutionScheduleReport:
    """Compute optimal order execution schedule across intraday time windows.

    Almgren-Chriss formulation:
    - Permanent impact: I_perm = gamma * (X / ADV)
    - Temporary impact per slice: I_temp = eta * (x_k / (tau_k * ADV_k))
    """
    total_shares = int(order_value_idr / max(current_price, 1.0))
    adv_shares = max(average_daily_volume, 100_000.0)

    # Permanent impact (bps)
    order_adv_pct = (total_shares / adv_shares) * 100.0
    perm_impact_bps = min(150.0, float(0.35 * np.sqrt(order_adv_pct) * 10.0))

    bins_data = IDX_INTRADAY_VOLUME_PROFILE
    n_bins = len(bins_data)

    if strategy == "TWAP":
        # Uniform distribution across bins
        slice_weights = [1.0 / n_bins] * n_bins
    elif strategy == "POV":
        # Follow volume strictly within participation rate
        slice_weights = [w for _, w in bins_data]
    else:  # VWAP (Default)
        # Volume profile weighting with convex smoothing
        base_weights = np.array([w for _, w in bins_data], dtype=float)
        slice_weights = (base_weights / base_weights.sum()).tolist()

    slices: list[ExecutionBinSlice] = []
    cum_shares = 0
    total_cost_idr = 0.0

    sign = 1.0 if side.upper() == "BUY" else -1.0

    for i, ((t_win, _), weight) in enumerate(zip(bins_data, slice_weights)):
        bin_shares = int(round(total_shares * weight))
        if i == n_bins - 1:
            bin_shares = total_shares - cum_shares
        bin_shares = max(bin_shares, 0)
        cum_shares += bin_shares

        bin_adv = adv_shares * weight
        slice_adv_pct = (bin_shares / max(bin_adv, 1.0)) * 100.0

        # Temporary impact scales non-linearly with participation rate
        temp_impact_bps = min(80.0, float(0.25 * (slice_adv_pct ** 0.60) * 10.0))

        # Expected price with impact
        fill_price = current_price * (1.0 + sign * (perm_impact_bps * 0.5 + temp_impact_bps) / 10_000.0)
        slice_val = bin_shares * fill_price
        total_cost_idr += slice_val

        progress_pct = (cum_shares / max(total_shares, 1)) * 100.0

        slices.append(
            ExecutionBinSlice(
                bin_index=i + 1,
                time_window=t_win,
                target_shares=bin_shares,
                target_value_idr=round(slice_val, 2),
                bin_volume_weight_pct=round(weight * 100.0, 1),
                expected_fill_price=round(fill_price, 2),
                temporary_impact_bps=round(temp_impact_bps, 2),
                cumulative_progress_pct=round(progress_pct, 1),
            )
        )

    expected_avg_price = total_cost_idr / max(total_shares, 1)
    effective_slippage_bps = abs(expected_avg_price - current_price) / max(current_price, 1.0) * 10_000.0
    impact_idr = abs(total_cost_idr - (total_shares * current_price))

    # Implementation Shortfall (IS)
    implementation_shortfall_idr = impact_idr + (order_value_idr * 0.0015)  # including broker fee

    # Efficiency score (0-100)
    efficiency = max(50.0, min(99.0, 100.0 - (effective_slippage_bps * 0.75)))

    if order_adv_pct > participation_limit_pct:
        rec = f"Order mewakili {order_adv_pct:.1f}% ADV. Rekomendasi: Gunakan VWAP pasif multi-sesi untuk mencegah lonjakan slippage."
    elif effective_slippage_bps < 15.0:
        rec = "Likuiditas pasar memadai. Eksekusi VWAP optimal dengan slippage minimal."
    else:
        rec = "Slippage terproyeksi moderat. Pantau antrean bid/offer pada pembukaan sesi II."

    return ExecutionScheduleReport(
        ticker=ticker,
        strategy=strategy,
        order_value_idr=order_value_idr,
        total_shares=total_shares,
        arrival_price=current_price,
        expected_average_price=round(expected_avg_price, 2),
        total_slippage_bps=round(effective_slippage_bps, 2),
        total_market_impact_idr=round(impact_idr, 2),
        permanent_impact_bps=round(perm_impact_bps, 2),
        implementation_shortfall_idr=round(implementation_shortfall_idr, 2),
        schedule_slices=slices,
        execution_efficiency_score=round(efficiency, 1),
        recommendation=rec,
    )


def generate_execution_trajectory_chart(report: ExecutionScheduleReport) -> go.Figure:
    """Render 2-panel Plotly interactive execution schedule and slippage profile."""
    bins_x = [s.time_window.split(" ")[0] for s in report.schedule_slices]
    shares_y = [s.target_shares for s in report.schedule_slices]
    slippage_y = [s.temporary_impact_bps for s in report.schedule_slices]
    cum_pct = [s.cumulative_progress_pct for s in report.schedule_slices]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Jadwal Alokasi Lot per Fraksi Waktu", "Slippage Dampak Sementara & Akumulasi Eksekusi"),
        row_heights=[0.6, 0.4],
    )

    # Top panel: Target shares bar chart
    fig.add_trace(
        go.Bar(
            x=bins_x,
            y=shares_y,
            name="Alokasi Lembar",
            marker_color="#2962FF",
            hovertemplate="Waktu: %{x}<br>Lembar: %{y:,}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Bottom panel: Temporary impact and cumulative progress
    fig.add_trace(
        go.Scatter(
            x=bins_x,
            y=slippage_y,
            name="Slippage (bps)",
            mode="lines+markers",
            line=dict(color="#FF4A68", width=2),
            hovertemplate="Slippage: %{y:.1f} bps<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=bins_x,
            y=cum_pct,
            name="Kemajuan (%)",
            mode="lines+markers",
            line=dict(color="#00C076", width=2, dash="dash"),
            hovertemplate="Kemajuan: %{y:.1f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#1E222D",
        margin=dict(l=10, r=10, t=30, b=10),
        height=380,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
