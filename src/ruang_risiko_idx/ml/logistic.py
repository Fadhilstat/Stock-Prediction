"""Leakage-safe Logistic Regression training and evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ruang_risiko_idx.ml.baselines import (
    evaluate_probability_predictions,
)
from ruang_risiko_idx.ml.features import FEATURE_COLUMNS
from ruang_risiko_idx.ml.splitting import TickerDatasetSplit


@dataclass(frozen=True)
class LogisticSearchConfig:
    """Configure Logistic Regression model selection."""

    c_values: tuple[float, ...] = (
        0.01,
        0.1,
        1.0,
        10.0,
    )
    maximum_iterations: int = 2_000
    random_state: int = 42

    def validate(self) -> None:
        """Validate Logistic Regression search settings."""

        if not self.c_values:
            raise ValueError("At least one regularization value is required.")

        if any(value <= 0 for value in self.c_values):
            raise ValueError("Every regularization value must be positive.")

        if self.maximum_iterations < 100:
            raise ValueError("Maximum iterations must be at least 100.")


@dataclass
class LogisticTickerResult:
    """Store selected model outputs for one ticker."""

    selected_c: float
    validation_results: pd.DataFrame
    validation_predictions: pd.DataFrame
    test_metrics: dict[str, float | int]
    test_predictions: pd.DataFrame
    coefficients: pd.DataFrame
    fitted_pipeline: Pipeline


def _validate_feature_columns(
    dataset: pd.DataFrame,
    feature_columns: Sequence[str],
) -> None:
    """Validate feature and target columns."""

    required_columns = {
        *feature_columns,
        "target_up_next_day",
    }

    missing_columns = required_columns.difference(dataset.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Logistic Regression data is missing columns: {missing_text}")

    if dataset[list(feature_columns)].isna().any().any():
        raise ValueError("Logistic Regression features contain missing values.")

    if not dataset["target_up_next_day"].isin([0, 1]).all():
        raise ValueError("Logistic Regression target must contain only zero and one.")


def build_logistic_pipeline(
    c_value: float,
    maximum_iterations: int = 2_000,
    random_state: int = 42,
) -> Pipeline:
    """Build a standardized Logistic Regression pipeline."""

    if c_value <= 0:
        raise ValueError("Regularization value must be positive.")

    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    penalty="l2",
                    solver="lbfgs",
                    max_iter=maximum_iterations,
                    random_state=random_state,
                ),
            ),
        ]
    )


def _fit_and_predict(
    training_data: pd.DataFrame,
    evaluation_data: pd.DataFrame,
    feature_columns: Sequence[str],
    c_value: float,
    config: LogisticSearchConfig,
) -> tuple[Pipeline, pd.Series]:
    """Fit one pipeline and produce positive-class probabilities."""

    _validate_feature_columns(
        training_data,
        feature_columns,
    )

    _validate_feature_columns(
        evaluation_data,
        feature_columns,
    )

    pipeline = build_logistic_pipeline(
        c_value=c_value,
        maximum_iterations=config.maximum_iterations,
        random_state=config.random_state,
    )

    pipeline.fit(
        training_data[list(feature_columns)],
        training_data["target_up_next_day"],
    )

    probability_up = pd.Series(
        pipeline.predict_proba(evaluation_data[list(feature_columns)])[:, 1],
        index=evaluation_data.index,
        dtype="float64",
        name="probability_up",
    )

    return pipeline, probability_up


def select_logistic_regularization(
    split: TickerDatasetSplit,
    config: LogisticSearchConfig,
    feature_columns: Sequence[str] = FEATURE_COLUMNS,
) -> tuple[float, pd.DataFrame, pd.DataFrame]:
    """Select regularization strength using validation log loss."""

    config.validate()

    metric_records: list[dict[str, float | int]] = []
    prediction_frames: list[pd.DataFrame] = []

    for c_value in config.c_values:
        _, probabilities = _fit_and_predict(
            training_data=split.train,
            evaluation_data=split.validation,
            feature_columns=feature_columns,
            c_value=c_value,
            config=config,
        )

        metrics = evaluate_probability_predictions(
            actual=split.validation["target_up_next_day"],
            probability_up=probabilities,
        )

        metric_records.append(
            {
                "c_value": float(c_value),
                **metrics,
            }
        )

        prediction_frame = split.validation[
            [
                "ticker",
                "trade_date",
                "target_date",
                "target_up_next_day",
            ]
        ].copy()

        prediction_frame["c_value"] = float(c_value)

        prediction_frame["probability_up"] = probabilities.to_numpy()

        prediction_frames.append(prediction_frame)

    validation_results = (
        pd.DataFrame.from_records(metric_records)
        .sort_values(
            [
                "log_loss",
                "brier_score",
                "c_value",
            ]
        )
        .reset_index(drop=True)
    )

    validation_results["validation_rank"] = np.arange(
        1,
        len(validation_results) + 1,
    )

    selected_c = float(validation_results.iloc[0]["c_value"])

    validation_predictions = pd.concat(
        prediction_frames,
        ignore_index=True,
    )

    validation_predictions["selected_model"] = validation_predictions["c_value"].eq(selected_c)

    return (
        selected_c,
        validation_results,
        validation_predictions,
    )


def extract_logistic_coefficients(
    pipeline: Pipeline,
    feature_columns: Sequence[str] = FEATURE_COLUMNS,
) -> pd.DataFrame:
    """Extract standardized Logistic Regression coefficients."""

    classifier = pipeline.named_steps["classifier"]

    coefficients = np.asarray(classifier.coef_).reshape(-1)

    if len(coefficients) != len(feature_columns):
        raise ValueError("Coefficient count does not match feature count.")

    result = pd.DataFrame(
        {
            "feature": list(feature_columns),
            "coefficient": coefficients,
        }
    )

    result["absolute_coefficient"] = result["coefficient"].abs()

    result["direction"] = np.where(
        result["coefficient"].gt(0),
        "positive",
        np.where(
            result["coefficient"].lt(0),
            "negative",
            "neutral",
        ),
    )

    return result.sort_values(
        "absolute_coefficient",
        ascending=False,
    ).reset_index(drop=True)


def train_logistic_for_ticker(
    split: TickerDatasetSplit,
    config: LogisticSearchConfig,
    feature_columns: Sequence[str] = FEATURE_COLUMNS,
) -> LogisticTickerResult:
    """Select, retrain, and evaluate Logistic Regression."""

    (
        selected_c,
        validation_results,
        validation_predictions,
    ) = select_logistic_regularization(
        split=split,
        config=config,
        feature_columns=feature_columns,
    )

    combined_training_data = pd.concat(
        [
            split.train,
            split.validation,
        ],
        ignore_index=True,
    )

    fitted_pipeline, test_probabilities = _fit_and_predict(
        training_data=combined_training_data,
        evaluation_data=split.test,
        feature_columns=feature_columns,
        c_value=selected_c,
        config=config,
    )

    test_metrics = evaluate_probability_predictions(
        actual=split.test["target_up_next_day"],
        probability_up=test_probabilities,
    )

    test_metrics["selected_c"] = selected_c
    test_metrics["training_observations"] = int(len(combined_training_data))

    test_predictions = split.test[
        [
            "ticker",
            "trade_date",
            "target_date",
            "target_up_next_day",
        ]
    ].copy()

    test_predictions["model_name"] = "logistic_regression"

    test_predictions["selected_c"] = selected_c

    test_predictions["probability_up"] = test_probabilities.to_numpy()

    coefficients = extract_logistic_coefficients(
        pipeline=fitted_pipeline,
        feature_columns=feature_columns,
    )

    return LogisticTickerResult(
        selected_c=selected_c,
        validation_results=validation_results,
        validation_predictions=validation_predictions,
        test_metrics=test_metrics,
        test_predictions=test_predictions,
        coefficients=coefficients,
        fitted_pipeline=fitted_pipeline,
    )
