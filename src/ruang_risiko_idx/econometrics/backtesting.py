"""Statistical backtests for Value at Risk forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import xlogy
from scipy.stats import chi2


def kupiec_unconditional_coverage_test(
    violations: pd.Series,
    tail_probability: float,
) -> dict[str, float | int]:
    """Test whether the VaR violation rate matches its target."""

    if not 0 < tail_probability < 1:
        raise ValueError("Tail probability must be between zero and one.")

    observed = (
        pd.Series(
            violations,
            copy=True,
        )
        .dropna()
        .astype(bool)
    )

    observations = int(len(observed))

    if observations == 0:
        raise ValueError("Kupiec test received no valid observations.")

    violation_count = int(observed.sum())
    observed_rate = violation_count / observations

    null_log_likelihood = float(
        xlogy(
            violation_count,
            tail_probability,
        )
        + xlogy(
            observations - violation_count,
            1.0 - tail_probability,
        )
    )

    alternative_log_likelihood = float(
        xlogy(
            violation_count,
            observed_rate,
        )
        + xlogy(
            observations - violation_count,
            1.0 - observed_rate,
        )
    )

    likelihood_ratio = max(
        0.0,
        2.0 * (alternative_log_likelihood - null_log_likelihood),
    )

    return {
        "observations": observations,
        "violation_count": violation_count,
        "expected_violation_rate": (tail_probability),
        "observed_violation_rate": (observed_rate),
        "kupiec_lr_statistic": (likelihood_ratio),
        "kupiec_p_value": float(
            chi2.sf(
                likelihood_ratio,
                df=1,
            )
        ),
    }


def christoffersen_independence_test(
    violations: pd.Series,
) -> dict[str, float | int]:
    """Test whether VaR violations are independent over time."""

    observed = (
        pd.Series(
            violations,
            copy=True,
        )
        .dropna()
        .astype(bool)
        .astype("int64")
        .reset_index(drop=True)
    )

    if len(observed) < 2:
        raise ValueError("Christoffersen test requires at least two observations.")

    previous = observed.iloc[:-1].to_numpy()
    current = observed.iloc[1:].to_numpy()

    count_00 = int(((previous == 0) & (current == 0)).sum())
    count_01 = int(((previous == 0) & (current == 1)).sum())
    count_10 = int(((previous == 1) & (current == 0)).sum())
    count_11 = int(((previous == 1) & (current == 1)).sum())

    total_transitions = count_00 + count_01 + count_10 + count_11

    unconditional_probability = (count_01 + count_11) / total_transitions

    zero_state_transitions = count_00 + count_01
    one_state_transitions = count_10 + count_11

    probability_01 = count_01 / zero_state_transitions if zero_state_transitions else 0.0

    probability_11 = count_11 / one_state_transitions if one_state_transitions else 0.0

    null_log_likelihood = float(
        xlogy(
            count_01 + count_11,
            unconditional_probability,
        )
        + xlogy(
            count_00 + count_10,
            1.0 - unconditional_probability,
        )
    )

    alternative_log_likelihood = float(
        xlogy(
            count_01,
            probability_01,
        )
        + xlogy(
            count_00,
            1.0 - probability_01,
        )
        + xlogy(
            count_11,
            probability_11,
        )
        + xlogy(
            count_10,
            1.0 - probability_11,
        )
    )

    likelihood_ratio = max(
        0.0,
        2.0 * (alternative_log_likelihood - null_log_likelihood),
    )

    return {
        "transition_00": count_00,
        "transition_01": count_01,
        "transition_10": count_10,
        "transition_11": count_11,
        "christoffersen_independence_lr": (likelihood_ratio),
        "christoffersen_independence_p_value": float(
            chi2.sf(
                likelihood_ratio,
                df=1,
            )
        ),
    }


def summarize_var_backtest(
    actual_returns: pd.Series,
    var_thresholds: pd.Series,
    tail_probability: float,
) -> dict[str, float | int]:
    """Summarize coverage and independence for one VaR series."""

    aligned = pd.concat(
        [
            pd.Series(
                actual_returns,
                copy=True,
                dtype="float64",
                name="actual_return",
            ),
            pd.Series(
                var_thresholds,
                copy=True,
                dtype="float64",
                name="var_threshold",
            ),
        ],
        axis=1,
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    )

    aligned = aligned.dropna()

    if aligned.empty:
        raise ValueError("VaR backtest received no valid observations.")

    violations = aligned["actual_return"] < aligned["var_threshold"]

    kupiec = kupiec_unconditional_coverage_test(
        violations=violations,
        tail_probability=tail_probability,
    )

    independence = christoffersen_independence_test(
        violations=violations,
    )

    conditional_coverage_lr = float(kupiec["kupiec_lr_statistic"]) + float(
        independence["christoffersen_independence_lr"]
    )

    return {
        **kupiec,
        **independence,
        "conditional_coverage_lr": (conditional_coverage_lr),
        "conditional_coverage_p_value": float(
            chi2.sf(
                conditional_coverage_lr,
                df=2,
            )
        ),
    }
