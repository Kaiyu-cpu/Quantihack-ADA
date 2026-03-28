"""
NYMEX WTI Crude Oil Futures Fetcher (Yahoo Finance via yfinance)
Fetches March/April 2026 contracts and saves to CSV.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Optional

import pandas as pd
import yfinance as yf

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from config import DATA_RAW_DIR


def _sanitize_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)


def fetch_futures(symbol: str, start: Optional[str] = None, end: Optional[str] = None,
                  interval: str = "1d") -> pd.DataFrame:
    """
    Fetch futures OHLCV data for a given symbol.
    start/end: YYYY-MM-DD or None for full available history.
    interval: e.g., '1d', '1h', '30m'
    """
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "timestamp"
    df = df.dropna()
    return df


def save_csv(df: pd.DataFrame, symbol: str, interval: str) -> str:
    out_dir = os.path.join(DATA_RAW_DIR, "nymex")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{_sanitize_symbol(symbol)}_{interval}.csv"
    path = os.path.join(out_dir, filename)
    df.to_csv(path)
    return path


def fetch_continuous_front_month(interval: str = "1d") -> dict[str, str]:
    """
    Fetch continuous front-month WTI crude oil futures (Yahoo: CL=F).
    Returns a dict of symbol -> csv path.
    """
    outputs = {}
    symbol = "CL=F"
    df = fetch_futures(symbol, interval=interval)
    outputs[symbol] = save_csv(df, symbol, interval)
    return outputs


if __name__ == "__main__":
    paths = fetch_continuous_front_month(interval="1d")
    for sym, path in paths.items():
        print(f"{sym} -> {path}")
