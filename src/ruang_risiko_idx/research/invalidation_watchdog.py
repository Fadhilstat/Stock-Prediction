"""Active Position and Invalidation Watchdog Engine for Issued Passports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ruang_risiko_idx.config import ProjectSettings


@dataclass(frozen=True)
class WatchdogAlert:
    """Real-time distance and alert state for an issued decision passport."""

    passport_id: str
    ticker: str
    current_price: float
    invalidation_price: float
    distance_percent: float
    distance_idr: float
    alert_level: Literal["SAFE_BUFFER", "WARNING_PROXIMITY", "INVALIDATED_BREACHED"]
    recommendation: str


def scan_active_passports_watchdog(
    current_prices: dict[str, float],
    passport_dir: Path | None = None,
) -> list[WatchdogAlert]:
    """Scan all persisted decision passports and calculate distance to invalidation."""
    if passport_dir is None:
        settings = ProjectSettings()
        passport_dir = settings.project_root / "reports" / "passports"

    if not passport_dir.exists():
        return []

    alerts: list[WatchdogAlert] = []

    for file_path in passport_dir.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            pass_id = file_path.stem

            ticker_match = re.search(r"Pre-Buy Decision Passport:\s*([A-Z0-9_\.]+)", content)
            if not ticker_match:
                continue
            ticker = ticker_match.group(1).replace("_", ".")

            inv_match = re.search(r"Level Invalidasi Kustom:\s*`Rp\s*([\d,]+)", content)
            if not inv_match:
                inv_match = re.search(r"daily close breaches Rp\s*([\d,]+)", content)

            if not inv_match:
                continue

            inv_str = inv_match.group(1).replace(",", "")
            inv_price = float(inv_str)

            cur_price = current_prices.get(ticker, inv_price * 1.05)
            dist_idr = cur_price - inv_price
            dist_pct = (dist_idr / cur_price) * 100.0 if cur_price > 0 else 0.0

            if dist_idr < 0:
                level = "INVALIDATED_BREACHED"
                rec = "TESIS BATAL: Harga telah menembus batas invalidasi. Lakukan cut loss defensif."
            elif dist_pct <= 3.0:
                level = "WARNING_PROXIMITY"
                rec = "WASPADA KETAT: Harga berada sangat dekat (<3%) dengan batas invalidasi tesis."
            else:
                level = "SAFE_BUFFER"
                rec = "AMAN: Posisi memiliki bantalan pengaman yang cukup di atas titik invalidasi."

            alerts.append(
                WatchdogAlert(
                    passport_id=pass_id,
                    ticker=ticker,
                    current_price=cur_price,
                    invalidation_price=inv_price,
                    distance_percent=round(dist_pct, 2),
                    distance_idr=round(dist_idr, 2),
                    alert_level=level,
                    recommendation=rec,
                )
            )
        except Exception:
            continue

    return sorted(alerts, key=lambda a: a.distance_percent)
