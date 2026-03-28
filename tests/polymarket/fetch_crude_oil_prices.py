"""
Fetch historical YES-token prices for every price level in the
"Will Crude Oil (CL) hit__ by end of March?" event.

Output: tests/polymarket/crude_oil_prices.csv
Columns: market_slug, price_level, token_id, timestamp, price
"""
import sys
import json
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

from api.polymarket.gemma import GammaClient
from api.polymarket.clob_and_relayer import ClobClient

EVENT_SLUG  = "will-crude-oil-cl-hit-by-end-of-march"
OUTPUT_FILE = Path(__file__).parent / "crude_oil_prices.csv"
INTERVAL    = "all"   # full history
FIDELITY    = 60      # 1-hour data points


def fetch_event(gamma: GammaClient) -> dict:
    data = gamma.get_events(slug=EVENT_SLUG)
    if not data:
        raise RuntimeError(f"Could not fetch event: {EVENT_SLUG}")
    events = data if isinstance(data, list) else data.get("data", data.get("events", [data]))
    return events[0]


def main():
    gamma = GammaClient()
    clob  = ClobClient()

    print(f"Fetching event: {EVENT_SLUG}")
    event = fetch_event(gamma)
    markets = event.get("markets", [])
    print(f"Found {len(markets)} price-level markets")

    rows = []
    for mkt in markets:
        price_level = mkt.get("groupItemTitle", mkt.get("question", "unknown"))
        slug        = mkt.get("slug", "")
        token_ids   = json.loads(mkt.get("clobTokenIds", "[]"))

        if not token_ids:
            print(f"  [skip] no token IDs for {price_level}")
            continue

        yes_token = token_ids[0]   # index 0 = YES outcome

        # Parse "↑ $120" → direction="up", strike="$120"
        if price_level.startswith("↑"):
            direction = "up"
            strike = price_level.lstrip("↑").strip()
        elif price_level.startswith("↓"):
            direction = "down"
            strike = price_level.lstrip("↓").strip()
        else:
            direction = ""
            strike = price_level.strip()

        print(f"  Fetching history for {direction} {strike}  (token: {yes_token[:12]}…)")

        try:
            result = clob.get_prices_history(yes_token, interval=INTERVAL, fidelity=FIDELITY)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        history = result if isinstance(result, list) else result.get("history", [])
        for point in history:
            rows.append({
                "market_slug": slug,
                "direction":   direction,
                "strike":      strike,
                "token_id":    yes_token,
                "timestamp":   point.get("t"),
                "price":       point.get("p"),
            })

        print(f"    → {len(history)} data points")

    if not rows:
        print("No data to save.")
        return

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["market_slug", "direction", "strike", "token_id", "timestamp", "price"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
