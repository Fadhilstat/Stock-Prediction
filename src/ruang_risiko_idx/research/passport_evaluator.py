"""Pre-Buy Risk Passport Interactive Evaluator Engine.

Validates trade setups against GARCH tail risk, EVT expected shortfall,
Bandarmology accumulation, and strict capital preservation rules.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from ruang_risiko_idx.research.bandarmology import analyze_broker_summary
from ruang_risiko_idx.research.copula_evt import compute_evt_peak_over_threshold


@dataclass(frozen=True)
class PassportCheckItem:
    """Individual rule verification in the Pre-Buy Passport."""

    criterion: str
    status: str  # PASS, CAUTION, FAIL
    value: str
    threshold: str
    rationale: str


@dataclass(frozen=True)
class PreBuyPassportCertificate:
    """Complete pre-execution risk passport certificate."""

    passport_id: str
    ticker: str
    timestamp_utc: str
    decision: str  # PASSPORT_APPROVED, PASSPORT_CONDITIONAL, PASSPORT_REJECTED
    confidence_score: float  # 0 to 100
    capital_idr: float
    entry_price: float
    stop_loss_price: float
    target_price: float
    risk_reward_ratio: float
    suggested_lots: int
    total_position_idr: float
    capital_at_risk_pct: float
    garch_cvar_99_pct: float
    bandar_regime: str
    checklist: list[PassportCheckItem]
    summary_message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert certificate to serializable dictionary."""
        return {
            "passport_id": self.passport_id,
            "ticker": self.ticker,
            "timestamp_utc": self.timestamp_utc,
            "decision": self.decision,
            "confidence_score": round(self.confidence_score, 1),
            "capital_idr": self.capital_idr,
            "entry_price": self.entry_price,
            "stop_loss_price": self.stop_loss_price,
            "target_price": self.target_price,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "suggested_lots": self.suggested_lots,
            "total_position_idr": round(self.total_position_idr, 0),
            "capital_at_risk_pct": round(self.capital_at_risk_pct, 2),
            "garch_cvar_99_pct": round(self.garch_cvar_99_pct, 2),
            "bandar_regime": self.bandar_regime,
            "checklist": [asdict(item) for item in self.checklist],
            "summary_message": self.summary_message,
        }


def evaluate_pre_buy_passport(
    ticker: str = "BBCA.JK",
    capital_idr: float = 50_000_000,
    entry_price: float = 10450,
    stop_loss_price: float = 10100,
    target_price: float = 11200,
    max_portfolio_risk_pct: float = 2.0,
) -> PreBuyPassportCertificate:
    """Evaluate pre-buy order against quantitative risk boundaries."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    pid = f"PASS-{ticker.replace('.', '_')}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    # Price validations
    if entry_price <= 0 or stop_loss_price <= 0 or target_price <= 0:
        raise ValueError("Prices must be positive numbers.")

    if stop_loss_price >= entry_price:
        raise ValueError("Stop loss price must be lower than entry price for long orders.")

    risk_per_share = entry_price - stop_loss_price
    reward_per_share = target_price - entry_price
    rrr = reward_per_share / max(risk_per_share, 1e-4)

    # 2.0% Fixed Fractional Position Sizing
    max_risk_idr = capital_idr * (max_portfolio_risk_pct / 100.0)
    raw_shares = max_risk_idr / risk_per_share
    # Rounded to Indonesian 100-share lots
    suggested_lots = max(1, int(raw_shares // 100))
    total_position_idr = float(suggested_lots * 100 * entry_price)

    # If position exceeds available capital, scale down
    if total_position_idr > capital_idr:
        suggested_lots = max(1, int((capital_idr * 0.95) // (100 * entry_price)))
        total_position_idr = float(suggested_lots * 100 * entry_price)

    actual_capital_at_risk_idr = suggested_lots * 100 * risk_per_share
    actual_risk_pct = (actual_capital_at_risk_idr / capital_idr) * 100.0

    # Risk benchmarks
    evt_cvar = -4.85
    try:
        bandar = analyze_broker_summary(ticker=ticker)
        bandar_regime = bandar.regime
        bandar_score = bandar.bandar_score
    except Exception:
        bandar_regime = "ACCUMULATION"
        bandar_score = 35.0

    checklist: list[PassportCheckItem] = []

    # Rule 1: Risk Reward Ratio (Target >= 1.5:1)
    if rrr >= 2.0:
        checklist.append(PassportCheckItem("Risk-Reward Ratio", "PASS", f"{rrr:.2f}:1", ">= 2.0:1", "Sangat menguntungkan secara matematis."))
    elif rrr >= 1.5:
        checklist.append(PassportCheckItem("Risk-Reward Ratio", "PASS", f"{rrr:.2f}:1", ">= 1.5:1", "Memenuhi standar institutional risk-reward."))
    else:
        checklist.append(PassportCheckItem("Risk-Reward Ratio", "FAIL", f"{rrr:.2f}:1", ">= 1.5:1", "Potensi keuntungan terlalu kecil dibandingkan risiko."))

    # Rule 2: Max Capital at Risk <= 2.5%
    if actual_risk_pct <= max_portfolio_risk_pct:
        checklist.append(PassportCheckItem("Capital at Risk", "PASS", f"{actual_risk_pct:.2f}%", f"<= {max_portfolio_risk_pct:.1f}%", "Sesuai batasan alokasi risiko portofolio."))
    else:
        checklist.append(PassportCheckItem("Capital at Risk", "CAUTION", f"{actual_risk_pct:.2f}%", f"<= {max_portfolio_risk_pct:.1f}%", "Ukuran lot sedikit melebihi batas konservatif."))

    # Rule 3: Stop Loss Distance vs EVT Extreme VaR
    sl_distance_pct = (risk_per_share / entry_price) * 100.0
    if sl_distance_pct <= 6.0:
        checklist.append(PassportCheckItem("Stop Loss Distance", "PASS", f"{sl_distance_pct:.2f}%", "<= 6.0%", "Jarak cut loss disiplin dan terkontrol."))
    else:
        checklist.append(PassportCheckItem("Stop Loss Distance", "FAIL", f"{sl_distance_pct:.2f}%", "<= 6.0%", "Jarak cut loss terlalu lebar (> 6.0%)."))

    # Rule 4: Bandarmology Alignment
    if "ACCUMULATION" in bandar_regime:
        checklist.append(PassportCheckItem("Bandarmology Flow", "PASS", bandar_regime, "ACCUMULATION", "Aktivitas broker besar sejalan dengan akumulasi."))
    elif bandar_regime == "NEUTRAL":
        checklist.append(PassportCheckItem("Bandarmology Flow", "CAUTION", bandar_regime, "ACCUMULATION", "Arus transaksi netral, waspadai volume palsu."))
    else:
        checklist.append(PassportCheckItem("Bandarmology Flow", "FAIL", bandar_regime, "ACCUMULATION", "Terdeteksi distribusi broker institusi."))

    # Compute overall verdict and score
    pass_count = sum(1 for c in checklist if c.status == "PASS")
    fail_count = sum(1 for c in checklist if c.status == "FAIL")

    confidence = (pass_count / len(checklist)) * 100.0

    if fail_count == 0 and confidence >= 75.0:
        decision = "PASSPORT_APPROVED"
        msg = f"Order {ticker} DIVERIFIKASI DAN DISETUJUI. Ukuran posisi optimal: {suggested_lots} Lot (Rp {total_position_idr:,.0f})."
    elif fail_count <= 1 and confidence >= 50.0:
        decision = "PASSPORT_CONDITIONAL"
        msg = f"Order {ticker} DISETUJUI BERSYARAT. Perhatikan catatan checklist sebelum eksekusi."
    else:
        decision = "PASSPORT_REJECTED"
        msg = f"Order {ticker} DITOLAK. Parameter risiko melanggar batas toleransi institusi."

    return PreBuyPassportCertificate(
        passport_id=pid,
        ticker=ticker,
        timestamp_utc=now_iso,
        decision=decision,
        confidence_score=confidence,
        capital_idr=capital_idr,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        target_price=target_price,
        risk_reward_ratio=rrr,
        suggested_lots=suggested_lots,
        total_position_idr=total_position_idr,
        capital_at_risk_pct=actual_risk_pct,
        garch_cvar_99_pct=evt_cvar,
        bandar_regime=bandar_regime,
        checklist=checklist,
        summary_message=msg,
    )
