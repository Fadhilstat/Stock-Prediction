"""Hidden Markov Model (HMM) Gaussian Mixture Regime Switching Engine.

Identifies unobservable market regimes (Bullish Trend, High-Volatility Bear, Sideways Compression)
using a 3-state continuous Gaussian Hidden Markov Model with transition matrix calibration,
Viterbi path decoding, and forward-backward smoothed posterior state probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class HmmStateProfile:
    """Statistical signature of an individual market regime."""

    state_id: int
    state_label: str
    mean_daily_return_pct: float
    volatility_daily_pct: float
    current_posterior_probability: float
    expected_duration_days: float


@dataclass(frozen=True)
class HmmRegimeReport:
    """Comprehensive HMM regime classification snapshot."""

    ticker: str
    current_regime: str
    current_regime_probability: float
    states: list[HmmStateProfile]
    transition_matrix: list[list[float]]
    viterbi_state_sequence: list[str]
    as_of_date: str
    regime_interpretation: str


REGIME_NAMES = [
    "BULLISH_TREND",
    "SIDEWAYS_COMPRESSION",
    "HIGH_VOLATILITY_BEAR",
]


def fit_gaussian_hmm_3state(
    returns: pd.Series,
    max_iter: int = 50,
    tol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit a 3-state Gaussian HMM using Expectation-Maximization (EM) algorithm.

    Returns:
    - means: array of shape (3,)
    - variances: array of shape (3,)
    - transition_matrix: matrix of shape (3, 3)
    - smoothed_posteriors: matrix of shape (T, 3)
    """
    rets = returns.dropna().to_numpy(dtype=float)
    t_len = len(rets)
    if t_len < 30:
        # Fallback parameters
        means = np.array([0.0012, 0.0001, -0.0018])
        variances = np.array([0.0001, 0.00025, 0.0007])
        trans = np.array([
            [0.85, 0.10, 0.05],
            [0.10, 0.80, 0.10],
            [0.08, 0.12, 0.80],
        ])
        post = np.tile([0.33, 0.34, 0.33], (max(t_len, 1), 1))
        return means, variances, trans, post

    # Quantile-based initial centroids
    p33 = float(np.percentile(rets, 33.3))
    p66 = float(np.percentile(rets, 66.7))

    # Initialize 3 states: [Bull, Sideways, Bear]
    means = np.array([float(np.mean(rets[rets >= p66])), float(np.mean(rets[(rets >= p33) & (rets < p66)])), float(np.mean(rets[rets < p33]))])
    variances = np.array([float(np.var(rets[rets >= p66])) + 1e-5, float(np.var(rets[(rets >= p33) & (rets < p66)])) + 1e-5, float(np.var(rets[rets < p33])) + 1e-5])
    trans = np.array([
        [0.85, 0.10, 0.05],
        [0.10, 0.80, 0.10],
        [0.05, 0.15, 0.80],
    ])
    pi = np.array([0.33, 0.34, 0.33])

    # EM Iterations
    log_likelihood_prev = -np.inf

    for _ in range(max_iter):
        # Emission probabilities B[t, k] = N(rets[t] | means[k], variances[k])
        b_mat = np.zeros((t_len, 3))
        for k in range(3):
            std_k = np.sqrt(max(variances[k], 1e-8))
            b_mat[:, k] = stats.norm.pdf(rets, loc=means[k], scale=std_k)
        b_mat = np.maximum(b_mat, 1e-12)

        # Forward Pass (alpha)
        alpha_mat = np.zeros((t_len, 3))
        scale = np.zeros(t_len)
        alpha_mat[0, :] = pi * b_mat[0, :]
        scale[0] = np.sum(alpha_mat[0, :])
        alpha_mat[0, :] /= max(scale[0], 1e-12)

        for t in range(1, t_len):
            for j in range(3):
                alpha_mat[t, j] = np.sum(alpha_mat[t - 1, :] * trans[:, j]) * b_mat[t, j]
            scale[t] = np.sum(alpha_mat[t, :])
            alpha_mat[t, :] /= max(scale[t], 1e-12)

        # Backward Pass (beta)
        beta_mat = np.zeros((t_len, 3))
        beta_mat[t_len - 1, :] = 1.0

        for t in range(t_len - 2, -1, -1):
            for i in range(3):
                beta_mat[t, i] = np.sum(trans[i, :] * b_mat[t + 1, :] * beta_mat[t + 1, :])
            beta_mat[t, :] /= max(scale[t + 1], 1e-12)

        # Smoothed posterior probabilities (gamma)
        gamma = alpha_mat * beta_mat
        gamma_sum = np.sum(gamma, axis=1, keepdims=True)
        gamma = gamma / np.maximum(gamma_sum, 1e-12)

        # Transition posteriors (xi)
        xi = np.zeros((t_len - 1, 3, 3))
        for t in range(t_len - 1):
            denom = np.sum(alpha_mat[t, :, None] * trans * b_mat[t + 1, None, :] * beta_mat[t + 1, None, :])
            denom = max(denom, 1e-12)
            xi[t, :, :] = (alpha_mat[t, :, None] * trans * b_mat[t + 1, None, :] * beta_mat[t + 1, None, :]) / denom

        # M-step: Update parameters
        pi = gamma[0, :]
        trans = np.sum(xi, axis=0) / np.maximum(np.sum(gamma[:-1, :], axis=0, keepdims=True).T, 1e-12)
        trans = trans / np.sum(trans, axis=1, keepdims=True)

        for k in range(3):
            gamma_k_sum = max(np.sum(gamma[:, k]), 1e-12)
            means[k] = np.sum(gamma[:, k] * rets) / gamma_k_sum
            diff = rets - means[k]
            variances[k] = np.sum(gamma[:, k] * (diff ** 2)) / gamma_k_sum
            variances[k] = max(variances[k], 1e-6)

        log_likelihood = np.sum(np.log(np.maximum(scale, 1e-12)))
        if abs(log_likelihood - log_likelihood_prev) < tol:
            break
        log_likelihood_prev = log_likelihood

    # Sort states by return: 0 = Bull, 1 = Sideways, 2 = Bear
    sort_idx = np.argsort(means)[::-1]
    means = means[sort_idx]
    variances = variances[sort_idx]
    trans = trans[sort_idx, :][:, sort_idx]
    gamma = gamma[:, sort_idx]

    return means, variances, trans, gamma


def decode_viterbi_path(
    returns: pd.Series,
    means: np.ndarray,
    variances: np.ndarray,
    trans: np.ndarray,
) -> list[str]:
    """Decode the most probable path of hidden states via Viterbi dynamic programming."""
    rets = returns.dropna().to_numpy(dtype=float)
    t_len = len(rets)
    if t_len == 0:
        return []

    log_trans = np.log(np.maximum(trans, 1e-12))
    log_pi = np.log(np.array([0.33, 0.34, 0.33]))

    v_matrix = np.zeros((t_len, 3))
    backpointer = np.zeros((t_len, 3), dtype=int)

    for k in range(3):
        std_k = np.sqrt(max(variances[k], 1e-8))
        pdf_val = max(stats.norm.pdf(rets[0], loc=means[k], scale=std_k), 1e-12)
        v_matrix[0, k] = log_pi[k] + np.log(pdf_val)

    for t in range(1, t_len):
        for j in range(3):
            std_j = np.sqrt(max(variances[j], 1e-8))
            pdf_val = max(stats.norm.pdf(rets[t], loc=means[j], scale=std_j), 1e-12)
            log_prob = np.log(pdf_val)
            candidates = v_matrix[t - 1, :] + log_trans[:, j]
            best_prev = int(np.argmax(candidates))
            v_matrix[t, j] = candidates[best_prev] + log_prob
            backpointer[t, j] = best_prev

    # Backtracking
    path = [int(np.argmax(v_matrix[t_len - 1, :]))]
    for t in range(t_len - 1, 0, -1):
        path.append(backpointer[t, path[-1]])
    path.reverse()

    return [REGIME_NAMES[idx] for idx in path]


def compute_hmm_regime_classification(
    price_series: pd.Series,
    ticker: str = "TICKER",
    as_of_date: str | None = None,
) -> HmmRegimeReport:
    """Analyze stock returns to classify hidden market regime and transition outlook."""
    rets = price_series.pct_change().dropna()
    means, variances, trans, gamma = fit_gaussian_hmm_3state(rets)
    viterbi_states = decode_viterbi_path(rets, means, variances, trans)

    last_posteriors = gamma[-1, :] if len(gamma) > 0 else np.array([0.33, 0.34, 0.33])
    current_state_idx = int(np.argmax(last_posteriors))
    current_regime = REGIME_NAMES[current_state_idx]
    current_prob = float(last_posteriors[current_state_idx])

    profiles: list[HmmStateProfile] = []
    for i, name in enumerate(REGIME_NAMES):
        duration = float(1.0 / max(1.0 - trans[i, i], 0.05))
        profiles.append(
            HmmStateProfile(
                state_id=i,
                state_label=name,
                mean_daily_return_pct=round(float(means[i] * 100.0), 3),
                volatility_daily_pct=round(float(np.sqrt(variances[i]) * 100.0), 3),
                current_posterior_probability=round(float(last_posteriors[i]), 4),
                expected_duration_days=round(duration, 1),
            )
        )

    trans_list = [[round(float(trans[i, j]), 4) for j in range(3)] for i in range(3)]

    if current_regime == "BULLISH_TREND":
        interp = "Pasar berada dalam tren kenaikan teratur dengan volatilitas rendah. Alokasi agresif dapat dipertahankan."
    elif current_regime == "HIGH_VOLATILITY_BEAR":
        interp = "Rezim koreksi tajam bervolatilitas tinggi. Aktifkan batas invalidasi keras dan kurangi eksposur."
    else:
        interp = "Rezim konsolidasi sideways terkompresi. Menanti konfirmasi breakout volume sebelum menambah posisi."

    return HmmRegimeReport(
        ticker=ticker,
        current_regime=current_regime,
        current_regime_probability=round(current_prob, 4),
        states=profiles,
        transition_matrix=trans_list,
        viterbi_state_sequence=viterbi_states[-30:] if len(viterbi_states) >= 30 else viterbi_states,
        as_of_date=as_of_date or datetime.now(UTC).strftime("%Y-%m-%d"),
        regime_interpretation=interp,
    )
