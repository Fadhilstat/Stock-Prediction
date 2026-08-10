"""Tests for dashboard user-facing error and warning helpers."""

import pandas as pd

from ruang_risiko_idx.dashboard.ux import (
    explain_data_error,
    find_convergence_warnings,
    ticker_has_convergence_warning,
)


def test_missing_artifact_message_does_not_expose_path() -> None:
    """Public guidance should explain the next step without showing internal paths."""

    error = RuntimeError(
        "Analytics dataset is not available at /private/project/data/file.parquet."
    )

    guidance = explain_data_error(error)

    assert guidance.title == "Data dashboard belum lengkap"
    assert "/private/project" not in guidance.explanation
    assert "/private/project" not in guidance.action
    assert "pipeline" in guidance.action.lower()


def test_stale_snapshot_message_explains_why_dashboard_stops() -> None:
    """Date mismatch guidance should explain the risk of mixing stale artifacts."""

    guidance = explain_data_error(
        RuntimeError("Risk snapshot date does not match the latest analytics date.")
    )

    assert guidance.title == "Snapshot belum selaras dengan data terbaru"
    assert "menyesatkan" in guidance.explanation


def test_convergence_warning_lists_only_affected_tickers() -> None:
    """Only nonzero or unreadable convergence flags should trigger warnings."""

    risk = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "convergence_flag": [0, 1, "bad"],
        }
    )

    warnings = find_convergence_warnings(risk)

    assert warnings == ("BBB", "CCC")
    assert ticker_has_convergence_warning(risk, "BBB")
    assert not ticker_has_convergence_warning(risk, "AAA")


def test_missing_convergence_column_is_not_treated_as_failure() -> None:
    """Older evidence without convergence flags should not create a false warning."""

    risk = pd.DataFrame({"ticker": ["AAA"]})

    assert find_convergence_warnings(risk) == ()
