"""Small UX helpers for readable dashboard states and warnings."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class UserFacingDataError:
    """Describe a runtime data problem without exposing internal file details."""

    title: str
    explanation: str
    action: str


def explain_data_error(error: Exception) -> UserFacingDataError:
    """Turn internal artifact errors into useful public-facing guidance."""

    message = str(error).lower()

    if "not available" in message:
        return UserFacingDataError(
            title="Data dashboard belum lengkap",
            explanation=(
                "Salah satu hasil pipeline offline belum tersedia. Dashboard tidak akan "
                "menghitung ulang model secara otomatis saat halaman dibuka."
            ),
            action=(
                "Jalankan pipeline pembaruan data dan snapshot, lalu muat ulang dashboard."
            ),
        )

    if "date does not match" in message:
        return UserFacingDataError(
            title="Snapshot belum selaras dengan data terbaru",
            explanation=(
                "Tanggal analytics dan snapshot model berbeda. Menampilkan keduanya bersama "
                "dapat membuat pembacaan risiko menjadi menyesatkan."
            ),
            action="Bangun ulang snapshot dari analytics terbaru sebelum melanjutkan.",
        )

    if "ticker universe" in message:
        return UserFacingDataError(
            title="Daftar ticker belum selaras",
            explanation=(
                "Sebagian artifact memakai daftar ticker yang berbeda. Dashboard berhenti agar "
                "angka dari saham yang berbeda tidak tercampur."
            ),
            action="Perbarui artifact dari satu pipeline dan konfigurasi ticker yang sama.",
        )

    return UserFacingDataError(
        title="Data dashboard belum dapat digunakan",
        explanation=(
            "Validasi menemukan masalah pada artifact runtime. Dashboard memilih berhenti "
            "daripada menampilkan angka yang belum konsisten."
        ),
        action="Periksa pipeline offline dan bangun ulang artifact yang bermasalah.",
    )


def find_convergence_warnings(risk_snapshot: pd.DataFrame) -> tuple[str, ...]:
    """Return tickers whose risk snapshot reports a convergence warning."""

    if "ticker" not in risk_snapshot.columns or "convergence_flag" not in risk_snapshot.columns:
        return ()

    flags = pd.to_numeric(risk_snapshot["convergence_flag"], errors="coerce")
    affected = risk_snapshot.loc[flags.fillna(1).ne(0), "ticker"].astype(str)

    return tuple(sorted(affected.unique()))


def ticker_has_convergence_warning(risk_snapshot: pd.DataFrame, ticker: str) -> bool:
    """Check whether one ticker carries a nonzero convergence flag."""

    return ticker in find_convergence_warnings(risk_snapshot)
