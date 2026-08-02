"""Tests for Value at Risk backtesting."""

import pandas as pd

from ruang_risiko_idx.econometrics.backtesting import (
    christoffersen_independence_test,
    kupiec_unconditional_coverage_test,
    summarize_var_backtest,
)


def test_kupiec_test_counts_violations() -> None:
    violations = pd.Series([False] * 95 + [True] * 5)

    result = kupiec_unconditional_coverage_test(
        violations=violations,
        tail_probability=0.05,
    )

    assert result["observations"] == 100
    assert result["violation_count"] == 5
    assert result["observed_violation_rate"] == 0.05
    assert 0 <= result["kupiec_p_value"] <= 1


def test_christoffersen_test_returns_transitions() -> None:
    violations = pd.Series(
        [
            False,
            False,
            True,
            False,
            False,
            True,
            False,
        ]
    )

    result = christoffersen_independence_test(violations)

    transition_total = (
        result["transition_00"]
        + result["transition_01"]
        + result["transition_10"]
        + result["transition_11"]
    )

    assert transition_total == 6
    assert 0 <= result["christoffersen_independence_p_value"] <= 1


def test_summarize_var_backtest() -> None:
    actual_returns = pd.Series(
        [
            -0.01,
            -0.04,
            0.01,
            -0.02,
            0.02,
        ]
    )

    thresholds = pd.Series([-0.03] * 5)

    result = summarize_var_backtest(
        actual_returns=actual_returns,
        var_thresholds=thresholds,
        tail_probability=0.05,
    )

    assert result["violation_count"] == 1
    assert result["observed_violation_rate"] == 0.2
    assert 0 <= result["conditional_coverage_p_value"] <= 1
