"""Fit all configured volatility models for each ticker."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from ruang_risiko_idx.econometrics import (
    DEFAULT_MODEL_SPECS,
    calculate_residual_diagnostics,
    fit_volatility_model,
    rank_in_sample_models,
    summarize_fitted_model,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "analytics_daily.parquet"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "garch"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=("Fit GARCH, EGARCH, and GJR-GARCH models."))

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the daily analytics dataset.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated model outputs.",
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Optional subset of tickers.",
    )

    parser.add_argument(
        "--diagnostic-lags",
        type=int,
        default=10,
        help="Number of lags used in residual diagnostics.",
    )

    parser.add_argument(
        "--minimum-observations",
        type=int,
        default=250,
        help="Minimum valid return observations per fit.",
    )

    return parser.parse_args()


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


def build_failure_record(
    ticker: str,
    model_name: str,
    error: Exception,
    elapsed_seconds: float,
) -> dict[str, object]:
    """Create a consistent failed-fit record."""

    return {
        "ticker": ticker,
        "model_name": model_name,
        "fit_status": "failed",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "elapsed_seconds": elapsed_seconds,
        "aic": np.nan,
        "bic": np.nan,
        "convergence_flag": -1,
        "ljung_box_p_value": np.nan,
        "squared_ljung_box_p_value": np.nan,
        "arch_lm_p_value": np.nan,
    }


def main() -> int:
    """Fit all model specifications and save comparison outputs."""

    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(f"Analytics data was not found at {args.input}.")

    analytics = pd.read_parquet(args.input)

    required_columns = {
        "ticker",
        "trade_date",
        "log_return",
    }

    missing_columns = required_columns.difference(analytics.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"GARCH fitting requires columns: {missing_text}")

    available_tickers = sorted(analytics["ticker"].dropna().astype(str).unique().tolist())

    tickers = args.tickers if args.tickers else available_tickers

    unknown_tickers = sorted(set(tickers).difference(available_tickers))

    if unknown_tickers:
        raise ValueError("Unknown tickers requested: " + ", ".join(unknown_tickers))

    fit_records: list[dict[str, object]] = []
    volatility_frames: list[pd.DataFrame] = []

    total_models = len(tickers) * len(DEFAULT_MODEL_SPECS)

    completed_models = 0

    print(f"Fitting {total_models} models for {len(tickers)} tickers.")

    for ticker in tickers:
        ticker_data = (
            analytics.loc[
                analytics["ticker"].eq(ticker),
                [
                    "trade_date",
                    "log_return",
                ],
            ]
            .sort_values("trade_date")
            .set_index("trade_date")
        )

        returns = ticker_data["log_return"]

        for specification in DEFAULT_MODEL_SPECS:
            completed_models += 1

            print(f"[{completed_models}/{total_models}] {ticker} | {specification.name}")

            started_at = perf_counter()

            try:
                fitted = fit_volatility_model(
                    returns=returns,
                    specification=specification,
                    minimum_observations=(args.minimum_observations),
                )

                summary = summarize_fitted_model(fitted)

                diagnostics = calculate_residual_diagnostics(
                    fitted.standardized_residuals,
                    lags=args.diagnostic_lags,
                )

                elapsed_seconds = perf_counter() - started_at

                record = {
                    "ticker": ticker,
                    "fit_status": "success",
                    "error_type": None,
                    "error_message": None,
                    "elapsed_seconds": elapsed_seconds,
                    "fitted_at": datetime.now(UTC).isoformat(),
                    **summary,
                    **diagnostics,
                }

                fit_records.append(record)

                volatility_frames.append(
                    pd.DataFrame(
                        {
                            "trade_date": (fitted.conditional_volatility.index),
                            "ticker": ticker,
                            "model_name": (specification.name),
                            "conditional_volatility": (fitted.conditional_volatility.to_numpy()),
                        }
                    )
                )

            except Exception as error:
                elapsed_seconds = perf_counter() - started_at

                fit_records.append(
                    build_failure_record(
                        ticker=ticker,
                        model_name=(specification.name),
                        error=error,
                        elapsed_seconds=(elapsed_seconds),
                    )
                )

                print(f"Fit failed: {type(error).__name__}: {error}")

    comparison = pd.DataFrame.from_records(fit_records)

    successful = comparison.loc[comparison["fit_status"].eq("success")].copy()

    failed = comparison.loc[comparison["fit_status"].eq("failed")].copy()

    if successful.empty:
        raise RuntimeError("Every volatility model fit failed.")

    ranked = rank_in_sample_models(successful)

    if volatility_frames:
        conditional_volatility = pd.concat(
            volatility_frames,
            ignore_index=True,
        )
    else:
        conditional_volatility = pd.DataFrame(
            columns=[
                "trade_date",
                "ticker",
                "model_name",
                "conditional_volatility",
            ]
        )

    latest_forecasts = (
        ranked[
            [
                "ticker",
                "model_name",
                "volatility_model",
                "distribution",
                "forecast_mean",
                "forecast_variance",
                "forecast_volatility",
                "persistence",
                "half_life_days",
                "aic",
                "bic",
                "aic_rank",
                "bic_rank",
                "convergence_flag",
                "variance_diagnostics_pass",
            ]
        ]
        .sort_values(
            [
                "ticker",
                "bic_rank",
                "aic_rank",
            ]
        )
        .reset_index(drop=True)
    )

    write_parquet_atomic(
        ranked,
        args.output_dir / "model_comparison.parquet",
    )

    write_parquet_atomic(
        latest_forecasts,
        args.output_dir / "latest_forecasts.parquet",
    )

    write_parquet_atomic(
        conditional_volatility,
        args.output_dir / "conditional_volatility.parquet",
    )

    if not failed.empty:
        write_parquet_atomic(
            failed,
            args.output_dir / "failed_fits.parquet",
        )

    winners = ranked.loc[
        ranked["preliminary_bic_winner"],
        [
            "ticker",
            "model_name",
            "distribution",
            "bic",
            "persistence",
            "half_life_days",
            "forecast_volatility",
            "variance_diagnostics_pass",
        ],
    ].sort_values("ticker")

    print(f"\nSuccessful fits: {len(successful)}")

    print(f"Failed fits: {len(failed)}")

    print("\nPreliminary BIC winners:")

    print(winners.to_string(index=False))

    print(f"\nOutputs saved to {args.output_dir}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
