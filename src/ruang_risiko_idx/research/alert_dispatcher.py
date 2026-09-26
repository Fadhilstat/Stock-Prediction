"""Real-Time Outbound Webhook Alert Dispatcher for Risk Invalidation and System Events."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from ruang_risiko_idx.research.actions import record_action


@dataclass(frozen=True)
class AlertPayload:
    """Standardized event alert payload for outbound webhooks."""

    event_type: Literal["INVALIDATION_BREACH", "WARNING_PROXIMITY", "RETAIL_TRAP_DETECTED", "TEST_PING"]
    ticker: str
    current_price: float
    invalidation_price: float
    distance_percent: float
    message: str
    passport_id: str | None = None
    timestamp: str | None = None


def format_discord_payload(alert: AlertPayload) -> dict[str, Any]:
    """Format alert as a Discord webhook embed."""
    color_map = {
        "INVALIDATED_BREACH": 16724584,  # Red
        "WARNING_PROXIMITY": 16098859,   # Amber
        "RETAIL_TRAP_DETECTED": 16738657, # Purple-Red
        "TEST_PING": 2712319,            # Stockbit Blue
    }
    color = color_map.get(alert.event_type, 2712319)

    return {
        "username": "Ruang Risiko IDX Watchdog",
        "embeds": [
            {
                "title": f"🚨 {alert.event_type}: {alert.ticker}",
                "description": alert.message,
                "color": color,
                "fields": [
                    {"name": "Harga Terkini", "value": f"Rp {alert.current_price:,.0f}", "inline": True},
                    {"name": "Level Invalidasi", "value": f"Rp {alert.invalidation_price:,.0f}", "inline": True},
                    {"name": "Jarak Pengaman", "value": f"{alert.distance_percent:+.2f}%", "inline": True},
                    {"name": "Passport ID", "value": alert.passport_id or "N/A", "inline": False},
                ],
                "footer": {"text": "Ruang Risiko IDX Autonomous Risk Engine"},
                "timestamp": alert.timestamp or datetime.now(UTC).isoformat(),
            }
        ],
    }


def dispatch_webhook_alert(
    webhook_url: str,
    alert: AlertPayload,
    service_type: Literal["generic", "discord"] = "generic",
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Dispatch alert to an external HTTP webhook destination."""
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return {
            "success": False,
            "error": "Invalid webhook URL. Must start with http:// or https://.",
            "status_code": None,
        }

    ts = alert.timestamp or datetime.now(UTC).isoformat()
    alert_with_ts = AlertPayload(
        event_type=alert.event_type,
        ticker=alert.ticker,
        current_price=alert.current_price,
        invalidation_price=alert.invalidation_price,
        distance_percent=alert.distance_percent,
        message=alert.message,
        passport_id=alert.passport_id,
        timestamp=ts,
    )

    if service_type == "discord" or "discord.com/api/webhooks" in webhook_url:
        post_data = format_discord_payload(alert_with_ts)
    else:
        post_data = asdict(alert_with_ts)

    body_bytes = json.dumps(post_data).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "RuangRisikoIDX-AlertDispatcher/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status_code = resp.status
            msg = f"Alert {alert.event_type} dispatched successfully to webhook (Status {status_code})."
            record_action(
                action_type="WEBHOOK_ALERT_DISPATCH",
                status="SUCCESS",
                summary_message=msg,
                parameters={"ticker": alert.ticker, "event_type": alert.event_type, "status_code": status_code},
            )
            return {"success": True, "status_code": status_code, "message": msg}
    except Exception as exc:
        err_msg = f"Failed to dispatch alert to webhook: {exc}"
        record_action(
            action_type="WEBHOOK_ALERT_DISPATCH",
            status="FAILED",
            summary_message=err_msg,
            parameters={"ticker": alert.ticker, "event_type": alert.event_type, "error": str(exc)},
        )
        return {"success": False, "status_code": getattr(exc, "code", None), "error": str(exc)}
