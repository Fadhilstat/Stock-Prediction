"""Historical volatility feature engineering."""

from __future__ import annotations

from math import sqrt

import pandas as pd

REQUIRED_COLUMNS = {
    "ticker",
    "log_return",
}


def add_volatility_features(
    data: pd.DataFrame,
    windows: tuple[int, ...] = (21, 63),
    annualization_factor: int = 252,
) -> pd.DataFrame:
    """Calculate rolling annualized volatility."""

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Volatility calculation requires columns: {missing_text}")

    if annualization_factor <= 0:
        raise ValueError("Annualization factor must be positive.")

    if not windows:
        raise ValueError("At least one volatility window is required.")

    result = data.copy()
    annualization_scale = sqrt(annualization_factor)

    for window in windows:
        if window < 2:
            raise ValueError("Volatility windows must contain at least two days.")

        column_name = f"volatility_{window}d"

        result[column_name] = (
            result.groupby(
                "ticker",
                sort=False,
            )["log_return"].transform(
                lambda values, current_window=window: values.rolling(
                    window=current_window,
                    min_periods=current_window,
                ).std(ddof=1)
            )
            * annualization_scale
        )

    return result
