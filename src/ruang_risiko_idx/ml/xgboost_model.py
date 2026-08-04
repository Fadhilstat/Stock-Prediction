"""Leakage-safe XGBoost training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ruang_risiko_idx.ml.baselines import evaluate_probability_predictions
from ruang_risiko_idx.ml.features import FEATURE_COLUMNS
from ruang_risiko_idx.ml.splitting import TickerDatasetSplit


@dataclass(frozen=True)
class XGBoostSearchConfig:
    """Configure XGBoost model selection."""

    n_estimators: int = 300
    max_depth_values: tuple[int, ...] = (2, 3, 5)
    learning_rate_values: tuple[float, ...] = (0.01, 0.05, 0.10)
    min_child_weight: float = 10.0
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_lambda: float = 1.0
    reg_alpha: float = 0.0
    random_state: int = 42
    n_jobs: int = -1


@dataclass
class XGBoostTickerResult:
    """Store selected XGBoost outputs for one ticker."""

    selected_parameters: dict[str, object]
    validation_results: pd.DataFrame
    validation_predictions: pd.DataFrame
    test_metrics: dict[str, float | int | object]
    test_predictions: pd.DataFrame
    feature_importances: pd.DataFrame
    fitted_model: XGBClassifier


def build_xgboost_model(
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    min_child_weight: float = 10.0,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    reg_lambda: float = 1.0,
    reg_alpha: float = 0.0,
    random_state: int = 42,
    n_jobs: int = -1,
) -> XGBClassifier:
    """Build one binary XGBoost classifier."""

    return XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        min_child_weight=min_child_weight,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_lambda=reg_lambda,
        reg_alpha=reg_alpha,
        random_state=random_state,
        n_jobs=n_jobs,
    )


def _fit_and_predict(
    training_data: pd.DataFrame,
    evaluation_data: pd.DataFrame,
    parameters: dict[str, Any],
    config: XGBoostSearchConfig,
) -> tuple[XGBClassifier, pd.Series]:
    """Fit one model and produce positive-class probabilities."""

    model = build_xgboost_model(
        n_estimators=config.n_estimators,
        max_depth=int(parameters["max_depth"]),
        learning_rate=float(parameters["learning_rate"]),
        min_child_weight=config.min_child_weight,
        subsample=config.subsample,
        colsample_bytree=config.colsample_bytree,
        reg_lambda=config.reg_lambda,
        reg_alpha=config.reg_alpha,
        random_state=config.random_state,
        n_jobs=config.n_jobs,
    )

    model.fit(
        training_data[list(FEATURE_COLUMNS)],
        training_data["target_up_next_day"],
    )

    probabilities = pd.Series(
        model.predict_proba(evaluation_data[list(FEATURE_COLUMNS)])[:, 1],
        index=evaluation_data.index,
        name="probability_up",
    )

    return model, probabilities


def select_xgboost_parameters(
    split: TickerDatasetSplit,
    config: XGBoostSearchConfig,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    """Select XGBoost parameters using validation log loss."""

    metric_records: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []

    for max_depth, learning_rate in product(
        config.max_depth_values,
        config.learning_rate_values,
    ):
        parameters = {
            "max_depth": max_depth,
            "learning_rate": learning_rate,
        }

        _, probabilities = _fit_and_predict(
            split.train,
            split.validation,
            parameters,
            config,
        )

        metrics = evaluate_probability_predictions(
            actual=split.validation["target_up_next_day"],
            probability_up=probabilities,
        )

        metric_records.append(
            {
                "max_depth": max_depth,
                "learning_rate": learning_rate,
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
        predictions["learning_rate"] = learning_rate
        predictions["probability_up"] = probabilities.to_numpy()
        prediction_frames.append(predictions)

    validation_results = (
        pd.DataFrame(metric_records)
        .sort_values(
            [
                "log_loss",
                "brier_score",
                "max_depth",
                "learning_rate",
            ]
        )
        .reset_index(drop=True)
    )

    validation_results["validation_rank"] = np.arange(
        1,
        len(validation_results) + 1,
    )

    best = validation_results.iloc[0]

    selected = {
        "max_depth": int(best["max_depth"]),
        "learning_rate": float(best["learning_rate"]),
    }

    validation_predictions = pd.concat(
        prediction_frames,
        ignore_index=True,
    )

    validation_predictions["selected_model"] = validation_predictions["max_depth"].eq(
        selected["max_depth"]
    ) & validation_predictions["learning_rate"].eq(selected["learning_rate"])

    return selected, validation_results, validation_predictions


def train_xgboost_for_ticker(
    split: TickerDatasetSplit,
    config: XGBoostSearchConfig,
) -> XGBoostTickerResult:
    """Select, retrain, and evaluate XGBoost."""

    selected, validation_results, validation_predictions = select_xgboost_parameters(split, config)

    combined_training = pd.concat(
        [split.train, split.validation],
        ignore_index=True,
    )

    model, test_probabilities = _fit_and_predict(
        combined_training,
        split.test,
        selected,
        config,
    )

    test_metrics = evaluate_probability_predictions(
        actual=split.test["target_up_next_day"],
        probability_up=test_probabilities,
    )

    test_metrics.update(
        {
            "max_depth": selected["max_depth"],
            "learning_rate": selected["learning_rate"],
            "n_estimators": config.n_estimators,
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

    test_predictions["model_name"] = "xgboost"
    test_predictions["probability_up"] = test_probabilities.to_numpy()

    feature_importances = pd.DataFrame(
        {
            "feature": list(FEATURE_COLUMNS),
            "importance": model.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    return XGBoostTickerResult(
        selected_parameters=selected,
        validation_results=validation_results,
        validation_predictions=validation_predictions,
        test_metrics=test_metrics,
        test_predictions=test_predictions,
        feature_importances=feature_importances,
        fitted_model=model,
    )
