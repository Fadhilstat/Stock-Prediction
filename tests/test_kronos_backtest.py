"""Tests for leakage-safe rolling Kronos backtesting."""

import numpy as np
import pandas as pd
import pytest

from ruang_risiko_idx.foundation.kronos_adapter import KronosWindow
from ruang_risiko_idx.foundation.kronos_backtest import (
    KronosBacktestConfig,
    build_kronos_backtest_windows,
    derive_window_seed,
    evaluate_kronos_prediction,
    summarize_kronos_backtest,
)


def make_market_data(
    observations: int = 520,
) -> pd.DataFrame:
    """Create deterministic synthetic OHLCV data."""

    dates = pd.bdate_range(
        start="2024-01-02",
        periods=observations,
    )

    close = np.linspace(
        100.0,
        160.0,
        observations,
    )

    return pd.DataFrame(
        {
            "ticker": ["AAA"] * observations,
            "trade_date": dates,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.arange(
                1_000,
                1_000 + observations,
                dtype="float64",
            ),
        }
    )


def make_evaluation_window() -> KronosWindow:
    """Create a deterministic one-step forecast window."""

    context_dates = pd.Series(
        pd.bdate_range(
            start="2026-01-05",
            periods=3,
        ),
        name="trade_date",
    )

    target_date = pd.Timestamp(context_dates.iloc[-1]) + pd.offsets.BDay(1)

    context = pd.DataFrame(
        {
            "open": [
                99.0,
                100.0,
                101.0,
            ],
            "high": [
                101.0,
                102.0,
                103.0,
            ],
            "low": [
                98.0,
                99.0,
                100.0,
            ],
            "close": [
                100.0,
                100.0,
                102.0,
            ],
            "volume": [
                1_000.0,
                1_100.0,
                1_200.0,
            ],
            "amount": [
                100_000.0,
                110_000.0,
                122_400.0,
            ],
        }
    )

    actual_future = pd.DataFrame(
        {
            "trade_date": [target_date],
            "open": [101.0],
            "high": [102.0],
            "low": [100.0],
            "close": [101.0],
            "volume": [1_300.0],
            "amount": [131_300.0],
        }
    )

    return KronosWindow(
        ticker="AAA",
        cutoff_date=pd.Timestamp(context_dates.iloc[-1]),
        context=context,
        context_timestamps=context_dates,
        forecast_timestamps=pd.Series(
            [target_date],
            name="trade_date",
        ),
        actual_future=actual_future,
    )


def test_backtest_config_rejects_invalid_stride() -> None:
    """Backtest stride must be positive."""

    config = KronosBacktestConfig(stride=0)

    with pytest.raises(
        ValueError,
        match="stride",
    ):
        config.validate()


def test_window_seed_is_stable() -> None:
    """The same forecast window should use the same seed."""

    first_seed = derive_window_seed(
        base_seed=42,
        ticker="AAA",
        cutoff_date="2026-01-07",
    )

    second_seed = derive_window_seed(
        base_seed=42,
        ticker="AAA",
        cutoff_date="2026-01-07",
    )

    assert first_seed == second_seed


def test_window_seed_changes_between_windows() -> None:
    """Different forecast windows should use different seeds."""

    first_seed = derive_window_seed(
        base_seed=42,
        ticker="AAA",
        cutoff_date="2026-01-07",
    )

    second_seed = derive_window_seed(
        base_seed=42,
        ticker="AAA",
        cutoff_date="2026-01-08",
    )

    third_seed = derive_window_seed(
        base_seed=42,
        ticker="BBB",
        cutoff_date="2026-01-07",
    )

    assert first_seed != second_seed
    assert first_seed != third_seed


def test_build_backtest_windows_uses_recent_stride() -> None:
    """Rolling targets should be recent and chronologically ordered."""

    market_data = make_market_data()

    windows = build_kronos_backtest_windows(
        data=market_data,
        ticker="AAA",
        config=KronosBacktestConfig(
            lookback=400,
            evaluation_size=3,
            stride=5,
            pred_len=1,
        ),
    )

    assert len(windows) == 3

    target_dates = [pd.Timestamp(window.forecast_timestamps.iloc[0]) for window in windows]

    expected_target_dates = (
        market_data["trade_date"]
        .iloc[
            [
                509,
                514,
                519,
            ]
        ]
        .tolist()
    )

    assert target_dates == expected_target_dates
    assert target_dates == sorted(target_dates)

    for window in windows:
        assert len(window.context) == 400
        assert len(window.actual_future) == 1

        assert pd.Timestamp(window.context_timestamps.max()) == pd.Timestamp(window.cutoff_date)

        assert pd.Timestamp(window.forecast_timestamps.min()) > pd.Timestamp(window.cutoff_date)


def test_build_backtest_windows_rejects_insufficient_history() -> None:
    """Backtest construction should reject insufficient history."""

    market_data = make_market_data(observations=405)

    config = KronosBacktestConfig(
        lookback=400,
        evaluation_size=3,
        stride=5,
        pred_len=1,
    )

    with pytest.raises(
        ValueError,
        match="eligible rolling windows",
    ):
        build_kronos_backtest_windows(
            data=market_data,
            ticker="AAA",
            config=config,
        )


def test_evaluate_kronos_prediction() -> None:
    """One forecast should produce model and baseline results."""

    window = make_evaluation_window()

    target_date = pd.Timestamp(window.forecast_timestamps.iloc[0])

    prediction = pd.DataFrame(
        {
            "trade_date": [target_date],
            "open": [102.0],
            "high": [104.0],
            "low": [101.0],
            "close": [103.0],
            "volume": [1_250.0],
            "amount": [128_750.0],
        }
    )

    result = evaluate_kronos_prediction(
        prediction=prediction,
        window=window,
        window_seed=123,
    )

    assert result["ticker"] == "AAA"
    assert result["window_seed"] == 123
    assert result["previous_close"] == 100.0
    assert result["last_close"] == 102.0
    assert result["actual_close"] == 101.0
    assert result["predicted_close"] == 103.0
    assert result["random_walk_close"] == 102.0

    assert np.isclose(
        result["persistence_close"],
        104.04,
    )

    assert result["actual_up"] == 0
    assert result["kronos_predicted_up"] == 1
    assert result["ohlc_is_valid"] is True
    assert result["volume_is_nonnegative"] is True


def test_evaluate_rejects_invalid_target_date() -> None:
    """Prediction and actual target dates must match."""

    window = make_evaluation_window()

    prediction = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2026-01-20")],
            "open": [102.0],
            "high": [104.0],
            "low": [101.0],
            "close": [103.0],
            "volume": [1_250.0],
            "amount": [128_750.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="target dates",
    ):
        evaluate_kronos_prediction(
            prediction=prediction,
            window=window,
            window_seed=123,
        )


def test_summarize_kronos_backtest() -> None:
    """Summary should compare Kronos with two naive baselines."""

    forecasts = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4,
            "actual_close": [
                101.0,
                99.0,
                102.0,
                98.0,
            ],
            "actual_log_return": [
                0.01,
                -0.01,
                0.02,
                -0.02,
            ],
            "actual_up": [
                1,
                0,
                1,
                0,
            ],
            "predicted_close": [
                102.0,
                98.0,
                101.0,
                97.0,
            ],
            "predicted_log_return": [
                0.02,
                -0.02,
                0.01,
                -0.01,
            ],
            "kronos_predicted_up": [
                1,
                0,
                1,
                0,
            ],
            "random_walk_close": [
                100.0,
                100.0,
                100.0,
                100.0,
            ],
            "random_walk_log_return": [
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            "random_walk_predicted_up": [
                0,
                0,
                0,
                0,
            ],
            "persistence_close": [
                101.0,
                101.0,
                99.0,
                99.0,
            ],
            "persistence_log_return": [
                0.01,
                0.01,
                -0.01,
                -0.01,
            ],
            "persistence_predicted_up": [
                1,
                1,
                0,
                0,
            ],
            "ohlc_is_valid": [
                True,
                True,
                False,
                True,
            ],
            "volume_is_nonnegative": [
                True,
                True,
                True,
                False,
            ],
        }
    )

    summary = summarize_kronos_backtest(forecasts)

    assert len(summary) == 3

    assert set(summary["model_name"]) == {
        "kronos",
        "random_walk",
        "return_persistence",
    }

    kronos = summary.loc[summary["model_name"].eq("kronos")].iloc[0]

    random_walk = summary.loc[summary["model_name"].eq("random_walk")].iloc[0]

    assert kronos["observations"] == 4
    assert kronos["direction_accuracy"] == 1.0
    assert kronos["balanced_accuracy"] == 1.0
    assert kronos["roc_auc"] == 1.0
    assert kronos["ohlc_valid_rate"] == 0.75

    assert kronos["nonnegative_volume_rate"] == 0.75

    assert random_walk["direction_accuracy"] == 0.5

    assert np.isnan(random_walk["ohlc_valid_rate"])
