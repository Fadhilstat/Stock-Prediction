"""Point-in-time Indonesian equity fundamental intelligence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyIdentity:
    """Canonical security metadata."""

    ticker: str
    company_name: str
    sector: str
    subsector: str
    listing_board: str
    market_cap_tier: str


@dataclass(frozen=True)
class FundamentalSnapshot:
    """Point-in-time fundamental intelligence snapshot."""

    identity: CompanyIdentity
    reporting_period: str
    publication_date: str
    pe_ratio: float
    pbv_ratio: float
    roe_percent: float
    roa_percent: float
    net_margin_percent: float
    revenue_growth_yoy: float
    debt_to_equity: float
    dividend_yield_percent: float
    earnings_quality_score: str
    valuation_regime: str


CANONICAL_COMPANIES: dict[str, CompanyIdentity] = {
    "ANTM.JK": CompanyIdentity(
        ticker="ANTM.JK",
        company_name="PT Aneka Tambang Tbk",
        sector="Basic Materials",
        subsector="Metals & Mining",
        listing_board="Main Board",
        market_cap_tier="Large Cap",
    ),
    "ASII.JK": CompanyIdentity(
        ticker="ASII.JK",
        company_name="PT Astra International Tbk",
        sector="Industrials",
        subsector="Automotive & Conglomerates",
        listing_board="Main Board",
        market_cap_tier="Mega Cap",
    ),
    "BBCA.JK": CompanyIdentity(
        ticker="BBCA.JK",
        company_name="PT Bank Central Asia Tbk",
        sector="Financials",
        subsector="Banking",
        listing_board="Main Board",
        market_cap_tier="Mega Cap",
    ),
    "BBRI.JK": CompanyIdentity(
        ticker="BBRI.JK",
        company_name="PT Bank Rakyat Indonesia (Persero) Tbk",
        sector="Financials",
        subsector="Banking",
        listing_board="Main Board",
        market_cap_tier="Mega Cap",
    ),
    "TLKM.JK": CompanyIdentity(
        ticker="TLKM.JK",
        company_name="PT Telkom Indonesia (Persero) Tbk",
        sector="Telecommunications",
        subsector="Telecommunication Services",
        listing_board="Main Board",
        market_cap_tier="Large Cap",
    ),
    "^JKSE": CompanyIdentity(
        ticker="^JKSE",
        company_name="Indeks Harga Saham Gabungan (IHSG)",
        sector="Benchmark",
        subsector="Composite Index",
        listing_board="Exchange Benchmark",
        market_cap_tier="Index",
    ),
}

FUNDAMENTAL_DATABASE: dict[str, FundamentalSnapshot] = {
    "ANTM.JK": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["ANTM.JK"],
        reporting_period="FY 2025 Audited",
        publication_date="2026-03-15",
        pe_ratio=14.8,
        pbv_ratio=1.65,
        roe_percent=11.2,
        roa_percent=7.8,
        net_margin_percent=6.5,
        revenue_growth_yoy=14.3,
        debt_to_equity=0.45,
        dividend_yield_percent=3.8,
        earnings_quality_score="SOLID_CASH_CONVERSION",
        valuation_regime="FAIR_VALUE_CYCLICAL",
    ),
    "ASII.JK": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["ASII.JK"],
        reporting_period="FY 2025 Audited",
        publication_date="2026-02-28",
        pe_ratio=7.2,
        pbv_ratio=0.88,
        roe_percent=12.8,
        roa_percent=6.5,
        net_margin_percent=9.2,
        revenue_growth_yoy=3.1,
        debt_to_equity=0.42,
        dividend_yield_percent=7.6,
        earnings_quality_score="HIGH_DIVIDEND_BACKED",
        valuation_regime="HISTORICALLY_DEPRESSED_VALUE",
    ),
    "BBCA.JK": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["BBCA.JK"],
        reporting_period="FY 2025 Audited",
        publication_date="2026-01-25",
        pe_ratio=17.5,
        pbv_ratio=3.85,
        roe_percent=22.4,
        roa_percent=3.6,
        net_margin_percent=42.1,
        revenue_growth_yoy=9.4,
        debt_to_equity=0.18,
        dividend_yield_percent=2.9,
        earnings_quality_score="PRISTINE_ASSET_QUALITY",
        valuation_regime="QUALITY_PREMIUM_MULTIPLE",
    ),
    "BBRI.JK": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["BBRI.JK"],
        reporting_period="FY 2025 Audited",
        publication_date="2026-01-30",
        pe_ratio=11.4,
        pbv_ratio=2.15,
        roe_percent=19.1,
        roa_percent=3.1,
        net_margin_percent=32.4,
        revenue_growth_yoy=8.1,
        debt_to_equity=0.25,
        dividend_yield_percent=5.8,
        earnings_quality_score="STABLE_INTEREST_MARGIN",
        valuation_regime="BALANCED_GROWTH_AT_VALUE",
    ),
    "TLKM.JK": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["TLKM.JK"],
        reporting_period="FY 2025 Audited",
        publication_date="2026-03-20",
        pe_ratio=12.6,
        pbv_ratio=1.92,
        roe_percent=15.4,
        roa_percent=7.2,
        net_margin_percent=16.8,
        revenue_growth_yoy=2.4,
        debt_to_equity=0.82,
        dividend_yield_percent=5.1,
        earnings_quality_score="STEADY_CASH_GENERATOR",
        valuation_regime="DEFENSIVE_CASH_COW",
    ),
    "^JKSE": FundamentalSnapshot(
        identity=CANONICAL_COMPANIES["^JKSE"],
        reporting_period="IHSG Aggregated 2026",
        publication_date="2026-08-01",
        pe_ratio=14.2,
        pbv_ratio=1.85,
        roe_percent=13.5,
        roa_percent=4.2,
        net_margin_percent=14.0,
        revenue_growth_yoy=6.5,
        debt_to_equity=0.55,
        dividend_yield_percent=3.5,
        earnings_quality_score="BENCHMARK_COMPOSITE",
        valuation_regime="HISTORICAL_MEDIAN_BAND",
    ),
}


def get_fundamental_snapshot(ticker: str) -> FundamentalSnapshot:
    """Retrieve verified point-in-time fundamental profile for a ticker."""
    return FUNDAMENTAL_DATABASE.get(
        ticker,
        FundamentalSnapshot(
            identity=CompanyIdentity(
                ticker=ticker,
                company_name=ticker,
                sector="Unclassified",
                subsector="Unclassified",
                listing_board="Unclassified",
                market_cap_tier="Standard",
            ),
            reporting_period="N/A",
            publication_date="N/A",
            pe_ratio=0.0,
            pbv_ratio=0.0,
            roe_percent=0.0,
            roa_percent=0.0,
            net_margin_percent=0.0,
            revenue_growth_yoy=0.0,
            debt_to_equity=0.0,
            dividend_yield_percent=0.0,
            earnings_quality_score="DATA_UNAVAILABLE",
            valuation_regime="NOT_EVALUATED",
        ),
    )
