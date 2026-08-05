"""Tests for Kronos zero-shot inference utilities."""

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.foundation.kronos_adapter import (
    KRONOS_FEATURE_COLUMNS,
    KronosWindow,
)
from ruang_risiko_idx.foundation.kronos_inference import (
    KronosInferenceConfig,
    predict_kronos_window,
    resolve_kronos_device,
)


class FakeKronosPredictor:
    """Return a predefined prediction without loading Kronos."""

    def __init__(
        self,
        prediction: pd.DataFrame,
    ) -> None:
        self.prediction = prediction

    def predict(
        self,
        **kwargs: object,
    ) -> pd.DataFrame:
        """Return a copy of the predefined prediction."""

        return self.prediction.copy()


def make_window(
    lookback: int = 3,
) -> KronosWindow:
    """Create a small deterministic Kronos window."""

    context_dates = pd.Series(
        pd.date_range(
            "2026-01-05",
            periods=lookback,
            freq="B",
        ),
        name="trade_date",
    )

    target_date = pd.Timestamp(context_dates.iloc[-1]) + pd.offsets.BDay(1)

    context = pd.DataFrame(
        {
            "open": np.linspace(
                100.0,
                102.0,
                lookback,
            ),
            "high": np.linspace(
                101.0,
                103.0,
                lookback,
            ),
            "low": np.linspace(
                99.0,
                101.0,
                lookback,
            ),
            "close": np.linspace(
                100.5,
                102.5,
                lookback,
            ),
            "volume": np.linspace(
                1_000.0,
                1_200.0,
                lookback,
            ),
            "amount": np.linspace(
                100_500.0,
                123_000.0,
                lookback,
            ),
        }
    )

    forecast_timestamps = pd.Series(
        [target_date],
        name="trade_date",
    )

    actual_future = pd.DataFrame(
        {
            "trade_date": [target_date],
            "open": [103.0],
            "high": [104.0],
            "low": [102.0],
            "close": [103.5],
            "volume": [1_300.0],
            "amount": [134_550.0],
        }
    )

    return KronosWindow(
        ticker="AAA",
        cutoff_date=pd.Timestamp(context_dates.iloc[-1]),
        context=context,
        context_timestamps=context_dates,
        forecast_timestamps=forecast_timestamps,
        actual_future=actual_future,
    )


def make_prediction(
    target_date: pd.Timestamp,
) -> pd.DataFrame:
    """Create one valid fake Kronos prediction."""

    return pd.DataFrame(
        {
            "open": [102.8],
            "high": [104.2],
            "low": [102.1],
            "close": [103.7],
            "volume": [1_250.0],
            "amount": [129_625.0],
        },
        index=pd.DatetimeIndex(
            [target_date],
            name="trade_date",
        ),
    )


def test_resolve_requested_device() -> None:
    """A requested device should be preserved."""

    assert resolve_kronos_device("cpu") == "cpu"


def test_inference_config_rejects_invalid_top_p() -> None:
    """Invalid nucleus sampling settings should fail."""

    config = KronosInferenceConfig(top_p=1.2)

    with pytest.raises(
        ValueError,
        match="top_p",
    ):
        config.validate()


def test_predict_kronos_window_adds_metadata() -> None:
    """Inference output should contain ticker and cutoff metadata."""

    window = make_window()

    target_date = pd.Timestamp(window.forecast_timestamps.iloc[0])

    predictor = FakeKronosPredictor(make_prediction(target_date))

    result = predict_kronos_window(
        predictor=predictor,
        window=window,
        config=KronosInferenceConfig(
            max_context=10,
            device="cpu",
        ),
        verbose=False,
    )

    expected_columns = [
        "ticker",
        "cutoff_date",
        "trade_date",
        *KRONOS_FEATURE_COLUMNS,
    ]

    assert list(result.columns) == expected_columns
    assert len(result) == 1
    assert result.loc[0, "ticker"] == "AAA"
    assert result.loc[0, "cutoff_date"] == window.cutoff_date
    assert result.loc[0, "trade_date"] == target_date


def test_predict_kronos_window_rejects_long_context() -> None:
    """Context longer than max_context should fail."""

    window = make_window(lookback=4)

    target_date = pd.Timestamp(window.forecast_timestamps.iloc[0])

    predictor = FakeKronosPredictor(make_prediction(target_date))

    with pytest.raises(
        ValueError,
        match="maximum context",
    ):
        predict_kronos_window(
            predictor=predictor,
            window=window,
            config=KronosInferenceConfig(
                max_context=3,
                device="cpu",
            ),
            verbose=False,
        )


def test_predict_kronos_window_rejects_nonfinite_values() -> None:
    """Non-finite model output should fail validation."""

    window = make_window()

    target_date = pd.Timestamp(window.forecast_timestamps.iloc[0])

    prediction = make_prediction(target_date)

    prediction.loc[
        target_date,
        "close",
    ] = np.nan

    predictor = FakeKronosPredictor(prediction)

    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        predict_kronos_window(
            predictor=predictor,
            window=window,
            config=KronosInferenceConfig(
                max_context=10,
                device="cpu",
            ),
            verbose=False,
        )
