"""Interactive Pre-Buy Decision Passport Issuer and Digital Signature Registry."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from ruang_risiko_idx.config import ProjectSettings
from ruang_risiko_idx.research.actions import record_action
from ruang_risiko_idx.research.decision_passport import PreBuyDecisionPassport


def issue_custom_passport(
    ticker: str,
    company_name: str,
    cutoff_date: str,
    current_price: float,
    custom_invalidation: float,
    position_size_pct: float,
    horizon: str,
    operator_notes: str,
    base_passport: PreBuyDecisionPassport,
    operator_name: str = "web_operator",
) -> tuple[PreBuyDecisionPassport, Path]:
    """Issue, digitally sign, and persist a customized Pre-Buy Decision Passport."""
    settings = ProjectSettings()
    passport_dir = settings.project_root / "reports" / "passports"
    passport_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(UTC)
    timestamp_str = now_utc.strftime("%Y%m%d-%H%M%S")
    passport_id = f"PASSPORT-{ticker.replace('.', '_')}-{timestamp_str}"

    # Build signature hash
    raw_sig_payload = f"{passport_id}|{ticker}|{current_price}|{custom_invalidation}|{position_size_pct}|{operator_notes}"
    digital_signature = hashlib.sha256(raw_sig_payload.encode("utf-8")).hexdigest()[:16].upper()

    custom_md = f"""# Pre-Buy Decision Passport: {ticker} ({company_name})

**Passport ID:** `{passport_id}`
**Digital Signature Stamp:** `SHA256:{digital_signature}`
**Issued At:** `{now_utc.isoformat()}`
**Operator / Desk:** `{operator_name}`
**Market Cutoff Date:** `{cutoff_date}`

---

## 1. Executive Clearance & Hard Risk Gates
- **Harga Acuan Terakhir:** Rp {current_price:,.0f}
- **Status Keputusan Sistem:** `{base_passport.decision_state}`
- **Batas Alokasi Portofolio Ditetapkan:** `{position_size_pct:.1f}%`
- **Horizon Investasi Terpilih:** `{horizon}`
- **Hard Veto Terpicu:** `{"AKTIF (DILARANG MEMBELI)" if base_passport.hard_veto else "TIDAK (LOLOS SELEKSI)"}`
- **Tingkat Risiko:** `{base_passport.risk_score_10}/10`

---

## 2. Parameter Invalidasi Tesis Kustom
- **Level Invalidasi Kustom:** `Rp {custom_invalidation:,.0f}`
- **Aturan Eksekusi Exit:** Segera lakukan likuidasi defensif jika harga penutupan harian menembus di bawah Rp {custom_invalidation:,.0f}.
- **Catatan & Rationale Operator:** {operator_notes}

---

## 3. Matriks Skenario & Rekapitulasi Multimodal
- **Model Arah Digunakan:** `{base_passport.selected_direction_model}`
- **Peluang Kenaikan Harian:** `{base_passport.direction_probability_up:.1%}`
- **Model Volatilitas:** `{base_passport.selected_volatility_model}`
- **Target Quantile 20D Median (q50):** `Rp {base_passport.forecast_quantiles_20d.q50:,.0f}`
- **Tail Risk Sisi Bawah (q10):** `Rp {base_passport.forecast_quantiles_20d.q10:,.0f}`

---

*Dokumen ini diterbitkan secara otonom melalui Ruang Risiko IDX Web Action Console. "
"Estimasi bersifat probabilitas statistik dan bukan merupakan jaminan keuntungan pasti.*
"""

    passport_path = passport_dir / f"{passport_id}.md"
    passport_path.write_text(custom_md, encoding="utf-8")

    record_action(
        action_type="PASSPORT_CUSTOM_ISSUANCE",
        status="SUCCESS",
        summary_message=f"Diterbitkan Decision Passport bertanda tangan {passport_id} untuk {ticker}.",
        parameters={
            "passport_id": passport_id,
            "ticker": ticker,
            "custom_invalidation": custom_invalidation,
            "position_size_pct": position_size_pct,
            "signature": digital_signature,
        },
        operator=operator_name,
    )

    custom_passport = PreBuyDecisionPassport(
        passport_id=passport_id,
        ticker=ticker,
        company_name=company_name,
        generated_at_utc=now_utc.isoformat(),
        data_cutoff_date=cutoff_date,
        current_price=current_price,
        decision_state=base_passport.decision_state,
        risk_score_10=base_passport.risk_score_10,
        hard_veto=base_passport.hard_veto,
        veto_reasons=base_passport.veto_reasons,
        forecast_quantiles_20d=base_passport.forecast_quantiles_20d,
        direction_probability_up=base_passport.direction_probability_up,
        selected_direction_model=base_passport.selected_direction_model,
        selected_volatility_model=base_passport.selected_volatility_model,
        technical=base_passport.technical,
        ict=base_passport.ict,
        fundamental=base_passport.fundamental,
        market_alignment=base_passport.market_alignment,
        liquidity=base_passport.liquidity,
        risk_evaluation=base_passport.risk_evaluation,
        invalidation_rule=f"Tembus level kustom Rp {custom_invalidation:,.0f}",
        markdown_content=custom_md,
    )

    return custom_passport, passport_path
