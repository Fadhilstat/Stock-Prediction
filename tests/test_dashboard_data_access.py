"""Tests for validated dashboard data access."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ruang_risiko_idx.dashboard.data_access import (
    DashboardDataError,
    load_dashboard_data,
)

TICKERS = ("AAA.JK", "BBB.JK")
LATEST_DATE = pd.Timestamp("2026-08-07")


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON fixture."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_project(tmp_path: Path) -> Path:
    """Build a complete synthetic dashboard artifact tree."""

    project_root = tmp_path / "project"

    analytics_rows = []
    for ticker_index, ticker in enumerate(TICKERS):
        for offset in range(3):
            trade_date = LATEST_DATE - pd.offsets.BDay(2 - offset)
            analytics_rows.append(
                {
                    "ticker": ticker,
                    "trade_date": trade_date,
                    "adjusted_close": 100.0 + ticker_index * 10 + offset,
                    "simple_return": 0.001 * offset,
                    "log_return": 0.001 * offset,
                    "benchmark_return": 0.0005 * offset,
                    "excess_return": 0.0005 * offset,
                    "volatility_21d": 0.02,
                    "volatility_63d": 0.018,
                    "drawdown": -0.01 * offset,
                    "time_under_water": offset,
                }
            )

    analytics_path = project_root / "data" / "processed" / "analytics_daily.parquet"
    analytics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(analytics_rows).to_parquet(analytics_path, index=False)

    risk_rows = [
        {
            "ticker": ticker,
            "as_of_date": str(LATEST_DATE.date()),
            "forecast_volatility": 0.02,
            "var_95": 0.03,
            "var_99": 0.05,
            "persistence": 0.97,
            "half_life_days": 23.0,
            "volatility_model": "egarch_student_t",
            "var_model": "egarch_student_t",
            "convergence_flag": 0,
        }
        for ticker in TICKERS
    ]
    _write_json(project_root / "reports" / "risk" / "latest_risk_snapshot.json", risk_rows)

    direction_rows = [
        {
            "ticker": ticker,
            "as_of_date": str(LATEST_DATE.date()),
            "forecast_horizon": "next_trading_day",
            "selected_model": "constant_probability",
            "probability_up": 0.45 + index * 0.05,
            "probability_down": 0.55 - index * 0.05,
            "training_observations": 1000,
            "training_end_date": "2026-08-06",
        }
        for index, ticker in enumerate(TICKERS)
    ]
    _write_json(
        project_root / "reports" / "ml" / "latest_direction_snapshot.json",
        direction_rows,
    )

    classical_rows = [
        {
            "ticker": ticker,
            "selected_model": "constant_probability",
            "selection_rule": "validation",
            "validation": {"log_loss": 0.69},
            "test": {"log_loss": 0.70},
        }
        for ticker in TICKERS
    ]
    _write_json(
        project_root / "reports" / "ml" / "classical_model_registry.json",
        classical_rows,
    )

    final_registry = {
        "metadata": {"phase": "5.4"},
        "deployment_roles": {},
        "risk_and_volatility": {
            "tickers": [{"ticker": ticker} for ticker in TICKERS],
        },
        "direction_probability": {
            "tickers": [{"ticker": ticker} for ticker in TICKERS],
        },
        "foundation_benchmarks": {},
    }
    _write_json(
        project_root / "reports" / "model_registry" / "final_model_registry.json",
        final_registry,
    )

    _write_json(
        project_root / "reports" / "foundation" / "kronos" / "phase_5_2_evidence.json",
        {"status": "complete", "decision": {"production_selection": "not_selected"}},
    )
    _write_json(
        project_root / "reports" / "foundation" / "granite" / "phase_5_3_evidence.json",
        {"status": "complete", "decision": {"production_selection": "not_selected"}},
    )

    return project_root


def test_load_dashboard_data_accepts_aligned_artifacts(tmp_path: Path) -> None:
    """A complete aligned artifact set should load successfully."""

    project_root = _build_project(tmp_path)
    data = load_dashboard_data(project_root)

    assert data.tickers == TICKERS
    assert data.latest_date == LATEST_DATE
    assert len(data.analytics) == 6
    assert len(data.risk_snapshot) == 2
    assert len(data.direction_snapshot) == 2
    assert len(data.classical_registry) == 2


def test_missing_runtime_artifact_has_readable_error(tmp_path: Path) -> None:
    """A missing runtime artifact should explain how to recover."""

    project_root = _build_project(tmp_path)
    direction_path = project_root / "reports" / "ml" / "latest_direction_snapshot.json"
    direction_path.unlink()

    with pytest.raises(DashboardDataError, match="offline data pipeline"):
        load_dashboard_data(project_root)


def test_risk_ticker_mismatch_is_rejected(tmp_path: Path) -> None:
    """Risk snapshot coverage must match the analytics universe."""

    project_root = _build_project(tmp_path)
    risk_path = project_root / "reports" / "risk" / "latest_risk_snapshot.json"
    risk_rows = json.loads(risk_path.read_text(encoding="utf-8"))
    _write_json(risk_path, risk_rows[:1])

    with pytest.raises(DashboardDataError, match="Risk snapshot ticker universe"):
        load_dashboard_data(project_root)


def test_stale_direction_snapshot_is_rejected(tmp_path: Path) -> None:
    """Direction estimates must share the latest analytics date."""

    project_root = _build_project(tmp_path)
    direction_path = project_root / "reports" / "ml" / "latest_direction_snapshot.json"
    direction_rows = json.loads(direction_path.read_text(encoding="utf-8"))

    for row in direction_rows:
        row["as_of_date"] = "2026-08-06"
        row["training_end_date"] = "2026-08-05"

    _write_json(direction_path, direction_rows)

    with pytest.raises(DashboardDataError, match="Direction snapshot date"):
        load_dashboard_data(project_root)


def test_invalid_direction_probability_is_rejected(tmp_path: Path) -> None:
    """Probabilities outside the unit interval must not reach the UI."""

    project_root = _build_project(tmp_path)
    direction_path = project_root / "reports" / "ml" / "latest_direction_snapshot.json"
    direction_rows = json.loads(direction_path.read_text(encoding="utf-8"))
    direction_rows[0]["probability_up"] = 1.20
    direction_rows[0]["probability_down"] = -0.20
    _write_json(direction_path, direction_rows)

    with pytest.raises(DashboardDataError, match="probability_up"):
        load_dashboard_data(project_root)


def test_final_registry_ticker_mismatch_is_rejected(tmp_path: Path) -> None:
    """Committed model governance must cover the runtime universe."""

    project_root = _build_project(tmp_path)
    registry_path = project_root / "reports" / "model_registry" / "final_model_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["risk_and_volatility"]["tickers"] = [{"ticker": "AAA.JK"}]
    _write_json(registry_path, registry)

    with pytest.raises(DashboardDataError, match="Final risk registry ticker universe"):
        load_dashboard_data(project_root)
