"""Parametric Value at Risk calculations."""

from __future__ import annotations

from math import sqrt

import pandas as pd
from scipy.stats import norm, t


def extract_degrees_of_freedom(
    parameters: pd.Series,
) -> float | None:
    """Read Student-t degrees of freedom from fitted parameters."""

    for parameter_name in ("nu", "eta"):
        if parameter_name in parameters.index:
            return float(parameters[parameter_name])

    return None


def standardized_return_quantile(
    distribution: str,
    tail_probability: float,
    degrees_of_freedom: float | None = None,
) -> float:
    """Calculate a lower-tail quantile with unit variance."""

    if not 0 < tail_probability < 0.5:
        raise ValueError("Tail probability must be between zero and 0.5.")

    normalized_distribution = distribution.strip().lower()

    if normalized_distribution in {
        "normal",
        "gaussian",
    }:
        return float(norm.ppf(tail_probability))

    if normalized_distribution in {
        "t",
        "student",
        "student-t",
        "student_t",
    }:
        if degrees_of_freedom is None or degrees_of_freedom <= 2:
            raise ValueError("Student-t VaR requires degrees of freedom above two.")

        raw_quantile = float(
            t.ppf(
                tail_probability,
                df=degrees_of_freedom,
            )
        )

        standardization_scale = sqrt((degrees_of_freedom - 2.0) / degrees_of_freedom)

        return raw_quantile * standardization_scale

    raise ValueError(f"Unsupported VaR distribution: {distribution}")


def calculate_var_threshold(
    forecast_mean: float,
    forecast_volatility: float,
    tail_probability: float,
    distribution: str,
    degrees_of_freedom: float | None = None,
) -> float:
    """Calculate the return threshold breached by a VaR violation."""

    if forecast_volatility < 0:
        raise ValueError("Forecast volatility cannot be negative.")

    quantile = standardized_return_quantile(
        distribution=distribution,
        tail_probability=tail_probability,
        degrees_of_freedom=degrees_of_freedom,
    )

    return float(forecast_mean + forecast_volatility * quantile)


def build_var_forecasts(
    forecast_mean: float,
    forecast_volatility: float,
    distribution: str,
    degrees_of_freedom: float | None = None,
    tail_probabilities: tuple[float, ...] = (
        0.05,
        0.01,
    ),
) -> dict[str, float]:
    """Create return thresholds and positive loss VaR values."""

    if not tail_probabilities:
        raise ValueError("At least one tail probability is required.")

    output: dict[str, float] = {}

    for tail_probability in tail_probabilities:
        confidence_level = int(round((1.0 - tail_probability) * 100))

        threshold = calculate_var_threshold(
            forecast_mean=forecast_mean,
            forecast_volatility=forecast_volatility,
            tail_probability=tail_probability,
            distribution=distribution,
            degrees_of_freedom=degrees_of_freedom,
        )

        output[f"var_threshold_{confidence_level}"] = threshold

        output[f"var_loss_{confidence_level}"] = -threshold

    return output
