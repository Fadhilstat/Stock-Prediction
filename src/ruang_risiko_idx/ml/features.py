"""Leakage-safe features for next-day return classification."""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = (
    "return_1d",
    "momentum_5d",
    "momentum_21d",
    "benchmark_return_1d",
    "excess_return_1d",
    "volatility_21d",
    "volatility_63d",
    "drawdown",
    "time_under_water",
    "intraday_range",
    "close_location",
    "log_volume",
    "volume_change_1d",
    "volume_zscore_21d",
)


def _validate_analytics_schema(
    analytics: pd.DataFrame,
) -> None:
    """Validate columns needed for ML feature engineering."""

    required_columns = {
        "ticker",
        "trade_date",
        "high",
        "low",
        "close",
        "volume",
        "log_return",
        "benchmark_return",
        "excess_return",
        "volatility_21d",
        "volatility_63d",
        "drawdown",
        "time_under_water",
    }

    missing_columns = required_columns.difference(analytics.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Analytics data is missing required columns: {missing_text}")


def _calculate_close_location(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> pd.Series:
    """Calculate where the close falls inside the daily price range."""

    price_range = high - low

    location = (close - low) / price_range.replace(0.0, np.nan)

    return location.clip(
        lower=0.0,
        upper=1.0,
    )


def _calculate_rolling_zscore(
    values: pd.Series,
    window: int,
    minimum_periods: int,
) -> pd.Series:
    """Calculate a trailing z-score using current and prior observations."""

    rolling_mean = values.rolling(
        window=window,
        min_periods=minimum_periods,
    ).mean()

    rolling_standard_deviation = values.rolling(
        window=window,
        min_periods=minimum_periods,
    ).std(ddof=1)

    return (values - rolling_mean) / rolling_standard_deviation.replace(
        0.0,
        np.nan,
    )


def build_ticker_ml_features(
    ticker_data: pd.DataFrame,
) -> pd.DataFrame:
    """Build features and next-day target for one ticker."""

    _validate_analytics_schema(ticker_data)

    ordered = ticker_data.copy().sort_values("trade_date").reset_index(drop=True)

    if ordered.empty:
        raise ValueError("Ticker data cannot be empty.")

    if ordered["ticker"].nunique() != 1:
        raise ValueError("Ticker feature builder requires exactly one ticker.")

    if ordered["trade_date"].duplicated().any():
        raise ValueError("Ticker data contains duplicate trade dates.")

    ordered["return_1d"] = ordered["log_return"]

    ordered["momentum_5d"] = (
        ordered["log_return"]
        .rolling(
            window=5,
            min_periods=5,
        )
        .sum()
    )

    ordered["momentum_21d"] = (
        ordered["log_return"]
        .rolling(
            window=21,
            min_periods=21,
        )
        .sum()
    )

    ordered["benchmark_return_1d"] = ordered["benchmark_return"]

    ordered["excess_return_1d"] = ordered["excess_return"]

    ordered["intraday_range"] = (ordered["high"] - ordered["low"]) / ordered["close"].replace(
        0.0,
        np.nan,
    )

    ordered["close_location"] = _calculate_close_location(
        high=ordered["high"],
        low=ordered["low"],
        close=ordered["close"],
    )

    ordered["log_volume"] = np.log1p(ordered["volume"].clip(lower=0))

    ordered["volume_change_1d"] = ordered["log_volume"].diff()

    ordered["volume_zscore_21d"] = _calculate_rolling_zscore(
        values=ordered["log_volume"],
        window=21,
        minimum_periods=21,
    )

    ordered["target_date"] = ordered["trade_date"].shift(-1)

    ordered["target_return_next_day"] = ordered["log_return"].shift(-1)

    ordered["target_up_next_day"] = ordered["target_return_next_day"].gt(0.0).astype("Int64")

    missing_target = ordered["target_return_next_day"].isna()

    ordered.loc[
        missing_target,
        "target_up_next_day",
    ] = pd.NA

    output_columns = [
        "ticker",
        "trade_date",
        "target_date",
        *FEATURE_COLUMNS,
        "target_return_next_day",
        "target_up_next_day",
    ]

    output = ordered[output_columns].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return output


def build_ml_feature_dataset(
    analytics: pd.DataFrame,
    drop_incomplete_rows: bool = True,
) -> pd.DataFrame:
    """Build the combined leakage-safe ML dataset."""

    _validate_analytics_schema(analytics)

    duplicate_count = int(
        analytics.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    if duplicate_count:
        raise ValueError("Analytics data contains duplicate ticker-date rows.")

    feature_frames: list[pd.DataFrame] = []

    for _ticker, group in analytics.groupby(
        "ticker",
        sort=True,
    ):
        ticker_features = build_ticker_ml_features(group)

        feature_frames.append(ticker_features)

    dataset = pd.concat(
        feature_frames,
        ignore_index=True,
    )

    if drop_incomplete_rows:
        required_complete_columns = [
            *FEATURE_COLUMNS,
            "target_date",
            "target_return_next_day",
            "target_up_next_day",
        ]

        dataset = dataset.dropna(subset=required_complete_columns)

    dataset["target_up_next_day"] = dataset["target_up_next_day"].astype("int8")

    return dataset.sort_values(
        [
            "trade_date",
            "ticker",
        ]
    ).reset_index(drop=True)


def validate_ml_dataset(
    dataset: pd.DataFrame,
) -> dict[str, object]:
    """Validate target alignment and feature completeness."""

    required_columns = {
        "ticker",
        "trade_date",
        "target_date",
        *FEATURE_COLUMNS,
        "target_return_next_day",
        "target_up_next_day",
    }

    missing_columns = required_columns.difference(dataset.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"ML dataset is missing columns: {missing_text}")

    if dataset.empty:
        raise ValueError("ML dataset cannot be empty.")

    if dataset.duplicated(
        subset=[
            "ticker",
            "trade_date",
        ]
    ).any():
        raise ValueError("ML dataset contains duplicate ticker-date rows.")

    if not (dataset["target_date"] > dataset["trade_date"]).all():
        raise ValueError("Every target date must occur after its feature date.")

    feature_missing_count = int(dataset[list(FEATURE_COLUMNS)].isna().sum().sum())

    if feature_missing_count:
        raise ValueError("ML dataset contains missing feature values.")

    target_values = set(dataset["target_up_next_day"].unique().tolist())

    if not target_values.issubset({0, 1}):
        raise ValueError("Classification target must contain only zero and one.")

    return {
        "rows": int(len(dataset)),
        "tickers": int(dataset["ticker"].nunique()),
        "first_feature_date": (dataset["trade_date"].min()),
        "last_feature_date": (dataset["trade_date"].max()),
        "first_target_date": (dataset["target_date"].min()),
        "last_target_date": (dataset["target_date"].max()),
        "positive_target_rate": float(dataset["target_up_next_day"].mean()),
        "missing_feature_values": (feature_missing_count),
    }
