"""Registry-driven inference for latest direction probability."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from ruang_risiko_idx.ml.features import (
    FEATURE_COLUMNS,
    build_ticker_ml_features,
)
from ruang_risiko_idx.ml.logistic import (
    build_logistic_pipeline,
)
from ruang_risiko_idx.ml.random_forest import (
    build_random_forest_model,
)

SUPPORTED_MODELS = {
    "constant_probability",
    "logistic_regression",
    "random_forest",
}


@dataclass(frozen=True)
class DirectionModelAssignment:
    """Store one ticker deployment assignment."""

    ticker: str
    model: str
    parameters: dict[str, Any]


def load_classical_deployment_registry(
    path: Path,
) -> dict[str, DirectionModelAssignment]:
    """Load and validate ticker-specific deployment assignments."""

    if not path.exists():
        raise FileNotFoundError(
            f"Classical deployment registry was not found at {path}."
        )

    payload = yaml.safe_load(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "Classical deployment registry must contain a mapping."
        )

    ticker_payload = payload.get("tickers")

    if not isinstance(ticker_payload, dict) or not ticker_payload:
        raise ValueError(
            "Classical deployment registry must contain ticker assignments."
        )

    assignments: dict[str, DirectionModelAssignment] = {}

    for ticker, config in ticker_payload.items():
        if not isinstance(config, dict):
            raise ValueError(
                f"Deployment configuration for {ticker} must be a mapping."
            )

        model = str(
            config.get(
                "model",
                "",
            )
        )

        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported deployment model for {ticker}: {model}."
            )

        parameters = config.get(
            "parameters",
            {},
        )

        if not isinstance(parameters, dict):
            raise ValueError(
                f"Deployment parameters for {ticker} must be a mapping."
            )

        assignments[str(ticker)] = DirectionModelAssignment(
            ticker=str(ticker),
            model=model,
            parameters=dict(parameters),
        )

    return assignments


def _prepare_ticker_inference_data(
    ticker_data: pd.DataFrame,
    minimum_labeled_observations: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prepare labeled history and the latest unlabeled feature row."""

    if minimum_labeled_observations < 250:
        raise ValueError(
            "Minimum labeled observations must be at least 250."
        )

    features = build_ticker_ml_features(
        ticker_data=ticker_data,
    )

    complete_features = features[
        list(FEATURE_COLUMNS)
    ].notna().all(axis=1)

    inference_candidates = features.loc[
        complete_features
    ].copy()

    if inference_candidates.empty:
        raise ValueError(
            "No complete feature row is available for inference."
        )

    latest = (
        inference_candidates.sort_values(
            "trade_date"
        )
        .tail(1)
        .copy()
    )

    latest_target = latest[
        "target_up_next_day"
    ].iloc[0]

    if pd.notna(latest_target):
        raise ValueError(
            "Latest inference row unexpectedly contains a known target."
        )

    labeled = features.dropna(
        subset=[
            *FEATURE_COLUMNS,
            "target_up_next_day",
        ]
    ).copy()

    labeled["target_up_next_day"] = labeled[
        "target_up_next_day"
    ].astype("int8")

    labeled = labeled.sort_values(
        "trade_date"
    ).reset_index(drop=True)

    if len(labeled) < minimum_labeled_observations:
        raise ValueError(
            "Not enough labeled observations for direction inference."
        )

    if not (
        labeled["trade_date"].max()
        < latest["trade_date"].iloc[0]
    ):
        raise ValueError(
            "Training observations must occur before the inference row."
        )

    return labeled, latest


def _predict_logistic_probability(
    training_data: pd.DataFrame,
    inference_row: pd.DataFrame,
    parameters: dict[str, Any],
) -> float:
    """Fit the frozen Logistic Regression configuration and predict."""

    pipeline = build_logistic_pipeline(
        c_value=float(
            parameters["C"]
        ),
        maximum_iterations=int(
            parameters.get(
                "maximum_iterations",
                2_000,
            )
        ),
        random_state=int(
            parameters.get(
                "random_state",
                42,
            )
        ),
    )

    pipeline.fit(
        training_data[
            list(FEATURE_COLUMNS)
        ],
        training_data[
            "target_up_next_day"
        ],
    )

    probability = pipeline.predict_proba(
        inference_row[
            list(FEATURE_COLUMNS)
        ]
    )[0, 1]

    return float(probability)


def _predict_random_forest_probability(
    training_data: pd.DataFrame,
    inference_row: pd.DataFrame,
    parameters: dict[str, Any],
) -> float:
    """Fit the frozen Random Forest configuration and predict."""

    max_depth_value = parameters.get(
        "max_depth"
    )

    max_depth = (
        None
        if max_depth_value is None
        else int(max_depth_value)
    )

    model = build_random_forest_model(
        n_estimators=int(
            parameters["n_estimators"]
        ),
        max_depth=max_depth,
        min_samples_leaf=int(
            parameters["min_samples_leaf"]
        ),
        max_features=parameters.get(
            "max_features",
            "sqrt",
        ),
        random_state=int(
            parameters.get(
                "random_state",
                42,
            )
        ),
        n_jobs=int(
            parameters.get(
                "n_jobs",
                -1,
            )
        ),
    )

    model.fit(
        training_data[
            list(FEATURE_COLUMNS)
        ],
        training_data[
            "target_up_next_day"
        ],
    )

    probability = model.predict_proba(
        inference_row[
            list(FEATURE_COLUMNS)
        ]
    )[0, 1]

    return float(probability)


def _predict_constant_probability(
    training_data: pd.DataFrame,
) -> float:
    """Return the positive rate from all available labeled history."""

    return float(
        training_data[
            "target_up_next_day"
        ].mean()
    )


def build_ticker_direction_snapshot(
    ticker_data: pd.DataFrame,
    assignment: DirectionModelAssignment,
    minimum_labeled_observations: int = 750,
) -> dict[str, object]:
    """Build the latest direction estimate for one ticker."""

    if ticker_data.empty:
        raise ValueError(
            f"No analytics data is available for {assignment.ticker}."
        )

    tickers = set(
        ticker_data["ticker"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if tickers != {assignment.ticker}:
        raise ValueError(
            "Ticker data does not match the deployment assignment."
        )

    training_data, inference_row = (
        _prepare_ticker_inference_data(
            ticker_data=ticker_data,
            minimum_labeled_observations=(
                minimum_labeled_observations
            ),
        )
    )

    if assignment.model == "logistic_regression":
        probability_up = (
            _predict_logistic_probability(
                training_data=training_data,
                inference_row=inference_row,
                parameters=assignment.parameters,
            )
        )
    elif assignment.model == "random_forest":
        probability_up = (
            _predict_random_forest_probability(
                training_data=training_data,
                inference_row=inference_row,
                parameters=assignment.parameters,
            )
        )
    elif assignment.model == "constant_probability":
        probability_up = (
            _predict_constant_probability(
                training_data=training_data,
            )
        )
    else:
        raise ValueError(
            f"Unsupported model: {assignment.model}."
        )

    if not np.isfinite(probability_up):
        raise ValueError(
            f"Probability for {assignment.ticker} is not finite."
        )

    if not 0.0 <= probability_up <= 1.0:
        raise ValueError(
            f"Probability for {assignment.ticker} is outside [0, 1]."
        )

    as_of_date = pd.Timestamp(
        inference_row[
            "trade_date"
        ].iloc[0]
    )

    return {
        "ticker": assignment.ticker,
        "as_of_date": as_of_date,
        "forecast_horizon": "next_trading_day",
        "selected_model": assignment.model,
        "probability_up": probability_up,
        "probability_down": 1.0 - probability_up,
        "training_observations": int(
            len(training_data)
        ),
        "training_start_date": pd.Timestamp(
            training_data[
                "trade_date"
            ].min()
        ),
        "training_end_date": pd.Timestamp(
            training_data[
                "trade_date"
            ].max()
        ),
        "feature_count": len(
            FEATURE_COLUMNS
        ),
    }


def build_latest_direction_snapshot(
    analytics: pd.DataFrame,
    assignments: dict[str, DirectionModelAssignment],
    minimum_labeled_observations: int = 750,
) -> pd.DataFrame:
    """Build the latest direction estimates for all registry tickers."""

    if analytics.empty:
        raise ValueError(
            "Analytics data cannot be empty."
        )

    required_columns = {
        "ticker",
        "trade_date",
    }

    missing_columns = required_columns.difference(
        analytics.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(
                missing_columns
            )
        )

        raise ValueError(
            f"Analytics data is missing required columns: {missing_text}"
        )

    analytics_tickers = set(
        analytics["ticker"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    registry_tickers = set(
        assignments
    )

    missing_tickers = (
        registry_tickers
        - analytics_tickers
    )

    if missing_tickers:
        missing_text = ", ".join(
            sorted(
                missing_tickers
            )
        )

        raise ValueError(
            f"Analytics data is missing registry tickers: {missing_text}"
        )

    records: list[
        dict[str, object]
    ] = []

    for ticker in sorted(
        assignments
    ):
        ticker_data = analytics.loc[
            analytics[
                "ticker"
            ].eq(ticker)
        ].copy()

        records.append(
            build_ticker_direction_snapshot(
                ticker_data=ticker_data,
                assignment=assignments[
                    ticker
                ],
                minimum_labeled_observations=(
                    minimum_labeled_observations
                ),
            )
        )

    return (
        pd.DataFrame.from_records(
            records
        )
        .sort_values(
            "ticker"
        )
        .reset_index(
            drop=True
        )
    )
