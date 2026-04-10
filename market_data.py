"""Fetches live market data using yfinance."""

import yfinance as yf
import pandas as pd
import ta
from config import (
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BOLLINGER_PERIOD, BOLLINGER_STD, MOMENTUM_LOOKBACK,
)


def get_price(ticker: str) -> float | None:
    """Get the current price for a ticker."""
    try:
        t = yf.Ticker(ticker)
        data = t.history(period="1d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception:
        return None


def get_history(ticker: str, period: str = "3mo") -> pd.DataFrame | None:
    """Get historical OHLCV data with technical indicators."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period)
        if df.empty or len(df) < 30:
            return None
        df = _add_indicators(df)
        return df
    except Exception:
        return None


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to a dataframe."""
    close = df["Close"]
    volume = df["Volume"]

    # RSI
    df["rsi"] = ta.momentum.RSIIndicator(close, window=RSI_PERIOD).rsi()

    # MACD
    macd = ta.trend.MACD(close, window_slow=MACD_SLOW, window_fast=MACD_FAST, window_sign=MACD_SIGNAL)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=BOLLINGER_PERIOD, window_dev=BOLLINGER_STD)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_pct"] = bb.bollinger_pband()

    # Moving averages
    df["sma_10"] = close.rolling(10).mean()
    df["sma_20"] = close.rolling(20).mean()
    df["ema_10"] = close.ewm(span=10).mean()

    # Momentum
    df["momentum"] = close.pct_change(MOMENTUM_LOOKBACK)

    # Volume moving average
    df["vol_sma"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / df["vol_sma"]

    # ATR for volatility
    df["atr"] = ta.volatility.AverageTrueRange(
        df["High"], df["Low"], close, window=14
    ).average_true_range()

    return df


def get_bulk_signals(tickers: list[str]) -> dict:
    """Get signals for multiple tickers at once."""
    signals = {}
    for ticker in tickers:
        df = get_history(ticker)
        if df is None:
            continue
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(latest["Close"])

        signals[ticker] = {
            "price": price,
            "rsi": float(latest["rsi"]) if pd.notna(latest["rsi"]) else 50.0,
            "macd_hist": float(latest["macd_hist"]) if pd.notna(latest["macd_hist"]) else 0.0,
            "macd_cross_up": (
                pd.notna(latest["macd"]) and pd.notna(prev["macd"]) and
                prev["macd"] < prev["macd_signal"] and
                latest["macd"] >= latest["macd_signal"]
            ),
            "macd_cross_down": (
                pd.notna(latest["macd"]) and pd.notna(prev["macd"]) and
                prev["macd"] > prev["macd_signal"] and
                latest["macd"] <= latest["macd_signal"]
            ),
            "bb_pct": float(latest["bb_pct"]) if pd.notna(latest["bb_pct"]) else 0.5,
            "above_sma_20": price > latest["sma_20"] if pd.notna(latest["sma_20"]) else False,
            "momentum": float(latest["momentum"]) if pd.notna(latest["momentum"]) else 0.0,
            "vol_ratio": float(latest["vol_ratio"]) if pd.notna(latest["vol_ratio"]) else 1.0,
            "atr_pct": float(latest["atr"] / price) if pd.notna(latest["atr"]) else 0.02,
            "daily_change": float((latest["Close"] - prev["Close"]) / prev["Close"]),
        }
    return signals
