"""Tests for out-of-sample volatility loss functions."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.losses import (
    build_volatility_loss_table,
    summarize_volatility_losses,
)


def test_volatility_loss_table_and_summary() -> None:
    actual_returns = pd.Series(
        [
            0.01,
            -0.02,
            0.03,
        ]
    )

    forecast_variance = pd.Series(
        [
            0.0001,
            0.0004,
            0.0009,
        ]
    )

    losses = build_volatility_loss_table(
        actual_returns=actual_returns,
        forecast_variance=forecast_variance,
    )

    assert np.allclose(
        losses["realized_variance"],
        forecast_variance,
    )

    assert np.allclose(
        losses["volatility_absolute_error"],
        0.0,
    )

    summary = summarize_volatility_losses(losses)

    assert summary["forecast_observations"] == 3
    assert np.isclose(
        summary["variance_mse"],
        0.0,
    )
    assert np.isclose(
        summary["volatility_mae"],
        0.0,
    )
