"""Foundation model data adapters and inference utilities."""

from ruang_risiko_idx.foundation.granite_adapter import (
    GRANITE_TARGET_COLUMN,
    GraniteWindow,
    build_granite_backtest_window,
    validate_granite_data,
)
from ruang_risiko_idx.foundation.granite_backtest import (
    GraniteBacktestConfig,
    build_granite_backtest_windows,
    evaluate_granite_prediction,
    summarize_granite_backtest,
)
from ruang_risiko_idx.foundation.granite_inference import (
    GraniteInferenceConfig,
    build_granite_input_array,
    configure_granite_seed,
    load_granite_model,
    predict_granite_windows,
    resolve_granite_device,
)
from ruang_risiko_idx.foundation.kronos_adapter import (
    KRONOS_FEATURE_COLUMNS,
    KronosWindow,
    add_kronos_amount_proxy,
    build_kronos_backtest_window,
    validate_market_data,
)
from ruang_risiko_idx.foundation.kronos_backtest import (
    KronosBacktestConfig,
    build_kronos_backtest_windows,
    derive_window_seed,
    evaluate_kronos_prediction,
    summarize_kronos_backtest,
)
from ruang_risiko_idx.foundation.kronos_inference import (
    KronosInferenceConfig,
    configure_inference_seed,
    load_kronos_predictor,
    predict_kronos_window,
    resolve_kronos_device,
)

__all__ = [
    "summarize_granite_backtest",
    "evaluate_granite_prediction",
    "build_granite_backtest_windows",
    "GraniteBacktestConfig",
    "resolve_granite_device",
    "predict_granite_windows",
    "load_granite_model",
    "configure_granite_seed",
    "build_granite_input_array",
    "GraniteInferenceConfig",
    "GRANITE_TARGET_COLUMN",
    "KRONOS_FEATURE_COLUMNS",
    "GraniteWindow",
    "KronosBacktestConfig",
    "KronosInferenceConfig",
    "KronosWindow",
    "add_kronos_amount_proxy",
    "build_granite_backtest_window",
    "build_kronos_backtest_window",
    "build_kronos_backtest_windows",
    "configure_inference_seed",
    "derive_window_seed",
    "evaluate_kronos_prediction",
    "load_kronos_predictor",
    "predict_kronos_window",
    "resolve_kronos_device",
    "summarize_kronos_backtest",
    "validate_granite_data",
    "validate_market_data",
]
