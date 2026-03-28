"""
News Fetcher (yfinance)
Fetches recent headlines for any topic via associated Yahoo Finance tickers.

Public interface
----------------
fetch_news(tickers, start_date)  -> list[dict]
save_raw(rows, topic)            -> Path   (appends to data/raw/news/{topic}.csv)

CLI example (crude oil):
    python ingestion/news_fetcher.py
    python ingestion/news_fetcher.py --topic crypto --tickers BTC-USD ETH-USD

NOTE: yfinance returns ~10 recent articles per ticker (~2-5 days back).
      Run daily and the CSV will accumulate a full history automatically.
"""
import sys
import csv
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root

import yfinance as yf
from config import DATA_RAW_DIR

FIELDNAMES = ["topic", "published_utc", "title", "summary", "source", "url"]

# ── Pre-defined topic configurations ─────────────────────────────────────────
TOPIC_DEFAULTS = {
    "oil": {
        "tickers":    ["CL=F", "BZ=F", "USO", "XLE"],
        "start_date": datetime(2026, 2, 28, tzinfo=timezone.utc),
    },
    "crypto": {
        "tickers":    ["BTC-USD", "ETH-USD"],
        "start_date": None,
    },
    "gold": {
        "tickers":    ["GC=F", "GLD"],
        "start_date": None,
    },
}
# ─────────────────────────────────────────────────────────────────────────────


def _parse_item(item: dict, topic: str) -> Optional[dict]:
    c       = item.get("content", {})
    pub_raw = c.get("pubDate") or c.get("displayTime")
    if not pub_raw:
        return None

    pub_dt  = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
    url     = (c.get("canonicalUrl") or c.get("clickThroughUrl") or {}).get("url", "")

    return {
        "topic":         topic,
        "published_utc": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "title":         c.get("title", "").strip(),
        "summary":       c.get("summary", "").strip(),
        "source":        c.get("provider", {}).get("displayName", ""),
        "url":           url,
    }


def fetch_news(
    tickers: list,
    topic: str = "general",
    start_date: Optional[datetime] = None,
) -> list:
    """
    Fetch news for a list of tickers.

    Parameters
    ----------
    tickers    : list of Yahoo Finance ticker symbols
    topic      : label stored in the 'topic' column
    start_date : drop articles published before this UTC datetime (or None)

    Returns
    -------
    list of dicts, sorted newest-first
    """
    seen_ids = set()
    rows     = []

    for ticker in tickers:
        print(f"  [{topic}] fetching news for {ticker} …")
        try:
            news = yf.Ticker(ticker).news or []
        except Exception as e:
            print(f"    [warn] {ticker}: {e}")
            continue

        for item in news:
            item_id = item.get("id", "")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            row = _parse_item(item, topic)
            if not row:
                continue

            if start_date:
                pub_dt = datetime.fromisoformat(row["published_utc"]).replace(tzinfo=timezone.utc)
                if pub_dt < start_date:
                    continue

            rows.append(row)

    rows.sort(key=lambda r: r["published_utc"], reverse=True)
    return rows


def save_raw(rows: list, topic: str) -> Path:
    """
    Append new rows to data/raw/news/{topic}.csv.
    Deduplicates by URL — existing articles are never overwritten.

    Returns the path to the CSV file.
    """
    out_dir = Path(DATA_RAW_DIR) / "news"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{topic}.csv"

    # Load existing URLs to avoid duplicates
    existing_urls: set = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            existing_urls = {r["url"] for r in csv.DictReader(f)}

    new_rows   = [r for r in rows if r["url"] not in existing_urls]
    write_hdr  = not out_path.exists()

    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_hdr:
            writer.writeheader()
        writer.writerows(new_rows)

    total = len(existing_urls) + len(new_rows)
    print(f"  Saved {len(new_rows)} new articles (total {total}) → {out_path}")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch yfinance news by topic")
    parser.add_argument("--topic",   default="oil",
                        help="Topic label, e.g. oil, crypto, gold (default: oil)")
    parser.add_argument("--tickers", nargs="*",
                        help="Override ticker list, e.g. --tickers CL=F BZ=F")
    parser.add_argument("--start",   default=None,
                        help="Start date YYYY-MM-DD (default: topic default)")
    args = parser.parse_args()

    cfg        = TOPIC_DEFAULTS.get(args.topic, {"tickers": [], "start_date": None})
    tickers    = args.tickers or cfg["tickers"]
    start_date = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc) if args.start else cfg["start_date"]

    if not tickers:
        parser.error(f"Unknown topic '{args.topic}' — provide --tickers or use: {list(TOPIC_DEFAULTS)}")

    print(f"\nFetching news — topic={args.topic}  tickers={tickers}")
    rows = fetch_news(tickers, topic=args.topic, start_date=start_date)
    save_raw(rows, topic=args.topic)

    if rows:
        print("\nLatest 5 headlines:")
        for r in rows[:5]:
            print(f"  [{r['published_utc']}]  {r['title'][:80]}")
