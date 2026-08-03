"""Build the latest registry-driven GARCH risk snapshot."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ruang_risiko_idx.econometrics.garch import (
    FittedVolatilityModel,
    fit_volatility_model,
    forecast_one_day,
)
from ruang_risiko_idx.econometrics.specification import (
    DEFAULT_MODEL_SPECS,
    VolatilityModelSpec,
)
from ruang_risiko_idx.econometrics.value_at_risk import (
    build_var_forecasts,
    extract_degrees_of_freedom,
)


@dataclass(frozen=True)
class RiskModelAssignment:
    """Store volatility and VaR model choices for one ticker."""

    ticker: str
    volatility_model: str
    var_model: str
    note: str | None = None


def load_garch_model_registry(
    registry_path: str | Path,
    specifications: Sequence[VolatilityModelSpec] = DEFAULT_MODEL_SPECS,
) -> dict[str, RiskModelAssignment]:
    """Load and validate ticker-level model assignments."""

    path = Path(registry_path)

    if not path.exists():
        raise FileNotFoundError(f"GARCH model registry was not found at {path}.")

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("GARCH model registry must contain a mapping.")

    ticker_settings = payload.get("tickers")

    if not isinstance(ticker_settings, dict):
        raise ValueError("GARCH model registry requires a tickers mapping.")

    valid_model_names = {specification.name for specification in specifications}

    assignments: dict[
        str,
        RiskModelAssignment,
    ] = {}

    for ticker, settings in ticker_settings.items():
        if not isinstance(settings, dict):
            raise ValueError(f"Registry settings for {ticker} must be a mapping.")

        volatility_model = settings.get("volatility_model")
        var_model = settings.get("var_model")

        if volatility_model not in valid_model_names:
            raise ValueError(f"{ticker} has an unknown volatility model: {volatility_model}")

        if var_model not in valid_model_names:
            raise ValueError(f"{ticker} has an unknown VaR model: {var_model}")

        assignments[str(ticker)] = RiskModelAssignment(
            ticker=str(ticker),
            volatility_model=str(volatility_model),
            var_model=str(var_model),
            note=settings.get("note"),
        )

    if not assignments:
        raise ValueError("GARCH model registry contains no ticker assignments.")

    return assignments


def _prepare_return_series(
    returns: pd.Series,
) -> pd.Series:
    """Clean and order one return series."""

    source = pd.Series(
        returns,
        copy=True,
    )

    parsed_dates = pd.to_datetime(
        source.index,
        errors="coerce",
    )

    numeric_returns = pd.to_numeric(
        source,
        errors="coerce",
    )

    cleaned = pd.DataFrame(
        {
            "trade_date": parsed_dates,
            "log_return": numeric_returns.to_numpy(),
        }
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    )

    cleaned = cleaned.dropna().sort_values("trade_date").reset_index(drop=True)

    if cleaned.empty:
        raise ValueError("Risk snapshot received no valid return observations.")

    if cleaned["trade_date"].duplicated().any():
        raise ValueError("Risk snapshot returns contain duplicate dates.")

    return cleaned.set_index("trade_date")["log_return"].astype("float64")


def _build_specification_map(
    specifications: Sequence[VolatilityModelSpec],
) -> dict[str, VolatilityModelSpec]:
    """Create a lookup table for volatility specifications."""

    specification_map = {specification.name: specification for specification in specifications}

    if not specification_map:
        raise ValueError("At least one volatility specification is required.")

    return specification_map


def _fit_assigned_models(
    returns: pd.Series,
    assignment: RiskModelAssignment,
    specification_map: dict[
        str,
        VolatilityModelSpec,
    ],
    minimum_observations: int,
) -> dict[str, FittedVolatilityModel]:
    """Fit each distinct assigned model once."""

    requested_models = {
        assignment.volatility_model,
        assignment.var_model,
    }

    fitted_models: dict[
        str,
        FittedVolatilityModel,
    ] = {}

    for model_name in sorted(requested_models):
        if model_name not in specification_map:
            raise ValueError(f"Unknown assigned model: {model_name}")

        fitted_models[model_name] = fit_volatility_model(
            returns=returns,
            specification=(specification_map[model_name]),
            minimum_observations=(minimum_observations),
        )

    return fitted_models


def build_ticker_risk_snapshot(
    returns: pd.Series,
    assignment: RiskModelAssignment,
    specifications: Sequence[VolatilityModelSpec] = DEFAULT_MODEL_SPECS,
    minimum_observations: int = 750,
) -> dict[str, object]:
    """Build the latest volatility and VaR snapshot for one ticker."""

    if minimum_observations < 250:
        raise ValueError("Minimum observations must be at least 250.")

    cleaned_returns = _prepare_return_series(returns)

    if len(cleaned_returns) < minimum_observations:
        raise ValueError(
            f"{assignment.ticker} has only "
            f"{len(cleaned_returns)} valid returns. "
            f"At least {minimum_observations} are required."
        )

    specification_map = _build_specification_map(specifications)

    fitted_models = _fit_assigned_models(
        returns=cleaned_returns,
        assignment=assignment,
        specification_map=specification_map,
        minimum_observations=minimum_observations,
    )

    volatility_fit = fitted_models[assignment.volatility_model]

    var_fit = fitted_models[assignment.var_model]

    volatility_specification = specification_map[assignment.volatility_model]

    var_specification = specification_map[assignment.var_model]

    volatility_forecast = forecast_one_day(volatility_fit)

    var_forecast = forecast_one_day(var_fit)

    degrees_of_freedom = extract_degrees_of_freedom(var_fit.result.params)

    var_values = build_var_forecasts(
        forecast_mean=var_forecast["forecast_mean"],
        forecast_volatility=var_forecast["forecast_volatility"],
        distribution=(var_specification.distribution),
        degrees_of_freedom=(degrees_of_freedom),
    )

    return {
        "ticker": assignment.ticker,
        "as_of_date": cleaned_returns.index.max(),
        "data_start_date": cleaned_returns.index.min(),
        "observations": int(len(cleaned_returns)),
        "forecast_horizon_days": 1,
        "volatility_model": (assignment.volatility_model),
        "volatility_distribution": (volatility_specification.distribution),
        "forecast_mean": float(volatility_forecast["forecast_mean"]),
        "forecast_variance": float(volatility_forecast["forecast_variance"]),
        "forecast_volatility": float(volatility_forecast["forecast_volatility"]),
        "persistence": float(volatility_fit.persistence),
        "half_life_days": float(volatility_fit.half_life_days),
        "convergence_flag": int(volatility_fit.result.convergence_flag),
        "var_model": assignment.var_model,
        "var_distribution": (var_specification.distribution),
        "var_forecast_mean": float(var_forecast["forecast_mean"]),
        "var_forecast_volatility": float(var_forecast["forecast_volatility"]),
        "var_degrees_of_freedom": (
            float(degrees_of_freedom) if degrees_of_freedom is not None else np.nan
        ),
        "var_95": float(var_values["var_loss_95"]),
        "var_99": float(var_values["var_loss_99"]),
        "var_threshold_95": float(var_values["var_threshold_95"]),
        "var_threshold_99": float(var_values["var_threshold_99"]),
        "var_persistence": float(var_fit.persistence),
        "var_half_life_days": float(var_fit.half_life_days),
        "var_convergence_flag": int(var_fit.result.convergence_flag),
        "selection_note": assignment.note,
    }


def build_latest_risk_snapshot(
    analytics: pd.DataFrame,
    assignments: dict[
        str,
        RiskModelAssignment,
    ],
    specifications: Sequence[VolatilityModelSpec] = DEFAULT_MODEL_SPECS,
    minimum_observations: int = 750,
) -> pd.DataFrame:
    """Build the latest risk snapshot for all registry tickers."""

    required_columns = {
        "ticker",
        "trade_date",
        "log_return",
    }

    missing_columns = required_columns.difference(analytics.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Analytics data is missing columns: {missing_text}")

    available_tickers = set(analytics["ticker"].dropna().astype(str).unique())

    missing_tickers = sorted(set(assignments).difference(available_tickers))

    if missing_tickers:
        raise ValueError(
            "Analytics data is missing registry tickers: " + ", ".join(missing_tickers)
        )

    records: list[dict[str, object]] = []

    for ticker in sorted(assignments):
        ticker_data = analytics.loc[
            analytics["ticker"].astype(str).eq(ticker),
            [
                "trade_date",
                "log_return",
            ],
        ].sort_values("trade_date")

        returns = pd.Series(
            ticker_data["log_return"].to_numpy(),
            index=ticker_data["trade_date"],
            name=ticker,
            dtype="float64",
        )

        print(f"Building risk snapshot for {ticker}.")

        records.append(
            build_ticker_risk_snapshot(
                returns=returns,
                assignment=assignments[ticker],
                specifications=specifications,
                minimum_observations=(minimum_observations),
            )
        )

    return pd.DataFrame.from_records(records).sort_values("ticker").reset_index(drop=True)
