"""Tests for leakage-safe walk-forward forecasting."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics.specification import (
    VolatilityModelSpec,
)
from ruang_risiko_idx.econometrics.walk_forward import (
    WalkForwardConfig,
    run_walk_forward_forecasts,
    select_training_returns,
)


def test_training_window_excludes_forecast_date() -> None:
    returns = pd.Series(
        [0.01, 0.02, 0.03, 0.04, 9.99],
        index=pd.date_range(
            "2026-01-01",
            periods=5,
            freq="D",
        ),
    )

    config = WalkForwardConfig(
        test_size=2,
        minimum_observations=250,
        window_type="expanding",
    )

    training = select_training_returns(
        returns=returns,
        forecast_position=4,
        config=config,
    )

    assert len(training) == 4
    assert 9.99 not in training.to_numpy()
    assert training.index.max() < returns.index[4]


def test_small_walk_forward_run() -> None:
    generator = np.random.default_rng(42)

    returns = pd.Series(
        generator.normal(
            loc=0.0,
            scale=0.01,
            size=260,
        ),
        index=pd.date_range(
            "2020-01-01",
            periods=260,
            freq="B",
        ),
    )

    specification = VolatilityModelSpec(
        name="garch_normal",
        volatility="GARCH",
        distribution="normal",
    )

    config = WalkForwardConfig(
        test_size=2,
        minimum_observations=250,
        progress_every=0,
    )

    run = run_walk_forward_forecasts(
        returns=returns,
        ticker="AAA",
        specification=specification,
        config=config,
    )

    assert len(run.forecasts) == 2
    assert run.failures.empty
    assert (run.forecasts["training_end_date"] < run.forecasts["forecast_date"]).all()
    assert (run.forecasts["forecast_variance"] > 0).all()
