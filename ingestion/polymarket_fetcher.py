"""
Polymarket Fetcher
Fetches historical YES-token prices for every market within a Polymarket
event, identified by event slug.

Public interface
----------------
fetch_event_prices(slug, interval, fidelity) -> pd.DataFrame
save_raw(df, filename)
"""
import json
import sys
from pathlib import Path
import pandas as pd

# Allow running directly from any working directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.polymarket.gemma import GammaClient
from api.polymarket.clob_and_relayer import ClobClient
from config import DATA_RAW_DIR


# ── Stateless client singletons (re-used across calls) ───────────────────────
_gamma = GammaClient()
_clob  = ClobClient()


def fetch_event_prices(
    slug: str,
    interval: str = "all",
    fidelity: int = 60,   # resolution in minutes (60 = hourly, 1 = per-minute)
) -> pd.DataFrame:
    """
    Fetch the full price history for every price-level market in an event.

    Parameters
    ----------
    slug     : Polymarket event slug, e.g. "will-crude-oil-cl-hit-by-end-of-march"
    interval : History window passed to the CLOB API ("1d", "1w", "1m", "all")
    fidelity : Granularity in minutes (60 = hourly, 1 = per-minute)

    Returns
    -------
    pd.DataFrame with columns:
        event_slug, market_slug, direction, strike, token_id, timestamp, price
    """
    # ── 1. Fetch event metadata ───────────────────────────────────────────────
    raw = _gamma.get_events(slug=slug)
    if not raw:
        raise ValueError(f"Event not found for slug: '{slug}'")
    events = raw if isinstance(raw, list) else raw.get("data", raw.get("events", [raw]))
    markets = events[0].get("markets", [])

    if not markets:
        raise ValueError(f"No markets found inside event: '{slug}'")

    # ── 2. Fetch price history for each market ────────────────────────────────
    rows = []
    for mkt in markets:
        group_title = mkt.get("groupItemTitle", mkt.get("question", ""))
        market_slug = mkt.get("slug", "")
        token_ids   = json.loads(mkt.get("clobTokenIds", "[]"))

        if not token_ids:
            continue

        yes_token = token_ids[0]  # index 0 → YES outcome

        # Parse "↑ $120" into direction + strike
        if group_title.startswith("↑"):
            direction, strike = "up",   group_title.lstrip("↑").strip()
        elif group_title.startswith("↓"):
            direction, strike = "down", group_title.lstrip("↓").strip()
        else:
            direction, strike = "",     group_title.strip()

        try:
            result  = _clob.get_prices_history(yes_token, interval=interval, fidelity=fidelity)
            history = result if isinstance(result, list) else result.get("history", [])
        except Exception as exc:
            print(f"  [warn] Could not fetch history for {direction} {strike}: {exc}")
            continue

        for point in history:
            rows.append({
                "event_slug":  slug,
                "market_slug": market_slug,
                "direction":   direction,
                "strike":      strike,
                "token_id":    yes_token,
                "timestamp":   pd.to_datetime(point["t"], unit="s", utc=True),
                "price":       float(point["p"]),
            })

    df = pd.DataFrame(rows, columns=["event_slug", "market_slug", "direction",
                                     "strike", "token_id", "timestamp", "price"])
    df.sort_values(["strike", "direction", "timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def save_raw(df: pd.DataFrame, filename: str) -> None:
    """Persist a DataFrame to data/raw/polymarket/ as CSV."""
    # Normalise extension to .csv regardless of what was passed
    filename = Path(filename).stem + ".csv"
    path = Path(DATA_RAW_DIR) / "polymarket" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows → {path}")


# ── CLI example ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SLUG = "will-crude-oil-cl-hit-by-end-of-march"

    print(f"Fetching prices for: {SLUG}")
    df = fetch_event_prices(SLUG)
    print(df.head(10).to_string(index=False))
    print(f"\nTotal rows: {len(df)}  |  Markets: {df['strike'].nunique()}")

    save_raw(df, "crude_oil_prices.parquet")

