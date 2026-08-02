"""In-sample comparison helpers for volatility models."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "model_name",
    "aic",
    "bic",
    "convergence_flag",
    "ljung_box_p_value",
    "squared_ljung_box_p_value",
    "arch_lm_p_value",
}


def rank_in_sample_models(
    results: pd.DataFrame,
    significance_level: float = 0.05,
) -> pd.DataFrame:
    """Add convergence, diagnostic, AIC, and BIC rankings."""

    missing_columns = REQUIRED_COLUMNS.difference(results.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Model ranking requires columns: {missing_text}")

    if not 0 < significance_level < 1:
        raise ValueError("Significance level must be between zero and one.")

    ranked = results.copy()

    finite_information_criteria = np.isfinite(ranked["aic"]) & np.isfinite(ranked["bic"])

    ranked["converged"] = ranked["convergence_flag"].eq(0)

    ranked["mean_diagnostics_pass"] = ranked["ljung_box_p_value"] > significance_level

    ranked["variance_diagnostics_pass"] = (
        ranked["squared_ljung_box_p_value"] > significance_level
    ) & (ranked["arch_lm_p_value"] > significance_level)

    ranked["eligible_in_sample"] = ranked["converged"] & finite_information_criteria

    ranked["aic_rank"] = (
        ranked["aic"]
        .where(ranked["eligible_in_sample"])
        .groupby(ranked["ticker"])
        .rank(
            method="min",
            ascending=True,
        )
    )

    ranked["bic_rank"] = (
        ranked["bic"]
        .where(ranked["eligible_in_sample"])
        .groupby(ranked["ticker"])
        .rank(
            method="min",
            ascending=True,
        )
    )

    ranked["preliminary_aic_winner"] = ranked["aic_rank"].eq(1)

    ranked["preliminary_bic_winner"] = ranked["bic_rank"].eq(1)

    return ranked.sort_values(
        [
            "ticker",
            "bic_rank",
            "aic_rank",
            "model_name",
        ],
        na_position="last",
    ).reset_index(drop=True)
