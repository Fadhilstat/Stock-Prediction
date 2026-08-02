"""Tests for conditional volatility model fitting."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.garch import (
    fit_volatility_model,
    forecast_one_day,
)
from ruang_risiko_idx.econometrics.specification import (
    VolatilityModelSpec,
)


def _generate_clustered_returns(
    observations: int = 600,
) -> pd.Series:
    """Generate simple synthetic volatility clustering."""

    random_generator = np.random.default_rng(42)

    variance = np.empty(observations)
    returns = np.empty(observations)

    variance[0] = 0.0001
    returns[0] = np.sqrt(variance[0]) * random_generator.standard_normal()

    for position in range(
        1,
        observations,
    ):
        variance[position] = (
            0.000002 + 0.08 * returns[position - 1] ** 2 + 0.90 * variance[position - 1]
        )

        returns[position] = np.sqrt(variance[position]) * random_generator.standard_normal()

    return pd.Series(
        returns,
        index=pd.date_range(
            "2020-01-01",
            periods=observations,
            freq="B",
        ),
    )


def test_fit_garch_model_and_forecast() -> None:
    specification = VolatilityModelSpec(
        name="garch_normal",
        volatility="GARCH",
        distribution="normal",
    )

    fitted = fit_volatility_model(
        returns=_generate_clustered_returns(),
        specification=specification,
    )

    assert len(fitted.conditional_volatility) == 600

    assert fitted.conditional_volatility.gt(0).all()

    assert len(fitted.standardized_residuals) > 500

    forecast = forecast_one_day(fitted)

    assert forecast["forecast_variance"] > 0
    assert forecast["forecast_volatility"] > 0
