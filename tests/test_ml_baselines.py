"""Tests for machine learning probability baselines."""

import numpy as np
import pandas as pd

from ruang_risiko_idx.ml.baselines import (
    build_constant_probability_baseline,
    evaluate_probability_predictions,
)


def test_probability_evaluation() -> None:
    actual = pd.Series([0, 0, 1, 1])

    probabilities = pd.Series([0.1, 0.4, 0.6, 0.9])

    metrics = evaluate_probability_predictions(
        actual=actual,
        probability_up=probabilities,
    )

    assert metrics["accuracy"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["roc_auc"] == 1.0


def test_constant_probability_baseline() -> None:
    training_target = pd.Series([0, 0, 0, 1])

    evaluation_target = pd.Series([0, 1, 0])

    probabilities, metrics = build_constant_probability_baseline(
        training_target=training_target,
        evaluation_target=evaluation_target,
    )

    assert np.allclose(
        probabilities,
        0.25,
    )

    assert metrics["training_positive_rate"] == 0.25
