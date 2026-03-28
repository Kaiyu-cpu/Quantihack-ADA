"""
Fetch oil-related news headlines via yfinance for CL=F (WTI Crude Oil futures).

Output: tests/news/oil_news.csv
Columns: published_utc, title, summary, source, url

NOTE: yfinance returns only the ~10 most recent articles per ticker.
      Run this script regularly (e.g. daily) to build up a history.
      Each run appends new articles; duplicates are skipped automatically.

Purpose: compare news release timestamps against Polymarket price moves
         to test whether prediction markets lead the news cycle.
"""
import sys
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

import yfinance as yf

# ── Config ────────────────────────────────────────────────────────────────────
TICKERS     = ["CL=F", "USO", "XLE", "BZ=F"]
OUTPUT_FILE = Path(__file__).parent / "oil_news.csv"

# Only keep articles published on or after this date (UTC).
# Set to None to keep everything yfinance returns.
START_DATE  = datetime(2026, 2, 28, tzinfo=timezone.utc)   # ← change as needed
# ─────────────────────────────────────────────────────────────────────────────


def parse_item(item: dict) -> Optional[dict]:
    """Extract flat fields from a yfinance news item."""
    c = item.get("content", {})

    pub_raw = c.get("pubDate") or c.get("displayTime")
    if not pub_raw:
        return None

    # Normalise to UTC datetime
    pub_dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))

    title   = c.get("title", "").strip()
    summary = c.get("summary", "").strip()
    source  = c.get("provider", {}).get("displayName", "")
    url     = (c.get("canonicalUrl") or c.get("clickThroughUrl") or {}).get("url", "")

    return {
        "published_utc": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "title":         title,
        "summary":       summary,
        "source":        source,
        "url":           url,
    }


def fetch_news() -> list:
    seen_ids = set()
    rows     = []

    for ticker in TICKERS:
        print(f"Fetching news for {ticker} …")
        try:
            news = yf.Ticker(ticker).news or []
        except Exception as e:
            print(f"  [warn] {e}")
            continue

        for item in news:
            item_id = item.get("id", "")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            row = parse_item(item)
            if not row:
                continue

            # Apply date filter
            if START_DATE:
                pub_dt = datetime.fromisoformat(row["published_utc"]).replace(tzinfo=timezone.utc)
                if pub_dt < START_DATE:
                    continue

            rows.append(row)

    # Sort newest first
    rows.sort(key=lambda r: r["published_utc"], reverse=True)
    return rows


def load_existing_urls() -> set:
    """Return URLs already in the CSV so we can skip duplicates on append."""
    if not OUTPUT_FILE.exists():
        return set()
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return {row["url"] for row in csv.DictReader(f)}


def main():
    rows = fetch_news()
    if not rows:
        print("No news found in the requested period.")
        return

    # ── Append-only: skip articles already saved ──────────────────────────────
    existing_urls = load_existing_urls()
    new_rows = [r for r in rows if r["url"] not in existing_urls]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUTPUT_FILE.exists()

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["published_utc", "title", "summary", "source", "url"])
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    total = len(existing_urls) + len(new_rows)
    print(f"\nAdded {len(new_rows)} new articles  |  Total in file: {total}  →  {OUTPUT_FILE}")
    if new_rows:
        print("\nLatest 5 headlines:")
        for r in new_rows[:5]:
            print(f"  [{r['published_utc']}]  {r['title'][:80]}")


if __name__ == "__main__":
    main()
