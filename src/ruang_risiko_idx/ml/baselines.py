"""Naive probability baselines for classification."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_probability_predictions(
    actual: pd.Series,
    probability_up: pd.Series,
    threshold: float = 0.5,
) -> dict[str, float | int]:
    """Evaluate binary probability predictions."""

    if not 0 < threshold < 1:
        raise ValueError("Classification threshold must be between zero and one.")

    aligned = pd.concat(
        [
            pd.Series(
                actual,
                copy=True,
                name="actual",
            ),
            pd.Series(
                probability_up,
                copy=True,
                dtype="float64",
                name="probability_up",
            ),
        ],
        axis=1,
    ).dropna()

    if aligned.empty:
        raise ValueError("Prediction evaluation received no observations.")

    if not aligned["actual"].isin([0, 1]).all():
        raise ValueError("Actual values must contain only zero and one.")

    if (
        not aligned["probability_up"]
        .between(
            0.0,
            1.0,
        )
        .all()
    ):
        raise ValueError("Predicted probabilities must be between zero and one.")

    actual_values = aligned["actual"].astype("int8")

    probabilities = aligned["probability_up"]

    predictions = probabilities.ge(threshold).astype("int8")

    metrics: dict[str, float | int] = {
        "observations": int(len(aligned)),
        "positive_rate": float(actual_values.mean()),
        "predicted_positive_rate": float(predictions.mean()),
        "accuracy": float(
            accuracy_score(
                actual_values,
                predictions,
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                actual_values,
                predictions,
            )
        ),
        "precision": float(
            precision_score(
                actual_values,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                actual_values,
                predictions,
                zero_division=0,
            )
        ),
        "brier_score": float(
            brier_score_loss(
                actual_values,
                probabilities,
            )
        ),
        "log_loss": float(
            log_loss(
                actual_values,
                probabilities,
                labels=[0, 1],
            )
        ),
    }

    if actual_values.nunique() == 2:
        metrics["roc_auc"] = float(
            roc_auc_score(
                actual_values,
                probabilities,
            )
        )
    else:
        metrics["roc_auc"] = np.nan

    return metrics


def build_constant_probability_baseline(
    training_target: pd.Series,
    evaluation_target: pd.Series,
) -> tuple[pd.Series, dict[str, float | int]]:
    """Predict the historical training positive rate."""

    clean_training_target = (
        pd.Series(
            training_target,
            copy=True,
        )
        .dropna()
        .astype("int8")
    )

    if clean_training_target.empty:
        raise ValueError("Baseline training target cannot be empty.")

    training_positive_rate = float(clean_training_target.mean())

    probabilities = pd.Series(
        training_positive_rate,
        index=evaluation_target.index,
        dtype="float64",
        name="probability_up",
    )

    metrics = evaluate_probability_predictions(
        actual=evaluation_target,
        probability_up=probabilities,
    )

    metrics["training_positive_rate"] = training_positive_rate

    return probabilities, metrics
