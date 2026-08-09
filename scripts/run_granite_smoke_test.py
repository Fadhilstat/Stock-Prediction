"""Run one leakage-safe Granite TTM smoke forecast."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ruang_risiko_idx.foundation.granite_adapter import (
    build_granite_backtest_window,
)
from ruang_risiko_idx.foundation.granite_inference import (
    GraniteInferenceConfig,
    load_granite_model,
    predict_granite_windows,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytics_daily.parquet"
)


def main() -> int:
    """Run one BBCA zero-shot forecast."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Analytics data was not found at {DATA_PATH}."
        )

    analytics = pd.read_parquet(
        DATA_PATH
    )

    ticker = "BBCA.JK"

    ticker_data = (
        analytics.loc[
            analytics["ticker"].eq(ticker),
            [
                "trade_date",
                "log_return",
            ],
        ]
        .dropna(subset=["log_return"])
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    cutoff_date = (
        ticker_data["trade_date"].iloc[-2]
    )

    config = GraniteInferenceConfig(
        context_length=512,
        prediction_length=1,
        frequency="D",
        batch_size=1,
        seed=42,
    )

    window = build_granite_backtest_window(
        data=analytics,
        ticker=ticker,
        cutoff_date=cutoff_date,
        context_length=config.context_length,
        pred_len=config.prediction_length,
    )

    model, device, model_key = (
        load_granite_model(
            config=config,
        )
    )

    prediction = predict_granite_windows(
        model=model,
        windows=[window],
        config=config,
        device=device,
    )

    row = prediction.iloc[0]

    predicted = float(
        row["predicted_log_return"]
    )

    actual = float(
        row["actual_log_return"]
    )

    print("Ticker:", ticker)
    print("Model revision:", model_key)
    print("Device:", device)

    print(
        "Context start:",
        window.context_timestamps.iloc[0].date(),
    )

    print(
        "Context cutoff:",
        window.context_timestamps.iloc[-1].date(),
    )

    print(
        "Target date:",
        pd.Timestamp(
            row["trade_date"]
        ).date(),
    )

    print(
        "Target after cutoff:",
        (
            pd.Timestamp(row["trade_date"])
            > window.context_timestamps.iloc[-1]
        ),
    )

    print(
        "Context observations:",
        window.context_length,
    )

    print(
        "Predicted log return:",
        f"{predicted:.8f}",
    )

    print(
        "Actual log return:",
        f"{actual:.8f}",
    )

    print(
        "Absolute error:",
        f"{abs(predicted - actual):.8f}",
    )

    print("Granite smoke test: OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
