"""Validated data access for the Ruang Risiko IDX dashboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class DashboardDataError(RuntimeError):
    """Raised when a dashboard artifact is missing or invalid."""


@dataclass(frozen=True)
class DashboardPaths:
    """Store paths for dashboard runtime and evidence artifacts."""

    analytics: Path
    risk_snapshot: Path
    direction_snapshot: Path
    final_registry: Path
    classical_registry: Path
    kronos_evidence: Path
    granite_evidence: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> DashboardPaths:
        """Build the standard dashboard artifact paths."""

        return cls(
            analytics=project_root / "data" / "processed" / "analytics_daily.parquet",
            risk_snapshot=project_root / "reports" / "risk" / "latest_risk_snapshot.json",
            direction_snapshot=(
                project_root / "reports" / "ml" / "latest_direction_snapshot.json"
            ),
            final_registry=(
                project_root / "reports" / "model_registry" / "final_model_registry.json"
            ),
            classical_registry=(
                project_root / "reports" / "ml" / "classical_model_registry.json"
            ),
            kronos_evidence=(
                project_root
                / "reports"
                / "foundation"
                / "kronos"
                / "phase_5_2_evidence.json"
            ),
            granite_evidence=(
                project_root
                / "reports"
                / "foundation"
                / "granite"
                / "phase_5_3_evidence.json"
            ),
        )


@dataclass(frozen=True)
class DashboardData:
    """Store validated data used by the dashboard."""

    analytics: pd.DataFrame
    risk_snapshot: pd.DataFrame
    direction_snapshot: pd.DataFrame
    final_registry: dict[str, Any]
    classical_registry: list[dict[str, Any]]
    kronos_evidence: dict[str, Any]
    granite_evidence: dict[str, Any]

    @property
    def tickers(self) -> tuple[str, ...]:
        """Return the validated ticker universe."""

        return tuple(sorted(self.analytics["ticker"].astype(str).unique()))

    @property
    def latest_date(self) -> pd.Timestamp:
        """Return the latest analytics date."""

        return pd.Timestamp(self.analytics["trade_date"].max())


def _require_file(path: Path, artifact_name: str) -> None:
    """Raise a readable error when an artifact is unavailable."""

    if not path.exists():
        raise DashboardDataError(
            f"{artifact_name} is not available at {path}. "
            "Run the offline data pipeline before starting the dashboard."
        )


def _load_json(path: Path, artifact_name: str) -> Any:
    """Load one JSON artifact with a readable validation error."""

    _require_file(path, artifact_name)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DashboardDataError(f"{artifact_name} contains invalid JSON.") from error


def _require_columns(
    data: pd.DataFrame,
    required_columns: set[str],
    artifact_name: str,
) -> None:
    """Validate required dataframe columns."""

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise DashboardDataError(f"{artifact_name} is missing columns: {missing_text}")


def load_analytics(path: Path) -> pd.DataFrame:
    """Load and validate the processed daily analytics dataset."""

    _require_file(path, "Analytics dataset")

    try:
        data = pd.read_parquet(path)
    except (OSError, ValueError) as error:
        raise DashboardDataError("Analytics dataset could not be read as Parquet.") from error

    required_columns = {
        "ticker",
        "trade_date",
        "adjusted_close",
        "simple_return",
        "log_return",
        "benchmark_return",
        "excess_return",
        "volatility_21d",
        "volatility_63d",
        "drawdown",
        "time_under_water",
    }

    _require_columns(data, required_columns, "Analytics dataset")

    if data.empty:
        raise DashboardDataError("Analytics dataset is empty.")

    data = data.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce")

    if data["trade_date"].isna().any():
        raise DashboardDataError("Analytics dataset contains invalid trade dates.")

    if data["ticker"].isna().any():
        raise DashboardDataError("Analytics dataset contains missing tickers.")

    if data.duplicated(["ticker", "trade_date"]).any():
        raise DashboardDataError("Analytics dataset contains duplicate ticker-date rows.")

    return data.sort_values(["ticker", "trade_date"]).reset_index(drop=True)


def load_risk_snapshot(path: Path) -> pd.DataFrame:
    """Load and validate the latest GARCH risk snapshot."""

    payload = _load_json(path, "Risk snapshot")

    if not isinstance(payload, list):
        raise DashboardDataError("Risk snapshot must contain a JSON list.")

    data = pd.DataFrame(payload)

    required_columns = {
        "ticker",
        "as_of_date",
        "forecast_volatility",
        "var_95",
        "var_99",
        "persistence",
        "half_life_days",
        "volatility_model",
        "var_model",
        "convergence_flag",
    }

    _require_columns(data, required_columns, "Risk snapshot")

    if data.empty:
        raise DashboardDataError("Risk snapshot is empty.")

    data = data.copy()
    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce")

    if data["as_of_date"].isna().any():
        raise DashboardDataError("Risk snapshot contains invalid as_of_date values.")

    if data["ticker"].duplicated().any():
        raise DashboardDataError("Risk snapshot contains duplicate tickers.")

    numeric_columns = [
        "forecast_volatility",
        "var_95",
        "var_99",
        "persistence",
        "half_life_days",
    ]
    numeric_values = data[numeric_columns].apply(pd.to_numeric, errors="coerce")

    if not np.isfinite(numeric_values.to_numpy(dtype="float64")).all():
        raise DashboardDataError("Risk snapshot contains invalid numeric values.")

    return data.sort_values("ticker").reset_index(drop=True)


def load_direction_snapshot(path: Path) -> pd.DataFrame:
    """Load and validate the latest direction probability snapshot."""

    payload = _load_json(path, "Direction snapshot")

    if not isinstance(payload, list):
        raise DashboardDataError("Direction snapshot must contain a JSON list.")

    data = pd.DataFrame(payload)

    required_columns = {
        "ticker",
        "as_of_date",
        "forecast_horizon",
        "selected_model",
        "probability_up",
        "probability_down",
        "training_observations",
        "training_end_date",
    }

    _require_columns(data, required_columns, "Direction snapshot")

    if data.empty:
        raise DashboardDataError("Direction snapshot is empty.")

    data = data.copy()
    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce")
    data["training_end_date"] = pd.to_datetime(
        data["training_end_date"],
        errors="coerce",
    )

    if data[["as_of_date", "training_end_date"]].isna().any().any():
        raise DashboardDataError("Direction snapshot contains invalid dates.")

    if data["ticker"].duplicated().any():
        raise DashboardDataError("Direction snapshot contains duplicate tickers.")

    for column in ("probability_up", "probability_down"):
        values = pd.to_numeric(data[column], errors="coerce")
        probability_valid = values.between(0.0, 1.0, inclusive="both").all()
        if values.isna().any() or not probability_valid:
            raise DashboardDataError(
                f"Direction snapshot contains invalid {column} values."
            )

    probability_sum = data["probability_up"] + data["probability_down"]

    if not np.allclose(
        probability_sum.to_numpy(dtype="float64"),
        1.0,
        atol=1e-12,
    ):
        raise DashboardDataError("Direction probabilities do not sum to one.")

    if set(data["forecast_horizon"].astype(str)) != {"next_trading_day"}:
        raise DashboardDataError("Direction snapshot contains an unexpected forecast horizon.")

    return data.sort_values("ticker").reset_index(drop=True)


def load_final_registry(path: Path) -> dict[str, Any]:
    """Load the final task-specific model registry."""

    payload = _load_json(path, "Final model registry")

    if not isinstance(payload, dict):
        raise DashboardDataError("Final model registry must contain a JSON object.")

    required_keys = {
        "metadata",
        "deployment_roles",
        "risk_and_volatility",
        "direction_probability",
        "foundation_benchmarks",
    }
    missing_keys = required_keys.difference(payload)

    if missing_keys:
        missing_text = ", ".join(sorted(missing_keys))
        raise DashboardDataError(f"Final model registry is missing keys: {missing_text}")

    return payload


def load_classical_registry(path: Path) -> list[dict[str, Any]]:
    """Load the validation-selected classical model registry."""

    payload = _load_json(path, "Classical model registry")

    if not isinstance(payload, list):
        raise DashboardDataError("Classical model registry must contain a JSON list.")

    if not payload:
        raise DashboardDataError("Classical model registry is empty.")

    required_keys = {
        "ticker",
        "selected_model",
        "selection_rule",
        "validation",
        "test",
    }

    for row in payload:
        if not isinstance(row, dict):
            raise DashboardDataError("Classical model registry contains an invalid row.")

        missing_keys = required_keys.difference(row)
        if missing_keys:
            missing_text = ", ".join(sorted(missing_keys))
            raise DashboardDataError(
                f"Classical model registry row is missing keys: {missing_text}"
            )

    tickers = [str(row["ticker"]) for row in payload]
    if len(tickers) != len(set(tickers)):
        raise DashboardDataError("Classical model registry contains duplicate tickers.")

    return payload


def load_evidence(path: Path, artifact_name: str) -> dict[str, Any]:
    """Load one foundation-model evidence artifact."""

    payload = _load_json(path, artifact_name)

    if not isinstance(payload, dict):
        raise DashboardDataError(f"{artifact_name} must contain a JSON object.")

    return payload


def validate_runtime_alignment(
    analytics: pd.DataFrame,
    risk_snapshot: pd.DataFrame,
    direction_snapshot: pd.DataFrame,
) -> None:
    """Validate ticker and date alignment across runtime artifacts."""

    analytics_tickers = set(analytics["ticker"].astype(str))
    risk_tickers = set(risk_snapshot["ticker"].astype(str))
    direction_tickers = set(direction_snapshot["ticker"].astype(str))

    if risk_tickers != analytics_tickers:
        raise DashboardDataError("Risk snapshot ticker universe does not match analytics.")

    if direction_tickers != analytics_tickers:
        raise DashboardDataError("Direction snapshot ticker universe does not match analytics.")

    analytics_date = pd.Timestamp(analytics["trade_date"].max())
    risk_dates = set(pd.to_datetime(risk_snapshot["as_of_date"]))
    direction_dates = set(pd.to_datetime(direction_snapshot["as_of_date"]))

    if risk_dates != {analytics_date}:
        raise DashboardDataError("Risk snapshot date does not match the latest analytics date.")

    if direction_dates != {analytics_date}:
        raise DashboardDataError(
            "Direction snapshot date does not match the latest analytics date."
        )

    training_before_inference = (
        direction_snapshot["training_end_date"]
        < direction_snapshot["as_of_date"]
    ).all()
    if not training_before_inference:
        raise DashboardDataError("Direction training period overlaps its inference date.")


def validate_registry_alignment(
    runtime_tickers: set[str],
    final_registry: dict[str, Any],
    classical_registry: list[dict[str, Any]],
) -> None:
    """Validate that committed registries cover the runtime ticker universe."""

    classical_tickers = {str(row["ticker"]) for row in classical_registry}
    if classical_tickers != runtime_tickers:
        raise DashboardDataError(
            "Classical model registry ticker universe does not match runtime data."
        )

    risk_entries = final_registry["risk_and_volatility"].get("tickers", [])
    direction_entries = final_registry["direction_probability"].get("tickers", [])

    risk_tickers = {
        str(row.get("ticker"))
        for row in risk_entries
        if isinstance(row, dict)
    }
    direction_tickers = {
        str(row.get("ticker"))
        for row in direction_entries
        if isinstance(row, dict)
    }

    if risk_tickers != runtime_tickers:
        raise DashboardDataError(
            "Final risk registry ticker universe does not match runtime data."
        )

    if direction_tickers != runtime_tickers:
        raise DashboardDataError(
            "Final direction registry ticker universe does not match runtime data."
        )


def load_dashboard_data(project_root: Path) -> DashboardData:
    """Load and validate all dashboard data and model evidence."""

    paths = DashboardPaths.from_project_root(project_root)

    analytics = load_analytics(paths.analytics)
    risk_snapshot = load_risk_snapshot(paths.risk_snapshot)
    direction_snapshot = load_direction_snapshot(paths.direction_snapshot)

    validate_runtime_alignment(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
    )

    final_registry = load_final_registry(paths.final_registry)
    classical_registry = load_classical_registry(paths.classical_registry)

    validate_registry_alignment(
        runtime_tickers=set(analytics["ticker"].astype(str)),
        final_registry=final_registry,
        classical_registry=classical_registry,
    )

    return DashboardData(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
        final_registry=final_registry,
        classical_registry=classical_registry,
        kronos_evidence=load_evidence(paths.kronos_evidence, "Kronos evidence"),
        granite_evidence=load_evidence(paths.granite_evidence, "Granite evidence"),
    )
