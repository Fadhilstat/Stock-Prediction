"""Run one reproducible Kronos zero-shot smoke test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ruang_risiko_idx.foundation import (
    KronosInferenceConfig,
    build_kronos_backtest_window,
    load_kronos_predictor,
    predict_kronos_window,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "foundation" / "kronos" / "smoke_test"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Run one leakage-safe Kronos zero-shot forecast.")
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )

    parser.add_argument(
        "--kronos-root",
        type=Path,
        default=Path("/content/Kronos"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--ticker",
        default="BBCA.JK",
    )

    parser.add_argument(
        "--cutoff-date",
        default="2026-07-31",
    )

    parser.add_argument(
        "--lookback",
        type=int,
        default=400,
    )

    parser.add_argument(
        "--pred-len",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--model-name",
        default="NeoQuasar/Kronos-small",
    )

    parser.add_argument(
        "--tokenizer-name",
        default="NeoQuasar/Kronos-Tokenizer-base",
    )

    parser.add_argument(
        "--max-context",
        type=int,
        default=512,
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
    )

    parser.add_argument(
        "--sample-count",
        type=int,
        default=1,
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

    parser.add_argument(
        "--quiet",
        action="store_true",
    )

    return parser.parse_args()


def build_output_stem(
    ticker: str,
    cutoff_date: pd.Timestamp,
) -> str:
    """Build a filesystem-safe output name."""

    safe_ticker = ticker.lower().replace(".", "_").replace("^", "")

    cutoff_text = cutoff_date.strftime("%Y%m%d")

    return f"{safe_ticker}_{cutoff_text}"


def evaluate_prediction(
    prediction: pd.DataFrame,
    actual_future: pd.DataFrame,
    last_close: float,
) -> dict[str, object]:
    """Evaluate a one-step Kronos smoke-test prediction."""

    if len(prediction) != 1:
        raise ValueError("The smoke test expects exactly one prediction row.")

    if len(actual_future) != 1:
        raise ValueError("The smoke test expects exactly one actual row.")

    predicted = prediction.iloc[0]
    actual = actual_future.iloc[0]

    predicted_close = float(predicted["close"])

    actual_close = float(actual["close"])

    predicted_log_return = float(np.log(predicted_close / last_close))

    actual_log_return = float(np.log(actual_close / last_close))

    predicted_open = float(predicted["open"])

    predicted_high = float(predicted["high"])

    predicted_low = float(predicted["low"])

    direction_correct = bool(np.sign(predicted_log_return) == np.sign(actual_log_return))

    ohlc_is_valid = bool(
        predicted_high
        >= max(
            predicted_open,
            predicted_close,
            predicted_low,
        )
        and predicted_low
        <= min(
            predicted_open,
            predicted_close,
            predicted_high,
        )
    )

    volume_is_nonnegative = bool(float(predicted["volume"]) >= 0)

    absolute_close_error = abs(predicted_close - actual_close)

    absolute_percentage_error = absolute_close_error / actual_close

    return {
        "target_date": str(pd.Timestamp(predicted["trade_date"]).date()),
        "last_close": last_close,
        "predicted_close": predicted_close,
        "actual_close": actual_close,
        "predicted_log_return": (predicted_log_return),
        "actual_log_return": (actual_log_return),
        "absolute_close_error": (absolute_close_error),
        "absolute_percentage_error": (absolute_percentage_error),
        "direction_correct": (direction_correct),
        "ohlc_is_valid": (ohlc_is_valid),
        "volume_is_nonnegative": (volume_is_nonnegative),
    }


def write_parquet_atomic(
    data: pd.DataFrame,
    destination: Path,
) -> None:
    """Write Parquet through a temporary file."""

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


def write_json_atomic(
    payload: object,
    destination: Path,
) -> None:
    """Write JSON through a temporary file."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f".{destination.name}.tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(destination)


def main() -> int:
    """Run one Kronos zero-shot smoke test."""

    args = parse_arguments()

    if args.pred_len != 1:
        raise ValueError("The smoke-test runner currently supports pred_len=1.")

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics data was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    window = build_kronos_backtest_window(
        data=analytics,
        ticker=args.ticker,
        cutoff_date=args.cutoff_date,
        lookback=args.lookback,
        pred_len=args.pred_len,
    )

    config = KronosInferenceConfig(
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

    print(f"Loading {config.tokenizer_name}.")

    print(f"Loading {config.model_name}.")

    predictor, device = load_kronos_predictor(
        kronos_root=args.kronos_root,
        config=config,
    )

    print("Running Kronos zero-shot forecast.")

    prediction = predict_kronos_window(
        predictor=predictor,
        window=window,
        config=config,
        verbose=not args.quiet,
    )

    last_close = float(window.context["close"].iloc[-1])

    evaluation = evaluate_prediction(
        prediction=prediction,
        actual_future=(window.actual_future),
        last_close=last_close,
    )

    metadata = {
        "ticker": window.ticker,
        "cutoff_date": str(window.cutoff_date.date()),
        "lookback": window.lookback,
        "pred_len": window.pred_len,
        "model_name": config.model_name,
        "tokenizer_name": (config.tokenizer_name),
        "device": device,
        "max_context": (config.max_context),
        "temperature": (config.temperature),
        "top_k": config.top_k,
        "top_p": config.top_p,
        "sample_count": (config.sample_count),
        "seed": config.seed,
        "amount_definition": ("closing price multiplied by volume proxy"),
        "evaluation": evaluation,
    }

    output_stem = build_output_stem(
        ticker=window.ticker,
        cutoff_date=window.cutoff_date,
    )

    prediction_path = args.output_dir / f"{output_stem}_prediction.parquet"

    actual_path = args.output_dir / f"{output_stem}_actual.parquet"

    evaluation_path = args.output_dir / f"{output_stem}_evaluation.json"

    write_parquet_atomic(
        prediction,
        prediction_path,
    )

    write_parquet_atomic(
        window.actual_future,
        actual_path,
    )

    write_json_atomic(
        metadata,
        evaluation_path,
    )

    print("\nKronos prediction:")
    print(prediction.to_string(index=False))

    print("\nActual observation:")
    print(window.actual_future.to_string(index=False))

    summary = pd.DataFrame(
        [
            {
                "ticker": window.ticker,
                "cutoff_date": (window.cutoff_date),
                "target_date": (evaluation["target_date"]),
                "predicted_close": (evaluation["predicted_close"]),
                "actual_close": (evaluation["actual_close"]),
                "absolute_close_error": (evaluation["absolute_close_error"]),
                "direction_correct": (evaluation["direction_correct"]),
                "ohlc_is_valid": (evaluation["ohlc_is_valid"]),
                "device": device,
            }
        ]
    )

    print("\nSmoke-test evaluation:")
    print(summary.to_string(index=False))

    print(f"\nPrediction saved to {prediction_path}.")

    print(f"Actual observation saved to {actual_path}.")

    print(f"Evaluation saved to {evaluation_path}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
