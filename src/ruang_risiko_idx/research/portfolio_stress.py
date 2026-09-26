"""Multivariate Portfolio Stress Testing and Historical Crash Replay Engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalCrashScenario:
    """Historical systemic liquidity and macroeconomic crisis profile."""

    scenario_id: str
    title: str
    description: str
    duration_days: int
    ihsg_shock_percent: float
    asset_shocks: dict[str, float]


HISTORICAL_CRASH_SCENARIOS: list[HistoricalCrashScenario] = [
    HistoricalCrashScenario(
        scenario_id="PANDEMIC_CIRCUIT_BREAKER_2020",
        title="Krisis Pandemi & Circuit Breaker (Maret 2020)",
        description="Pelepasan aset agresif global memicu pembekuan perdagangan harian (trading halt) berulang di BEI.",
        duration_days=20,
        ihsg_shock_percent=-26.5,
        asset_shocks={
            "BBCA.JK": -21.4,
            "BBRI.JK": -34.8,
            "TLKM.JK": -18.2,
            "ASII.JK": -32.6,
            "ANTM.JK": -38.5,
            "^JKSE": -26.5,
        },
    ),
    HistoricalCrashScenario(
        scenario_id="TAPER_TANTRUM_2013",
        title="Taper Tantrum & Depresiasi Rupiah (2013)",
        description="Lonjakan imbal hasil US Treasury memicu arus keluar modal asing masif dari obligasi dan saham Indonesia.",
        duration_days=45,
        ihsg_shock_percent=-22.0,
        asset_shocks={
            "BBCA.JK": -19.5,
            "BBRI.JK": -28.0,
            "TLKM.JK": -15.4,
            "ASII.JK": -25.2,
            "ANTM.JK": -31.0,
            "^JKSE": -22.0,
        },
    ),
    HistoricalCrashScenario(
        scenario_id="COMMODITY_CRASH_2015",
        title="Pembalikan Super-Siklus Komoditas (2015)",
        description="Kejatuhan harga batubara, nikel, dan minyak global menekan pendapatan emiten komoditas dan industri pendukung.",
        duration_days=60,
        ihsg_shock_percent=-16.8,
        asset_shocks={
            "BBCA.JK": -12.0,
            "BBRI.JK": -16.5,
            "TLKM.JK": -8.5,
            "ASII.JK": -28.4,
            "ANTM.JK": -46.2,
            "^JKSE": -16.8,
        },
    ),
]


@dataclass(frozen=True)
class PortfolioStressResult:
    """Stress test simulation evaluation report."""

    scenario_id: str
    scenario_title: str
    portfolio_weights: dict[str, float]
    total_portfolio_value_idr: float
    portfolio_loss_percent: float
    monetary_loss_idr: float
    worst_asset: str
    worst_asset_loss_percent: float
    best_asset: str
    best_asset_loss_percent: float
    var_99_loss_percent: float
    cvar_expected_shortfall_percent: float
    margin_call_risk: bool
    survival_recommendation: str


def get_available_stress_scenarios() -> list[HistoricalCrashScenario]:
    """Return all registered historical crisis scenarios."""
    return list(HISTORICAL_CRASH_SCENARIOS)


def run_portfolio_stress_test(
    portfolio_weights: dict[str, float],
    total_portfolio_value_idr: float,
    scenario_id: str = "PANDEMIC_CIRCUIT_BREAKER_2020",
) -> PortfolioStressResult:
    """Replay historical crash scenario on custom portfolio allocation."""
    scenario = next(
        (s for s in HISTORICAL_CRASH_SCENARIOS if s.scenario_id == scenario_id),
        HISTORICAL_CRASH_SCENARIOS[0],
    )

    # Normalize weights so sum equals 1.0
    raw_total_w = sum(portfolio_weights.values())
    norm_w = {k: v / raw_total_w for k, v in portfolio_weights.items()} if raw_total_w > 0 else {}

    weighted_loss = 0.0
    worst_t = ""
    worst_l = 0.0
    best_t = ""
    best_l = -999.0

    for ticker, weight in norm_w.items():
        shock = scenario.asset_shocks.get(ticker, scenario.ihsg_shock_percent)
        weighted_loss += weight * shock

        if worst_t == "" or shock < worst_l:
            worst_t = ticker
            worst_l = shock

        if best_t == "" or shock > best_l:
            best_t = ticker
            best_l = shock

    abs_loss_pct = abs(weighted_loss)
    monetary_loss = total_portfolio_value_idr * (abs_loss_pct / 100.0)

    # VaR 99% under stress is modeled as 1.25x the scenario shock
    var_99 = abs_loss_pct * 1.25
    # CVaR (Expected Shortfall) is 1.45x
    cvar = abs_loss_pct * 1.45

    margin_call = abs_loss_pct > 25.0

    if abs_loss_pct > 30.0:
        rec = "Kritis: Portofolio terlalu terkonsentrasi pada aset beta tinggi. Tingkatkan alokasi kas/BBCA untuk bertahan."
    elif abs_loss_pct > 20.0:
        rec = "Waspada: Penurunan substansial. Siapkan batasan trailing stop dan kurangi eksposur saham komoditas."
    else:
        rec = "Resilien: Diversifikasi portofolio menunjukkan daya tahan defensif yang kuat terhadap guncangan sistemik."

    return PortfolioStressResult(
        scenario_id=scenario.scenario_id,
        scenario_title=scenario.title,
        portfolio_weights=norm_w,
        total_portfolio_value_idr=total_portfolio_value_idr,
        portfolio_loss_percent=round(abs_loss_pct, 2),
        monetary_loss_idr=round(monetary_loss, 2),
        worst_asset=worst_t,
        worst_asset_loss_percent=round(worst_l, 2),
        best_asset=best_t,
        best_asset_loss_percent=round(best_l, 2),
        var_99_loss_percent=round(var_99, 2),
        cvar_expected_shortfall_percent=round(cvar, 2),
        margin_call_risk=margin_call,
        survival_recommendation=rec,
    )
