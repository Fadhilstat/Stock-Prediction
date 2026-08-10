"""Tests for the static dashboard deployment bundle."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.dashboard.deployment import (
    deployment_bundle_available,
    load_deployment_dashboard_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TICKERS = ("AAA.JK", "BBB.JK")
LATEST_DATE = pd.Timestamp("2026-08-07")


def write_json(path: Path, payload: object) -> None:
    """Write a JSON fixture with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def build_runtime_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build aligned analytics, risk, and direction inputs."""

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
                    "unused_column": "not deployed",
                }
            )

    analytics_path = tmp_path / "analytics.parquet"
    pd.DataFrame(analytics_rows).to_parquet(analytics_path, index=False)

    risk_path = tmp_path / "risk.json"
    write_json(
        risk_path,
        [
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
        ],
    )

    direction_path = tmp_path / "direction.json"
    write_json(
        direction_path,
        [
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
        ],
    )

    return analytics_path, risk_path, direction_path


def write_governance_artifacts(project_root: Path) -> None:
    """Write the committed registries and evidence needed by the dashboard loader."""

    write_json(
        project_root / "reports" / "ml" / "classical_model_registry.json",
        [
            {
                "ticker": ticker,
                "selected_model": "constant_probability",
                "selection_rule": "validation",
                "validation": {"log_loss": 0.69},
                "test": {"log_loss": 0.70},
            }
            for ticker in TICKERS
        ],
    )

    write_json(
        project_root / "reports" / "model_registry" / "final_model_registry.json",
        {
            "metadata": {"phase": "5.4"},
            "deployment_roles": {},
            "risk_and_volatility": {
                "tickers": [{"ticker": ticker} for ticker in TICKERS],
            },
            "direction_probability": {
                "tickers": [{"ticker": ticker} for ticker in TICKERS],
            },
            "foundation_benchmarks": {},
        },
    )

    write_json(
        project_root
        / "reports"
        / "foundation"
        / "kronos"
        / "phase_5_2_evidence.json",
        {"status": "complete"},
    )
    write_json(
        project_root
        / "reports"
        / "foundation"
        / "granite"
        / "phase_5_3_evidence.json",
        {"status": "complete"},
    )


def test_bundle_builder_writes_valid_slim_runtime_artifacts(tmp_path: Path) -> None:
    """Deployment bundle should be aligned, slim, and loadable by the dashboard."""

    analytics_path, risk_path, direction_path = build_runtime_inputs(tmp_path)
    project_root = tmp_path / "project"
    deployment_dir = project_root / "deployment"

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "build_deployment_bundle.py"),
            "--analytics",
            str(analytics_path),
            "--risk",
            str(risk_path),
            "--direction",
            str(direction_path),
            "--output-dir",
            str(deployment_dir),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert deployment_bundle_available(project_root)

    deployed_analytics = pd.read_parquet(
        deployment_dir / "analytics_daily.parquet"
    )
    assert "unused_column" not in deployed_analytics.columns
    assert len(deployed_analytics) == 6

    manifest = json.loads(
        (deployment_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == 1
    assert manifest["latest_trade_date"] == "2026-08-07"
    assert manifest["analytics_rows"] == 6
    assert manifest["ticker_count"] == 2
    assert len(manifest["files"]) == 3

    write_governance_artifacts(project_root)
    dashboard_data = load_deployment_dashboard_data(project_root)

    assert dashboard_data.tickers == TICKERS
    assert dashboard_data.latest_date == LATEST_DATE


def test_incomplete_bundle_is_not_reported_as_available(tmp_path: Path) -> None:
    """Deployment fallback should require all runtime artifacts before activation."""

    deployment_dir = tmp_path / "deployment"
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "latest_risk_snapshot.json").write_text("[]\n", encoding="utf-8")

    assert not deployment_bundle_available(tmp_path)
