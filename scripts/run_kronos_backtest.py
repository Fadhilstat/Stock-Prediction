"""Run a leakage-safe rolling zero-shot Kronos backtest."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ruang_risiko_idx.foundation import (
    KronosBacktestConfig,
    KronosInferenceConfig,
    build_kronos_backtest_windows,
    configure_inference_seed,
    derive_window_seed,
    evaluate_kronos_prediction,
    load_kronos_predictor,
    predict_kronos_window,
    summarize_kronos_backtest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "foundation" / "kronos" / "rolling_backtest"

DEFAULT_TICKERS = [
    "ANTM.JK",
    "ASII.JK",
    "BBCA.JK",
    "BBRI.JK",
    "TLKM.JK",
    "^JKSE",
]


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Run a rolling one-step zero-shot Kronos backtest.")
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the analytics Parquet dataset.",
    )

    parser.add_argument(
        "--kronos-root",
        type=Path,
        default=Path("/content/Kronos"),
        help="Path to the cloned Kronos repository.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for forecast and summary files.",
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Ticker symbols included in the backtest.",
    )

    parser.add_argument(
        "--lookback",
        type=int,
        default=400,
        help="Historical observations in each context window.",
    )

    parser.add_argument(
        "--evaluation-size",
        type=int,
        default=20,
        help="Forecast windows evaluated for each ticker.",
    )

    parser.add_argument(
        "--stride",
        type=int,
        default=5,
        help="Trading-day distance between target windows.",
    )

    parser.add_argument(
        "--model-name",
        default="NeoQuasar/Kronos-small",
        help="Hugging Face Kronos model identifier.",
    )

    parser.add_argument(
        "--tokenizer-name",
        default="NeoQuasar/Kronos-Tokenizer-base",
        help="Hugging Face Kronos tokenizer identifier.",
    )

    parser.add_argument(
        "--max-context",
        type=int,
        default=512,
        help="Maximum model context length.",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Kronos sampling temperature.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=0,
        help="Kronos top-k sampling value.",
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Kronos nucleus sampling value.",
    )

    parser.add_argument(
        "--sample-count",
        type=int,
        default=1,
        help="Generated samples for each forecast window.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base seed used to derive per-window seeds.",
    )

    parser.add_argument(
        "--device",
        default=None,
        help="Inference device such as cpu, cuda, or mps.",
    )

    parser.add_argument(
        "--verbose-model",
        action="store_true",
        help="Show detailed Kronos generation progress.",
    )

    return parser.parse_args()


def validate_input_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and normalize the analytics dataset."""

    required_columns = {
        "ticker",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Analytics data is missing columns: {missing_text}")

    clean_data = data.copy()

    clean_data["trade_date"] = pd.to_datetime(
        clean_data["trade_date"],
        errors="raise",
    )

    clean_data = (
        clean_data.sort_values(
            [
                "ticker",
                "trade_date",
            ]
        )
        .drop_duplicates(
            subset=[
                "ticker",
                "trade_date",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if clean_data.empty:
        raise ValueError("Analytics data must not be empty.")

    return clean_data


def write_parquet_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write a Parquet file through a temporary path."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    data.to_parquet(
        temporary_path,
        index=False,
    )

    temporary_path.replace(destination)


def make_json_safe(
    value: Any,
) -> Any:
    """Convert nested values into strict JSON-compatible values."""

    if isinstance(
        value,
        dict,
    ):
        return {str(key): make_json_safe(item) for key, item in value.items()}

    if isinstance(
        value,
        list | tuple,
    ):
        return [make_json_safe(item) for item in value]

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        np.generic,
    ):
        return make_json_safe(value.item())

    if isinstance(
        value,
        float,
    ):
        if not math.isfinite(value):
            return None

    return value


def write_json_atomic(
    payload: dict[str, Any],
    destination: Path,
) -> None:
    """Write strict JSON through a temporary path."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    safe_payload = make_json_safe(payload)

    temporary_path.write_text(
        json.dumps(
            safe_payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(destination)


def build_summary_payload(
    forecasts: pd.DataFrame,
    metrics: pd.DataFrame,
    args: argparse.Namespace,
    device: str,
    runtime_seconds: float,
) -> dict[str, Any]:
    """Build lightweight evidence for the rolling backtest."""

    ticker_ranges = []

    for ticker, ticker_data in forecasts.groupby(
        "ticker",
        sort=True,
    ):
        ticker_ranges.append(
            {
                "ticker": ticker,
                "forecast_count": int(len(ticker_data)),
                "first_target_date": pd.Timestamp(ticker_data["target_date"].min()),
                "last_target_date": pd.Timestamp(ticker_data["target_date"].max()),
            }
        )

    return {
        "generated_at_utc": pd.Timestamp.now(tz="UTC"),
        "experiment": "rolling_zero_shot_kronos_backtest",
        "evaluation_scope": (
            "full_252" if args.evaluation_size == 252 and args.stride == 1 else "custom"
        ),
        "model_name": args.model_name,
        "tokenizer_name": args.tokenizer_name,
        "device": str(device),
        "base_seed": int(args.seed),
        "configuration": {
            "lookback": int(args.lookback),
            "evaluation_size_per_ticker": int(args.evaluation_size),
            "stride": int(args.stride),
            "pred_len": 1,
            "max_context": int(args.max_context),
            "temperature": float(args.temperature),
            "top_k": int(args.top_k),
            "top_p": float(args.top_p),
            "sample_count": int(args.sample_count),
        },
        "ticker_count": int(forecasts["ticker"].nunique()),
        "forecast_count": int(len(forecasts)),
        "runtime_seconds": float(runtime_seconds),
        "amount_definition": (
            "Close multiplied by volume as a proxy. It is not actual exchange transaction value."
        ),
        "baseline_definitions": {
            "random_walk": ("The next close equals the latest observed close."),
            "return_persistence": ("The next log return equals the latest observed log return."),
        },
        "ticker_ranges": ticker_ranges,
        "metrics": metrics.to_dict(orient="records"),
    }


def main() -> int:
    """Run rolling forecasts and save evaluation artifacts."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics dataset was not found at {args.input}.")

    if not args.kronos_root.exists():
        raise FileNotFoundError(f"Kronos repository was not found at {args.kronos_root}.")

    backtest_config = KronosBacktestConfig(
        lookback=args.lookback,
        evaluation_size=(args.evaluation_size),
        stride=args.stride,
        pred_len=1,
    )

    inference_config = KronosInferenceConfig(
        model_name=args.model_name,
        tokenizer_name=(args.tokenizer_name),
        max_context=args.max_context,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        sample_count=args.sample_count,
        seed=args.seed,
        device=args.device,
    )

    backtest_config.validate()
    inference_config.validate()

    if backtest_config.lookback > inference_config.max_context:
        raise ValueError("Backtest lookback cannot exceed the Kronos maximum context.")

    analytics = validate_input_data(pd.read_parquet(args.input))

    missing_tickers = sorted(set(args.tickers).difference(analytics["ticker"].unique()))

    if missing_tickers:
        missing_text = ", ".join(missing_tickers)

        raise ValueError(f"Analytics data does not contain tickers: {missing_text}")

    print(f"Loading tokenizer: {inference_config.tokenizer_name}")

    print(f"Loading model: {inference_config.model_name}")

    predictor, device = load_kronos_predictor(
        kronos_root=args.kronos_root,
        config=inference_config,
    )

    windows = []

    for ticker in args.tickers:
        ticker_windows = build_kronos_backtest_windows(
            data=analytics,
            ticker=ticker,
            config=backtest_config,
        )

        windows.extend(ticker_windows)

        print(f"Prepared {len(ticker_windows)} windows for {ticker}.")

    forecast_count = len(windows)

    print(f"Running {forecast_count} forecasts on device {device}.")

    start_time = time.perf_counter()

    forecast_records: list[dict[str, object]] = []

    for position, window in enumerate(
        windows,
        start=1,
    ):
        window_seed = derive_window_seed(
            base_seed=inference_config.seed,
            ticker=window.ticker,
            cutoff_date=window.cutoff_date,
        )

        configure_inference_seed(window_seed)

        print(f"[{position}/{forecast_count}] {window.ticker} cutoff={window.cutoff_date.date()}")

        prediction = predict_kronos_window(
            predictor=predictor,
            window=window,
            config=inference_config,
            verbose=args.verbose_model,
        )

        evaluation = evaluate_kronos_prediction(
            prediction=prediction,
            window=window,
            window_seed=window_seed,
        )

        forecast_records.append(evaluation)

    runtime_seconds = time.perf_counter() - start_time

    forecasts = (
        pd.DataFrame.from_records(forecast_records)
        .sort_values(
            [
                "ticker",
                "target_date",
            ]
        )
        .reset_index(drop=True)
    )

    metrics = summarize_kronos_backtest(forecasts)

    forecasts_path = args.output_dir / "forecasts.parquet"

    metrics_path = args.output_dir / "metrics.parquet"

    summary_path = args.output_dir / "summary.json"

    write_parquet_atomic(
        forecasts,
        forecasts_path,
    )

    write_parquet_atomic(
        metrics,
        metrics_path,
    )

    summary_payload = build_summary_payload(
        forecasts=forecasts,
        metrics=metrics,
        args=args,
        device=str(device),
        runtime_seconds=runtime_seconds,
    )

    write_json_atomic(
        summary_payload,
        summary_path,
    )

    display_columns = [
        "ticker",
        "model_name",
        "observations",
        "close_mae",
        "close_rmse",
        "log_return_mae",
        "direction_accuracy",
        "balanced_accuracy",
        "roc_auc",
        "ohlc_valid_rate",
    ]

    print()
    print("Rolling backtest metrics:")
    print(metrics[display_columns].to_string(index=False))

    print()
    print(f"Runtime: {runtime_seconds:.2f} seconds")

    print(f"Forecasts: {forecasts_path}")

    print(f"Metrics: {metrics_path}")

    print(f"Summary: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
