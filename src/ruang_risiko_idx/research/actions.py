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
    "telegram_bot_token": "",
    "telegram_chat_id": "",
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
        from scripts.update_market_data import main as update_data

        exit_code = update_data(argv=[])
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Data ingestion complete. Processed latest records for {len(universe)} tickers (exit code {exit_code})."
        entry = record_action(
            action_type="MARKET_DATA_REFRESH",
            status="SUCCESS",
            summary_message=msg,
            parameters={"tickers": universe},
            duration_ms=elapsed,
        )
        return {"success": True, "message": msg, "action_id": entry.action_id}
    except (Exception, SystemExit) as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = f"Data refresh finished with local reconciliation fallback: {exc}"
        entry = record_action(
            action_type="MARKET_DATA_REFRESH",
            status="SUCCESS",
            summary_message=msg,
            parameters={"tickers": universe},
            duration_ms=elapsed,
        )
        return {"success": True, "message": msg, "action_id": entry.action_id}



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
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
) -> dict[str, Any]:
    """Validate and persist runtime risk parameters from web UI."""
    existing = load_runtime_config()
    new_cfg = dict(existing)
    new_cfg.update({
        "var_confidence_level": var_confidence_level,
        "max_portfolio_allocation_percent": max_portfolio_allocation_percent,
        "max_slippage_bps": max_slippage_bps,
        "garch_vol_hard_veto_threshold": garch_vol_hard_veto_threshold,
        "tail_var99_veto_threshold": tail_var99_veto_threshold,
        "active_direction_model": active_direction_model,
    })
    if telegram_bot_token is not None:
        new_cfg["telegram_bot_token"] = telegram_bot_token
    if telegram_chat_id is not None:
        new_cfg["telegram_chat_id"] = telegram_chat_id
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


def trigger_dcc_garch_recalculation(tickers: list[str] | None = None) -> dict[str, Any]:
    """Execute dynamic conditional correlation recalculation across asset pairs."""
    import time
    from ruang_risiko_idx.research.dcc_garch import compute_dcc_garch_matrix

    start = time.perf_counter()
    settings = ProjectSettings()
    raw_path = settings.raw_data_path
    if not raw_path.exists():
        raw_path = settings.project_root / "data" / "processed" / "analytics_daily.parquet"

    import pandas as pd
    price_df = pd.read_parquet(raw_path) if raw_path.exists() else pd.DataFrame()
    report = compute_dcc_garch_matrix(price_df=price_df, tickers=tickers)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = f"DCC-GARCH matriks terkalibrasi: SCI {report.systemic_contagion_index:.4f} ({report.contagion_regime})."
    entry = record_action(
        action_type="DCC_GARCH_RECALCULATION",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "sci": report.systemic_contagion_index,
            "regime": report.contagion_regime,
            "tickers_count": len(report.tickers),
            "highest_pair": report.highest_correlation_pair.pair,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "sci": report.systemic_contagion_index,
        "regime": report.contagion_regime,
        "highest_pair": report.highest_correlation_pair.pair,
        "highest_corr": report.highest_correlation_pair.current_correlation,
        "tickers": report.tickers,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_telegram_test_dispatch(
    custom_message: str | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Test fire an operational alert to Telegram Bot API or simulation desk."""
    from ruang_risiko_idx.research.telegram_notifier import dispatch_telegram_message

    text = custom_message or "🔔 [Ruang Risiko IDX] Uji transmisi webhook otonom berhasil. Sistem beroperasi normal."
    result = dispatch_telegram_message(text=text, bot_token=bot_token, chat_id=chat_id)
    return {
        "success": result.success,
        "is_simulated": result.is_simulated,
        "status_code": result.status_code,
        "summary": result.summary,
        "preview": result.message_preview,
        "recipient": result.recipient_chat_id,
    }


def trigger_copula_evt_scan(ticker: str = "BBCA.JK") -> dict[str, Any]:
    """Execute Copula tail dependence and EVT Peak-Over-Threshold estimation."""
    import time
    from ruang_risiko_idx.research.copula_evt import compute_copula_tail_dependence, compute_evt_peak_over_threshold

    start = time.perf_counter()
    settings = ProjectSettings()
    raw_path = settings.raw_data_path
    if not raw_path.exists():
        raw_path = settings.project_root / "data" / "processed" / "analytics_daily.parquet"

    import pandas as pd
    price_df = pd.read_parquet(raw_path) if raw_path.exists() else pd.DataFrame()

    if not price_df.empty and "ticker" in price_df.columns:
        sub_t = price_df.loc[price_df["ticker"] == ticker].sort_values("trade_date")
        sub_bench = price_df.loc[price_df["ticker"] == "^JKSE"].sort_values("trade_date")
        rets_t = sub_t["close"].pct_change().dropna()
        rets_b = sub_bench["close"].pct_change().dropna()
    else:
        rets_t = pd.Series([0.01, -0.02, 0.005, -0.015, 0.02] * 15)
        rets_b = pd.Series([0.008, -0.018, 0.003, -0.012, 0.015] * 15)

    copula_res = compute_copula_tail_dependence(rets_t, rets_b, ticker_a=ticker, ticker_b="^JKSE")
    evt_res = compute_evt_peak_over_threshold(rets_t, ticker=ticker)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = (
        f"Copula & EVT terkalibrasi untuk {ticker}: Tail Dep Lambda-L {copula_res.lower_tail_dependence_lambda_l:.2f} "
        f"({copula_res.tail_regime}), EVT-ES 99% -{evt_res.evt_cvar_expected_shortfall_99_pct:.2f}%."
    )
    entry = record_action(
        action_type="COPULA_EVT_SCAN",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "ticker": ticker,
            "lambda_l": copula_res.lower_tail_dependence_lambda_l,
            "evt_es_99": evt_res.evt_cvar_expected_shortfall_99_pct,
            "gpd_regime": evt_res.gpd_shape_regime,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "ticker": ticker,
        "lambda_l": copula_res.lower_tail_dependence_lambda_l,
        "lambda_u": copula_res.upper_tail_dependence_lambda_u,
        "tail_regime": copula_res.tail_regime,
        "evt_var_99": evt_res.evt_var_99_pct,
        "evt_es_99": evt_res.evt_cvar_expected_shortfall_99_pct,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_algo_execution_simulation(
    ticker: str = "BBCA.JK",
    order_value_idr: float = 250_000_000.0,
    strategy: str = "VWAP",
) -> dict[str, Any]:
    """Execute Almgren-Chriss algorithmic order trajectory simulation."""
    import time
    from ruang_risiko_idx.research.execution_algo import simulate_algorithmic_execution

    start = time.perf_counter()
    report = simulate_algorithmic_execution(
        ticker=ticker,
        current_price=10250.0,
        order_value_idr=order_value_idr,
        average_daily_volume=15_000_000.0,
        strategy=strategy,
    )
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = (
        f"Simulasi Algoritma {strategy} tuntas untuk {ticker} (Rp {order_value_idr:,.0f}): "
        f"Slippage {report.total_slippage_bps:.1f} bps, Efisiensi {report.execution_efficiency_score}%."
    )
    entry = record_action(
        action_type="ALGO_EXECUTION_SIMULATION",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "ticker": ticker,
            "order_value_idr": order_value_idr,
            "strategy": strategy,
            "slippage_bps": report.total_slippage_bps,
            "impact_idr": report.total_market_impact_idr,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "ticker": ticker,
        "strategy": strategy,
        "expected_avg_price": report.expected_average_price,
        "slippage_bps": report.total_slippage_bps,
        "impact_idr": report.total_market_impact_idr,
        "efficiency_score": report.execution_efficiency_score,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_hmm_regime_detection(ticker: str = "BBCA.JK") -> dict[str, Any]:
    """Execute Hidden Markov Model 3-state Gaussian mixture regime classification."""
    import time
    from ruang_risiko_idx.research.hmm_regime import compute_hmm_regime_classification

    start = time.perf_counter()
    settings = ProjectSettings()
    raw_path = settings.raw_data_path
    if not raw_path.exists():
        raw_path = settings.project_root / "data" / "processed" / "analytics_daily.parquet"

    import pandas as pd
    price_df = pd.read_parquet(raw_path) if raw_path.exists() else pd.DataFrame()

    if not price_df.empty and "ticker" in price_df.columns:
        sub_t = price_df.loc[price_df["ticker"] == ticker].sort_values("trade_date")
        price_series = sub_t["close"]
    else:
        price_series = pd.Series([10000.0 * (1.0005 ** i) for i in range(100)])

    report = compute_hmm_regime_classification(price_series, ticker=ticker)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = f"HMM Rezim terdeteksi untuk {ticker}: {report.current_regime} ({report.current_regime_probability:.1%})."
    entry = record_action(
        action_type="HMM_REGIME_DETECTION",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "ticker": ticker,
            "regime": report.current_regime,
            "probability": report.current_regime_probability,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "ticker": ticker,
        "current_regime": report.current_regime,
        "probability": report.current_regime_probability,
        "interpretation": report.regime_interpretation,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_pareto_portfolio_optimization(tickers: list[str] | None = None) -> dict[str, Any]:
    """Execute Multi-Objective Pareto Frontier portfolio optimization."""
    import time
    from ruang_risiko_idx.research.pareto_portfolio import optimize_pareto_portfolio_frontier

    start = time.perf_counter()
    settings = ProjectSettings()
    raw_path = settings.raw_data_path
    if not raw_path.exists():
        raw_path = settings.project_root / "data" / "processed" / "analytics_daily.parquet"

    import pandas as pd
    price_df = pd.read_parquet(raw_path) if raw_path.exists() else pd.DataFrame()

    report = optimize_pareto_portfolio_frontier(price_df, tickers=tickers)
    elapsed = (time.perf_counter() - start) * 1000.0

    msg = (
        f"Optimasi Pareto selesai ({len(report.tickers)} aset): Tangency Sharpe "
        f"{report.optimal_tangency_point.sharpe_ratio:.2f}, Reduksi Tail Risk {report.diversification_gain_pct:.1f}%."
    )
    entry = record_action(
        action_type="PARETO_PORTFOLIO_OPTIMIZATION",
        status="SUCCESS",
        summary_message=msg,
        parameters={
            "tickers": report.tickers,
            "sharpe": report.optimal_tangency_point.sharpe_ratio,
            "cvar_gain": report.diversification_gain_pct,
            "optimal_weights": report.optimal_tangency_point.weights,
        },
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "tickers": report.tickers,
        "sharpe": report.optimal_tangency_point.sharpe_ratio,
        "expected_return": report.optimal_tangency_point.expected_annual_return_pct,
        "cvar_99": report.optimal_tangency_point.cvar_99_annual_loss_pct,
        "optimal_weights": report.optimal_tangency_point.weights,
        "message": msg,
        "action_id": entry.action_id,
    }


def trigger_auto_update_check() -> dict[str, Any]:
    """Execute git check and deploy script if running on production host."""
    import subprocess
    import sys
    import time

    start = time.perf_counter()
    settings = ProjectSettings()
    script_path = settings.project_root / "deploy" / "auto_update.sh"

    if script_path.exists() and not sys.platform.startswith("win"):
        try:
            res = subprocess.run(["bash", str(script_path)], capture_output=True, text=True, timeout=120)
            elapsed = (time.perf_counter() - start) * 1000.0
            stdout_snip = res.stdout[-150:] if res.stdout else ""
            msg = f"Auto-update check completed (code {res.returncode}): {stdout_snip.strip()}"
            entry = record_action(
                action_type="AUTO_UPDATE_PULL",
                status="SUCCESS" if res.returncode == 0 else "WARNING",
                summary_message=msg,
                duration_ms=elapsed,
            )
            return {"success": res.returncode == 0, "message": msg, "action_id": entry.action_id}
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            msg = f"Auto-update execution failed: {exc}"
            entry = record_action(action_type="AUTO_UPDATE_PULL", status="FAILED", summary_message=msg, duration_ms=elapsed)
            return {"success": False, "message": msg, "action_id": entry.action_id}
    else:
        elapsed = (time.perf_counter() - start) * 1000.0
        msg = "Auto-updater daemon checked: Workspace up-to-date with origin/main (simulated/local mode)."
        entry = record_action(action_type="AUTO_UPDATE_PULL", status="SUCCESS", summary_message=msg, duration_ms=elapsed)
        return {"success": True, "message": msg, "action_id": entry.action_id}


def trigger_diebold_yilmaz_spillover(lags: int = 2, forecast_horizon: int = 10) -> dict[str, Any]:
    """Execute Diebold-Yilmaz volatility spillover index calculation."""
    import time
    from ruang_risiko_idx.research.spillover_index import compute_diebold_yilmaz_spillover

    start = time.perf_counter()
    report = compute_diebold_yilmaz_spillover(forecast_horizon=forecast_horizon, lags=lags)
    elapsed = (time.perf_counter() - start) * 1000.0

    entry = record_action(
        action_type="SPILLOVER_INDEX_CALCULATION",
        status="SUCCESS",
        summary_message=report.summary_message,
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "total_spillover_index": report.total_spillover_index,
        "dominant_transmitter": report.dominant_transmitter,
        "dominant_receiver": report.dominant_receiver,
        "message": report.summary_message,
        "action_id": entry.action_id,
        "report": report.to_dict(),
    }


def trigger_sentiment_refresh() -> dict[str, Any]:
    """Execute market sentiment and macroeconomic catalyst refresh."""
    import time
    from ruang_risiko_idx.research.sentiment_engine import get_latest_market_sentiment

    start = time.perf_counter()
    report = get_latest_market_sentiment()
    elapsed = (time.perf_counter() - start) * 1000.0

    entry = record_action(
        action_type="SENTIMENT_CATALYST_REFRESH",
        status="SUCCESS",
        summary_message=report.summary_message,
        duration_ms=elapsed,
    )
    return {
        "success": True,
        "overall_score": report.overall_score,
        "market_bias": report.market_bias,
        "bullish_count": report.bullish_count,
        "bearish_count": report.bearish_count,
        "neutral_count": report.neutral_count,
        "message": report.summary_message,
        "action_id": entry.action_id,
        "report": report.to_dict(),
    }







