"""
Market Volatility & Sentiment Features
Derived from Polymarket price/volume time-series.
"""
import pandas as pd
import numpy as np


def compute_market_features(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """
    Input:  time-series DataFrame with [timestamp, price, volume (optional)]
    Output: DataFrame with volatility + sentiment features
    """
    df = df.sort_values("timestamp").copy()

    df["returns"]     = df["price"].pct_change()
    df["volatility"]  = df["returns"].rolling(window).std()
    df["momentum"]    = df["price"] / df["price"].shift(window) - 1
    df["mean_revert"] = (df["price"] - df["price"].rolling(window).mean()) / (df["price"].rolling(window).std() + 1e-9)

    # Sentiment proxy: price > 0.5 means market leans YES (bullish)
    df["sentiment"] = (df["price"] > 0.5).astype(int) * 2 - 1   # +1 / -1

    return df.dropna()


if __name__ == "__main__":
    ts = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=60, freq="D"),
        "price": np.random.uniform(0.2, 0.8, 60),
    })
    result = compute_market_features(ts)
    print(result.tail())
