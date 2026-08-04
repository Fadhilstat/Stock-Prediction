"""Leakage-safe Random Forest training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ruang_risiko_idx.ml.baselines import (
    evaluate_probability_predictions,
)
from ruang_risiko_idx.ml.features import FEATURE_COLUMNS
from ruang_risiko_idx.ml.splitting import TickerDatasetSplit


@dataclass(frozen=True)
class RandomForestSearchConfig:
    """Configure Random Forest model selection."""

    n_estimators: int = 400
    max_depth_values: tuple[int | None, ...] = (
        3,
        6,
        None,
    )
    min_samples_leaf_values: tuple[int, ...] = (
        10,
        25,
        50,
    )
    max_features: str | float | None = "sqrt"
    random_state: int = 42
    n_jobs: int = -1

    def validate(self) -> None:
        """Validate Random Forest search settings."""

        if self.n_estimators < 50:
            raise ValueError("The number of trees must be at least 50.")

        if not self.max_depth_values:
            raise ValueError("At least one maximum depth is required.")

        if not self.min_samples_leaf_values:
            raise ValueError("At least one minimum leaf size is required.")

        if any(value < 1 for value in self.min_samples_leaf_values):
            raise ValueError("Minimum leaf sizes must be positive.")


@dataclass
class RandomForestTickerResult:
    """Store selected Random Forest outputs for one ticker."""

    selected_parameters: dict[str, object]
    validation_results: pd.DataFrame
    validation_predictions: pd.DataFrame
    test_metrics: dict[str, float | int | object]
    test_predictions: pd.DataFrame
    feature_importances: pd.DataFrame
    fitted_model: RandomForestClassifier


def _validate_model_data(
    dataset: pd.DataFrame,
) -> None:
    """Validate Random Forest features and target."""

    required_columns = {
        *FEATURE_COLUMNS,
        "target_up_next_day",
    }

    missing_columns = required_columns.difference(dataset.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Random Forest data is missing columns: {missing_text}")

    if dataset[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("Random Forest features contain missing values.")

    if not dataset["target_up_next_day"].isin([0, 1]).all():
        raise ValueError("Random Forest target must contain only zero and one.")


def build_random_forest_model(
    n_estimators: int,
    max_depth: int | None,
    min_samples_leaf: int,
    max_features: str | float | None = "sqrt",
    random_state: int = 42,
    n_jobs: int = -1,
) -> RandomForestClassifier:
    """Build one Random Forest classifier."""

    if n_estimators < 50:
        raise ValueError("The number of trees must be at least 50.")

    if min_samples_leaf < 1:
        raise ValueError("Minimum leaf size must be positive.")

    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        criterion="log_loss",
        bootstrap=True,
        class_weight=None,
        random_state=random_state,
        n_jobs=n_jobs,
    )


def _fit_and_predict(
    training_data: pd.DataFrame,
    evaluation_data: pd.DataFrame,
    parameters: dict[str, Any],
    config: RandomForestSearchConfig,
) -> tuple[RandomForestClassifier, pd.Series]:
    """Fit one model and produce positive-class probabilities."""

    _validate_model_data(training_data)
    _validate_model_data(evaluation_data)

    model = build_random_forest_model(
        n_estimators=config.n_estimators,
        max_depth=parameters["max_depth"],
        min_samples_leaf=int(parameters["min_samples_leaf"]),
        max_features=config.max_features,
        random_state=config.random_state,
        n_jobs=config.n_jobs,
    )

    model.fit(
        training_data[list(FEATURE_COLUMNS)],
        training_data["target_up_next_day"],
    )

    probability_up = pd.Series(
        model.predict_proba(evaluation_data[list(FEATURE_COLUMNS)])[:, 1],
        index=evaluation_data.index,
        dtype="float64",
        name="probability_up",
    )

    return model, probability_up


def select_random_forest_parameters(
    split: TickerDatasetSplit,
    config: RandomForestSearchConfig,
) -> tuple[
    dict[str, object],
    pd.DataFrame,
    pd.DataFrame,
]:
    """Select model parameters using validation log loss."""

    config.validate()

    metric_records: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []

    parameter_grid = product(
        config.max_depth_values,
        config.min_samples_leaf_values,
    )

    for max_depth, min_samples_leaf in parameter_grid:
        parameters = {
            "max_depth": max_depth,
            "min_samples_leaf": (min_samples_leaf),
        }

        _, probabilities = _fit_and_predict(
            training_data=split.train,
            evaluation_data=split.validation,
            parameters=parameters,
            config=config,
        )

        metrics = evaluate_probability_predictions(
            actual=split.validation["target_up_next_day"],
            probability_up=probabilities,
        )

        metric_records.append(
            {
                "max_depth": max_depth,
                "min_samples_leaf": (min_samples_leaf),
                **metrics,
            }
        )

        predictions = split.validation[
            [
                "ticker",
                "trade_date",
                "target_date",
                "target_up_next_day",
            ]
        ].copy()

        predictions["max_depth"] = max_depth

        predictions["min_samples_leaf"] = min_samples_leaf

        predictions["probability_up"] = probabilities.to_numpy()

        prediction_frames.append(predictions)

    validation_results = (
        pd.DataFrame.from_records(metric_records)
        .sort_values(
            [
                "log_loss",
                "brier_score",
                "max_depth",
                "min_samples_leaf",
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    validation_results["validation_rank"] = np.arange(
        1,
        len(validation_results) + 1,
    )

    best_row = validation_results.iloc[0]

    selected_parameters = {
        "max_depth": (None if pd.isna(best_row["max_depth"]) else int(best_row["max_depth"])),
        "min_samples_leaf": int(best_row["min_samples_leaf"]),
    }

    validation_predictions = pd.concat(
        prediction_frames,
        ignore_index=True,
    )

    selected_depth = selected_parameters["max_depth"]

    depth_matches = (
        validation_predictions["max_depth"].isna()
        if selected_depth is None
        else validation_predictions["max_depth"].eq(selected_depth)
    )

    validation_predictions["selected_model"] = depth_matches & validation_predictions[
        "min_samples_leaf"
    ].eq(selected_parameters["min_samples_leaf"])

    return (
        selected_parameters,
        validation_results,
        validation_predictions,
    )


def extract_random_forest_importances(
    model: RandomForestClassifier,
) -> pd.DataFrame:
    """Extract impurity-based feature importances."""

    importances = np.asarray(model.feature_importances_)

    if len(importances) != len(FEATURE_COLUMNS):
        raise ValueError("Feature importance count does not match feature count.")

    result = pd.DataFrame(
        {
            "feature": list(FEATURE_COLUMNS),
            "importance": importances,
        }
    )

    return result.sort_values(
        "importance",
        ascending=False,
    ).reset_index(drop=True)


def train_random_forest_for_ticker(
    split: TickerDatasetSplit,
    config: RandomForestSearchConfig,
) -> RandomForestTickerResult:
    """Select, retrain, and evaluate Random Forest."""

    (
        selected_parameters,
        validation_results,
        validation_predictions,
    ) = select_random_forest_parameters(
        split=split,
        config=config,
    )

    combined_training_data = pd.concat(
        [
            split.train,
            split.validation,
        ],
        ignore_index=True,
    )

    fitted_model, test_probabilities = _fit_and_predict(
        training_data=combined_training_data,
        evaluation_data=split.test,
        parameters=selected_parameters,
        config=config,
    )

    test_metrics = evaluate_probability_predictions(
        actual=split.test["target_up_next_day"],
        probability_up=test_probabilities,
    )

    test_metrics.update(
        {
            "max_depth": selected_parameters["max_depth"],
            "min_samples_leaf": (selected_parameters["min_samples_leaf"]),
            "n_estimators": (config.n_estimators),
            "training_observations": int(len(combined_training_data)),
        }
    )

    test_predictions = split.test[
        [
            "ticker",
            "trade_date",
            "target_date",
            "target_up_next_day",
        ]
    ].copy()

    test_predictions["model_name"] = "random_forest"

    test_predictions["probability_up"] = test_probabilities.to_numpy()

    feature_importances = extract_random_forest_importances(fitted_model)

    return RandomForestTickerResult(
        selected_parameters=selected_parameters,
        validation_results=validation_results,
        validation_predictions=validation_predictions,
        test_metrics=test_metrics,
        test_predictions=test_predictions,
        feature_importances=feature_importances,
        fitted_model=fitted_model,
    )
