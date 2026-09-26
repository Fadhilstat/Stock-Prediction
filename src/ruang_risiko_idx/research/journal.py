"""Immutable Prediction Journal, forward testing tracker, and replay ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class PredictionRecord:
    """Immutable registered forward prediction record."""

    prediction_id: str
    ticker: str
    created_date: str
    cutoff_date: str
    horizon_label: str
    maturity_date: str
    reference_price: float
    direction_probability_up: float
    selected_model: str
    q10: float
    q50: float
    q90: float
    status: Literal["REGISTERED", "ACTIVE", "MATURED", "EVALUATED"]
    actual_price: float | None
    actual_return: float | None
    outcome_direction_correct: bool | None
    log_loss_contribution: float | None


DEFAULT_JOURNAL_RECORDS: list[PredictionRecord] = [
    PredictionRecord(
        prediction_id="PRED-BBCA-20260731-1D",
        ticker="BBCA.JK",
        created_date="2026-07-31",
        cutoff_date="2026-07-31",
        horizon_label="1D",
        maturity_date="2026-08-03",
        reference_price=10250.0,
        direction_probability_up=0.584,
        selected_model="random_forest",
        q10=10050.0,
        q50=10280.0,
        q90=10450.0,
        status="EVALUATED",
        actual_price=10300.0,
        actual_return=0.00488,
        outcome_direction_correct=True,
        log_loss_contribution=0.537,
    ),
    PredictionRecord(
        prediction_id="PRED-ASII-20260731-1D",
        ticker="ASII.JK",
        created_date="2026-07-31",
        cutoff_date="2026-07-31",
        horizon_label="1D",
        maturity_date="2026-08-03",
        reference_price=4650.0,
        direction_probability_up=0.512,
        selected_model="random_forest",
        q10=4540.0,
        q50=4660.0,
        q90=4780.0,
        status="EVALUATED",
        actual_price=4620.0,
        actual_return=-0.00645,
        outcome_direction_correct=False,
        log_loss_contribution=0.717,
    ),
    PredictionRecord(
        prediction_id="PRED-ANTM-20260731-1D",
        ticker="ANTM.JK",
        created_date="2026-07-31",
        cutoff_date="2026-07-31",
        horizon_label="1D",
        maturity_date="2026-08-03",
        reference_price=1380.0,
        direction_probability_up=0.465,
        selected_model="logistic_regression",
        q10=1330.0,
        q50=1375.0,
        q90=1430.0,
        status="EVALUATED",
        actual_price=1370.0,
        actual_return=-0.00725,
        outcome_direction_correct=True,
        log_loss_contribution=0.625,
    ),
    PredictionRecord(
        prediction_id="PRED-BBRI-20260731-1D",
        ticker="BBRI.JK",
        created_date="2026-07-31",
        cutoff_date="2026-07-31",
        horizon_label="1D",
        maturity_date="2026-08-03",
        reference_price=4720.0,
        direction_probability_up=0.456,
        selected_model="constant_probability",
        q10=4600.0,
        q50=4710.0,
        q90=4830.0,
        status="EVALUATED",
        actual_price=4700.0,
        actual_return=-0.00424,
        outcome_direction_correct=True,
        log_loss_contribution=0.608,
    ),
    PredictionRecord(
        prediction_id="PRED-TLKM-20260731-1D",
        ticker="TLKM.JK",
        created_date="2026-07-31",
        cutoff_date="2026-07-31",
        horizon_label="1D",
        maturity_date="2026-08-03",
        reference_price=2910.0,
        direction_probability_up=0.528,
        selected_model="random_forest",
        q10=2840.0,
        q50=2920.0,
        q90=3000.0,
        status="EVALUATED",
        actual_price=2940.0,
        actual_return=0.01031,
        outcome_direction_correct=True,
        log_loss_contribution=0.638,
    ),
    PredictionRecord(
        prediction_id="PRED-BBCA-20260925-1D",
        ticker="BBCA.JK",
        created_date="2026-09-25",
        cutoff_date="2026-09-25",
        horizon_label="1D",
        maturity_date="2026-09-28",
        reference_price=6250.0,
        direction_probability_up=0.330,
        selected_model="random_forest",
        q10=6135.0,
        q50=6240.0,
        q90=6365.0,
        status="ACTIVE",
        actual_price=None,
        actual_return=None,
        outcome_direction_correct=None,
        log_loss_contribution=None,
    ),
]


def load_prediction_journal() -> pd.DataFrame:
    """Return the immutable prediction journal as a DataFrame."""
    records = []
    for r in DEFAULT_JOURNAL_RECORDS:
        records.append(
            {
                "prediction_id": r.prediction_id,
                "ticker": r.ticker,
                "created_date": r.created_date,
                "horizon": r.horizon_label,
                "maturity_date": r.maturity_date,
                "reference_price": r.reference_price,
                "prob_up": r.direction_probability_up,
                "model": r.selected_model,
                "q10": r.q10,
                "q50": r.q50,
                "q90": r.q90,
                "status": r.status,
                "actual_price": r.actual_price,
                "actual_return": r.actual_return,
                "direction_correct": r.outcome_direction_correct,
            }
        )
    return pd.DataFrame(records)
