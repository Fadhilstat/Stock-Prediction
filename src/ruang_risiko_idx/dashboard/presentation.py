"""Prepare clear dashboard views from validated analytics artifacts."""

from __future__ import annotations

import pandas as pd

MODEL_LABELS = {
    "constant_probability": "Baseline probabilitas historis",
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "egarch_normal": "EGARCH Normal",
    "egarch_student_t": "EGARCH Student-t",
    "gjr_garch_normal": "GJR-GARCH Normal",
    "gjr_garch_student_t": "GJR-GARCH Student-t",
}

REGISTRY_STATUS_LABELS = {
    "provisional_out_of_sample_selection": (
        "Seleksi provisional berdasarkan evaluasi out-of-sample"
    ),
}


def format_model_name(model_name: str) -> str:
    """Return a readable model label without hiding its technical name."""

    return MODEL_LABELS.get(model_name, model_name.replace("_", " ").title())


def format_registry_status(status: str) -> str:
    """Turn a technical registry status into a readable label."""

    return REGISTRY_STATUS_LABELS.get(
        status,
        status.replace("_", " ").capitalize(),
    )


def build_market_snapshot(analytics: pd.DataFrame) -> pd.DataFrame:
    """Build one latest descriptive row for every market series."""

    required_columns = {
        "ticker",
        "trade_date",
        "adjusted_close",
        "simple_return",
        "volatility_21d",
        "drawdown",
    }
    missing = required_columns.difference(analytics.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Analytics data is missing columns: {missing_text}")

    if analytics.empty:
        raise ValueError("Analytics data cannot be empty.")

    latest = (
        analytics.sort_values(["ticker", "trade_date"])
        .groupby("ticker", as_index=False)
        .tail(1)
        .copy()
    )

    return latest[
        [
            "ticker",
            "trade_date",
            "adjusted_close",
            "simple_return",
            "volatility_21d",
            "drawdown",
        ]
    ].sort_values("ticker").reset_index(drop=True)


def build_risk_overview(
    risk_snapshot: pd.DataFrame,
    direction_snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """Join precomputed risk and direction outputs for a compact overview."""

    risk_columns = {
        "ticker",
        "as_of_date",
        "forecast_volatility",
        "var_95",
        "var_99",
        "volatility_model",
        "var_model",
    }
    direction_columns = {
        "ticker",
        "as_of_date",
        "probability_up",
        "selected_model",
    }

    missing_risk = risk_columns.difference(risk_snapshot.columns)
    missing_direction = direction_columns.difference(direction_snapshot.columns)

    if missing_risk:
        text = ", ".join(sorted(missing_risk))
        raise ValueError(f"Risk snapshot is missing columns: {text}")
    if missing_direction:
        text = ", ".join(sorted(missing_direction))
        raise ValueError(f"Direction snapshot is missing columns: {text}")

    risk = risk_snapshot[list(risk_columns)].copy()
    direction = direction_snapshot[list(direction_columns)].copy()

    joined = risk.merge(
        direction,
        on=["ticker", "as_of_date"],
        how="inner",
        validate="one_to_one",
    )

    if len(joined) != len(risk_snapshot) or len(joined) != len(direction_snapshot):
        raise ValueError("Risk and direction snapshots do not align one-to-one.")

    joined["volatility_model_label"] = joined["volatility_model"].map(
        format_model_name
    )
    joined["var_model_label"] = joined["var_model"].map(format_model_name)
    joined["direction_model_label"] = joined["selected_model"].map(
        format_model_name
    )

    return joined.sort_values("ticker").reset_index(drop=True)


def get_ticker_row(data: pd.DataFrame, ticker: str) -> pd.Series:
    """Return one ticker row and fail clearly when it is unavailable."""

    if "ticker" not in data.columns:
        raise ValueError("Data does not contain a ticker column.")

    rows = data.loc[data["ticker"].astype(str).eq(ticker)]
    if len(rows) != 1:
        raise ValueError(f"Expected one row for {ticker}, found {len(rows)}.")

    return rows.iloc[0]
