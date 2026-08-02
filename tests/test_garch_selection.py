"""Tests for in-sample volatility model ranking."""

import pandas as pd

from ruang_risiko_idx.econometrics.selection import (
    rank_in_sample_models,
)


def test_rank_in_sample_models() -> None:
    results = pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "AAA",
                "AAA",
            ],
            "model_name": [
                "model_a",
                "model_b",
                "model_c",
            ],
            "aic": [
                100.0,
                95.0,
                90.0,
            ],
            "bic": [
                110.0,
                108.0,
                105.0,
            ],
            "convergence_flag": [
                0,
                0,
                1,
            ],
            "ljung_box_p_value": [
                0.20,
                0.01,
                0.50,
            ],
            "squared_ljung_box_p_value": [
                0.30,
                0.40,
                0.50,
            ],
            "arch_lm_p_value": [
                0.30,
                0.40,
                0.50,
            ],
        }
    )

    ranked = rank_in_sample_models(results)

    model_a = ranked.loc[ranked["model_name"].eq("model_a")].iloc[0]

    model_b = ranked.loc[ranked["model_name"].eq("model_b")].iloc[0]

    model_c = ranked.loc[ranked["model_name"].eq("model_c")].iloc[0]

    assert model_b["aic_rank"] == 1
    assert model_b["bic_rank"] == 1
    assert not model_b["mean_diagnostics_pass"]
    assert model_b["variance_diagnostics_pass"]

    assert model_a["aic_rank"] == 2
    assert model_a["mean_diagnostics_pass"]

    assert not model_c["eligible_in_sample"]
    assert pd.isna(model_c["aic_rank"])
