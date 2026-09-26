"""Unit tests for Macroeconomic, News Sentiment, Biweekly Validation, and Flexible Universe."""

from __future__ import annotations

import pandas as pd
import pytest

from ruang_risiko_idx.research.macro_economy import (
    calculate_hurst_exponent,
    compute_mathematical_moments,
    get_macroeconomic_report,
    MathematicalMoments,
    MacroeconomicReport,
)
from ruang_risiko_idx.research.news_sentiment import (
    get_news_sentiment_profile,
    TickerNewsProfile,
)
from ruang_risiko_idx.research.biweekly_validation import (
    generate_biweekly_validation_ledger,
    BiweeklyModelHealthReport,
)
from ruang_risiko_idx.research.flexible_universe import (
    normalize_ticker_symbol,
    resolve_stock_metadata,
    ensure_ticker_data_available,
    EXPANDED_IDX_UNIVERSE,
)


def test_normalize_ticker_symbol() -> None:
    assert normalize_ticker_symbol("bbca") == "BBCA.JK"
    assert normalize_ticker_symbol("BBRI.JK") == "BBRI.JK"
    assert normalize_ticker_symbol("ihsg") == "^JKSE"
    assert normalize_ticker_symbol("^JKSE") == "^JKSE"
    assert normalize_ticker_symbol("bmri") == "BMRI.JK"


def test_resolve_stock_metadata() -> None:
    bbca = resolve_stock_metadata("BBCA")
    assert bbca.ticker == "BBCA.JK"
    assert bbca.sector == "Financials"

    custom = resolve_stock_metadata("BRPT")
    assert custom.ticker == "BRPT.JK"
    assert "Kustom" in custom.company_name


def test_ensure_ticker_data_available() -> None:
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "trade_date": dates,
        "ticker": "^JKSE",
        "close": [7000.0 + i for i in range(10)],
        "open": [7000.0 for _ in range(10)],
        "high": [7050.0 for _ in range(10)],
        "low": [6950.0 for _ in range(10)],
        "volume": [1_000_000 for _ in range(10)],
        "adjusted_close": [7000.0 for _ in range(10)],
    })

    # When ticker already exists
    df_same = ensure_ticker_data_available(df, "^JKSE")
    assert len(df_same) == 10

    # When custom ticker does not exist
    df_new = ensure_ticker_data_available(df, "BREN.JK")
    assert len(df_new) == 20
    assert "BREN.JK" in df_new["ticker"].values


def test_macroeconomic_report() -> None:
    rep = get_macroeconomic_report("2026-09-25")
    assert isinstance(rep, MacroeconomicReport)
    assert rep.bank_indonesia_rate_pct == 6.00
    assert rep.ten_year_sun_yield_pct == 6.65
    assert rep.equity_risk_premium_pct > 0
    assert len(rep.indicators) >= 5


def test_mathematical_moments() -> None:
    dates = pd.date_range("2025-01-01", periods=100, freq="D")
    prices = [5000.0 * (1.0 + 0.005 * i) for i in range(100)]
    df = pd.DataFrame({
        "trade_date": dates,
        "ticker": "BBCA.JK",
        "close": prices,
    })

    moments = compute_mathematical_moments(df, "BBCA.JK")
    assert isinstance(moments, MathematicalMoments)
    assert moments.annualized_volatility_pct > 0.0
    assert 0.0 < moments.hurst_exponent < 1.0
    assert moments.memory_regime in ["MEAN_REVERTING", "RANDOM_WALK", "TREND_PERSISTENT"]


def test_news_sentiment_profile() -> None:
    profile = get_news_sentiment_profile("BBCA.JK")
    assert isinstance(profile, TickerNewsProfile)
    assert profile.ticker == "BBCA.JK"
    assert profile.sentiment_regime in ["BULLISH_CATALYST", "NEUTRAL_BALANCED", "BEARISH_OVERHANG"]
    assert len(profile.articles) > 0


def test_biweekly_validation_ledger() -> None:
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "trade_date": dates,
        "ticker": "BBCA.JK",
        "close": [9000.0 + (i * 20.0) for i in range(60)],
    })

    ledger = generate_biweekly_validation_ledger("BBCA.JK", df)
    assert isinstance(ledger, BiweeklyModelHealthReport)
    assert ledger.evaluation_cadence == "14 Hari (Bi-Weekly Out-Of-Sample)"
    assert len(ledger.cycles) > 0
    assert ledger.mean_hit_rate_pct > 0.0
