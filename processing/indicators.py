"""
Indicator + signal helpers for Polymarket price series.
Ported from the oil notebook for reuse in main.py and dashboard.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def get_series(df: pd.DataFrame, strike_val: int, direction: str = "up",
               resample_rule: str = "1h") -> pd.Series:
    """
    Return a clean price Series for a specific strike + direction.
    """
    mask = (df["strike_val"] == strike_val) & (df["direction"] == direction)
    s = (
        df[mask]
        .set_index("timestamp")["price"]
        .sort_index()
        .resample(resample_rule).last()
        .dropna()
    )
    if s.empty:
        raise ValueError(f"No data for strike={strike_val} direction={direction}")
    s.name = f"{direction} ${strike_val}"
    return s


def add_indicators(s: pd.Series, sma_w: int = 12, ema_w: int = 12,
                   bb_w: int = 20, rsi_w: int = 14) -> pd.DataFrame:
    """
    Attach indicators to a price series.
    Returns DataFrame with columns: price, sma, ema, bb_upper, bb_lower, rsi
    """
    d = pd.DataFrame({"price": s})
    d["sma"] = d["price"].rolling(sma_w).mean()
    d["ema"] = d["price"].ewm(span=ema_w, adjust=False).mean()

    rolling_std = d["price"].rolling(bb_w).std()
    rolling_mean = d["price"].rolling(bb_w).mean()
    d["bb_upper"] = rolling_mean + 2 * rolling_std
    d["bb_lower"] = rolling_mean - 2 * rolling_std

    delta = d["price"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(rsi_w).mean()
    roll_down = down.rolling(rsi_w).mean()
    rs = roll_up / (roll_down + 1e-9)
    d["rsi"] = 100 - (100 / (1 + rs))

    return d.dropna()


def generate_mean_reversion_signals(ind: pd.DataFrame,
                                    rsi_low: float = 35,
                                    rsi_high: float = 65) -> pd.Series:
    """
    Mean-reversion signals (RSI-only for Polymarket):
      +1 RSI < rsi_low  → oversold
      -1 RSI > rsi_high → overbought
       0 otherwise
    """
    sig = pd.Series(0, index=ind.index, name="signal", dtype=int)
    sig[ind["rsi"] < rsi_low] = 1
    sig[ind["rsi"] > rsi_high] = -1
    return sig


def build_signals_from_event_df(
    df: pd.DataFrame,
    strike_val: int,
    direction: str = "up",
    resample_rule: str = "1h",
    sma_w: int = 12,
    ema_w: int = 12,
    bb_w: int = 20,
    rsi_w: int = 14,
    rsi_low: float = 35,
    rsi_high: float = 65,
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """
    Returns: prices series, signals series, indicator DataFrame
    """
    prices = get_series(df, strike_val, direction, resample_rule)
    ind = add_indicators(prices, sma_w=sma_w, ema_w=ema_w, bb_w=bb_w, rsi_w=rsi_w)
    signals = generate_mean_reversion_signals(ind, rsi_low=rsi_low, rsi_high=rsi_high)
    return ind["price"], signals, ind
