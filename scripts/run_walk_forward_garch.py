"""Run leakage-safe one-day GARCH forecasts."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ruang_risiko_idx.econometrics import (
    DEFAULT_MODEL_SPECS,
    WalkForwardConfig,
    run_walk_forward_forecasts,
    summarize_walk_forward_losses,
    summarize_walk_forward_var,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "walk_forward"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Run daily one-step GARCH walk-forward forecasts.")
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
    )

    parser.add_argument(
        "--models",
        nargs="+",
    )

    parser.add_argument(
        "--test-size",
        type=int,
        default=252,
    )

    parser.add_argument(
        "--minimum-observations",
        type=int,
        default=750,
    )

    parser.add_argument(
        "--window-type",
        choices=[
            "expanding",
            "rolling",
        ],
        default="expanding",
    )

    parser.add_argument(
        "--rolling-window",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--progress-every",
        type=int,
        default=25,
    )

    return parser.parse_args()


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


def main() -> int:
    """Run selected ticker and model combinations."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics data was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    available_tickers = sorted(analytics["ticker"].dropna().astype(str).unique().tolist())

    selected_tickers = args.tickers if args.tickers else available_tickers

    unknown_tickers = sorted(set(selected_tickers).difference(available_tickers))

    if unknown_tickers:
        raise ValueError("Unknown tickers: " + ", ".join(unknown_tickers))

    specification_map = {specification.name: specification for specification in DEFAULT_MODEL_SPECS}

    selected_model_names = args.models if args.models else list(specification_map)

    unknown_models = sorted(set(selected_model_names).difference(specification_map))

    if unknown_models:
        raise ValueError("Unknown models: " + ", ".join(unknown_models))

    config = WalkForwardConfig(
        test_size=args.test_size,
        minimum_observations=(args.minimum_observations),
        window_type=args.window_type,
        rolling_window=(args.rolling_window if args.window_type == "rolling" else None),
        progress_every=args.progress_every,
    )

    forecast_frames: list[pd.DataFrame] = []

    failure_frames: list[pd.DataFrame] = []

    total_runs = len(selected_tickers) * len(selected_model_names)

    completed_runs = 0

    print(f"Running {total_runs} ticker-model combinations.")

    for ticker in selected_tickers:
        ticker_returns = (
            analytics.loc[
                analytics["ticker"].eq(ticker),
                [
                    "trade_date",
                    "log_return",
                ],
            ]
            .sort_values("trade_date")
            .set_index("trade_date")["log_return"]
        )

        for model_name in selected_model_names:
            completed_runs += 1

            print(f"\n[{completed_runs}/{total_runs}] {ticker} | {model_name}")

            run = run_walk_forward_forecasts(
                returns=ticker_returns,
                ticker=ticker,
                specification=(specification_map[model_name]),
                config=config,
            )

            if not run.forecasts.empty:
                forecast_frames.append(run.forecasts)

            if not run.failures.empty:
                failure_frames.append(run.failures)

    if not forecast_frames:
        raise RuntimeError("No walk-forward forecasts were produced.")

    forecasts = pd.concat(
        forecast_frames,
        ignore_index=True,
    )

    losses = summarize_walk_forward_losses(forecasts)

    var_backtests = summarize_walk_forward_var(forecasts)

    write_parquet_atomic(
        forecasts,
        args.output_dir / "walk_forward_forecasts.parquet",
    )

    write_parquet_atomic(
        losses,
        args.output_dir / "volatility_metrics.parquet",
    )

    write_parquet_atomic(
        var_backtests,
        args.output_dir / "var_backtests.parquet",
    )

    failure_count = 0

    if failure_frames:
        failures = pd.concat(
            failure_frames,
            ignore_index=True,
        )

        failure_count = len(failures)

        write_parquet_atomic(
            failures,
            args.output_dir / "failed_forecasts.parquet",
        )

    print(f"\nSuccessful forecasts: {len(forecasts):,}")

    print(f"Failed forecasts: {failure_count:,}")

    print("\nVolatility metrics:")
    print(losses.to_string(index=False))

    print("\nVaR backtests:")
    print(
        var_backtests[
            [
                "ticker",
                "model_name",
                "confidence_level",
                "observations",
                "violation_count",
                "observed_violation_rate",
                "kupiec_p_value",
                "christoffersen_independence_p_value",
                "conditional_coverage_p_value",
            ]
        ].to_string(index=False)
    )

    print(f"\nOutputs saved to {args.output_dir}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
