"""Trading strategies — each returns a score from -1 (strong sell) to +1 (strong buy)."""

from config import RSI_OVERSOLD, RSI_OVERBOUGHT


def momentum_score(signal: dict) -> float:
    """Buy assets with strong upward momentum and volume confirmation."""
    score = 0.0

    # Price momentum over lookback period
    mom = signal["momentum"]
    if mom > 0.10:
        score += 0.4
    elif mom > 0.05:
        score += 0.2
    elif mom < -0.10:
        score -= 0.4
    elif mom < -0.05:
        score -= 0.2

    # Above 20-day SMA = uptrend
    if signal["above_sma_20"]:
        score += 0.2
    else:
        score -= 0.2

    # Volume confirmation
    if signal["vol_ratio"] > 1.5:
        score += 0.2
    elif signal["vol_ratio"] > 1.2:
        score += 0.1

    # MACD crossover
    if signal["macd_cross_up"]:
        score += 0.3
    elif signal["macd_cross_down"]:
        score -= 0.3

    return max(-1.0, min(1.0, score))


def mean_reversion_score(signal: dict) -> float:
    """Buy oversold assets, sell overbought ones."""
    score = 0.0
    rsi = signal["rsi"]
    bb_pct = signal["bb_pct"]

    # RSI extremes
    if rsi < RSI_OVERSOLD:
        score += 0.5
    elif rsi < 40:
        score += 0.2
    elif rsi > RSI_OVERBOUGHT:
        score -= 0.5
    elif rsi > 60:
        score -= 0.1

    # Bollinger Band position
    if bb_pct < 0.0:
        score += 0.3  # Below lower band — oversold
    elif bb_pct < 0.2:
        score += 0.15
    elif bb_pct > 1.0:
        score -= 0.3  # Above upper band — overbought
    elif bb_pct > 0.8:
        score -= 0.15

    return max(-1.0, min(1.0, score))


def breakout_score(signal: dict) -> float:
    """Detect breakouts — price moving above resistance with volume."""
    score = 0.0

    # Price breaking above upper Bollinger Band with volume
    if signal["bb_pct"] > 1.0 and signal["vol_ratio"] > 1.5:
        score += 0.6
    elif signal["bb_pct"] > 0.9 and signal["vol_ratio"] > 1.3:
        score += 0.3

    # Strong daily move with volume
    if signal["daily_change"] > 0.03 and signal["vol_ratio"] > 1.5:
        score += 0.3
    elif signal["daily_change"] < -0.03 and signal["vol_ratio"] > 1.5:
        score -= 0.2  # Breakdown, not breakout

    # MACD histogram increasing
    if signal["macd_hist"] > 0:
        score += 0.1
    else:
        score -= 0.1

    return max(-1.0, min(1.0, score))


def volatility_score(signal: dict) -> float:
    """Prefer assets with high but not extreme volatility — more room to profit."""
    atr_pct = signal["atr_pct"]

    if 0.02 < atr_pct < 0.06:
        return 0.3  # Sweet spot
    elif atr_pct >= 0.06:
        return 0.0  # Too volatile, risky
    else:
        return -0.2  # Too boring for our 100% target


def composite_score(signal: dict) -> float:
    """Weighted combination of all strategies."""
    weights = {
        "momentum": 0.30,
        "mean_reversion": 0.25,
        "breakout": 0.25,
        "volatility": 0.20,
    }

    scores = {
        "momentum": momentum_score(signal),
        "mean_reversion": mean_reversion_score(signal),
        "breakout": breakout_score(signal),
        "volatility": volatility_score(signal),
    }

    total = sum(scores[k] * weights[k] for k in weights)

    return total, scores
