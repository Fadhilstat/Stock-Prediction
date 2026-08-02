"""Leakage-safe walk-forward volatility forecasting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.backtesting import (
    summarize_var_backtest,
)
from ruang_risiko_idx.econometrics.garch import (
    fit_volatility_model,
    forecast_one_day,
)
from ruang_risiko_idx.econometrics.losses import (
    build_volatility_loss_table,
    summarize_volatility_losses,
)
from ruang_risiko_idx.econometrics.specification import (
    VolatilityModelSpec,
)
from ruang_risiko_idx.econometrics.value_at_risk import (
    build_var_forecasts,
    extract_degrees_of_freedom,
)


@dataclass(frozen=True)
class WalkForwardConfig:
    """Configure a one-day-ahead walk-forward evaluation."""

    test_size: int = 252
    minimum_observations: int = 750
    window_type: str = "expanding"
    rolling_window: int | None = None
    progress_every: int = 25

    def validate(self) -> None:
        """Validate walk-forward configuration."""

        if self.test_size < 2:
            raise ValueError("Walk-forward evaluation requires at least two forecasts.")

        if self.minimum_observations < 250:
            raise ValueError("The minimum training sample must contain at least 250 observations.")

        if self.window_type not in {
            "expanding",
            "rolling",
        }:
            raise ValueError("Window type must be expanding or rolling.")

        if self.window_type == "rolling":
            if self.rolling_window is None:
                raise ValueError("A rolling window size is required.")

            if self.rolling_window < self.minimum_observations:
                raise ValueError("The rolling window cannot be smaller than the minimum sample.")

        if self.progress_every < 0:
            raise ValueError("Progress frequency cannot be negative.")


@dataclass
class WalkForwardRun:
    """Store successful forecasts and failed forecast attempts."""

    forecasts: pd.DataFrame
    failures: pd.DataFrame


def select_training_returns(
    returns: pd.Series,
    forecast_position: int,
    config: WalkForwardConfig,
) -> pd.Series:
    """Select observations available before one forecast date."""

    config.validate()

    if not 0 < forecast_position < len(returns):
        raise ValueError("Forecast position must have prior and future observations.")

    training = returns.iloc[:forecast_position]

    if config.window_type == "rolling":
        training = training.iloc[-int(config.rolling_window) :]

    return training.copy()


def _prepare_returns(
    returns: pd.Series,
) -> pd.Series:
    """Clean and order a return series for evaluation."""

    cleaned = (
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

    parsed_index = pd.to_datetime(
        cleaned.index,
        errors="coerce",
    )

    if parsed_index.isna().any():
        raise ValueError("Walk-forward returns require valid date indices.")

    cleaned.index = parsed_index
    cleaned = cleaned.sort_index()

    if cleaned.index.duplicated().any():
        raise ValueError("Walk-forward returns contain duplicate dates.")

    return cleaned


def run_walk_forward_forecasts(
    returns: pd.Series,
    ticker: str,
    specification: VolatilityModelSpec,
    config: WalkForwardConfig,
) -> WalkForwardRun:
    """Refit a model daily and forecast the following return."""

    config.validate()
    cleaned = _prepare_returns(returns)

    if len(cleaned) <= config.minimum_observations:
        raise ValueError("The return series does not contain enough observations.")

    available_test_size = len(cleaned) - config.minimum_observations

    effective_test_size = min(
        config.test_size,
        available_test_size,
    )

    first_forecast_position = len(cleaned) - effective_test_size

    forecast_records: list[dict[str, object]] = []

    failure_records: list[dict[str, object]] = []

    total_forecasts = len(cleaned) - first_forecast_position

    for completed, position in enumerate(
        range(
            first_forecast_position,
            len(cleaned),
        ),
        start=1,
    ):
        forecast_date = cleaned.index[position]

        training_returns = select_training_returns(
            returns=cleaned,
            forecast_position=position,
            config=config,
        )

        try:
            fitted = fit_volatility_model(
                returns=training_returns,
                specification=specification,
                minimum_observations=(config.minimum_observations),
            )

            forecast = forecast_one_day(fitted)

            degrees_of_freedom = extract_degrees_of_freedom(fitted.result.params)

            var_forecasts = build_var_forecasts(
                forecast_mean=forecast["forecast_mean"],
                forecast_volatility=forecast["forecast_volatility"],
                distribution=(specification.distribution),
                degrees_of_freedom=(degrees_of_freedom),
            )

            forecast_records.append(
                {
                    "ticker": ticker,
                    "model_name": specification.name,
                    "volatility_model": (specification.volatility),
                    "distribution": (specification.distribution),
                    "forecast_date": forecast_date,
                    "training_start_date": (training_returns.index.min()),
                    "training_end_date": (training_returns.index.max()),
                    "training_observations": int(len(training_returns)),
                    "actual_return": float(cleaned.iloc[position]),
                    "forecast_mean": float(forecast["forecast_mean"]),
                    "forecast_variance": float(forecast["forecast_variance"]),
                    "forecast_volatility": float(forecast["forecast_volatility"]),
                    "degrees_of_freedom": (
                        float(degrees_of_freedom) if degrees_of_freedom is not None else np.nan
                    ),
                    "convergence_flag": int(fitted.result.convergence_flag),
                    **var_forecasts,
                }
            )

        except Exception as error:
            failure_records.append(
                {
                    "ticker": ticker,
                    "model_name": specification.name,
                    "forecast_date": forecast_date,
                    "training_start_date": (training_returns.index.min()),
                    "training_end_date": (training_returns.index.max()),
                    "training_observations": int(len(training_returns)),
                    "error_type": (type(error).__name__),
                    "error_message": str(error),
                }
            )

        if config.progress_every and (
            completed % config.progress_every == 0 or completed == total_forecasts
        ):
            print(f"{ticker} | {specification.name} | {completed}/{total_forecasts} forecasts")

    return WalkForwardRun(
        forecasts=pd.DataFrame.from_records(forecast_records),
        failures=pd.DataFrame.from_records(failure_records),
    )


def summarize_walk_forward_losses(
    forecasts: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize volatility losses for every ticker and model."""

    required_columns = {
        "ticker",
        "model_name",
        "forecast_date",
        "actual_return",
        "forecast_variance",
    }

    missing_columns = required_columns.difference(forecasts.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Walk-forward summary requires columns: {missing_text}")

    if forecasts.empty:
        raise ValueError("Walk-forward summary received no forecasts.")

    records: list[dict[str, object]] = []

    for (
        ticker,
        model_name,
    ), group in forecasts.groupby(
        [
            "ticker",
            "model_name",
        ],
        sort=True,
    ):
        ordered = group.sort_values("forecast_date")

        loss_table = build_volatility_loss_table(
            actual_returns=(ordered["actual_return"].reset_index(drop=True)),
            forecast_variance=(ordered["forecast_variance"].reset_index(drop=True)),
        )

        summary = summarize_volatility_losses(loss_table)

        records.append(
            {
                "ticker": ticker,
                "model_name": model_name,
                "forecast_start": (ordered["forecast_date"].min()),
                "forecast_end": (ordered["forecast_date"].max()),
                **summary,
            }
        )

    result = pd.DataFrame.from_records(records)

    result["qlike_rank"] = result.groupby("ticker")["mean_qlike"].rank(
        method="min",
        ascending=True,
    )

    result["volatility_mae_rank"] = result.groupby("ticker")["volatility_mae"].rank(
        method="min",
        ascending=True,
    )

    result["preliminary_qlike_winner"] = result["qlike_rank"].eq(1)

    return result.sort_values(
        [
            "ticker",
            "qlike_rank",
            "model_name",
        ]
    ).reset_index(drop=True)


def summarize_walk_forward_var(
    forecasts: pd.DataFrame,
) -> pd.DataFrame:
    """Run 95 and 99 percent VaR backtests."""

    confidence_settings = {
        95: 0.05,
        99: 0.01,
    }

    records: list[dict[str, object]] = []

    for (
        ticker,
        model_name,
    ), group in forecasts.groupby(
        [
            "ticker",
            "model_name",
        ],
        sort=True,
    ):
        ordered = group.sort_values("forecast_date")

        for (
            confidence_level,
            tail_probability,
        ) in confidence_settings.items():
            threshold_column = f"var_threshold_{confidence_level}"

            if threshold_column not in ordered:
                raise ValueError(f"Missing VaR column: {threshold_column}")

            summary = summarize_var_backtest(
                actual_returns=(ordered["actual_return"].reset_index(drop=True)),
                var_thresholds=(ordered[threshold_column].reset_index(drop=True)),
                tail_probability=tail_probability,
            )

            records.append(
                {
                    "ticker": ticker,
                    "model_name": model_name,
                    "confidence_level": (confidence_level),
                    "tail_probability": (tail_probability),
                    **summary,
                }
            )

    return (
        pd.DataFrame.from_records(records)
        .sort_values(
            [
                "ticker",
                "model_name",
                "confidence_level",
            ]
        )
        .reset_index(drop=True)
    )
