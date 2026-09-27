"""Multi-Objective Pareto Portfolio Optimization Engine.

Generates the Mean-CVaR efficient frontier with Diversification Entropy regularization,
solving for optimal non-dominated asset weight allocations across IDX equities
to avoid corner solutions and mitigate severe tail risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import optimize


@dataclass(frozen=True)
class ParetoFrontierPoint:
    """Individual non-dominated portfolio allocation on the efficient frontier."""

    point_id: int
    expected_annual_return_pct: float
    cvar_99_annual_loss_pct: float
    volatility_annual_pct: float
    sharpe_ratio: float
    diversification_entropy: float
    weights: dict[str, float]


@dataclass(frozen=True)
class ParetoPortfolioReport:
    """Complete multi-objective portfolio optimization solution."""

    tickers: list[str]
    frontier_points: list[ParetoFrontierPoint]
    optimal_tangency_point: ParetoFrontierPoint
    minimum_cvar_point: ParetoFrontierPoint
    diversification_gain_pct: float
    as_of_date: str
    recommendation: str


def compute_portfolio_cvar_99(weights: np.ndarray, returns_matrix: np.ndarray, alpha: float = 0.99) -> float:
    """Compute 99% Expected Shortfall (CVaR) of portfolio returns."""
    port_rets = np.dot(returns_matrix, weights)
    losses = -port_rets
    var_threshold = float(np.percentile(losses, alpha * 100.0))
    tail_losses = losses[losses >= var_threshold]
    return float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_threshold


def optimize_pareto_portfolio_frontier(
    price_df: pd.DataFrame,
    tickers: list[str] | None = None,
    num_points: int = 15,
    risk_free_rate_pct: float = 6.0,
    entropy_penalty: float = 0.005,
) -> ParetoPortfolioReport:
    """Generate multi-objective Pareto optimal frontier balancing Return, CVaR, and Entropy."""
    if price_df.empty:
        from ruang_risiko_idx.config import ProjectSettings

        raw_p = ProjectSettings().raw_data_path
        if raw_p.exists():
            price_df = pd.read_parquet(raw_p)

    pivot_df = price_df.pivot(index="trade_date", columns="ticker", values="close").ffill().bfill()
    valid_cols = [c for c in (tickers or list(pivot_df.columns)) if c in pivot_df.columns]
    if len(valid_cols) < 2:
        valid_cols = list(pivot_df.columns)[:4]

    returns_df = pivot_df[valid_cols].pct_change().dropna().tail(252)
    rets_matrix = returns_df.to_numpy(dtype=float)
    mean_daily = np.mean(rets_matrix, axis=0)
    k = len(valid_cols)

    # Constraints: sum(w) = 1, 0 <= w_i <= 0.40 (prevent single asset domination)
    bounds = [(0.02, 0.40) for _ in range(k)]
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)

    # 1. Find Minimum CVaR portfolio
    def obj_min_cvar(w: np.ndarray) -> float:
        entropy = -np.sum(w * np.log(np.maximum(w, 1e-8)))
        return compute_portfolio_cvar_99(w, rets_matrix) - entropy_penalty * entropy

    w0 = np.ones(k) / k
    res_min = optimize.minimize(obj_min_cvar, w0, method="SLSQP", bounds=bounds, constraints=cons)
    w_min = res_min.x if res_min.success else w0

    # 2. Find Maximum Return portfolio
    def obj_max_ret(w: np.ndarray) -> float:
        return -float(np.dot(w, mean_daily))

    res_max = optimize.minimize(obj_max_ret, w0, method="SLSQP", bounds=bounds, constraints=cons)
    w_max = res_max.x if res_max.success else w0

    min_ret = float(np.dot(w_min, mean_daily))
    max_ret = float(np.dot(w_max, mean_daily))

    target_returns = np.linspace(min_ret, max_ret, num_points)
    frontier_points: list[ParetoFrontierPoint] = []

    rf_daily = (risk_free_rate_pct / 100.0) / 252.0

    for idx, target_r in enumerate(target_returns):
        target_cons = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, tr=target_r: float(np.dot(w, mean_daily)) - tr},
        )
        res_p = optimize.minimize(obj_min_cvar, w0, method="SLSQP", bounds=bounds, constraints=target_cons)
        w_p = res_p.x if res_p.success else w0
        w_p = np.maximum(w_p, 0.0)
        w_p /= np.sum(w_p)

        ann_ret = float(np.dot(w_p, mean_daily) * 252.0 * 100.0)
        daily_cvar = compute_portfolio_cvar_99(w_p, rets_matrix)
        ann_cvar = float(daily_cvar * np.sqrt(252.0) * 100.0)
        port_std = float(np.std(np.dot(rets_matrix, w_p)) * np.sqrt(252.0) * 100.0)
        entropy = float(-np.sum(w_p * np.log(np.maximum(w_p, 1e-8))))

        sharpe = (ann_ret - risk_free_rate_pct) / max(port_std, 1e-4)

        w_dict = {valid_cols[i]: round(float(w_p[i] * 100.0), 1) for i in range(k)}

        frontier_points.append(
            ParetoFrontierPoint(
                point_id=idx + 1,
                expected_annual_return_pct=round(ann_ret, 2),
                cvar_99_annual_loss_pct=round(ann_cvar, 2),
                volatility_annual_pct=round(port_std, 2),
                sharpe_ratio=round(sharpe, 2),
                diversification_entropy=round(entropy, 3),
                weights=w_dict,
            )
        )

    # Identify Tangency Portfolio (maximum Sharpe)
    sorted_sharpe = sorted(frontier_points, key=lambda p: p.sharpe_ratio, reverse=True)
    optimal_tangency = sorted_sharpe[0]
    min_cvar_pt = sorted(frontier_points, key=lambda p: p.cvar_99_annual_loss_pct)[0]

    # Calculate diversification gain vs naive 1/N
    w_equal = np.ones(k) / k
    cvar_equal = compute_portfolio_cvar_99(w_equal, rets_matrix) * np.sqrt(252.0) * 100.0
    div_gain = max(0.0, float((cvar_equal - optimal_tangency.cvar_99_annual_loss_pct) / max(cvar_equal, 1e-4) * 100.0))

    as_of = str(returns_df.index[-1])[:10] if not returns_df.empty else "2026-09-25"
    rec = (
        f"Alokasi Pareto Tangency menghasilkan Sharpe {optimal_tangency.sharpe_ratio:.2f} "
        f"dengan reduksi tail risk {div_gain:.1f}% dibandingkan bobot setara (1/N)."
    )

    return ParetoPortfolioReport(
        tickers=valid_cols,
        frontier_points=frontier_points,
        optimal_tangency_point=optimal_tangency,
        minimum_cvar_point=min_cvar_pt,
        diversification_gain_pct=round(div_gain, 1),
        as_of_date=as_of,
        recommendation=rec,
    )


def generate_pareto_frontier_chart(report: ParetoPortfolioReport) -> go.Figure:
    """Render interactive Plotly Pareto Efficient Frontier (Return vs CVaR 99%)."""
    cvar_x = [p.cvar_99_annual_loss_pct for p in report.frontier_points]
    ret_y = [p.expected_annual_return_pct for p in report.frontier_points]
    sharpe_vals = [p.sharpe_ratio for p in report.frontier_points]

    fig = go.Figure()

    # Efficient frontier curve
    fig.add_trace(
        go.Scatter(
            x=cvar_x,
            y=ret_y,
            mode="lines+markers",
            name="Frontier Mean-CVaR",
            line=dict(color="#2962FF", width=2.5, shape="spline"),
            marker=dict(
                size=8,
                color=sharpe_vals,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title=dict(text="Sharpe", side="top", font=dict(color="#D1D4DC", size=10)), len=0.8),
            ),
            hovertemplate="Tail Loss (CVaR): -%{x:.1f}%<br>Imbal Hasil: +%{y:.1f}%<extra></extra>",
        )
    )

    # Highlight Optimal Tangency Point
    opt = report.optimal_tangency_point
    fig.add_trace(
        go.Scatter(
            x=[opt.cvar_99_annual_loss_pct],
            y=[opt.expected_annual_return_pct],
            mode="markers+text",
            name="Tangency Maksimal Sharpe",
            marker=dict(size=14, color="#00C076", symbol="star"),
            text=["Tangency Optimal"],
            textposition="top right",
            textfont=dict(color="#00C076", size=11),
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#1E222D",
        margin=dict(l=10, r=10, t=30, b=10),
        height=380,
        xaxis=dict(title="Expected Shortfall Tahunan CVaR 99% (Beban Risiko Ekor)", gridcolor="#2A2E39"),
        yaxis=dict(title="Ekspektasi Imbal Hasil Tahunan (%)", gridcolor="#2A2E39"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
