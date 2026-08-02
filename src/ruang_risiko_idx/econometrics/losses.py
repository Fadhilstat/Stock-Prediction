"""Loss functions for out-of-sample volatility forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_volatility_loss_table(
    actual_returns: pd.Series,
    forecast_variance: pd.Series,
    epsilon: float = 1e-12,
) -> pd.DataFrame:
    """Calculate QLIKE, variance MSE, and volatility MAE inputs."""

    if epsilon <= 0:
        raise ValueError("Epsilon must be positive.")

    actual = pd.Series(
        actual_returns,
        copy=True,
        dtype="float64",
        name="actual_return",
    )

    variance = pd.Series(
        forecast_variance,
        copy=True,
        dtype="float64",
        name="forecast_variance",
    )

    aligned = pd.concat(
        [actual, variance],
        axis=1,
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    )

    aligned = aligned.dropna()

    if aligned.empty:
        raise ValueError("Volatility loss calculation received no valid observations.")

    if aligned["forecast_variance"].lt(0).any():
        raise ValueError("Forecast variance cannot be negative.")

    aligned["forecast_variance"] = aligned["forecast_variance"].clip(lower=epsilon)

    aligned["realized_variance"] = aligned["actual_return"].pow(2)

    aligned["forecast_volatility"] = np.sqrt(aligned["forecast_variance"])

    aligned["realized_volatility"] = aligned["actual_return"].abs()

    aligned["qlike_loss"] = (
        np.log(aligned["forecast_variance"])
        + aligned["realized_variance"] / aligned["forecast_variance"]
    )

    aligned["variance_squared_error"] = (
        aligned["realized_variance"] - aligned["forecast_variance"]
    ).pow(2)

    aligned["volatility_absolute_error"] = (
        aligned["realized_volatility"] - aligned["forecast_volatility"]
    ).abs()

    return aligned


def summarize_volatility_losses(
    loss_table: pd.DataFrame,
) -> dict[str, float | int]:
    """Summarize observation-level volatility losses."""

    required_columns = {
        "qlike_loss",
        "variance_squared_error",
        "volatility_absolute_error",
    }

    missing_columns = required_columns.difference(loss_table.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Volatility loss summary requires columns: {missing_text}")

    if loss_table.empty:
        raise ValueError("Volatility loss summary received an empty table.")

    return {
        "forecast_observations": int(len(loss_table)),
        "mean_qlike": float(loss_table["qlike_loss"].mean()),
        "variance_mse": float(loss_table["variance_squared_error"].mean()),
        "volatility_mae": float(loss_table["volatility_absolute_error"].mean()),
    }
