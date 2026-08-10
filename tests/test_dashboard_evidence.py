"""Tests for model evidence and Learn presentation helpers."""

from ruang_risiko_idx.dashboard.evidence import (
    build_learn_topics,
    summarize_direction_registry,
    summarize_granite_evidence,
    summarize_kronos_evidence,
)


def test_summarize_kronos_preserves_not_selected_decision() -> None:
    """Kronos evidence should stay experimental when the artifact says so."""

    evidence = {
        "configuration": {"evaluation_size_per_ticker": 252},
        "forecast_count": 1512,
        "ticker_count": 6,
        "decision": {
            "model_role": "experimental_benchmark",
            "production_selection": "not_selected",
            "reason": "Random walk won the primary error metrics.",
            "structural_result": "Most raw OHLC forecasts were structurally valid.",
        },
    }

    summary = summarize_kronos_evidence(evidence)

    assert summary["production_selection"] == "not_selected"
    assert summary["forecast_count"] == 1512
    assert summary["evaluation_size"] == 252


def test_summarize_granite_keeps_random_walk_comparison() -> None:
    """Granite summary should show both favorable and unfavorable comparisons."""

    evidence = {
        "decision": "experimental_benchmark_not_production",
        "forecast_rows": 1260,
        "ticker_count": 5,
        "evaluation_size_per_ticker": 252,
        "model_revision": "512-48-ft-r2.1",
        "target": "log_return",
        "comparison": {
            "granite_return_mae_wins_vs_persistence": 5,
            "granite_return_mae_wins_vs_random_walk": 0,
        },
    }

    summary = summarize_granite_evidence(evidence)

    assert summary["wins_vs_persistence"] == 5
    assert summary["wins_vs_random_walk"] == 0
    assert summary["decision"] == "experimental_benchmark_not_production"


def test_direction_registry_uses_validation_and_keeps_test_context() -> None:
    """Direction evidence should expose validation selection and test context separately."""

    registry = [
        {
            "ticker": "AAA",
            "selected_model": "logistic_regression",
            "validation": {"log_loss": 0.68, "brier_score": 0.24},
            "test": {"log_loss": 0.71},
        }
    ]

    rows = summarize_direction_registry(registry)

    assert rows == [
        {
            "ticker": "AAA",
            "selected_model": "logistic_regression",
            "validation_log_loss": 0.68,
            "validation_brier": 0.24,
            "test_log_loss": 0.71,
        }
    ]


def test_learn_topics_cover_core_risk_concepts() -> None:
    """Learn content should cover concepts needed to read the dashboard responsibly."""

    topics = build_learn_topics()
    titles = {topic["title"] for topic in topics}

    assert titles == {
        "Return",
        "Volatilitas",
        "Drawdown",
        "Value at Risk",
        "Walk-forward",
        "Baseline",
    }

    var_topic = next(topic for topic in topics if topic["title"] == "Value at Risk")
    assert "bukan kerugian maksimum" in var_topic["explanation"]
