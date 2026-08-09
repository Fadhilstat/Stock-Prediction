"""Build the final task-specific model registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GARCH_PATH = (
    PROJECT_ROOT
    / "config"
    / "garch_model_registry.yml"
)

DEFAULT_CLASSICAL_REGISTRY_PATH = (
    PROJECT_ROOT
    / "reports"
    / "ml"
    / "classical_model_registry.json"
)

DEFAULT_CLASSICAL_SUMMARY_PATH = (
    PROJECT_ROOT
    / "reports"
    / "ml"
    / "classical_model_summary.json"
)

DEFAULT_KRONOS_PATH = (
    PROJECT_ROOT
    / "reports"
    / "foundation"
    / "kronos"
    / "phase_5_2_evidence.json"
)

DEFAULT_GRANITE_PATH = (
    PROJECT_ROOT
    / "reports"
    / "foundation"
    / "granite"
    / "phase_5_3_evidence.json"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_registry"
)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the final task-specific model registry "
            "from committed model evidence."
        )
    )

    parser.add_argument(
        "--garch",
        type=Path,
        default=DEFAULT_GARCH_PATH,
    )

    parser.add_argument(
        "--classical-registry",
        type=Path,
        default=DEFAULT_CLASSICAL_REGISTRY_PATH,
    )

    parser.add_argument(
        "--classical-summary",
        type=Path,
        default=DEFAULT_CLASSICAL_SUMMARY_PATH,
    )

    parser.add_argument(
        "--kronos",
        type=Path,
        default=DEFAULT_KRONOS_PATH,
    )

    parser.add_argument(
        "--granite",
        type=Path,
        default=DEFAULT_GRANITE_PATH,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    return parser.parse_args()


def load_json(
    path: Path,
) -> Any:
    """Load one JSON document."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSON evidence was not found at {path}."
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_yaml(
    path: Path,
) -> dict[str, Any]:
    """Load one YAML document."""

    if not path.exists():
        raise FileNotFoundError(
            f"YAML evidence was not found at {path}."
        )

    payload = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "GARCH registry must contain a mapping."
        )

    return payload


def validate_garch_registry(
    payload: dict[str, Any],
) -> None:
    """Validate the GARCH source registry."""

    required_metadata = {
        "project",
        "status",
        "evaluation_method",
        "forecast_horizon",
        "evaluation_observations",
        "primary_volatility_metric",
        "var_confidence_levels",
        "selection_note",
    }

    metadata = payload.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        dict,
    ):
        raise ValueError(
            "GARCH registry metadata is missing."
        )

    missing_metadata = (
        required_metadata.difference(
            metadata
        )
    )

    if missing_metadata:
        missing_text = ", ".join(
            sorted(
                missing_metadata
            )
        )

        raise ValueError(
            "GARCH metadata is missing fields: "
            + missing_text
        )

    tickers = payload.get(
        "tickers"
    )

    if not isinstance(
        tickers,
        dict,
    ) or not tickers:
        raise ValueError(
            "GARCH registry tickers are missing."
        )

    for ticker, settings in tickers.items():
        if not isinstance(
            settings,
            dict,
        ):
            raise ValueError(
                f"GARCH settings for {ticker} must be a mapping."
            )

        required_ticker_fields = {
            "volatility_model",
            "var_model",
            "note",
        }

        missing_fields = (
            required_ticker_fields.difference(
                settings
            )
        )

        if missing_fields:
            missing_text = ", ".join(
                sorted(
                    missing_fields
                )
            )

            raise ValueError(
                f"GARCH ticker {ticker} is missing fields: "
                + missing_text
            )


def validate_classical_registry(
    registry: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    """Validate the classical model evidence."""

    if not registry:
        raise ValueError(
            "Classical model registry must not be empty."
        )

    tickers = [
        row.get("ticker")
        for row in registry
    ]

    if any(
        ticker is None
        for ticker in tickers
    ):
        raise ValueError(
            "Every classical registry row needs a ticker."
        )

    if len(tickers) != len(
        set(tickers)
    ):
        raise ValueError(
            "Classical registry contains duplicate tickers."
        )

    required_row_fields = {
        "ticker",
        "selected_model",
        "selection_rule",
        "validation",
        "test",
    }

    for row in registry:
        missing_fields = (
            required_row_fields.difference(
                row
            )
        )

        if missing_fields:
            missing_text = ", ".join(
                sorted(
                    missing_fields
                )
            )

            raise ValueError(
                "Classical registry row is missing fields: "
                + missing_text
            )

    if summary.get(
        "selection_basis"
    ) != "validation":
        raise ValueError(
            "Classical selection basis must be validation."
        )

    if summary.get(
        "test_used_for_selection"
    ) is not False:
        raise ValueError(
            "Classical test results must not drive selection."
        )

    if summary.get(
        "ticker_count"
    ) != len(
        registry
    ):
        raise ValueError(
            "Classical ticker count does not match the registry."
        )

    observed_counts = Counter(
        row["selected_model"]
        for row in registry
    )

    expected_counts = summary.get(
        "selected_model_counts"
    )

    if dict(
        observed_counts
    ) != expected_counts:
        raise ValueError(
            "Classical selected model counts are inconsistent."
        )


def validate_kronos_evidence(
    payload: dict[str, Any],
) -> None:
    """Validate the Kronos final evidence."""

    decision = payload.get(
        "decision"
    )

    if not isinstance(
        decision,
        dict,
    ):
        raise ValueError(
            "Kronos decision evidence is missing."
        )

    if decision.get(
        "model_role"
    ) != "experimental_benchmark":
        raise ValueError(
            "Kronos must remain an experimental benchmark."
        )

    if decision.get(
        "production_selection"
    ) != "not_selected":
        raise ValueError(
            "Kronos must not be marked as selected for production."
        )

    if payload.get(
        "evaluation_scope"
    ) != "full_252":
        raise ValueError(
            "Kronos final evidence must use the full 252 evaluation."
        )


def validate_granite_evidence(
    payload: dict[str, Any],
) -> None:
    """Validate the Granite final evidence."""

    if payload.get(
        "status"
    ) != "completed":
        raise ValueError(
            "Granite evaluation must be completed."
        )

    if payload.get(
        "decision"
    ) != "experimental_benchmark_not_production":
        raise ValueError(
            "Granite must remain an experimental benchmark."
        )

    if payload.get(
        "evaluation_size_per_ticker"
    ) != 252:
        raise ValueError(
            "Granite final evidence must use 252 observations per ticker."
        )

    audit = payload.get(
        "audit",
        {},
    )

    if audit.get(
        "duplicate_windows"
    ) != 0:
        raise ValueError(
            "Granite final evidence contains duplicate windows."
        )

    if audit.get(
        "target_after_cutoff"
    ) is not True:
        raise ValueError(
            "Granite target dates must follow their cutoffs."
        )


def build_garch_section(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build the risk and volatility registry section."""

    metadata = payload[
        "metadata"
    ]

    tickers = []

    for ticker, settings in sorted(
        payload["tickers"].items()
    ):
        tickers.append(
            {
                "ticker": ticker,
                "volatility_model": (
                    settings[
                        "volatility_model"
                    ]
                ),
                "var_model": (
                    settings[
                        "var_model"
                    ]
                ),
                "note": settings["note"],
            }
        )

    return {
        "task": "risk_and_volatility",
        "role": "selected_risk_model_registry",
        "selection_status": metadata[
            "status"
        ],
        "source": (
            "config/garch_model_registry.yml"
        ),
        "evaluation_method": metadata[
            "evaluation_method"
        ],
        "forecast_horizon": metadata[
            "forecast_horizon"
        ],
        "evaluation_observations": metadata[
            "evaluation_observations"
        ],
        "primary_volatility_metric": metadata[
            "primary_volatility_metric"
        ],
        "var_confidence_levels": metadata[
            "var_confidence_levels"
        ],
        "selection_note": metadata[
            "selection_note"
        ],
        "tickers": tickers,
    }


def build_classical_section(
    registry: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Build the direction probability registry section."""

    rows = sorted(
        registry,
        key=lambda row: row["ticker"],
    )

    return {
        "task": "direction_probability",
        "role": "selected_direction_model_registry",
        "source": (
            "reports/ml/classical_model_registry.json"
        ),
        "selection_basis": summary[
            "selection_basis"
        ],
        "primary_metric": summary[
            "primary_metric"
        ],
        "tie_breaker": summary[
            "tie_breaker"
        ],
        "test_used_for_selection": summary[
            "test_used_for_selection"
        ],
        "selected_model_counts": summary[
            "selected_model_counts"
        ],
        "tickers": rows,
    }


def build_kronos_section(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build the Kronos benchmark section."""

    decision = payload[
        "decision"
    ]

    return {
        "task": "ohlcv_forecasting",
        "role": decision[
            "model_role"
        ],
        "production_selection": decision[
            "production_selection"
        ],
        "source": (
            "reports/foundation/kronos/"
            "phase_5_2_evidence.json"
        ),
        "experiment": payload[
            "experiment"
        ],
        "evaluation_scope": payload[
            "evaluation_scope"
        ],
        "forecast_count": payload[
            "forecast_count"
        ],
        "configuration": payload[
            "configuration"
        ],
        "reason": decision[
            "reason"
        ],
        "directional_result": decision[
            "directional_result"
        ],
        "structural_result": decision[
            "structural_result"
        ],
        "postprocessing": decision[
            "postprocessing"
        ],
        "tuning_policy": decision[
            "tuning_policy"
        ],
    }


def build_granite_section(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build the Granite benchmark section."""

    return {
        "task": "return_forecasting",
        "role": "experimental_benchmark",
        "production_selection": "not_selected",
        "source": (
            "reports/foundation/granite/"
            "phase_5_3_evidence.json"
        ),
        "experiment": payload[
            "experiment"
        ],
        "model_name": payload[
            "model_name"
        ],
        "model_revision": payload[
            "model_revision"
        ],
        "target": payload[
            "target"
        ],
        "price_basis": payload[
            "price_basis"
        ],
        "context_length": payload[
            "context_length"
        ],
        "prediction_length": payload[
            "prediction_length"
        ],
        "evaluation_size_per_ticker": payload[
            "evaluation_size_per_ticker"
        ],
        "forecast_rows": payload[
            "forecast_rows"
        ],
        "comparison": payload[
            "comparison"
        ],
        "selection_rule": payload[
            "selection_rule"
        ],
        "reason": (
            "Granite TTM did not beat the zero-return "
            "random-walk baseline on return MAE for any "
            "of the five evaluated stocks."
        ),
    }


def build_registry(
    garch: dict[str, Any],
    classical_registry: list[dict[str, Any]],
    classical_summary: dict[str, Any],
    kronos: dict[str, Any],
    granite: dict[str, Any],
) -> dict[str, Any]:
    """Build the final task-specific registry."""

    validate_garch_registry(
        garch
    )

    validate_classical_registry(
        classical_registry,
        classical_summary,
    )

    validate_kronos_evidence(
        kronos
    )

    validate_granite_evidence(
        granite
    )

    garch_section = build_garch_section(
        garch
    )

    classical_section = build_classical_section(
        classical_registry,
        classical_summary,
    )

    kronos_section = build_kronos_section(
        kronos
    )

    granite_section = build_granite_section(
        granite
    )

    garch_tickers = {
        row["ticker"]
        for row in garch_section[
            "tickers"
        ]
    }

    classical_tickers = {
        row["ticker"]
        for row in classical_section[
            "tickers"
        ]
    }

    if garch_tickers != classical_tickers:
        raise ValueError(
            "GARCH and classical registry ticker universes do not match."
        )

    return {
        "metadata": {
            "project": "Ruang Risiko IDX",
            "phase": "5.4",
            "status": "final_task_specific_model_registry",
            "generated_at_utc": datetime.now(
                UTC
            ).isoformat(),
            "registry_principle": (
                "Models are assigned by analytical task. "
                "Metrics from different prediction targets are "
                "not combined into one leaderboard."
            ),
            "retraining_performed": False,
            "hyperparameter_tuning_performed": False,
        },
        "risk_and_volatility": (
            garch_section
        ),
        "direction_probability": (
            classical_section
        ),
        "foundation_benchmarks": {
            "kronos": kronos_section,
            "granite_ttm": granite_section,
        },
        "deployment_roles": {
            "risk_and_volatility": {
                "decision": (
                    "use_provisional_garch_registry"
                ),
                "purpose": (
                    "One-day volatility and VaR estimation."
                ),
            },
            "direction_probability": {
                "decision": (
                    "use_classical_validation_registry"
                ),
                "purpose": (
                    "Probability-oriented daily direction analytics."
                ),
            },
            "ohlcv_forecasting": {
                "decision": (
                    "no_production_model_selected"
                ),
                "benchmark": "kronos",
            },
            "return_forecasting": {
                "decision": (
                    "no_production_model_selected"
                ),
                "benchmark": "granite_ttm",
            },
        },
    }


def build_decision_markdown(
    registry: dict[str, Any],
) -> str:
    """Build the Phase 5.4 decision note."""

    garch_rows = []

    for row in registry[
        "risk_and_volatility"
    ]["tickers"]:
        garch_rows.append(
            "| "
            + row["ticker"]
            + " | "
            + row["volatility_model"]
            + " | "
            + row["var_model"]
            + " |"
        )

    classical_rows = []

    for row in registry[
        "direction_probability"
    ]["tickers"]:
        classical_rows.append(
            "| "
            + row["ticker"]
            + " | "
            + row["selected_model"]
            + " | "
            + f"{row['validation']['log_loss']:.6f}"
            + " | "
            + f"{row['test']['roc_auc']:.6f}"
            + " |"
        )

    garch_table = "\n".join(
        garch_rows
    )

    classical_table = "\n".join(
        classical_rows
    )

    garch_status = registry[
        "risk_and_volatility"
    ]["selection_status"]

    kronos = registry[
        "foundation_benchmarks"
    ]["kronos"]

    granite = registry[
        "foundation_benchmarks"
    ]["granite_ttm"]

    return f"""# Phase 5.4 Final Model Decision Registry

## Decision principle

Ruang Risiko IDX does not use a single leaderboard across all models.

GARCH-family models estimate volatility and tail risk. Classical
machine-learning models estimate daily direction probability. Kronos
and Granite TTM are forecasting benchmarks with different targets.

Because these tasks are different, their metrics are not combined into
one score.

No model was retrained or tuned during Phase 5.4. This phase only
consolidates decisions that were already supported by their original
evaluation protocols.

## Risk and volatility

The GARCH registry keeps its source status exactly as recorded:

`{garch_status}`

Volatility selection is based primarily on mean QLIKE from a daily
expanding walk-forward evaluation with 252 observations. VaR selection
also considers the reported coverage and independence tests.

| Ticker | Volatility model | VaR model |
| --- | --- | --- |
{garch_table}

These selections are used for the risk analytics role while retaining
the provisional status from the source registry.

## Direction probability

Classical model selection uses validation log loss as the primary
metric and validation Brier score as the tie-breaker.

Test results were not used for model selection.

| Ticker | Selected model | Validation log loss | Test ROC AUC |
| --- | --- | ---: | ---: |
{classical_table}

A simple constant-probability baseline remains selected when it wins
under the frozen validation rule. Model complexity is not treated as
a selection criterion.

## Kronos

Role: `{kronos["role"]}`

Production selection: `{kronos["production_selection"]}`

The full evaluation contained {kronos["forecast_count"]:,} rolling
forecasts.

Decision reason:

{kronos["reason"]}

Kronos remains useful as an OHLCV foundation-model benchmark, but it is
not promoted to production forecasting.

## Granite TTM

Role: `{granite["role"]}`

Production selection: `{granite["production_selection"]}`

The full evaluation contained {granite["forecast_rows"]:,} rolling
forecasts.

Granite beat return persistence on return MAE for
{granite["comparison"]["granite_return_mae_wins_vs_persistence"]} of
5 stocks, but beat random walk on
{granite["comparison"]["granite_return_mae_wins_vs_random_walk"]} of
5 stocks.

Granite therefore remains a return-forecasting benchmark and is not
promoted to production forecasting.

## Final task assignments

Risk and volatility analytics use the ticker-specific GARCH registry.

Direction probability uses the ticker-specific classical validation
registry.

No foundation model is selected as the production OHLCV or return
forecasting model.

Kronos and Granite remain visible in the project as experimental
benchmarks because their evaluations provide useful evidence about the
limits of model complexity.

## Guardrails

The dashboard must not present these models as buy, sell, or target
price recommendations.

Foundation-model test sets remain frozen. Future fine-tuning or
multivariate experiments require a separately defined validation
protocol.

The GARCH registry must continue to be described as provisional until
a later process explicitly changes that status.
"""


def write_text_atomic(
    text: str,
    destination: Path,
) -> None:
    """Write text through a temporary path."""

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(
        f".{destination.name}.tmp"
    )

    temporary_path.write_text(
        text,
        encoding="utf-8",
    )

    temporary_path.replace(
        destination
    )


def write_json_atomic(
    payload: dict[str, Any],
    destination: Path,
) -> None:
    """Write strict JSON through a temporary path."""

    write_text_atomic(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        destination,
    )


def main() -> int:
    """Build the registry and decision note."""

    args = parse_arguments()

    garch = load_yaml(
        args.garch
    )

    classical_registry = load_json(
        args.classical_registry
    )

    classical_summary = load_json(
        args.classical_summary
    )

    kronos = load_json(
        args.kronos
    )

    granite = load_json(
        args.granite
    )

    registry = build_registry(
        garch=garch,
        classical_registry=classical_registry,
        classical_summary=classical_summary,
        kronos=kronos,
        granite=granite,
    )

    decision = build_decision_markdown(
        registry
    )

    registry_path = (
        args.output_dir
        / "final_model_registry.json"
    )

    decision_path = (
        args.output_dir
        / "PHASE_5_4_DECISION.md"
    )

    write_json_atomic(
        registry,
        registry_path,
    )

    write_text_atomic(
        decision,
        decision_path,
    )

    print(
        "Registry:",
        registry_path,
    )

    print(
        "Decision:",
        decision_path,
    )

    print(
        "GARCH tickers:",
        len(
            registry[
                "risk_and_volatility"
            ]["tickers"]
        ),
    )

    print(
        "Classical tickers:",
        len(
            registry[
                "direction_probability"
            ]["tickers"]
        ),
    )

    print(
        "Kronos role:",
        registry[
            "foundation_benchmarks"
        ]["kronos"]["role"],
    )

    print(
        "Granite role:",
        registry[
            "foundation_benchmarks"
        ]["granite_ttm"]["role"],
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
