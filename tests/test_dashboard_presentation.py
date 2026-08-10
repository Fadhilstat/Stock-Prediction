"""Tests for dashboard presentation helpers."""

import pandas as pd
import pytest

from ruang_risiko_idx.dashboard.presentation import (
    build_market_snapshot,
    build_risk_overview,
    format_model_name,
    format_registry_status,
    get_ticker_row,
)


def test_build_market_snapshot_returns_latest_row_per_ticker() -> None:
    """Market snapshot should keep the latest descriptive row per ticker."""

    analytics = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "BBB"],
            "trade_date": pd.to_datetime(
                ["2026-08-06", "2026-08-07", "2026-08-06", "2026-08-07"]
            ),
            "adjusted_close": [100.0, 101.0, 200.0, 198.0],
            "simple_return": [0.01, 0.01, 0.02, -0.01],
            "volatility_21d": [0.02, 0.021, 0.03, 0.031],
            "drawdown": [-0.05, -0.04, -0.10, -0.11],
        }
    )

    snapshot = build_market_snapshot(analytics)

    assert list(snapshot["ticker"]) == ["AAA", "BBB"]
    assert snapshot["trade_date"].eq(pd.Timestamp("2026-08-07")).all()
    assert snapshot.loc[snapshot["ticker"].eq("AAA"), "adjusted_close"].iloc[0] == 101.0


def test_build_risk_overview_aligns_precomputed_outputs() -> None:
    """Risk overview should join one row per ticker on the same date."""

    dates = pd.to_datetime(["2026-08-07", "2026-08-07"])
    risk = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "as_of_date": dates,
            "forecast_volatility": [0.02, 0.03],
            "var_95": [0.03, 0.04],
            "var_99": [0.05, 0.07],
            "volatility_model": ["egarch_normal", "gjr_garch_student_t"],
            "var_model": ["egarch_student_t", "gjr_garch_student_t"],
        }
    )
    direction = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "as_of_date": dates,
            "probability_up": [0.55, 0.45],
            "selected_model": ["logistic_regression", "constant_probability"],
        }
    )

    overview = build_risk_overview(risk, direction)

    assert list(overview["ticker"]) == ["AAA", "BBB"]
    assert overview.loc[0, "direction_model_label"] == "Logistic Regression"
    assert overview.loc[1, "volatility_model_label"] == "GJR-GARCH Student-t"


def test_build_risk_overview_rejects_misaligned_snapshots() -> None:
    """A missing ticker should fail instead of silently dropping a row."""

    risk = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "as_of_date": pd.to_datetime(["2026-08-07"]),
            "forecast_volatility": [0.02],
            "var_95": [0.03],
            "var_99": [0.05],
            "volatility_model": ["egarch_normal"],
            "var_model": ["egarch_student_t"],
        }
    )
    direction = pd.DataFrame(
        {
            "ticker": ["BBB"],
            "as_of_date": pd.to_datetime(["2026-08-07"]),
            "probability_up": [0.45],
            "selected_model": ["random_forest"],
        }
    )

    with pytest.raises(ValueError, match="do not align"):
        build_risk_overview(risk, direction)


def test_get_ticker_row_requires_exactly_one_match() -> None:
    """Ticker lookup should reject missing or duplicate rows."""

    data = pd.DataFrame({"ticker": ["AAA"], "value": [1.0]})
    row = get_ticker_row(data, "AAA")
    assert row["value"] == 1.0

    with pytest.raises(ValueError, match="Expected one row"):
        get_ticker_row(data, "BBB")


def test_format_model_name_has_readable_fallback() -> None:
    """Unknown technical names should still receive a readable label."""

    assert format_model_name("random_forest") == "Random Forest"
    assert format_model_name("custom_model") == "Custom Model"


def test_format_registry_status_has_readable_label() -> None:
    """Technical registry status should remain accurate but readable."""

    status = format_registry_status("provisional_out_of_sample_selection")

    assert status == "Seleksi provisional berdasarkan evaluasi out-of-sample"
