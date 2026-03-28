"""
Polymarket Fetcher
Pulls price/volume and orderbook time-series data.
"""
import requests
import pandas as pd
from config import POLYMARKET_API_KEY, POLYMARKET_BASE_URL, DATA_RAW_DIR


HEADERS = {"Authorization": f"Bearer {POLYMARKET_API_KEY}"} if POLYMARKET_API_KEY else {}


def fetch_markets() -> pd.DataFrame:
    """Return available markets."""
    resp = requests.get(f"{POLYMARKET_BASE_URL}/markets", headers=HEADERS)
    resp.raise_for_status()
    return pd.DataFrame(resp.json().get("data", []))


def fetch_timeseries(market_id: str, resolution: str = "1d") -> pd.DataFrame:
    """Return OHLCV time-series for a given market."""
    resp = requests.get(
        f"{POLYMARKET_BASE_URL}/prices-history",
        headers=HEADERS,
        params={"market": market_id, "resolution": resolution},
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json().get("history", []))
    df["t"] = pd.to_datetime(df["t"], unit="s")
    return df.rename(columns={"t": "timestamp", "p": "price"})


def save_raw(df: pd.DataFrame, filename: str) -> None:
    path = f"{DATA_RAW_DIR}/polymarket/{filename}"
    df.to_parquet(path, index=False)
    print(f"Saved {len(df)} rows → {path}")


if __name__ == "__main__":
    markets = fetch_markets()
    print(markets.head())
