"""Load the committed deployment bundle while preserving dashboard validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ruang_risiko_idx.dashboard.data_access import (
    DashboardData,
    DashboardDataError,
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

RUNTIME_FILENAMES = (
    "analytics_daily.parquet",
    "latest_risk_snapshot.json",
    "latest_direction_snapshot.json",
)

DEPLOYMENT_FILENAMES = (*RUNTIME_FILENAMES, "manifest.json")

CANONICAL_RUNTIME_PATHS = (
    Path("data/processed/analytics_daily.parquet"),
    Path("reports/risk/latest_risk_snapshot.json"),
    Path("reports/ml/latest_direction_snapshot.json"),
)


def canonical_runtime_available(project_root: Path) -> bool:
    """Return True only when all canonical runtime artifacts are available."""

    return all((project_root / path).exists() for path in CANONICAL_RUNTIME_PATHS)


def deployment_bundle_available(project_root: Path) -> bool:
    """Return True only when the complete deployment bundle is present."""

    deployment_dir = project_root / "deployment"
    return all((deployment_dir / filename).exists() for filename in DEPLOYMENT_FILENAMES)


def _sha256_file(path: Path) -> str:
    """Calculate the SHA-256 digest used by the deployment manifest."""

    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    """Load the deployment manifest and reject an unsupported schema."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DashboardDataError("Deployment manifest could not be read.") from error

    if not isinstance(payload, dict):
        raise DashboardDataError("Deployment manifest must contain a JSON object.")

    if payload.get("schema_version") != 1:
        raise DashboardDataError("Deployment manifest uses an unsupported schema version.")

    return payload


def _validate_manifest_files(
    deployment_dir: Path,
    manifest: dict[str, Any],
) -> None:
    """Verify that runtime files still match the bundle that was published."""

    file_hashes = manifest.get("files")
    if not isinstance(file_hashes, dict):
        raise DashboardDataError("Deployment manifest is missing file checksums.")

    if set(file_hashes) != set(RUNTIME_FILENAMES):
        raise DashboardDataError("Deployment manifest file list is inconsistent.")

    for filename in RUNTIME_FILENAMES:
        expected_digest = file_hashes.get(filename)
        actual_digest = _sha256_file(deployment_dir / filename)
        if not isinstance(expected_digest, str) or actual_digest != expected_digest:
            raise DashboardDataError(
                f"Deployment bundle checksum does not match for {filename}."
            )


def _validate_manifest_summary(
    manifest: dict[str, Any],
    analytics: Any,
) -> None:
    """Check manifest counts and date against the validated analytics table."""

    latest_date = analytics["trade_date"].max().date().isoformat()
    analytics_rows = int(len(analytics))
    ticker_count = int(analytics["ticker"].nunique())

    if manifest.get("latest_trade_date") != latest_date:
        raise DashboardDataError("Deployment manifest trade date is inconsistent.")

    if manifest.get("analytics_rows") != analytics_rows:
        raise DashboardDataError("Deployment manifest analytics row count is inconsistent.")

    if manifest.get("ticker_count") != ticker_count:
        raise DashboardDataError("Deployment manifest ticker count is inconsistent.")


def load_deployment_dashboard_data(project_root: Path) -> DashboardData:
    """Load deployment runtime files with committed registries and model evidence."""

    deployment_dir = project_root / "deployment"
    standard_paths = DashboardPaths.from_project_root(project_root)

    if not deployment_bundle_available(project_root):
        raise DashboardDataError("Deployment bundle is incomplete.")

    manifest = _load_manifest(deployment_dir / "manifest.json")
    _validate_manifest_files(deployment_dir, manifest)

    analytics = load_analytics(deployment_dir / "analytics_daily.parquet")
    risk_snapshot = load_risk_snapshot(
        deployment_dir / "latest_risk_snapshot.json"
    )
    direction_snapshot = load_direction_snapshot(
        deployment_dir / "latest_direction_snapshot.json"
    )

    _validate_manifest_summary(manifest, analytics)

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
