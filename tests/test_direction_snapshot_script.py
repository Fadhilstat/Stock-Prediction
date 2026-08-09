"""Integration tests for the latest direction snapshot runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_synthetic_analytics(
    ticker: str,
    observations: int = 320,
) -> pd.DataFrame:
    """Build deterministic analytics data for runner tests."""

    dates = pd.bdate_range(
        start="2024-01-02",
        periods=observations,
    )

    index = np.arange(
        observations,
        dtype="float64",
    )

    log_return = (
        0.012 * np.sin(index / 4.0)
        + 0.004 * np.cos(index / 11.0)
    )

    benchmark_return = (
        0.006 * np.sin(index / 5.0)
    )

    close = (
        100.0
        * np.exp(
            np.cumsum(log_return)
        )
    )

    high = close * 1.01
    low = close * 0.99

    volume = (
        1_000_000
        + 50_000 * np.sin(index / 7.0)
        + index * 100
    )

    wealth = np.exp(
        np.cumsum(log_return)
    )

    running_peak = np.maximum.accumulate(
        wealth
    )

    drawdown = (
        wealth / running_peak
        - 1.0
    )

    return pd.DataFrame(
        {
            "ticker": ticker,
            "trade_date": dates,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "log_return": log_return,
            "benchmark_return": benchmark_return,
            "excess_return": (
                log_return
                - benchmark_return
            ),
            "volatility_21d": 0.20,
            "volatility_63d": 0.22,
            "drawdown": drawdown,
            "time_under_water": (
                drawdown < 0.0
            ).astype("int64"),
        }
    )


def test_direction_snapshot_runner_writes_valid_artifacts(
    tmp_path: Path,
) -> None:
    """Runner should write consistent JSON and Parquet snapshots."""

    tickers = (
        "LOGI.JK",
        "FOREST.JK",
        "BASE.JK",
    )

    analytics = pd.concat(
        [
            build_synthetic_analytics(
                ticker=ticker,
            )
            for ticker in tickers
        ],
        ignore_index=True,
    )

    input_path = (
        tmp_path
        / "analytics.parquet"
    )

    registry_path = (
        tmp_path
        / "deployment.yml"
    )

    parquet_output = (
        tmp_path
        / "latest_direction.parquet"
    )

    json_output = (
        tmp_path
        / "latest_direction.json"
    )

    analytics.to_parquet(
        input_path,
        index=False,
    )

    registry = {
        "metadata": {
            "task": "direction_probability",
        },
        "tickers": {
            "LOGI.JK": {
                "model": "logistic_regression",
                "parameters": {
                    "C": 0.01,
                    "maximum_iterations": 2_000,
                    "random_state": 42,
                },
            },
            "FOREST.JK": {
                "model": "random_forest",
                "parameters": {
                    "n_estimators": 50,
                    "max_depth": 3,
                    "min_samples_leaf": 10,
                    "max_features": "sqrt",
                    "random_state": 42,
                    "n_jobs": 1,
                },
            },
            "BASE.JK": {
                "model": "constant_probability",
                "parameters": {
                    "probability_rule": (
                        "full_labeled_history_positive_rate"
                    ),
                },
            },
        },
    }

    registry_path.write_text(
        yaml.safe_dump(
            registry,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(
                PROJECT_ROOT
                / "scripts"
                / "build_latest_direction_snapshot.py"
            ),
            "--input",
            str(input_path),
            "--registry",
            str(registry_path),
            "--output",
            str(parquet_output),
            "--json-output",
            str(json_output),
            "--minimum-labeled-observations",
            "250",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert parquet_output.exists()
    assert json_output.exists()

    parquet_data = pd.read_parquet(
        parquet_output
    )

    json_data = json.loads(
        json_output.read_text(
            encoding="utf-8"
        )
    )

    assert len(parquet_data) == 3
    assert len(json_data) == 3

    assert set(
        parquet_data["ticker"]
    ) == set(tickers)

    assert parquet_data[
        "ticker"
    ].is_unique

    expected_as_of = pd.Timestamp(
        analytics["trade_date"].max()
    )

    assert parquet_data[
        "as_of_date"
    ].eq(
        expected_as_of
    ).all()

    assert (
        parquet_data[
            "training_end_date"
        ]
        < parquet_data[
            "as_of_date"
        ]
    ).all()

    assert parquet_data[
        "probability_up"
    ].between(
        0.0,
        1.0,
        inclusive="both",
    ).all()

    assert parquet_data[
        "probability_down"
    ].between(
        0.0,
        1.0,
        inclusive="both",
    ).all()

    probability_sum = (
        parquet_data[
            "probability_up"
        ]
        + parquet_data[
            "probability_down"
        ]
    )

    assert np.allclose(
        probability_sum,
        1.0,
    )

    assert set(
        parquet_data[
            "forecast_horizon"
        ]
    ) == {
        "next_trading_day"
    }

    models = dict(
        zip(
            parquet_data[
                "ticker"
            ],
            parquet_data[
                "selected_model"
            ],
            strict=True,
        )
    )

    assert models == {
        "BASE.JK": "constant_probability",
        "FOREST.JK": "random_forest",
        "LOGI.JK": "logistic_regression",
    }

    json_by_ticker = {
        row["ticker"]: row
        for row in json_data
    }

    assert set(
        json_by_ticker
    ) == set(tickers)

    for ticker in tickers:
        json_probability = float(
            json_by_ticker[
                ticker
            ]["probability_up"]
        )

        parquet_probability = float(
            parquet_data.loc[
                parquet_data[
                    "ticker"
                ].eq(ticker),
                "probability_up",
            ].iloc[0]
        )

        assert np.isclose(
            json_probability,
            parquet_probability,
        )
