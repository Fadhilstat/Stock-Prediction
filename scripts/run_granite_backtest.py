"""Run a leakage-safe rolling zero-shot Granite TTM backtest."""

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
    GraniteBacktestConfig,
    GraniteInferenceConfig,
    build_granite_backtest_windows,
    evaluate_granite_prediction,
    load_granite_model,
    predict_granite_windows,
    summarize_granite_backtest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytics_daily.parquet"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "foundation"
    / "granite"
    / "rolling_backtest"
)

DEFAULT_TICKERS = [
    "ANTM.JK",
    "ASII.JK",
    "BBCA.JK",
    "BBRI.JK",
    "TLKM.JK",
]


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run a rolling one-step zero-shot Granite TTM backtest."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
    )

    parser.add_argument(
        "--context-length",
        type=int,
        default=512,
    )

    parser.add_argument(
        "--evaluation-size",
        type=int,
        default=252,
    )

    parser.add_argument(
        "--stride",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
    )

    parser.add_argument(
        "--model-name",
        default=(
            "ibm-granite/"
            "granite-timeseries-ttm-r2"
        ),
    )

    parser.add_argument(
        "--frequency",
        default="D",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--device",
        default=None,
    )

    return parser.parse_args()


def validate_input_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and normalize the analytics dataset."""

    required_columns = {
        "ticker",
        "trade_date",
        "adjusted_close",
        "log_return",
    }

    missing_columns = required_columns.difference(
        data.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Analytics data is missing columns: "
            + missing_text
        )

    if data.empty:
        raise ValueError(
            "Analytics data must not be empty."
        )

    result = data.copy()

    result["trade_date"] = pd.to_datetime(
        result["trade_date"],
        errors="raise",
    )

    if result.duplicated(
        subset=[
            "ticker",
            "trade_date",
        ]
    ).any():
        raise ValueError(
            "Analytics data contains duplicate ticker dates."
        )

    return (
        result.sort_values(
            [
                "ticker",
                "trade_date",
            ]
        )
        .reset_index(drop=True)
    )


def write_parquet_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write Parquet through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(
        f".{destination.name}.tmp"
    )

    data.to_parquet(
        temporary_path,
        index=False,
    )

    temporary_path.replace(
        destination
    )


def make_json_safe(
    value: Any,
) -> Any:
    """Convert nested values into strict JSON values."""

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        list | tuple,
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        np.generic,
    ):
        return make_json_safe(
            value.item()
        )

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
    """Write strict JSON through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(
        f".{destination.name}.tmp"
    )

    safe_payload = make_json_safe(
        payload
    )

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

    temporary_path.replace(
        destination
    )


def build_summary_payload(
    forecasts: pd.DataFrame,
    metrics: pd.DataFrame,
    args: argparse.Namespace,
    model_key: str,
    device: str,
    runtime_seconds: float,
) -> dict[str, Any]:
    """Build lightweight evidence for the backtest."""

    ticker_ranges = []

    for ticker, ticker_data in forecasts.groupby(
        "ticker",
        sort=True,
    ):
        ticker_ranges.append(
            {
                "ticker": ticker,
                "forecast_count": int(
                    len(ticker_data)
                ),
                "first_target_date": pd.Timestamp(
                    ticker_data[
                        "target_date"
                    ].min()
                ),
                "last_target_date": pd.Timestamp(
                    ticker_data[
                        "target_date"
                    ].max()
                ),
            }
        )

    return {
        "generated_at_utc": pd.Timestamp.now(
            tz="UTC"
        ),
        "experiment": (
            "rolling_zero_shot_granite_ttm_backtest"
        ),
        "evaluation_scope": (
            "full_252"
            if (
                args.evaluation_size == 252
                and args.stride == 1
                and len(args.tickers) == 5
            )
            else "custom"
        ),
        "model_name": args.model_name,
        "model_revision": model_key,
        "target": "log_return",
        "price_basis": "adjusted_close",
        "context_length": int(
            args.context_length
        ),
        "prediction_length": 1,
        "frequency": args.frequency,
        "evaluation_size": int(
            args.evaluation_size
        ),
        "stride": int(
            args.stride
        ),
        "batch_size": int(
            args.batch_size
        ),
        "seed": int(
            args.seed
        ),
        "device": device,
        "runtime_seconds": float(
            runtime_seconds
        ),
        "forecast_rows": int(
            len(forecasts)
        ),
        "metric_rows": int(
            len(metrics)
        ),
        "ticker_count": int(
            forecasts["ticker"].nunique()
        ),
        "target_after_cutoff": bool(
            (
                forecasts["target_date"]
                > forecasts["cutoff_date"]
            ).all()
        ),
        "all_numeric_finite": bool(
            np.isfinite(
                forecasts[
                    [
                        "actual_log_return",
                        "predicted_log_return",
                        "actual_adjusted_close",
                        "predicted_adjusted_close",
                    ]
                ].to_numpy(
                    dtype="float64"
                )
            ).all()
        ),
        "duplicate_windows": int(
            forecasts.duplicated(
                subset=[
                    "ticker",
                    "target_date",
                ]
            ).sum()
        ),
        "ticker_ranges": ticker_ranges,
        "metrics": metrics.to_dict(
            orient="records"
        ),
    }


def main() -> int:
    """Run the rolling Granite TTM backtest."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Analytics data was not found at {args.input}."
        )

    analytics = validate_input_data(
        pd.read_parquet(
            args.input
        )
    )

    available_tickers = set(
        analytics["ticker"]
        .dropna()
        .astype(str)
        .unique()
    )

    unknown_tickers = sorted(
        set(args.tickers).difference(
            available_tickers
        )
    )

    if unknown_tickers:
        raise ValueError(
            "Unknown tickers: "
            + ", ".join(
                unknown_tickers
            )
        )

    backtest_config = GraniteBacktestConfig(
        context_length=args.context_length,
        evaluation_size=args.evaluation_size,
        stride=args.stride,
        pred_len=1,
    )

    inference_config = GraniteInferenceConfig(
        model_name=args.model_name,
        context_length=args.context_length,
        prediction_length=1,
        frequency=args.frequency,
        batch_size=args.batch_size,
        seed=args.seed,
        device=args.device,
    )

    all_windows = []

    for ticker in args.tickers:
        ticker_windows = (
            build_granite_backtest_windows(
                data=analytics,
                ticker=ticker,
                config=backtest_config,
            )
        )

        all_windows.extend(
            ticker_windows
        )

        print(
            f"{ticker}: "
            f"{len(ticker_windows)} windows"
        )

    print(
        "Total windows:",
        len(all_windows),
    )

    start_time = time.perf_counter()

    model, device, model_key = (
        load_granite_model(
            config=inference_config,
        )
    )

    print(
        "Model revision:",
        model_key,
    )

    print(
        "Device:",
        device,
    )

    predictions = predict_granite_windows(
        model=model,
        windows=all_windows,
        config=inference_config,
        device=device,
    )

    if len(predictions) != len(all_windows):
        raise RuntimeError(
            "Prediction count does not match window count."
        )

    evaluation_records = []

    for index, window in enumerate(
        all_windows
    ):
        prediction = predictions.iloc[
            [index]
        ].copy()

        record = evaluate_granite_prediction(
            prediction=prediction,
            window=window,
            data=analytics,
        )

        evaluation_records.append(
            record
        )

    forecasts = pd.DataFrame.from_records(
        evaluation_records
    )

    forecasts = (
        forecasts.sort_values(
            [
                "ticker",
                "target_date",
            ]
        )
        .reset_index(drop=True)
    )

    metrics = summarize_granite_backtest(
        forecasts
    )

    runtime_seconds = (
        time.perf_counter()
        - start_time
    )

    summary = build_summary_payload(
        forecasts=forecasts,
        metrics=metrics,
        args=args,
        model_key=model_key,
        device=device,
        runtime_seconds=runtime_seconds,
    )

    write_parquet_atomic(
        forecasts,
        args.output_dir
        / "forecasts.parquet",
    )

    write_parquet_atomic(
        metrics,
        args.output_dir
        / "metrics.parquet",
    )

    write_json_atomic(
        summary,
        args.output_dir
        / "summary.json",
    )

    print()
    print(
        metrics.to_string(
            index=False
        )
    )

    print()
    print(
        "Forecast rows:",
        len(forecasts),
    )

    print(
        "Duplicate windows:",
        summary["duplicate_windows"],
    )

    print(
        "Target after cutoff:",
        summary["target_after_cutoff"],
    )

    print(
        "All numeric finite:",
        summary["all_numeric_finite"],
    )

    print(
        "Runtime seconds:",
        f"{runtime_seconds:.2f}",
    )

    print(
        "Outputs:",
        args.output_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
