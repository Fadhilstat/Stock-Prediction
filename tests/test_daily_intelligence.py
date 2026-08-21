"""Tests for the transparent daily intelligence layer."""

from datetime import UTC, datetime

import pandas as pd

from ruang_risiko_idx.intelligence.daily import build_daily_intelligence


def build_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create aligned synthetic market, risk, and direction inputs."""

    dates = pd.to_datetime(["2026-08-19", "2026-08-20"])
    analytics = pd.DataFrame(
        [
            {
                "ticker": ticker,
                "trade_date": date,
                "simple_return": daily_return,
                "volatility_21d": vol_21,
                "volatility_63d": vol_63,
                "drawdown": drawdown,
            }
            for ticker, daily_return, vol_21, vol_63, drawdown in (
                ("AAA.JK", 0.01, 0.30, 0.20, -0.12),
                ("^JKSE", -0.005, 0.15, 0.16, -0.08),
            )
            for date in dates
        ]
    )

    risk = pd.DataFrame(
        [
            {
                "ticker": "AAA.JK",
                "as_of_date": "2026-08-20",
                "forecast_volatility": 0.03,
                "var_95": 0.05,
                "var_99": 0.08,
                "convergence_flag": 0,
            },
            {
                "ticker": "^JKSE",
                "as_of_date": "2026-08-20",
                "forecast_volatility": 0.01,
                "var_95": 0.02,
                "var_99": 0.03,
                "convergence_flag": 0,
            },
        ]
    )

    direction = pd.DataFrame(
        [
            {
                "ticker": "AAA.JK",
                "as_of_date": "2026-08-20",
                "selected_model": "random_forest",
                "probability_up": 0.62,
            },
            {
                "ticker": "^JKSE",
                "as_of_date": "2026-08-20",
                "selected_model": "constant_probability",
                "probability_up": 0.51,
            },
        ]
    )
    return analytics, risk, direction


def test_daily_intelligence_builds_distinct_analyst_roles() -> None:
    """Each ticker should receive market, risk, and direction interpretations."""

    analytics, risk, direction = build_inputs()
    artifact = build_daily_intelligence(
        analytics,
        risk,
        direction,
        generated_at_utc=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
    )

    assert artifact["schema_version"] == 1
    assert artifact["as_of_date"] == "2026-08-20"
    assert artifact["paid_language_model_api_used"] is False
    assert set(artifact["ticker_briefs"]) == {"AAA.JK", "^JKSE"}
    assert artifact["ticker_briefs"]["AAA.JK"]["risk"]["state"] == (
        "risiko model tertinggi di universe"
    )
    assert "bukan sinyal transaksi" in (
        artifact["ticker_briefs"]["AAA.JK"]["direction"]["summary"].lower()
    )
    assert artifact["model_audit"]["state"] == "pipeline selaras"


def test_daily_intelligence_keeps_auditable_news_metadata() -> None:
    """News output should keep source links and classify only configured metadata."""

    analytics, risk, direction = build_inputs()
    news = [
        {
            "title": "Bank Indonesia discusses monetary policy",
            "url": "https://www.bi.go.id/example",
            "domain": "bi.go.id",
            "source_label": "Bank Indonesia",
            "published_at": "20260820T100000Z",
            "tickers": [],
            "themes": ["monetary_policy"],
        },
        {
            "title": "Duplicate URL should not be repeated",
            "url": "https://www.bi.go.id/example",
            "domain": "bi.go.id",
            "source_label": "Bank Indonesia",
            "published_at": "20260820T100000Z",
            "tickers": [],
            "themes": [],
        },
    ]

    artifact = build_daily_intelligence(analytics, risk, direction, news_items=news)

    assert len(artifact["news_items"]) == 1
    assert artifact["news_items"][0]["domain"] == "bi.go.id"
    assert artifact["macro_news"]["active_themes"] == ["monetary_policy"]
    assert artifact["macro_news"]["article_count"] == 1


def test_market_role_reports_short_term_volatility_context() -> None:
    """Market role should compare descriptive 21-day and 63-day volatility."""

    analytics, risk, direction = build_inputs()
    artifact = build_daily_intelligence(analytics, risk, direction)

    market = artifact["ticker_briefs"]["AAA.JK"]["market"]
    assert market["state"] == "lebih bergejolak"
    assert "Volatilitas jangka pendek berada di atas ritme 63 hari." in market["summary"]
