"""Tests for Granite TTM inference utilities."""

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.foundation.granite_adapter import (
    GraniteWindow,
)
from ruang_risiko_idx.foundation.granite_inference import (
    GraniteInferenceConfig,
    build_granite_input_array,
)


def make_window(
    context_length: int = 512,
    pred_len: int = 1,
) -> GraniteWindow:
    """Create a deterministic Granite window."""

    context_dates = pd.bdate_range(
        "2022-01-03",
        periods=context_length,
    )

    forecast_dates = pd.bdate_range(
        context_dates[-1] + pd.offsets.BDay(1),
        periods=pred_len,
    )

    context = pd.DataFrame(
        {
            "log_return": np.linspace(
                -0.02,
                0.02,
                context_length,
                dtype="float64",
            )
        }
    )

    actual_future = pd.DataFrame(
        {
            "trade_date": forecast_dates,
            "log_return": np.linspace(
                0.001,
                0.002,
                pred_len,
                dtype="float64",
            ),
        }
    )

    return GraniteWindow(
        ticker="BBCA.JK",
        cutoff_date=context_dates[-1],
        context=context,
        context_timestamps=pd.Series(
            context_dates,
            name="trade_date",
        ),
        forecast_timestamps=pd.Series(
            forecast_dates,
            name="trade_date",
        ),
        actual_future=actual_future,
    )


def test_granite_inference_config_defaults() -> None:
    """Validate the frozen zero-shot defaults."""

    config = GraniteInferenceConfig()

    config.validate()

    assert config.context_length == 512
    assert config.prediction_length == 1
    assert config.frequency == "D"
    assert config.batch_size == 64


def test_build_granite_input_array_shape() -> None:
    """Build the expected batch, context, channel tensor shape."""

    config = GraniteInferenceConfig()

    windows = [
        make_window(),
        make_window(),
    ]

    values = build_granite_input_array(
        windows=windows,
        config=config,
    )

    assert values.shape == (
        2,
        512,
        1,
    )

    assert values.dtype == np.float32
    assert np.isfinite(values).all()


def test_build_granite_input_array_rejects_context_mismatch() -> None:
    """Reject a window that does not match the model context."""

    config = GraniteInferenceConfig(
        context_length=512,
    )

    window = make_window(
        context_length=400,
    )

    with pytest.raises(
        ValueError,
        match="context length",
    ):
        build_granite_input_array(
            windows=[window],
            config=config,
        )


def test_build_granite_input_array_rejects_horizon_mismatch() -> None:
    """Reject a window that does not match the forecast horizon."""

    config = GraniteInferenceConfig(
        prediction_length=1,
    )

    window = make_window(
        pred_len=2,
    )

    with pytest.raises(
        ValueError,
        match="prediction length",
    ):
        build_granite_input_array(
            windows=[window],
            config=config,
        )


def test_build_granite_input_array_requires_windows() -> None:
    """Reject an empty inference batch."""

    config = GraniteInferenceConfig()

    with pytest.raises(
        ValueError,
        match="At least one Granite window",
    ):
        build_granite_input_array(
            windows=[],
            config=config,
        )
