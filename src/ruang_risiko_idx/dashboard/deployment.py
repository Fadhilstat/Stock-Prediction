"""Load the committed deployment bundle while preserving dashboard validation."""

from __future__ import annotations

from pathlib import Path

from ruang_risiko_idx.dashboard.data_access import (
    DashboardData,
    DashboardPaths,
    load_analytics,
    load_classical_registry,
    load_direction_snapshot,
    load_evidence,
    load_final_registry,
    load_risk_snapshot,
    validate_registry_alignment,
    validate_runtime_alignment,
)

DEPLOYMENT_FILENAMES = (
    "analytics_daily.parquet",
    "latest_risk_snapshot.json",
    "latest_direction_snapshot.json",
)


def deployment_bundle_available(project_root: Path) -> bool:
    """Return True only when the three runtime deployment artifacts are present."""

    deployment_dir = project_root / "deployment"
    return all((deployment_dir / filename).exists() for filename in DEPLOYMENT_FILENAMES)


def load_deployment_dashboard_data(project_root: Path) -> DashboardData:
    """Load deployment runtime files with committed registries and model evidence."""

    deployment_dir = project_root / "deployment"
    standard_paths = DashboardPaths.from_project_root(project_root)

    analytics = load_analytics(deployment_dir / "analytics_daily.parquet")
    risk_snapshot = load_risk_snapshot(
        deployment_dir / "latest_risk_snapshot.json"
    )
    direction_snapshot = load_direction_snapshot(
        deployment_dir / "latest_direction_snapshot.json"
    )

    validate_runtime_alignment(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
    )

    final_registry = load_final_registry(standard_paths.final_registry)
    classical_registry = load_classical_registry(standard_paths.classical_registry)

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
        kronos_evidence=load_evidence(
            standard_paths.kronos_evidence,
            "Kronos evidence",
        ),
        granite_evidence=load_evidence(
            standard_paths.granite_evidence,
            "Granite evidence",
        ),
    )
