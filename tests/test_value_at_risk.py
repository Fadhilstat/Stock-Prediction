"""Tests for parametric Value at Risk calculations."""

import numpy as np

from ruang_risiko_idx.econometrics.value_at_risk import (
    build_var_forecasts,
    calculate_var_threshold,
    standardized_return_quantile,
)


def test_normal_var_threshold() -> None:
    threshold = calculate_var_threshold(
        forecast_mean=0.0,
        forecast_volatility=1.0,
        tail_probability=0.05,
        distribution="normal",
    )

    assert np.isclose(
        threshold,
        -1.6448536269514729,
    )


def test_student_t_quantile_is_finite() -> None:
    quantile = standardized_return_quantile(
        distribution="t",
        tail_probability=0.01,
        degrees_of_freedom=6.0,
    )

    assert np.isfinite(quantile)
    assert quantile < 0


def test_build_var_forecasts() -> None:
    forecasts = build_var_forecasts(
        forecast_mean=0.001,
        forecast_volatility=0.02,
        distribution="normal",
    )

    assert "var_threshold_95" in forecasts
    assert "var_threshold_99" in forecasts
    assert forecasts["var_threshold_99"] < (forecasts["var_threshold_95"])
    assert forecasts["var_loss_99"] > (forecasts["var_loss_95"])
