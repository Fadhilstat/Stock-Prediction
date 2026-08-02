"""Tests for standardized residual diagnostics."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.diagnostics import (
    calculate_residual_diagnostics,
)


def test_residual_diagnostics_return_valid_probabilities() -> None:
    random_generator = np.random.default_rng(42)

    residuals = pd.Series(random_generator.standard_normal(500))

    diagnostics = calculate_residual_diagnostics(
        residuals,
        lags=10,
    )

    probability_keys = [
        "ljung_box_p_value",
        "squared_ljung_box_p_value",
        "arch_lm_p_value",
        "jarque_bera_p_value",
    ]

    for key in probability_keys:
        assert 0 <= diagnostics[key] <= 1
