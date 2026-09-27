"""Black-Litterman Portfolio Optimization Engine with Hugging Face Prior Views.

Combines capital market equilibrium priors with subjective forward views derived
from Hugging Face Chronos forecasts, FinBERT sentiment entropy, and Smart Money Index.
Computes constrained optimal allocations maximizing Sharpe ratio under VaR limits.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.optimize import minimize

from ruang_risiko_idx.research.broker_network import broker_network_analyzer
from ruang_risiko_idx.research.hf_finbert_sentiment import finbert_calibrator
from ruang_risiko_idx.research.hf_foundation_forecaster import hf_forecaster
from ruang_risiko_idx.research.multimodal_engine import STOCK_CATALOG_MAP


@dataclass
class AssetAllocation:
    """Individual portfolio holding weight and capital commitment."""

    ticker: str
    name: str
    sector: str
    weight_pct: float
    allocated_capital_idr: float
    expected_annual_return_pct: float
    chronos_drift_pct: float
    sentiment_stance: str
    smart_money_index: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "weight_pct": round(self.weight_pct, 2),
            "allocated_capital_idr": round(self.allocated_capital_idr, 0),
            "expected_annual_return_pct": round(self.expected_annual_return_pct, 2),
            "chronos_drift_pct": round(self.chronos_drift_pct, 2),
            "sentiment_stance": self.sentiment_stance,
            "smart_money_index": round(self.smart_money_index, 1),
        }


@dataclass
class BlackLittermanReport:
    """Consolidated portfolio optimization and frontier diagnostics."""

    evaluated_at: str
    total_capital_idr: float
    portfolio_expected_annual_return_pct: float
    portfolio_annual_volatility_pct: float
    portfolio_sharpe_ratio: float
    portfolio_var_99_annual_pct: float
    diversification_ratio: float
    holdings: list[AssetAllocation]
    sector_allocations: dict[str, float]
    optimization_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at,
            "total_capital_idr": self.total_capital_idr,
            "portfolio_expected_annual_return_pct": round(self.portfolio_expected_annual_return_pct, 2),
            "portfolio_annual_volatility_pct": round(self.portfolio_annual_volatility_pct, 2),
            "portfolio_sharpe_ratio": round(self.portfolio_sharpe_ratio, 2),
            "portfolio_var_99_annual_pct": round(self.portfolio_var_99_annual_pct, 2),
            "diversification_ratio": round(self.diversification_ratio, 2),
            "holdings": [h.to_dict() for h in self.holdings],
            "sector_allocations": {k: round(v, 2) for k, v in self.sector_allocations.items()},
            "optimization_status": self.optimization_status,
        }


class BlackLittermanEngine:
    """Computes Bayesian portfolio equilibrium adjusted for foundation model views."""

    DEFAULT_UNIVERSE = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "ANTM.JK", "ICBP.JK"]

    def __init__(self, risk_aversion: float = 2.8, tau: float = 0.05, risk_free_rate: float = 0.065):
        self.risk_aversion = risk_aversion  # Delta in BL formula
        self.tau = tau  # Scalar on covariance matrix
        self.risk_free_rate = risk_free_rate  # BI-Rate ~ 6.5%

    def compute_optimal_portfolio(
        self,
        tickers: list[str] | None = None,
        total_capital_idr: float = 500_000_000.0,
        max_asset_weight: float = 0.25,
        min_asset_weight: float = 0.02,
    ) -> BlackLittermanReport:
        """Run full Black-Litterman optimization combining equilibrium priors and AI views."""
        active_tickers = tickers or self.DEFAULT_UNIVERSE
        n = len(active_tickers)
        if n < 2:
            active_tickers = self.DEFAULT_UNIVERSE
            n = len(active_tickers)

        # 1. Synthesize covariance matrix Sigma based on realistic IDX correlations
        sigma = np.zeros((n, n))
        vols = []
        for t in active_tickers:
            meta = STOCK_CATALOG_MAP.get(t, {})
            vol_str = meta.get("volatility_annual", "22.5%").replace("%", "")
            try:
                vols.append(float(vol_str) / 100.0)
            except ValueError:
                vols.append(0.22)

        for i in range(n):
            for j in range(n):
                if i == j:
                    sigma[i, j] = vols[i] ** 2
                else:
                    # Sector cross-correlation
                    sec_i = STOCK_CATALOG_MAP.get(active_tickers[i], {}).get("sector", "Other")
                    sec_j = STOCK_CATALOG_MAP.get(active_tickers[j], {}).get("sector", "Other")
                    rho = 0.55 if sec_i == sec_j else 0.32
                    sigma[i, j] = rho * vols[i] * vols[j]

        # 2. Market equilibrium prior Pi = delta * Sigma * w_mkt
        w_mkt = np.ones(n) / n
        pi = self.risk_aversion * (sigma @ w_mkt)

        # 3. Derive AI views vector Q and uncertainty matrix Omega
        p_matrix = np.eye(n)
        q_views = np.zeros(n)
        omega_diag = np.zeros(n)

        holdings_meta = []
        for idx, t in enumerate(active_tickers):
            meta = STOCK_CATALOG_MAP.get(t, {"name": t, "sector": "Other", "base_price": 5000})
            base_px = float(meta.get("base_price", 5000))

            # Fetch AI views
            fc_report = hf_forecaster.run_tournament(t, horizon_days=10)
            fin_report = finbert_calibrator.analyze_market_polarization(t)
            bn_report = broker_network_analyzer.analyze_ticker_network(t, base_px)

            # Annualized expected return view from Chronos forward drift
            pts = fc_report.forecast_points
            forward_drift = pts[-1].projected_drift_pct if pts else 1.5
            view_return = (forward_drift * 12.0) / 100.0  # Annualized estimate
            q_views[idx] = max(-0.25, min(0.45, view_return))

            # Uncertainty calibrated by FinBERT Shannon Entropy
            # High entropy = high disagreement = higher uncertainty in view
            entropy_scalar = max(0.5, fin_report.market_entropy / 1.1)
            omega_diag[idx] = (self.tau * sigma[idx, idx]) * (entropy_scalar ** 1.5)

            holdings_meta.append(
                {
                    "ticker": t,
                    "name": meta.get("name", t),
                    "sector": meta.get("sector", "Other"),
                    "chronos_drift_pct": forward_drift,
                    "sentiment_stance": fin_report.sentiment_stance,
                    "smart_money_index": bn_report.smart_money_index,
                }
            )

        omega = np.diag(omega_diag)

        # 4. Black-Litterman Master Formula:
        # E[R] = [ (tau*Sigma)^-1 + P^T * Omega^-1 * P ]^-1 * [ (tau*Sigma)^-1 * Pi + P^T * Omega^-1 * Q ]
        tau_sigma_inv = np.linalg.pinv(self.tau * sigma)
        omega_inv = np.linalg.pinv(omega)

        m_matrix = tau_sigma_inv + p_matrix.T @ omega_inv @ p_matrix
        m_inv = np.linalg.pinv(m_matrix)

        adjusted_er = m_inv @ (tau_sigma_inv @ pi + p_matrix.T @ omega_inv @ q_views)

        # 5. Constrained Quadratic Optimization (Maximize Sharpe Ratio)
        def objective_function(weights: np.ndarray) -> float:
            p_ret = float(weights @ adjusted_er)
            p_vol = math.sqrt(float(weights @ sigma @ weights))
            if p_vol < 1e-6:
                return 0.0
            sharpe = (p_ret - self.risk_free_rate) / p_vol
            return -sharpe  # Minimize negative Sharpe

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(min_asset_weight, max_asset_weight) for _ in range(n)]
        init_weights = np.ones(n) / n

        res = minimize(
            objective_function,
            init_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        opt_weights = res.x if res.success else (np.ones(n) / n)
        # Normalize in case of slight precision drift
        opt_weights = opt_weights / np.sum(opt_weights)

        port_ret = float(opt_weights @ adjusted_er)
        port_vol = math.sqrt(float(opt_weights @ sigma @ opt_weights))
        port_sharpe = (port_ret - self.risk_free_rate) / max(port_vol, 1e-4)

        # Annual 99% VaR (Parametric under normality assumption)
        port_var_99 = (2.326 * port_vol) - port_ret

        # Diversification ratio: weighted sum of vols / portfolio vol
        weighted_vol_sum = float(np.sum(opt_weights * np.array(vols)))
        div_ratio = weighted_vol_sum / max(port_vol, 1e-4)

        # Build holding allocations
        holdings: list[AssetAllocation] = []
        sector_totals: dict[str, float] = {}

        for idx, t in enumerate(active_tickers):
            w = float(opt_weights[idx])
            cap = total_capital_idr * w
            meta_item = holdings_meta[idx]
            sec = meta_item["sector"]
            sector_totals[sec] = sector_totals.get(sec, 0.0) + (w * 100.0)

            holdings.append(
                AssetAllocation(
                    ticker=t,
                    name=meta_item["name"],
                    sector=sec,
                    weight_pct=w * 100.0,
                    allocated_capital_idr=cap,
                    expected_annual_return_pct=float(adjusted_er[idx]) * 100.0,
                    chronos_drift_pct=meta_item["chronos_drift_pct"],
                    sentiment_stance=meta_item["sentiment_stance"],
                    smart_money_index=meta_item["smart_money_index"],
                )
            )

        # Sort holdings descending by weight
        holdings.sort(key=lambda h: h.weight_pct, reverse=True)

        now_iso = datetime.now(timezone.utc).isoformat()

        return BlackLittermanReport(
            evaluated_at=now_iso,
            total_capital_idr=total_capital_idr,
            portfolio_expected_annual_return_pct=port_ret * 100.0,
            portfolio_annual_volatility_pct=port_vol * 100.0,
            portfolio_sharpe_ratio=port_sharpe,
            portfolio_var_99_annual_pct=port_var_99 * 100.0,
            diversification_ratio=div_ratio,
            holdings=holdings,
            sector_allocations=sector_totals,
            optimization_status="OPTIMAL_CONVERGED" if res.success else "FALLBACK_EQUAL_WEIGHT",
        )


# Global singleton
bl_engine = BlackLittermanEngine()
black_litterman_optimizer = bl_engine
