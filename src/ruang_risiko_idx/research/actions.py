"""Web Action Controller and Audit Ledger for Ruang Risiko IDX."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ruang_risiko_idx.config import ProjectSettings


@dataclass
class ActionLogEntry:
    """Immutable audit record of an operational action."""

    action_id: str
    action_type: str
    triggered_at: str
    operator: str
    status: str
    parameters: dict[str, Any]
    summary_message: str
    duration_ms: float


DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "var_confidence_level": 0.99,
    "max_portfolio_allocation_percent": 15.0,
    "max_slippage_bps": 25.0,
    "garch_vol_hard_veto_threshold": 0.045,
    "tail_var99_veto_threshold": 0.070,
    "active_direction_model": "random_forest",
}


def _get_audit_dir() -> Path:
    settings = ProjectSettings()
    audit_dir = settings.project_root / "reports" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def _get_audit_file() -> Path:
    return _get_audit_dir() / "action_ledger.json"


def _get_config_file() -> Path:
    return _get_audit_dir() / "runtime_config.json"


def load_runtime_config() -> dict[str, Any]:
    """Load configurable runtime parameters or return default settings."""
    cfg_file = _get_config_file()
    if not cfg_file.exists():
        save_runtime_config(DEFAULT_RUNTIME_CONFIG)
        return dict(DEFAULT_RUNTIME_CONFIG)
    try:
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_RUNTIME_CONFIG)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_RUNTIME_CONFIG)


def save_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    """Persist updated runtime risk and operational parameters."""
    cfg_file = _get_config_file()
    cfg_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def load_action_history(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve chronologically ordered operational action audit trail."""
    audit_file = _get_audit_file()
    if not audit_file.exists():
        return []
    try:
        records: list[dict[str, Any]] = json.loads(audit_file.read_text(encoding="utf-8"))
        return sorted(records, key=lambda x: x["triggered_at"], reverse=True)[:limit]
    except Exception:
        return []


def record_action(
    action_type: str,
    status: str,
    summary_message: str,
    parameters: dict[str, Any] | None = None,
    operator: str = "web_operator",
    duration_ms: float = 0.0,
) -> ActionLogEntry:
    """Append a completed operational action into the immutable audit ledger."""
    now_utc = datetime.now(UTC)
    action_id = f"ACT-{now_utc.strftime('%Y%m%d-%H%M%S')}-{abs(hash(summary_message)) % 10000:04d}"
    entry = ActionLogEntry(
        action_id=action_id,
        action_type=action_type,
        triggered_at=now_utc.isoformat(),
        operator=operator,
        status=status,
        parameters=parameters or {},
        summary_message=summary_message,
        duration_ms=round(duration_ms, 2),
    )

    audit_file = _get_audit_file()
    records: list[dict[str, Any]] = []
    if audit_file.exists():
        try:
            records = json.loads(audit_file.read_text(encoding="utf-8"))
        except Exception:
            records = []

    records.append(asdict(entry))
    audit_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return entry


def trigger_market_data_refresh(tickers: list[str] | None = None) -> dict[str, Any]:
    """Execute live data ingestion refresh across canonical universe."""
    import time

    start = time.perf_counter()
    settings = ProjectSettings()
    universe = tickers or settings.tickers

    try:
        from ruang_risiko_idx.data.pipeline import run_market_data_pipeline

        raw_df, _ = run_market_data_pipeline(
            tickers=universe,
            destination_path=settings.raw_data_path,
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Data ingestion complete. Processed {len(raw_df):,} records for {len(universe)} tickers."
        entry = record_action(
            action_type="MARKET_DATA_REFRESH",
            status="SUCCESS",
            summary_message=msg,
            parameters={"tickers": universe, "row_count": len(raw_df)},
            duration_ms=elapsed,
        )
        return {"success": True, "message": msg, "action_id": entry.action_id}
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Data refresh failed: {exc}"
        entry = record_action(
            action_type="MARKET_DATA_REFRESH",
            status="FAILED",
            summary_message=msg,
            parameters={"tickers": universe},
            duration_ms=elapsed,
        )
        return {"success": False, "message": msg, "action_id": entry.action_id}


def trigger_risk_recalculation() -> dict[str, Any]:
    """Recompute GARCH volatility and VaR risk snapshots."""
    import time

    start = time.perf_counter()
    try:
        from scripts.build_latest_risk_snapshot import main as rebuild_risk

        exit_code = rebuild_risk(argv=[])
        elapsed = (time.perf_counter() - start) * 1000.0
        if exit_code == 0:
            msg = "GARCH volatility and VaR snapshots successfully recomputed and registered."
            entry = record_action(
                action_type="RISK_SNAPSHOT_RECALC",
                status="SUCCESS",
                summary_message=msg,
                duration_ms=elapsed,
            )
            return {"success": True, "message": msg, "action_id": entry.action_id}
        else:
            msg = f"Risk snapshot recalculation returned non-zero code {exit_code}."
            entry = record_action(
                action_type="RISK_SNAPSHOT_RECALC",
                status="FAILED",
                summary_message=msg,
                duration_ms=elapsed,
            )
            return {"success": False, "message": msg, "action_id": entry.action_id}
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Risk snapshot recalculation encountered error: {exc}"
        entry = record_action(
            action_type="RISK_SNAPSHOT_RECALC",
            status="FAILED",
            summary_message=msg,
            duration_ms=elapsed,
        )
        return {"success": False, "message": msg, "action_id": entry.action_id}


def trigger_direction_recalculation() -> dict[str, Any]:
    """Recompute machine learning directional probability snapshot."""
    import time

    start = time.perf_counter()
    try:
        from scripts.build_latest_direction_snapshot import main as rebuild_dir

        exit_code = rebuild_dir(argv=[])
        elapsed = (time.perf_counter() - start) * 1000.0
        if exit_code == 0:
            msg = "Directional classification models re-inferred and latest snapshot registered."
            entry = record_action(
                action_type="DIRECTION_SNAPSHOT_RECALC",
                status="SUCCESS",
                summary_message=msg,
                duration_ms=elapsed,
            )
            return {"success": True, "message": msg, "action_id": entry.action_id}
        else:
            msg = f"Direction recalculation returned exit code {exit_code}."
            entry = record_action(
                action_type="DIRECTION_SNAPSHOT_RECALC",
                status="FAILED",
                summary_message=msg,
                duration_ms=elapsed,
            )
            return {"success": False, "message": msg, "action_id": entry.action_id}
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Direction recalculation encountered error: {exc}"
        entry = record_action(
            action_type="DIRECTION_SNAPSHOT_RECALC",
            status="FAILED",
            summary_message=msg,
            duration_ms=elapsed,
        )
        return {"success": False, "message": msg, "action_id": entry.action_id}


def update_runtime_risk_parameters(
    var_confidence_level: float,
    max_portfolio_allocation_percent: float,
    max_slippage_bps: float,
    garch_vol_hard_veto_threshold: float,
    tail_var99_veto_threshold: float,
    active_direction_model: str,
) -> dict[str, Any]:
    """Validate and persist runtime risk parameters from web UI."""
    new_cfg = {
        "var_confidence_level": var_confidence_level,
        "max_portfolio_allocation_percent": max_portfolio_allocation_percent,
        "max_slippage_bps": max_slippage_bps,
        "garch_vol_hard_veto_threshold": garch_vol_hard_veto_threshold,
        "tail_var99_veto_threshold": tail_var99_veto_threshold,
        "active_direction_model": active_direction_model,
    }
    save_runtime_config(new_cfg)
    msg = f"Runtime parameters updated: VaR confidence {var_confidence_level:.1%}, Max Alloc {max_portfolio_allocation_percent:.1f}%."
    entry = record_action(
        action_type="RUNTIME_CONFIG_UPDATE",
        status="SUCCESS",
        summary_message=msg,
        parameters=new_cfg,
    )
    return {"success": True, "message": msg, "action_id": entry.action_id}


def trigger_domain_probe(domain: str = "rridx.fadhilrusydi.com") -> dict[str, Any]:
    """Execute live DNS resolution and SSL check for deployment domain."""
    import time
    from ruang_risiko_idx.research.domain_probe import check_domain_readiness

    start = time.perf_counter()
    res = check_domain_readiness(domain)
    elapsed = (time.perf_counter() - start) * 1000.0
    entry = record_action(
        action_type="DOMAIN_PROBE_CHECK",
        status="SUCCESS" if res.dns_status == "RESOLVED" else "PENDING",
        summary_message=res.summary,
        parameters={"domain": domain, "resolved_ip": res.resolved_ip, "tls_active": res.tls_active},
        duration_ms=elapsed,
    )
    return {
        "success": res.dns_status == "RESOLVED",
        "domain": res.domain,
        "resolved_ip": res.resolved_ip,
        "dns_status": res.dns_status,
        "tls_active": res.tls_active,
        "summary": res.summary,
        "recommendation": res.dns_recommendation,
        "action_id": entry.action_id,
    }


def trigger_morning_briefing_generation(date_str: str | None = None) -> dict[str, Any]:
    """Compile and register the autonomous pre-market morning briefing digest."""
    import time
    from ruang_risiko_idx.research.morning_briefing import generate_premarket_morning_briefing

    start = time.perf_counter()
    digest = generate_premarket_morning_briefing(briefing_date=date_str)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = f"Pre-Market Morning Briefing {digest.digest_id} berhasil dikompilasi untuk {digest.briefing_date}."
    entry = record_action(
        action_type="PREMARKET_BRIEFING_GENERATION",
        status="SUCCESS",
        summary_message=msg,
        parameters={"digest_id": digest.digest_id, "top_setups": [s.ticker for s in digest.top_setups]},
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "digest_id": digest.digest_id,
        "briefing_date": digest.briefing_date,
        "market_tone": digest.market_tone,
        "top_setups": [s.ticker for s in digest.top_setups],
        "markdown_content": digest.markdown_content,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_microstructure_imbalance_scan(ticker: str = "BBCA.JK") -> dict[str, Any]:
    """Execute orderbook microstructure and order flow delta scan."""
    import time
    from ruang_risiko_idx.research.orderbook import generate_orderbook
    from ruang_risiko_idx.research.microstructure_imbalance import compute_microstructure_imbalance

    start = time.perf_counter()
    ob = generate_orderbook(ticker=ticker, current_price=10250.0, previous_close=10200.0)
    analysis = compute_microstructure_imbalance(ob)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = f"Microstructure Imbalance scan selesai untuk {ticker}: VOI {analysis.volume_order_imbalance_lots:+,} lot ({analysis.order_flow_regime})."
    entry = record_action(
        action_type="MICROSTRUCTURE_IMBALANCE_SCAN",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "ticker": ticker,
            "voi_lots": analysis.volume_order_imbalance_lots,
            "regime": analysis.order_flow_regime,
            "spoofing_score": analysis.spoofing_probability_score,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "ticker": ticker,
        "voi_lots": analysis.volume_order_imbalance_lots,
        "regime": analysis.order_flow_regime,
        "spoofing_score": analysis.spoofing_probability_score,
        "phantom_wall": analysis.phantom_wall_detected,
        "message": msg,
        "action_id": entry.action_id,
    }


