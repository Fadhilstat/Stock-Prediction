"""Diagnostics for standardized volatility model residuals."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera
from statsmodels.stats.diagnostic import (
    acorr_ljungbox,
    het_arch,
)


def calculate_residual_diagnostics(
    standardized_residuals: pd.Series,
    lags: int = 10,
) -> dict[str, float | int]:
    """Run distribution and remaining dependence checks."""

    if lags < 1:
        raise ValueError("Diagnostic lags must be positive.")

    residuals = (
        pd.Series(
            standardized_residuals,
            dtype="float64",
        )
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    if len(residuals) <= lags + 2:
        raise ValueError("Residual diagnostics received too few observations.")

    ljung_box = acorr_ljungbox(
        residuals,
        lags=[lags],
        return_df=True,
    )

    squared_ljung_box = acorr_ljungbox(
        residuals.pow(2),
        lags=[lags],
        return_df=True,
    )

    arch_lm = het_arch(
        residuals,
        nlags=lags,
    )

    normality = jarque_bera(residuals)

    return {
        "diagnostic_lags": lags,
        "residual_count": int(len(residuals)),
        "ljung_box_statistic": float(ljung_box["lb_stat"].iloc[-1]),
        "ljung_box_p_value": float(ljung_box["lb_pvalue"].iloc[-1]),
        "squared_ljung_box_statistic": float(squared_ljung_box["lb_stat"].iloc[-1]),
        "squared_ljung_box_p_value": float(squared_ljung_box["lb_pvalue"].iloc[-1]),
        "arch_lm_statistic": float(arch_lm[0]),
        "arch_lm_p_value": float(arch_lm[1]),
        "jarque_bera_statistic": float(normality.statistic),
        "jarque_bera_p_value": float(normality.pvalue),
    }
