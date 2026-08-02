"""Fit conditional volatility models to daily returns."""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from typing import Any

import numpy as np
import pandas as pd
from arch import arch_model

from ruang_risiko_idx.econometrics.specification import (
    VolatilityModelSpec,
)


@dataclass
class FittedVolatilityModel:
    """Store a fitted model and reusable derived outputs."""

    specification: VolatilityModelSpec
    result: Any
    input_returns: pd.Series
    conditional_volatility: pd.Series
    standardized_residuals: pd.Series
    persistence: float
    half_life_days: float


def _sum_parameters(
    parameters: pd.Series,
    prefix: str,
) -> float:
    """Sum parameters whose names begin with a prefix."""

    names = parameters.index.astype(str)
    selected = parameters.loc[names.str.startswith(prefix)]

    return float(selected.sum())


def calculate_persistence(
    parameters: pd.Series,
    specification: VolatilityModelSpec,
) -> float:
    """Estimate volatility persistence from fitted parameters."""

    beta_sum = _sum_parameters(
        parameters,
        "beta[",
    )

    if specification.volatility.upper() == "EGARCH":
        return beta_sum

    alpha_sum = _sum_parameters(
        parameters,
        "alpha[",
    )

    gamma_sum = _sum_parameters(
        parameters,
        "gamma[",
    )

    return alpha_sum + beta_sum + 0.5 * gamma_sum


def calculate_half_life(
    persistence: float,
) -> float:
    """Convert mean-reverting persistence into a half-life."""

    if not 0 < persistence < 1:
        return float("nan")

    return log(0.5) / log(persistence)


def fit_volatility_model(
    returns: pd.Series,
    specification: VolatilityModelSpec,
    minimum_observations: int = 250,
) -> FittedVolatilityModel:
    """Fit one conditional volatility model."""

    clean_returns = (
        pd.Series(
            returns,
            copy=True,
            dtype="float64",
        )
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    if len(clean_returns) < minimum_observations:
        raise ValueError(
            f"Volatility fitting requires at least {minimum_observations} valid observations."
        )

    if clean_returns.std(ddof=1) == 0:
        raise ValueError("Volatility fitting requires non-constant returns.")

    scaled_returns = clean_returns * 100.0

    model = arch_model(
        scaled_returns,
        mean="Constant",
        vol=specification.volatility,
        p=specification.p,
        o=specification.o,
        q=specification.q,
        dist=specification.distribution,
        rescale=False,
    )

    result = model.fit(
        update_freq=0,
        disp="off",
    )

    persistence = calculate_persistence(
        parameters=result.params,
        specification=specification,
    )

    conditional_volatility = pd.Series(
        np.asarray(
            result.conditional_volatility,
            dtype="float64",
        )
        / 100.0,
        index=clean_returns.index,
        name="conditional_volatility",
    )

    standardized_residuals = pd.Series(
        np.asarray(
            result.std_resid,
            dtype="float64",
        ),
        index=clean_returns.index,
        name="standardized_residual",
    ).dropna()

    return FittedVolatilityModel(
        specification=specification,
        result=result,
        input_returns=clean_returns,
        conditional_volatility=conditional_volatility,
        standardized_residuals=standardized_residuals,
        persistence=persistence,
        half_life_days=calculate_half_life(persistence),
    )


def forecast_one_day(
    fitted_model: FittedVolatilityModel,
) -> dict[str, float]:
    """Produce a one-day mean and volatility forecast."""

    forecast = fitted_model.result.forecast(
        horizon=1,
        reindex=False,
    )

    forecast_mean = float(forecast.mean.iloc[-1, 0]) / 100.0

    forecast_variance = float(forecast.variance.iloc[-1, 0]) / 10_000.0

    forecast_variance = max(
        forecast_variance,
        0.0,
    )

    return {
        "forecast_mean": forecast_mean,
        "forecast_variance": forecast_variance,
        "forecast_volatility": sqrt(forecast_variance),
    }


def summarize_fitted_model(
    fitted_model: FittedVolatilityModel,
) -> dict[str, float | int | str]:
    """Create a serializable model summary."""

    result = fitted_model.result
    forecast = forecast_one_day(fitted_model)

    return {
        "model_name": fitted_model.specification.name,
        "volatility_model": (fitted_model.specification.volatility),
        "distribution": (fitted_model.specification.distribution),
        "p": fitted_model.specification.p,
        "o": fitted_model.specification.o,
        "q": fitted_model.specification.q,
        "observations": int(result.nobs),
        "log_likelihood": float(result.loglikelihood),
        "aic": float(result.aic),
        "bic": float(result.bic),
        "convergence_flag": int(result.convergence_flag),
        "persistence": float(fitted_model.persistence),
        "half_life_days": float(fitted_model.half_life_days),
        **forecast,
    }
