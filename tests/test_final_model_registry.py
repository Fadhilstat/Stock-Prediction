"""Tests for the final task-specific model registry."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "build_final_model_registry.py"
)


def test_build_final_model_registry(
    tmp_path: Path,
) -> None:
    """Build and validate the final registry."""

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
        + "\n"
        + result.stderr
    )

    registry_path = (
        tmp_path
        / "final_model_registry.json"
    )

    decision_path = (
        tmp_path
        / "PHASE_5_4_DECISION.md"
    )

    assert registry_path.exists()
    assert decision_path.exists()

    registry = json.loads(
        registry_path.read_text(
            encoding="utf-8"
        )
    )

    assert registry[
        "metadata"
    ]["phase"] == "5.4"

    assert registry[
        "metadata"
    ]["retraining_performed"] is False

    assert registry[
        "metadata"
    ]["hyperparameter_tuning_performed"] is False

    garch = registry[
        "risk_and_volatility"
    ]

    classical = registry[
        "direction_probability"
    ]

    foundations = registry[
        "foundation_benchmarks"
    ]

    assert garch[
        "selection_status"
    ] == "provisional_out_of_sample_selection"

    assert garch[
        "primary_volatility_metric"
    ] == "mean_qlike"

    assert len(
        garch["tickers"]
    ) == 6

    assert len(
        classical["tickers"]
    ) == 6

    assert classical[
        "selection_basis"
    ] == "validation"

    assert classical[
        "test_used_for_selection"
    ] is False

    selected_models = {
        row["ticker"]: row[
            "selected_model"
        ]
        for row in classical[
            "tickers"
        ]
    }

    assert selected_models[
        "ANTM.JK"
    ] == "logistic_regression"

    assert selected_models[
        "ASII.JK"
    ] == "random_forest"

    assert selected_models[
        "BBCA.JK"
    ] == "random_forest"

    assert selected_models[
        "BBRI.JK"
    ] == "constant_probability"

    assert selected_models[
        "TLKM.JK"
    ] == "random_forest"

    assert selected_models[
        "^JKSE"
    ] == "constant_probability"

    assert foundations[
        "kronos"
    ]["role"] == "experimental_benchmark"

    assert foundations[
        "kronos"
    ]["production_selection"] == "not_selected"

    assert foundations[
        "granite_ttm"
    ]["role"] == "experimental_benchmark"

    assert foundations[
        "granite_ttm"
    ]["production_selection"] == "not_selected"

    assert foundations[
        "granite_ttm"
    ]["comparison"][
        "granite_return_mae_wins_vs_random_walk"
    ] == 0

    decision_text = decision_path.read_text(
        encoding="utf-8"
    )

    assert (
        "single leaderboard"
        in decision_text
    )

    assert (
        "provisional_out_of_sample_selection"
        in decision_text
    )

    assert (
        "No foundation model is selected"
        in decision_text
    )
