"""Select one classical ML model per ticker using validation metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORTS_DIR = PROJECT_ROOT / "reports" / "ml"

OUTPUT_REGISTRY = REPORTS_DIR / "classical_model_registry.json"

OUTPUT_SUMMARY = REPORTS_DIR / "classical_model_summary.json"


def load_selected_validation_metrics(
    path: Path,
) -> pd.DataFrame:
    """Load the selected validation result for each ticker."""

    data = pd.read_parquet(path)

    if "validation_rank" in data.columns:
        data = data.loc[data["validation_rank"].eq(1)].copy()

    return data


def prepare_baseline_metrics() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Prepare validation and test metrics for the baseline."""

    baseline = pd.read_parquet(REPORTS_DIR / "baseline_metrics.parquet")

    validation = baseline.loc[baseline["split"].eq("validation")].copy()

    test = baseline.loc[baseline["split"].eq("test")].copy()

    validation["model_name"] = "constant_probability"

    test["model_name"] = "constant_probability"

    return validation, test


def prepare_model_metrics(
    directory: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load selected validation and test metrics."""

    model_directory = REPORTS_DIR / directory

    validation = load_selected_validation_metrics(model_directory / "validation_metrics.parquet")

    test = pd.read_parquet(model_directory / "test_metrics.parquet")

    return validation, test


def build_registry() -> tuple[
    list[dict[str, object]],
    dict[str, object],
]:
    """Build a validation-selected model registry."""

    baseline_validation, baseline_test = prepare_baseline_metrics()

    logistic_validation, logistic_test = prepare_model_metrics("logistic")

    random_forest_validation, random_forest_test = prepare_model_metrics("random_forest")

    xgboost_validation, xgboost_test = prepare_model_metrics("xgboost")

    validation_metrics = pd.concat(
        [
            baseline_validation,
            logistic_validation,
            random_forest_validation,
            xgboost_validation,
        ],
        ignore_index=True,
        sort=False,
    )

    test_metrics = pd.concat(
        [
            baseline_test,
            logistic_test,
            random_forest_test,
            xgboost_test,
        ],
        ignore_index=True,
        sort=False,
    )

    selected_validation = (
        validation_metrics.sort_values(
            [
                "ticker",
                "log_loss",
                "brier_score",
                "model_name",
            ]
        )
        .groupby(
            "ticker",
            sort=True,
        )
        .head(1)
        .reset_index(drop=True)
    )

    registry: list[dict[str, object]] = []

    for _, selected_row in selected_validation.iterrows():
        ticker = str(selected_row["ticker"])
        model_name = str(selected_row["model_name"])

        matching_test = test_metrics.loc[
            test_metrics["ticker"].eq(ticker) & test_metrics["model_name"].eq(model_name)
        ]

        if len(matching_test) != 1:
            raise ValueError(f"Expected one matching test result for {ticker} and {model_name}.")

        test_row = matching_test.iloc[0]

        registry.append(
            {
                "ticker": ticker,
                "selected_model": model_name,
                "selection_rule": (
                    "lowest validation log loss, then lowest validation Brier score"
                ),
                "validation": {
                    "log_loss": float(selected_row["log_loss"]),
                    "brier_score": float(selected_row["brier_score"]),
                    "roc_auc": float(selected_row["roc_auc"]),
                    "balanced_accuracy": float(selected_row["balanced_accuracy"]),
                },
                "test": {
                    "log_loss": float(test_row["log_loss"]),
                    "brier_score": float(test_row["brier_score"]),
                    "roc_auc": float(test_row["roc_auc"]),
                    "balanced_accuracy": float(test_row["balanced_accuracy"]),
                },
            }
        )

    model_counts = selected_validation["model_name"].value_counts().sort_index().to_dict()

    summary = {
        "selection_basis": "validation",
        "primary_metric": "log_loss",
        "tie_breaker": "brier_score",
        "test_used_for_selection": False,
        "ticker_count": len(registry),
        "selected_model_counts": {str(key): int(value) for key, value in model_counts.items()},
    }

    return registry, summary


def write_json(
    payload: object,
    destination: Path,
) -> None:
    """Write readable JSON."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Create the classical model registry."""

    registry, summary = build_registry()

    write_json(
        registry,
        OUTPUT_REGISTRY,
    )

    write_json(
        summary,
        OUTPUT_SUMMARY,
    )

    registry_frame = pd.DataFrame(
        [
            {
                "ticker": row["ticker"],
                "selected_model": (row["selected_model"]),
                "validation_log_loss": (row["validation"]["log_loss"]),
                "test_log_loss": (row["test"]["log_loss"]),
                "test_roc_auc": (row["test"]["roc_auc"]),
            }
            for row in registry
        ]
    )

    print("Selected classical models:")
    print(registry_frame.to_string(index=False))

    print(f"\nRegistry saved to {OUTPUT_REGISTRY}.")

    print(f"Summary saved to {OUTPUT_SUMMARY}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
