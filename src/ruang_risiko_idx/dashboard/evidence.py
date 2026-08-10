"""Turn model evidence into concise, testable dashboard summaries."""

from __future__ import annotations

from typing import Any


def summarize_kronos_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Summarize the frozen Kronos benchmark without changing its decision."""

    decision = evidence.get("decision", {})
    configuration = evidence.get("configuration", {})

    return {
        "role": decision.get("model_role", "experimental_benchmark"),
        "production_selection": decision.get("production_selection", "not_selected"),
        "forecast_count": int(evidence.get("forecast_count", 0)),
        "ticker_count": int(evidence.get("ticker_count", 0)),
        "evaluation_size": int(configuration.get("evaluation_size_per_ticker", 0)),
        "reason": str(decision.get("reason", "Alasan keputusan tidak tersedia.")),
        "structural_result": str(
            decision.get("structural_result", "Hasil audit struktur tidak tersedia.")
        ),
    }


def summarize_granite_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Summarize the frozen Granite benchmark without promoting the model."""

    comparison = evidence.get("comparison", {})

    return {
        "decision": str(evidence.get("decision", "experimental_benchmark_not_production")),
        "forecast_rows": int(evidence.get("forecast_rows", 0)),
        "ticker_count": int(evidence.get("ticker_count", 0)),
        "evaluation_size": int(evidence.get("evaluation_size_per_ticker", 0)),
        "wins_vs_persistence": int(
            comparison.get("granite_return_mae_wins_vs_persistence", 0)
        ),
        "wins_vs_random_walk": int(
            comparison.get("granite_return_mae_wins_vs_random_walk", 0)
        ),
        "model_revision": str(evidence.get("model_revision", "tidak tersedia")),
        "target": str(evidence.get("target", "tidak tersedia")),
    }


def summarize_direction_registry(
    classical_registry: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare validation-selected direction model evidence by ticker."""

    rows: list[dict[str, Any]] = []

    for item in classical_registry:
        validation = item.get("validation", {})
        test = item.get("test", {})
        rows.append(
            {
                "ticker": str(item.get("ticker", "")),
                "selected_model": str(item.get("selected_model", "")),
                "validation_log_loss": float(validation.get("log_loss")),
                "validation_brier": float(validation.get("brier_score")),
                "test_log_loss": float(test.get("log_loss")),
            }
        )

    return sorted(rows, key=lambda row: row["ticker"])


def build_learn_topics() -> tuple[dict[str, str], ...]:
    """Return plain-language concepts used by the Learn section."""

    return (
        {
            "title": "Return",
            "question": "Seberapa besar nilai berubah dari satu periode ke periode berikutnya?",
            "explanation": (
                "Return membantu membandingkan perubahan harga dalam skala yang lebih masuk akal "
                "daripada melihat selisih rupiah saja. Return tetap bisa sangat berisik dari hari "
                "ke hari, jadi satu observasi tidak cukup untuk menyimpulkan pola."
            ),
        },
        {
            "title": "Volatilitas",
            "question": "Seberapa besar perubahan return cenderung berfluktuasi?",
            "explanation": (
                "Volatilitas membahas besarnya variasi, bukan arah. Nilai yang tinggi tidak "
                "berarti harga pasti turun. Nilai yang rendah juga tidak membuat investasi "
                "menjadi aman."
            ),
        },
        {
            "title": "Drawdown",
            "question": "Seberapa jauh posisi berada di bawah puncak sebelumnya?",
            "explanation": (
                "Drawdown melihat pengalaman kerugian dari perjalanan nilai. Angka yang semakin "
                "negatif menunjukkan jarak yang semakin besar dari puncak sebelumnya."
            ),
        },
        {
            "title": "Value at Risk",
            "question": (
                "Berapa ambang kerugian yang diperkirakan pada tingkat keyakinan tertentu?"
            ),
            "explanation": (
                "VaR memakai model dan horizon tertentu. VaR bukan kerugian maksimum. Hasil yang "
                "lebih buruk dari ambang tersebut tetap dapat terjadi."
            ),
        },
        {
            "title": "Walk-forward",
            "question": "Apakah model diuji dengan urutan waktu yang menyerupai penggunaan nyata?",
            "explanation": (
                "Walk-forward menjaga masa depan di luar data pelatihan saat prediksi dibuat. "
                "Cara ini membantu mengurangi evaluasi yang terlalu optimistis karena informasi "
                "masa depan bocor ke proses training."
            ),
        },
        {
            "title": "Baseline",
            "question": "Apakah model yang rumit benar-benar memberi nilai tambah?",
            "explanation": (
                "Baseline sederhana memberi pembanding yang penting. Model yang lebih canggih "
                "belum layak dipilih hanya karena teknologinya menarik. Ia perlu mengalahkan "
                "pembanding yang relevan pada target yang sama."
            ),
        },
    )
