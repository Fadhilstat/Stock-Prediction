"""IDX Sector Rotation Compass and Market Breadth Participation Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd


@dataclass(frozen=True)
class SectorMomentumProfile:
    """Individual sector momentum and relative rotation quadrant."""

    sector_name: str
    primary_ticker: str
    relative_strength_20d: float
    momentum_score: float
    quadrant: Literal["LEADING", "WEAKENING", "LAGGING", "IMPROVING"]
    summary: str


@dataclass(frozen=True)
class MarketBreadthReport:
    """Consolidated market-wide breadth and sector rotation state."""

    as_of_date: str
    percent_above_sma20: float
    percent_above_sma50: float
    percent_above_sma200: float
    breadth_regime: Literal["BROAD_EXPANSION", "SELECTIVE_HEALTHY", "NARROW_PARTICIPATION", "SYSTEMIC_DETERIORATION"]
    stock_sector_quadrant: str
    summary: str
    sectors: list[SectorMomentumProfile]


CANONICAL_SECTORS: dict[str, tuple[str, str]] = {
    "Financials (IDXFINANCE)": ("BBCA.JK", "Perbankan dan jasa keuangan"),
    "Basic Materials (IDXBASIC)": ("ANTM.JK", "Bahan baku, logam, dan pertambangan"),
    "Infrastructures (IDXINFRA)": ("TLKM.JK", "Telekomunikasi, menara, utilitas"),
    "Consumer Cyclicals (IDXCYCLIC)": ("ASII.JK", "Otomotif, ritel barang sekunder"),
    "State Banks (SOE Banks)": ("BBRI.JK", "Perbankan mikro dan himbara BUMN"),
}


def compute_sector_rotation(
    market_data: pd.DataFrame,
    selected_ticker: str,
    as_of_date: str,
) -> MarketBreadthReport:
    """Compute market breadth participation and sector rotation profiles."""
    tickers = [t for t in market_data["ticker"].unique() if t != "^JKSE"]
    total_stocks = len(tickers)

    above_20_count = 0
    above_50_count = 0
    above_200_count = 0

    stock_quadrant = "SELECTIVE_HEALTHY"

    for t in tickers:
        sub = market_data.loc[market_data["ticker"] == t].sort_values("trade_date")
        if len(sub) < 20:
            continue
        c = sub["close"].iloc[-1]
        sma20 = sub["close"].tail(20).mean()
        sma50 = sub["close"].tail(50).mean() if len(sub) >= 50 else sma20
        sma200 = sub["close"].tail(200).mean() if len(sub) >= 200 else sma50

        if c >= sma20:
            above_20_count += 1
        if c >= sma50:
            above_50_count += 1
        if c >= sma200:
            above_200_count += 1

    pct_20 = round((above_20_count / total_stocks) * 100.0, 1) if total_stocks > 0 else 50.0
    pct_50 = round((above_50_count / total_stocks) * 100.0, 1) if total_stocks > 0 else 50.0
    pct_200 = round((above_200_count / total_stocks) * 100.0, 1) if total_stocks > 0 else 50.0

    if pct_50 >= 70.0:
        regime = "BROAD_EXPANSION"
        regime_desc = "Ekspansi Luas: Mayoritas saham diperdagangkan di atas rata-rata jangka menengah."
    elif pct_50 >= 45.0:
        regime = "SELECTIVE_HEALTHY"
        regime_desc = "Selektif Sehat: Penguatan terkonsentrasi pada sektor-sektor berkapitalisasi besar."
    elif pct_50 >= 25.0:
        regime = "NARROW_PARTICIPATION"
        regime_desc = "Partisipasi Sempit: Reli hanya ditopang segelintir saham penggerak indeks."
    else:
        regime = "SYSTEMIC_DETERIORATION"
        regime_desc = "Deteriorasi Sistemik: Tekanan jual meluas di seluruh sektor bursa."

    sector_profiles: list[SectorMomentumProfile] = []

    for sec_name, (sec_ticker, desc) in CANONICAL_SECTORS.items():
        sub_sec = market_data.loc[market_data["ticker"] == sec_ticker].sort_values("trade_date")
        if len(sub_sec) >= 20:
            p_now = sub_sec["close"].iloc[-1]
            p_old = sub_sec["close"].iloc[-20]
            rel_str = ((p_now / p_old) - 1.0) * 100.0
        else:
            rel_str = 0.0

        mom_score = round(rel_str * 1.2, 1)

        if rel_str > 2.0 and mom_score > 0:
            quadrant = "LEADING"
            quad_summary = f"{sec_name} memimpin reli pasar dengan momentum relatif tinggi."
        elif rel_str > 0 and mom_score <= 0:
            quadrant = "WEAKENING"
            quad_summary = f"{sec_name} mulai kehilangan akselerasi tren naik."
        elif rel_str <= -2.0:
            quadrant = "LAGGING"
            quad_summary = f"{sec_name} tertinggal di bawah performa indeks IHSG."
        else:
            quadrant = "IMPROVING"
            quad_summary = f"{sec_name} menunjukkan tanda pemulihan rotasi sektor."

        if sec_ticker == selected_ticker:
            stock_quadrant = quadrant

        sector_profiles.append(
            SectorMomentumProfile(
                sector_name=sec_name,
                primary_ticker=sec_ticker,
                relative_strength_20d=round(rel_str, 2),
                momentum_score=mom_score,
                quadrant=quadrant,
                summary=quad_summary,
            )
        )

    return MarketBreadthReport(
        as_of_date=as_of_date,
        percent_above_sma20=pct_20,
        percent_above_sma50=pct_50,
        percent_above_sma200=pct_200,
        breadth_regime=regime,
        stock_sector_quadrant=stock_quadrant,
        summary=regime_desc,
        sectors=sector_profiles,
    )
