"""Tests for the optional daily intelligence dashboard loader."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ruang_risiko_idx.dashboard.data_access import DashboardDataError
from ruang_risiko_idx.dashboard.intelligence import load_daily_intelligence


def write_artifact(path: Path, as_of_date: str = "2026-08-20") -> None:
    """Write one minimal intelligence fixture."""

    payload = {
        "schema_version": 1,
        "generated_at_utc": "2026-08-20T12:00:00+00:00",
        "as_of_date": as_of_date,
        "generation_method": "deterministic_rule_based",
        "paid_language_model_api_used": False,
        "ticker_briefs": {
            "AAA.JK": {
                "market": {"role": "Analis pasar", "state": "tenang", "summary": "x"},
                "risk": {"role": "Analis risiko", "state": "normal", "summary": "y"},
                "direction": {
                    "role": "Analis probabilitas arah",
                    "state": "imbang",
                    "summary": "z",
                },
            }
        },
        "macro_news": {"role": "Analis makro dan berita"},
        "model_audit": {"role": "Auditor model dan data"},
        "news_items": [
            {
                "title": "Official update",
                "url": "https://www.bi.go.id/example",
                "domain": "bi.go.id",
                "source_label": "Bank Indonesia",
                "tickers": [],
                "themes": ["monetary_policy"],
            }
        ],
        "synthesis": ["Market context."],
        "disclaimer": "Bukan rekomendasi investasi.",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_loader_accepts_aligned_intelligence(tmp_path: Path) -> None:
    """Aligned intelligence should load for the dashboard."""

    path = tmp_path / "intelligence.json"
    write_artifact(path)

    payload = load_daily_intelligence(
        path,
        latest_date=pd.Timestamp("2026-08-20"),
        tickers=("AAA.JK",),
    )

    assert payload["as_of_date"] == "2026-08-20"
    assert payload["news_items"][0]["domain"] == "bi.go.id"


def test_loader_rejects_stale_intelligence(tmp_path: Path) -> None:
    """A stale daily summary must not be mixed with newer market data."""

    path = tmp_path / "intelligence.json"
    write_artifact(path, as_of_date="2026-08-19")

    with pytest.raises(DashboardDataError, match="date does not match"):
        load_daily_intelligence(
            path,
            latest_date=pd.Timestamp("2026-08-20"),
            tickers=("AAA.JK",),
        )


def test_loader_rejects_non_https_news_url(tmp_path: Path) -> None:
    """Public news links must use HTTPS."""

    path = tmp_path / "intelligence.json"
    write_artifact(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["news_items"][0]["url"] = "http://example.com"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DashboardDataError, match="invalid news URL"):
        load_daily_intelligence(
            path,
            latest_date=pd.Timestamp("2026-08-20"),
            tickers=("AAA.JK",),
        )
