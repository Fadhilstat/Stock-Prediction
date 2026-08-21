"""Load and validate the optional daily intelligence artifact for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from ruang_risiko_idx.dashboard.data_access import DashboardDataError

CANONICAL_INTELLIGENCE_PATH = Path(
    "reports/intelligence/latest_daily_intelligence.json"
)
DEPLOYMENT_INTELLIGENCE_PATH = Path("deployment/latest_daily_intelligence.json")


def intelligence_path(project_root: Path) -> Path | None:
    """Prefer the canonical artifact and fall back to the deployment copy."""

    canonical = project_root / CANONICAL_INTELLIGENCE_PATH
    if canonical.exists():
        return canonical

    deployed = project_root / DEPLOYMENT_INTELLIGENCE_PATH
    if deployed.exists():
        return deployed

    return None


def _host_matches_domain(hostname: str, domain: str) -> bool:
    """Allow one source domain and its subdomains."""

    host = hostname.casefold().strip(".")
    allowed = domain.casefold().strip(".")
    return host == allowed or host.endswith(f".{allowed}")


def _validate_news_item(item: Any) -> None:
    """Validate compact article metadata without fetching article content."""

    if not isinstance(item, dict):
        raise DashboardDataError("Daily intelligence contains an invalid news item.")

    required = {"title", "url", "domain", "source_label", "tickers", "themes"}
    missing = required.difference(item)
    if missing:
        text = ", ".join(sorted(missing))
        raise DashboardDataError(f"Daily intelligence news item is missing: {text}")

    parsed = urlparse(str(item["url"]))
    domain = str(item["domain"])
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not hostname
        or not _host_matches_domain(hostname, domain)
    ):
        raise DashboardDataError("Daily intelligence contains an invalid news URL.")


def load_daily_intelligence(
    path: Path,
    latest_date: pd.Timestamp,
    tickers: tuple[str, ...],
) -> dict[str, Any]:
    """Load one intelligence artifact and align it with dashboard runtime data."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DashboardDataError("Daily intelligence artifact could not be read.") from error

    if not isinstance(payload, dict):
        raise DashboardDataError("Daily intelligence artifact must contain a JSON object.")

    if payload.get("schema_version") != 1:
        raise DashboardDataError("Daily intelligence uses an unsupported schema version.")

    if payload.get("generation_method") != "deterministic_rule_based":
        raise DashboardDataError("Daily intelligence generation method is unexpected.")

    artifact_date = pd.to_datetime(payload.get("as_of_date"), errors="coerce")
    if pd.isna(artifact_date):
        raise DashboardDataError("Daily intelligence contains an invalid as_of_date.")

    if pd.Timestamp(artifact_date) != pd.Timestamp(latest_date):
        raise DashboardDataError("Daily intelligence date does not match dashboard data.")

    ticker_briefs = payload.get("ticker_briefs")
    if not isinstance(ticker_briefs, dict):
        raise DashboardDataError("Daily intelligence is missing ticker briefs.")

    if set(ticker_briefs) != set(tickers):
        raise DashboardDataError(
            "Daily intelligence ticker universe does not match dashboard data."
        )

    for item in payload.get("news_items", []):
        _validate_news_item(item)

    synthesis = payload.get("synthesis")
    if not isinstance(synthesis, list) or not all(
        isinstance(value, str) for value in synthesis
    ):
        raise DashboardDataError("Daily intelligence synthesis is invalid.")

    return payload


def load_runtime_intelligence(
    project_root: Path,
    latest_date: pd.Timestamp,
    tickers: tuple[str, ...],
) -> dict[str, Any] | None:
    """Load intelligence when available without making it a core dashboard dependency."""

    path = intelligence_path(project_root)
    if path is None:
        return None

    return load_daily_intelligence(path, latest_date=latest_date, tickers=tickers)
