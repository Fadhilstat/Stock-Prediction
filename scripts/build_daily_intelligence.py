"""Build the daily intelligence artifact from market outputs and verified news metadata."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import yaml

from ruang_risiko_idx.dashboard.data_access import (
    load_analytics,
    load_direction_snapshot,
    load_risk_snapshot,
    validate_runtime_alignment,
)
from ruang_risiko_idx.intelligence.daily import build_daily_intelligence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYTICS = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"
DEFAULT_RISK = PROJECT_ROOT / "reports" / "risk" / "latest_risk_snapshot.json"
DEFAULT_DIRECTION = PROJECT_ROOT / "reports" / "ml" / "latest_direction_snapshot.json"
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "intelligence_sources.yml"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "intelligence" / "latest_daily_intelligence.json"
MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "RuangRisikoIDX/0.1 educational-market-risk-dashboard"


def parse_arguments() -> argparse.Namespace:
    """Parse paths and optional offline news fixture."""

    parser = argparse.ArgumentParser(description="Build the latest daily intelligence artifact.")
    parser.add_argument("--analytics", type=Path, default=DEFAULT_ANALYTICS)
    parser.add_argument("--risk", type=Path, default=DEFAULT_RISK)
    parser.add_argument("--direction", type=Path, default=DEFAULT_DIRECTION)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--news-json",
        type=Path,
        default=None,
        help="Optional local article metadata fixture. Network access is skipped when supplied.",
    )
    return parser.parse_args()


def load_source_config(path: Path) -> dict[str, Any]:
    """Load the source allowlist and keyword policy."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Intelligence source config must contain a mapping.")

    domains = payload.get("verified_domains")
    if not isinstance(domains, list) or not domains:
        raise ValueError("Intelligence source config must contain verified domains.")

    return payload


def _fetch_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    """Fetch one bounded JSON response with a short retry for transient failures."""

    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "")
                if "json" not in content_type.lower():
                    raise ValueError("News discovery response is not JSON.")

                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("News discovery response exceeded the size limit.")

                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("News discovery response must contain a JSON object.")
                return payload
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == 0:
                time.sleep(1.0)

    if last_error is None:
        raise RuntimeError("News discovery failed without an error detail.")
    raise RuntimeError("News discovery request failed after retry.") from last_error


def _match_keywords(title: str, keyword_map: dict[str, list[str]]) -> list[str]:
    """Return keys whose configured phrases appear in a headline."""

    lowered = title.casefold()
    matches: list[str] = []
    for key, phrases in keyword_map.items():
        if any(str(phrase).casefold() in lowered for phrase in phrases):
            matches.append(str(key))
    return sorted(matches)


def _host_matches_domain(hostname: str, domain: str) -> bool:
    """Allow a verified domain and its subdomains, but no unrelated host."""

    host = hostname.casefold().strip(".")
    allowed = domain.casefold().strip(".")
    return host == allowed or host.endswith(f".{allowed}")


def _article_from_gdelt(
    item: dict[str, Any],
    domain_config: dict[str, Any],
    ticker_keywords: dict[str, list[str]],
    macro_keywords: dict[str, list[str]],
) -> dict[str, Any] | None:
    """Convert GDELT metadata into the compact project news contract."""

    title = str(item.get("title", "")).strip()
    url = str(item.get("url", "")).strip()
    reported_domain = str(item.get("domain", "")).strip().lower()
    seen_date = str(item.get("seendate", "")).strip()
    expected_domain = str(domain_config["domain"]).lower()
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""

    metadata_domain_valid = _host_matches_domain(reported_domain, expected_domain)
    link_domain_valid = _host_matches_domain(hostname, expected_domain)
    if (
        not title
        or parsed_url.scheme != "https"
        or not metadata_domain_valid
        or not link_domain_valid
    ):
        return None

    configured_tickers = [str(value) for value in domain_config.get("tickers", [])]
    keyword_tickers = _match_keywords(title, ticker_keywords)
    tickers = sorted(set(configured_tickers).union(keyword_tickers))
    themes = _match_keywords(title, macro_keywords)

    return {
        "title": title,
        "url": url,
        "domain": expected_domain,
        "source_label": str(domain_config["label"]),
        "published_at": seen_date,
        "tickers": tickers,
        "themes": themes,
    }


def fetch_verified_news(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Discover metadata only from domains that were verified in the source policy."""

    discovery = config["news_discovery"]
    base_url = str(discovery["base_url"])
    timeout_seconds = int(discovery.get("timeout_seconds", 20))
    timespan = str(discovery.get("lookback", "3d"))
    max_records = int(discovery.get("max_records_per_domain", 20))
    pause_seconds = float(discovery.get("request_pause_seconds", 0.0))
    ticker_keywords = config.get("ticker_keywords", {})
    macro_keywords = config.get("macro_keywords", {})
    domain_configs = config["verified_domains"]

    articles: list[dict[str, Any]] = []
    failures: list[str] = []

    for index, domain_config in enumerate(domain_configs):
        domain = str(domain_config["domain"])
        params = {
            "query": f"domain:{domain}",
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "timespan": timespan,
            "sort": "datedesc",
        }
        url = f"{base_url}?{urlencode(params)}"

        try:
            payload = _fetch_json(url, timeout_seconds=timeout_seconds)
        except RuntimeError:
            failures.append(domain)
        else:
            raw_articles = payload.get("articles", [])
            if not isinstance(raw_articles, list):
                failures.append(domain)
            else:
                for raw_item in raw_articles:
                    if not isinstance(raw_item, dict):
                        continue
                    article = _article_from_gdelt(
                        raw_item,
                        domain_config=domain_config,
                        ticker_keywords=ticker_keywords,
                        macro_keywords=macro_keywords,
                    )
                    if article is not None:
                        articles.append(article)

        if pause_seconds > 0 and index < len(domain_configs) - 1:
            time.sleep(pause_seconds)

    return articles, failures


def load_news_fixture(path: Path) -> list[dict[str, Any]]:
    """Load article metadata for tests or reproducible offline builds."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("News fixture must contain a JSON list.")
    return [item for item in payload if isinstance(item, dict)]


def write_json_atomic(payload: object, destination: Path) -> None:
    """Write JSON through a temporary file before replacing the destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def main() -> int:
    """Build one daily intelligence artifact and report source availability."""

    args = parse_arguments()
    source_config = load_source_config(args.config)

    analytics = load_analytics(args.analytics)
    risk_snapshot = load_risk_snapshot(args.risk)
    direction_snapshot = load_direction_snapshot(args.direction)
    validate_runtime_alignment(analytics, risk_snapshot, direction_snapshot)

    if args.news_json is not None:
        news_items = load_news_fixture(args.news_json)
        failed_domains: list[str] = []
        news_mode = "offline_fixture"
    else:
        news_items, failed_domains = fetch_verified_news(source_config)
        news_mode = "gdelt_metadata_discovery"

    artifact = build_daily_intelligence(
        analytics=analytics,
        risk_snapshot=risk_snapshot,
        direction_snapshot=direction_snapshot,
        news_items=news_items,
        generated_at_utc=datetime.now(UTC),
    )
    artifact["news_discovery"] = {
        "mode": news_mode,
        "provider": source_config["news_discovery"]["provider"],
        "verified_source_count": len(source_config["verified_domains"]),
        "failed_domains": failed_domains,
        "article_count": len(artifact["news_items"]),
    }

    write_json_atomic(artifact, args.output)

    print("Daily intelligence artifact built successfully.")
    print(f"As of date: {artifact['as_of_date']}")
    print(f"News articles: {len(artifact['news_items'])}")
    if failed_domains:
        print(f"News domains unavailable in this run: {', '.join(failed_domains)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
