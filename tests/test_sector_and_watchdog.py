"""Tests for Sector Rotation Compass and Invalidation Watchdog Engine."""

from __future__ import annotations

import pandas as pd
import pytest

from ruang_risiko_idx.research.sector_rotation import (
    compute_sector_rotation,
    MarketBreadthReport,
)
from ruang_risiko_idx.research.invalidation_watchdog import (
    scan_active_passports_watchdog,
    WatchdogAlert,
)


def test_compute_sector_rotation_basic() -> None:
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    records = []
    for ticker in ["BBCA.JK", "ANTM.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"]:
        for i, dt in enumerate(dates):
            records.append({
                "trade_date": dt,
                "ticker": ticker,
                "close": 5000.0 + (i * 10.0),
                "open": 5000.0 + (i * 10.0),
                "high": 5050.0 + (i * 10.0),
                "low": 4950.0 + (i * 10.0),
                "volume": 1_000_000,
            })
    # Also add ^JKSE
    for i, dt in enumerate(dates):
        records.append({
            "trade_date": dt,
            "ticker": "^JKSE",
            "close": 7000.0 + (i * 5.0),
            "open": 7000.0,
            "high": 7050.0,
            "low": 6950.0,
            "volume": 10_000_000,
        })

    df = pd.DataFrame(records)
    report = compute_sector_rotation(df, "BBCA.JK", "2026-03-01")

    assert isinstance(report, MarketBreadthReport)
    assert report.percent_above_sma20 == 100.0
    assert report.percent_above_sma50 == 100.0
    assert report.breadth_regime == "BROAD_EXPANSION"
    assert len(report.sectors) == 5
    assert report.stock_sector_quadrant in ["LEADING", "WEAKENING", "LAGGING", "IMPROVING"]


def test_scan_active_passports_watchdog(tmp_path) -> None:
    passports_dir = tmp_path / "reports" / "passports"

    # Empty dir scenario
    alerts_empty = scan_active_passports_watchdog({"BBCA.JK": 10000.0}, passport_dir=passports_dir)
    assert alerts_empty == []

    # Create dummy passport file
    passports_dir.mkdir(parents=True)

    dummy_passport_safe = (
        "# Pre-Buy Decision Passport: BBCA.JK\n"
        "- Level Invalidasi Kustom: `Rp 9,000`\n"
        "- Catatan Risiko: Aman\n"
    )
    (passports_dir / "PASSPORT-BBCA-SAFE.md").write_text(dummy_passport_safe, encoding="utf-8")

    dummy_passport_breached = (
        "# Pre-Buy Decision Passport: BBRI.JK\n"
        "- Level Invalidasi Kustom: `Rp 5,500`\n"
        "- Catatan Risiko: Tes breached\n"
    )
    (passports_dir / "PASSPORT-BBRI-BREACH.md").write_text(dummy_passport_breached, encoding="utf-8")

    dummy_passport_warn = (
        "# Pre-Buy Decision Passport: TLKM.JK\n"
        "- daily close breaches Rp 3,000\n"
    )
    (passports_dir / "PASSPORT-TLKM-WARN.md").write_text(dummy_passport_warn, encoding="utf-8")

    prices = {
        "BBCA.JK": 10000.0,  # +10% above 9000 -> SAFE_BUFFER
        "BBRI.JK": 5000.0,   # below 5500 -> INVALIDATED_BREACHED
        "TLKM.JK": 3050.0,   # +1.6% above 3000 -> WARNING_PROXIMITY (< 3%)
    }

    alerts = scan_active_passports_watchdog(prices, passport_dir=passports_dir)
    assert len(alerts) == 3

    alert_dict = {a.ticker: a for a in alerts}
    assert alert_dict["BBCA.JK"].alert_level == "SAFE_BUFFER"
    assert alert_dict["BBRI.JK"].alert_level == "INVALIDATED_BREACHED"
    assert alert_dict["TLKM.JK"].alert_level == "WARNING_PROXIMITY"
    # Check sorting by distance_percent ascending
    assert alerts[0].distance_percent <= alerts[1].distance_percent <= alerts[2].distance_percent
