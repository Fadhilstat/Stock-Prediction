"""Tests for GARCH persistence and half-life helpers."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.garch import (
    calculate_half_life,
    calculate_persistence,
)
from ruang_risiko_idx.econometrics.specification import (
    VolatilityModelSpec,
)


def test_garch_persistence_and_half_life() -> None:
    parameters = pd.Series(
        {
            "omega": 0.01,
            "alpha[1]": 0.08,
            "beta[1]": 0.90,
        }
    )

    specification = VolatilityModelSpec(
        name="garch_normal",
        volatility="GARCH",
        distribution="normal",
    )

    persistence = calculate_persistence(
        parameters,
        specification,
    )

    assert np.isclose(
        persistence,
        0.98,
    )

    half_life = calculate_half_life(persistence)

    assert half_life > 0
    assert np.isfinite(half_life)


def test_gjr_persistence_includes_asymmetry() -> None:
    parameters = pd.Series(
        {
            "omega": 0.01,
            "alpha[1]": 0.05,
            "gamma[1]": 0.04,
            "beta[1]": 0.90,
        }
    )

    specification = VolatilityModelSpec(
        name="gjr_garch_normal",
        volatility="GARCH",
        distribution="normal",
        o=1,
    )

    persistence = calculate_persistence(
        parameters,
        specification,
    )

    assert np.isclose(
        persistence,
        0.97,
    )
