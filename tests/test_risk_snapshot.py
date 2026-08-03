"""Tests for registry-driven GARCH risk snapshots."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ruang_risiko_idx.econometrics.risk_snapshot import (
    RiskModelAssignment,
    build_ticker_risk_snapshot,
    load_garch_model_registry,
)


def test_load_garch_model_registry(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "garch_model_registry.yml"

    payload = {
        "tickers": {
            "AAA": {
                "volatility_model": ("garch_normal"),
                "var_model": ("garch_student_t"),
                "note": "Test assignment.",
            }
        }
    }

    registry_path.write_text(
        yaml.safe_dump(payload),
        encoding="utf-8",
    )

    assignments = load_garch_model_registry(registry_path)

    assert assignments["AAA"].volatility_model == "garch_normal"

    assert assignments["AAA"].var_model == "garch_student_t"


def test_registry_rejects_unknown_model(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "invalid_registry.yml"

    payload = {
        "tickers": {
            "AAA": {
                "volatility_model": ("unknown_model"),
                "var_model": ("garch_normal"),
            }
        }
    }

    registry_path.write_text(
        yaml.safe_dump(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="unknown volatility model",
    ):
        load_garch_model_registry(registry_path)


def test_build_ticker_risk_snapshot() -> None:
    generator = np.random.default_rng(42)

    returns = pd.Series(
        generator.normal(
            loc=0.0002,
            scale=0.015,
            size=320,
        ),
        index=pd.date_range(
            "2024-01-01",
            periods=320,
            freq="B",
        ),
    )

    assignment = RiskModelAssignment(
        ticker="AAA",
        volatility_model="garch_normal",
        var_model="garch_normal",
    )

    snapshot = build_ticker_risk_snapshot(
        returns=returns,
        assignment=assignment,
        minimum_observations=250,
    )

    assert snapshot["ticker"] == "AAA"
    assert snapshot["volatility_model"] == "garch_normal"

    assert snapshot["var_model"] == "garch_normal"

    assert snapshot["forecast_volatility"] > 0

    assert snapshot["var_95"] > 0
    assert snapshot["var_99"] > snapshot["var_95"]

    assert snapshot["var_threshold_99"] < snapshot["var_threshold_95"]
