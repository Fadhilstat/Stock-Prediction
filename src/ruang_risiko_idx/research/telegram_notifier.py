"""Telegram Notification and Automated Webhook Dispatcher for Ruang Risiko IDX.

Dispatches actionable quantitative alerts (Premarket Morning Briefing, Dynamic Trailing
Boundary ratchet notifications, DCC Contagion spikes, and Bi-Weekly model calibration audits)
directly to Telegram channels and private investor desks.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ruang_risiko_idx.research.actions import load_runtime_config, record_action


@dataclass(frozen=True)
class TelegramDispatchResult:
    """Outcome of a Telegram notification transmission."""

    success: bool
    status_code: int
    recipient_chat_id: str
    is_simulated: bool
    summary: str
    message_preview: str
    timestamp_utc: str


def format_morning_briefing_telegram(briefing_digest: Any) -> str:
    """Format Premarket Morning Briefing for mobile Telegram readability."""
    date_str = getattr(briefing_digest, "briefing_date", datetime.now(UTC).strftime("%Y-%m-%d"))
    tone = getattr(briefing_digest, "market_tone", "NEUTRAL")
    setups = getattr(briefing_digest, "top_setups", [])

    lines = [
        f"☀️ *RUANG RISIKO IDX: MORNING BRIEFING*",
        f"📅 Tanggal: `{date_str}` | Nada: *{tone}*",
        f"",
        f"🔍 *Top 3 Setup Peluang Saham Terpilih:*",
    ]

    for i, s in enumerate(setups[:3], start=1):
        ticker = getattr(s, "ticker", "N/A")
        price = getattr(s, "current_price", 0.0)
        prob = getattr(s, "prob_up_pct", 50.0)
        target = getattr(s, "q50_target", 0.0)
        inval = getattr(s, "invalidation_price", 0.0)
        state = getattr(s, "state", "WATCH")
        lines.append(
            f"{i}. *{ticker}* ({state})\n"
            f"   • Harga: Rp {price:,.0f} | Peluang Naik: *{prob:.1f}%*\n"
            f"   • Target q50: Rp {target:,.0f} | Batas Veto: Rp {inval:,.0f}"
        )

    lines.extend([
        f"",
        f"🛡️ *Dashboard Web:* https://rridx.fadhilrusydi.com",
        f"⚠️ _Probabilitas statistik terkalibrasi; bukan rekomendasi mutlak._",
    ])
    return "\n".join(lines)


def format_trailing_stop_telegram(
    ticker: str,
    current_price: float,
    trailing_price: float,
    stage: str,
    status: str,
) -> str:
    """Format Dynamic Trailing Stop Ratchet notification."""
    now_str = datetime.now(UTC).strftime("%H:%M WIB")
    alert_emoji = "🚨" if status == "TRIGGERED_EXIT" else "🛡️"

    lines = [
        f"{alert_emoji} *RUANG RISIKO IDX: DYNAMIC TRAILING ALERT*",
        f"Saham: *{ticker}* | Waktu: `{now_str}`",
        f"Status Ratchet: *{stage}* ({status})",
        f"",
        f"• Harga Terakhir: *Rp {current_price:,.0f}*",
        f"• Batas Trailing Aktif: *Rp {trailing_price:,.0f}*",
        f"",
        f"Kunjungi Console: https://rridx.fadhilrusydi.com",
    ]
    return "\n".join(lines)


def format_biweekly_audit_telegram(audit_summary: dict[str, Any]) -> str:
    """Format Bi-Weekly 14-day calibration audit outcome."""
    cycle = audit_summary.get("cycle_number", 1)
    brier = float(audit_summary.get("brier_score", 0.22))
    status = audit_summary.get("status", "HEALTHY")
    champion = audit_summary.get("champion_model", "random_forest")

    lines = [
        f"⏱️ *RUANG RISIKO IDX: AUDIT 14-HARI BI-WEEKLY*",
        f"Siklus: #{cycle} | Kalibrasi Model: *{status}*",
        f"• Brier Score: `{brier:.4f}` (Ambang Batas Maks: 0.2500)",
        f"• Model Juara Aktif: *{champion}*",
        f"",
        f"Audit ledger tersimpan permanen di reports/audit/.",
    ]
    return "\n".join(lines)


def format_dcc_contagion_alert(dcc_report: Any) -> str:
    """Format DCC Contagion Risk Alert."""
    sci = getattr(dcc_report, "systemic_contagion_index", 0.0)
    regime = getattr(dcc_report, "contagion_regime", "UNKNOWN")
    highest_pair = getattr(dcc_report, "highest_correlation_pair", None)
    pair_name = getattr(highest_pair, "pair", "N/A") if highest_pair else "N/A"
    pair_corr = getattr(highest_pair, "current_correlation", 0.0) if highest_pair else 0.0

    lines = [
        f"🌐 *RUANG RISIKO IDX: DCC-GARCH CONTAGION SPIKE*",
        f"Systemic Contagion Index (SCI): *{sci:.4f}*",
        f"Rezim Korelasi: *{regime}*",
        f"Pasangan Terkorelasi Tertinggi: *{pair_name}* (`{pair_corr:+.2f}`)",
        f"",
        f"Efek diversifikasi antar saham IDX berkurang saat SCI melonjak.",
    ]
    return "\n".join(lines)


def dispatch_telegram_message(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
    timeout_seconds: float = 5.0,
) -> TelegramDispatchResult:
    """Dispatch formatted markdown message to Telegram Bot API.

    Falls back cleanly to simulation mode if bot token is not configured or in testing environment,
    ensuring zero downtime and zero deployment blockers.
    """
    cfg = load_runtime_config()
    token = bot_token or os.getenv("RRIDX_TELEGRAM_BOT_TOKEN") or cfg.get("telegram_bot_token", "")
    target_chat = chat_id or os.getenv("RRIDX_TELEGRAM_CHAT_ID") or cfg.get("telegram_chat_id", "")
    now_iso = datetime.now(UTC).isoformat()
    preview = text[:80] + "..." if len(text) > 80 else text

    # Check whether live transmission or mock mode
    is_live = bool(token and target_chat and not token.startswith("MOCK") and not token.startswith("SIMULATED"))

    if not is_live:
        # Graceful simulated delivery (standard in automated testing and dev sandboxes)
        summary = "Telegram alert processed via simulated dispatcher (offline/dry-run mode)."
        record_action(
            action_type="TELEGRAM_ALERT_DISPATCH",
            status="SUCCESS",
            summary_message=summary,
            parameters={"chat_id": target_chat or "SIMULATED_CHANNEL", "preview": preview, "mode": "SIMULATION"},
        )
        return TelegramDispatchResult(
            success=True,
            status_code=200,
            recipient_chat_id=target_chat or "SIMULATED_CHANNEL",
            is_simulated=True,
            summary=summary,
            message_preview=preview,
            timestamp_utc=now_iso,
        )

    # Real HTTP POST to Telegram Bot API via standard library
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    encoded_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=encoded_data,
        headers={"Content-Type": "application/json", "User-Agent": "RuangRisikoIDX-Bot/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode()
            summary = f"Telegram alert successfully dispatched to chat {target_chat} (HTTP {status_code})."
            record_action(
                action_type="TELEGRAM_ALERT_DISPATCH",
                status="SUCCESS",
                summary_message=summary,
                parameters={"chat_id": target_chat, "preview": preview, "mode": "LIVE"},
            )
            return TelegramDispatchResult(
                success=True,
                status_code=status_code,
                recipient_chat_id=target_chat,
                is_simulated=False,
                summary=summary,
                message_preview=preview,
                timestamp_utc=now_iso,
            )
    except urllib.error.HTTPError as err:
        err_msg = f"Telegram API HTTP error {err.code}: {err.reason}."
        record_action(
            action_type="TELEGRAM_ALERT_DISPATCH",
            status="FAILED",
            summary_message=err_msg,
            parameters={"chat_id": target_chat, "preview": preview, "error_code": err.code},
        )
        return TelegramDispatchResult(
            success=False,
            status_code=err.code,
            recipient_chat_id=target_chat,
            is_simulated=False,
            summary=err_msg,
            message_preview=preview,
            timestamp_utc=now_iso,
        )
    except Exception as exc:
        err_msg = f"Telegram dispatch network exception: {str(exc)}."
        record_action(
            action_type="TELEGRAM_ALERT_DISPATCH",
            status="FAILED",
            summary_message=err_msg,
            parameters={"chat_id": target_chat, "preview": preview, "exception": str(exc)},
        )
        return TelegramDispatchResult(
            success=False,
            status_code=500,
            recipient_chat_id=target_chat,
            is_simulated=False,
            summary=err_msg,
            message_preview=preview,
            timestamp_utc=now_iso,
        )
