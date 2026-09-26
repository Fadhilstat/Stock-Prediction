"""Deterministic technical research features and indicators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TechnicalSummary:
    """Encapsulates latest technical state for a stock."""

    ticker: str
    as_of_date: pd.Timestamp
    close: float
    sma_20: float
    sma_50: float
    sma_200: float
    rsi_14: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    atr_14: float
    trend_state: str
    momentum_state: str
    volatility_state: str


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index."""
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Wilder smoothing
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute deterministic technical features for a price DataFrame."""
    data = df.sort_values("trade_date").copy()
    close = data["close"]
    high = data["high"]
    low = data["low"]

    data["sma_20"] = close.rolling(20, min_periods=1).mean()
    data["sma_50"] = close.rolling(50, min_periods=1).mean()
    data["sma_200"] = close.rolling(200, min_periods=1).mean()

    data["rsi_14"] = compute_rsi(close, 14)

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    data["macd"] = ema_12 - ema_26
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
    data["macd_histogram"] = data["macd"] - data["macd_signal"]

    data["bollinger_middle"] = data["sma_20"]
    rolling_std = close.rolling(20, min_periods=1).std().fillna(0.0)
    data["bollinger_upper"] = data["bollinger_middle"] + 2.0 * rolling_std
    data["bollinger_lower"] = data["bollinger_middle"] - 2.0 * rolling_std

    data["atr_14"] = compute_atr(high, low, close, 14)

    return data


def summarize_technical_state(df: pd.DataFrame, ticker: str) -> TechnicalSummary:
    """Summarize the latest technical indicator readings."""
    features = compute_technical_features(df)
    latest = features.iloc[-1]

    close = float(latest["close"])
    sma_20 = float(latest["sma_20"])
    sma_50 = float(latest["sma_50"])
    sma_200 = float(latest["sma_200"])
    rsi = float(latest["rsi_14"])
    macd = float(latest["macd"])
    macd_signal = float(latest["macd_signal"])
    bb_upper = float(latest["bollinger_upper"])
    bb_middle = float(latest["bollinger_middle"])
    bb_lower = float(latest["bollinger_lower"])
    atr = float(latest["atr_14"]) if not np.isnan(latest["atr_14"]) else 0.0

    if close > sma_50 > sma_200:
        trend = "BULLISH_UPTREND"
    elif close < sma_50 < sma_200:
        trend = "BEARISH_DOWNTREND"
    elif close > sma_50 and close < sma_200:
        trend = "COUNTER_TREND_RALLY"
    else:
        trend = "CONSOLIDATION_RANGE"

    if rsi > 70:
        momentum = "OVERBOUGHT_EXTENDED"
    elif rsi < 30:
        momentum = "OVERSOLD_COMPRESSED"
    elif macd > macd_signal:
        momentum = "POSITIVE_MOMENTUM"
    else:
        momentum = "NEGATIVE_MOMENTUM"

    bandwidth = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0.0
    if bandwidth > 0.15:
        vol_state = "VOLATILITY_EXPANDED"
    elif bandwidth < 0.05:
        vol_state = "VOLATILITY_COMPRESSED_SQUEEZE"
    else:
        vol_state = "VOLATILITY_NORMAL"

    return TechnicalSummary(
        ticker=ticker,
        as_of_date=pd.Timestamp(latest["trade_date"]),
        close=close,
        sma_20=sma_20,
        sma_50=sma_50,
        sma_200=sma_200,
        rsi_14=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=float(latest["macd_histogram"]),
        bollinger_upper=bb_upper,
        bollinger_middle=bb_middle,
        bollinger_lower=bb_lower,
        atr_14=atr,
        trend_state=trend,
        momentum_state=momentum,
        volatility_state=vol_state,
    )
