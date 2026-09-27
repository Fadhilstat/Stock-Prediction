"""Automated Institutional Signal & Microstructure Alert Dispatcher.

Monitors real-time anomalies including institutional stealth accumulation,
Shannon entropy discord, conformal bound breakouts, and orderbook spoofing.
Dispatches structured alerts for web terminal display and external webhook/Telegram integrations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from ruang_risiko_idx.research.broker_network import broker_network_analyzer
from ruang_risiko_idx.research.hf_finbert_sentiment import finbert_calibrator
from ruang_risiko_idx.research.hf_foundation_forecaster import hf_forecaster
from ruang_risiko_idx.research.multimodal_engine import STOCK_CATALOG_MAP
from ruang_risiko_idx.research.stress_testing import stress_engine


@dataclass
class MarketAlert:
    """Structured actionable alert payload."""

    alert_id: str
    ticker: str
    alert_type: str  # STEALTH_ACCUMULATION, SHANNON_DISCORD, CONFORMAL_BREAKOUT, SPOOFING_RISK, STRESS_VULNERABLE
    severity: str  # INFO, WARNING, CRITICAL
    title: str
    message: str
    actionable_step: str
    metric_value: str
    detected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AlertDispatcher:
    """Continuously evaluates anomaly criteria and dispatches market alerts."""

    MONITORED_TICKERS = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "ANTM.JK", "GOTO.JK"]

    def scan_active_alerts(self, tickers: list[str] | None = None) -> list[MarketAlert]:
        """Scan target universe for high-confidence institutional anomalies."""
        active = tickers or self.MONITORED_TICKERS
        alerts: list[MarketAlert] = []

        now_iso = datetime.now(timezone.utc).isoformat()

        for t in active:
            meta = STOCK_CATALOG_MAP.get(t, {"name": t, "base_price": 5000, "sector": "Other"})
            base_px = float(meta.get("base_price", 5000))
            sector = str(meta.get("sector", "Other"))

            # 1. Check Broker Cluster Network & Whale Accumulation
            bn = broker_network_analyzer.analyze_ticker_network(t, base_px)
            if bn.smart_money_index >= 45.0 and bn.absorption_ratio >= 1.5:
                whales = [w.code for w in bn.top_foreign_whales if w.action_type == "ACCUMULATION"]
                alerts.append(
                    MarketAlert(
                        alert_id=f"ALT-STEALTH-{t}",
                        ticker=t,
                        alert_type="STEALTH_ACCUMULATION",
                        severity="INFO",
                        title=f"Akumulasi Senyap Whale Asing Terdeteksi di {t}",
                        message=f"Paus asing ({', '.join(whales)}) menyerap likuiditas ritel agresif dengan rasio penyerapan {bn.absorption_ratio:.2f}x dan SMI {bn.smart_money_index:.1f}.",
                        actionable_step="Pertimbangkan entry bertahap mengikuti jejak akumulasi whale asing.",
                        metric_value=f"Absorption {bn.absorption_ratio:.2f}x | SMI +{bn.smart_money_index:.1f}",
                        detected_at=now_iso,
                    )
                )

            # 2. Check Orderbook Spoofing Risk
            if bn.spoofing_risk_score >= 0.45:
                alerts.append(
                    MarketAlert(
                        alert_id=f"ALT-SPOOF-{t}",
                        ticker=t,
                        alert_type="SPOOFING_RISK",
                        severity="WARNING",
                        title=f"Waspada Potensi Phantom Bids / Spoofing di {t}",
                        message=f"Orderbook menunjukkan asimetri antrian bid artifisial dengan skor risiko spoofing {(bn.spoofing_risk_score * 100):.0f}%.",
                        actionable_step="Hindari market buy agresif, pasang limit order di level support kuat.",
                        metric_value=f"Spoofing Risk {(bn.spoofing_risk_score * 100):.0f}%",
                        detected_at=now_iso,
                    )
                )

            # 3. Check FinBERT Shannon Entropy Discord
            fb = finbert_calibrator.analyze_market_polarization(t)
            if fb.market_entropy >= 1.15 and fb.polarization_index >= 0.20:
                alerts.append(
                    MarketAlert(
                        alert_id=f"ALT-ENTROPY-{t}",
                        ticker=t,
                        alert_type="SHANNON_DISCORD",
                        severity="WARNING",
                        title=f"Lonjakan Entropi FinBERT (Polarisasi Opini Tinggi) di {t}",
                        message=f"Entropi informasi mencapai {fb.market_entropy:.2f} nats dengan indeks polarisasi {fb.polarization_index:.2f}. Pengali volatilitas dinaikkan menjadi {fb.volatility_scale_factor:.2f}x.",
                        actionable_step="Perlebar toleransi stop-loss atau kurangi size posisi menjelang rilis katalis.",
                        metric_value=f"Entropy {fb.market_entropy:.2f} nats | Scale {fb.volatility_scale_factor:.2f}x",
                        detected_at=now_iso,
                    )
                )

            # 4. Check Conformal Model Forecast Breakout
            fc = hf_forecaster.run_tournament(t, horizon_days=5)
            if fc.forecast_points and fc.forecast_points[-1].projected_drift_pct >= 4.0:
                drift = fc.forecast_points[-1].projected_drift_pct
                alerts.append(
                    MarketAlert(
                        alert_id=f"ALT-BREAKOUT-{t}",
                        ticker=t,
                        alert_type="CONFORMAL_BREAKOUT",
                        severity="INFO",
                        title=f"Peluang Breakout Model Champion ({fc.champion_model_name}) di {t}",
                        message=f"Proyeksi drift forward mencapai +{drift:.1f}% dengan batas keyakinan conformal {fc.conformal_coverage_pct:.0f}%.",
                        actionable_step="Siapkan trailing stop untuk mengunci potensi profit swing.",
                        metric_value=f"Drift +{drift:.1f}% | RMSE Rp {fc.champion_metrics.rmse:,.0f}",
                        detected_at=now_iso,
                    )
                )

            # 5. Check Systemic Stress Vulnerability
            st = stress_engine.run_full_stress_test(t, base_px, sector)
            if st.composite_vulnerability_score >= 65.0:
                alerts.append(
                    MarketAlert(
                        alert_id=f"ALT-STRESS-{t}",
                        ticker=t,
                        alert_type="STRESS_VULNERABLE",
                        severity="CRITICAL",
                        title=f"Kerentanan Tail Risk Tinggi pada Skenario Krisis di {t}",
                        message=f"Skor kerentanan gabungan mencapai {st.composite_vulnerability_score:.1f}/100. Sensitif terhadap guncangan The Fed dan likuiditas.",
                        actionable_step="Wajib lindung nilai (hedging) menggunakan cash buffer atau instrumen defensif.",
                        metric_value=f"Vulnerability {st.composite_vulnerability_score:.1f}/100",
                        detected_at=now_iso,
                    )
                )

        # Sort: CRITICAL first, then WARNING, then INFO
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        return alerts

    scan_universe = scan_active_alerts


# Global singleton
alert_dispatcher = AlertDispatcher()
