"""
Reddit Fetcher (public JSON API)
Fetches posts for any topic from configurable subreddits.
No credentials required.

Public interface
----------------
fetch_posts(subreddits, keywords, start_date, topic) -> list[dict]
save_raw(rows, topic)                                -> Path

CLI example (crude oil):
    python ingestion/reddit_fetcher.py
    python ingestion/reddit_fetcher.py --topic crypto --subreddits CryptoCurrency Bitcoin --keywords bitcoin ethereum

Rate limit: Reddit public API allows ~60 req/min; a 1 s sleep is added between
requests. For large topic configs, the full run may take a few minutes.
"""
import sys
import csv
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root

import requests
from config import DATA_RAW_DIR

FIELDNAMES = ["topic", "published_utc", "subreddit", "title", "selftext",
              "score", "num_comments", "upvote_ratio", "url", "permalink"]

REDDIT_HEADERS = {"User-Agent": "quantihack-research/1.0 (data analysis, no login)"}

# ── Pre-defined topic configurations ─────────────────────────────────────────
TOPIC_DEFAULTS = {
    "oil": {
        "subreddits": ["crudeoil", "investing", "stocks", "commodities", "wallstreetbets"],
        "keywords":   ["crude oil", "WTI", "oil price", "OPEC", "CL futures"],
        "start_date": datetime(2026, 2, 28, tzinfo=timezone.utc),
    },
    "crypto": {
        "subreddits": ["CryptoCurrency", "Bitcoin", "investing"],
        "keywords":   ["bitcoin", "ethereum", "crypto"],
        "start_date": None,
    },
    "gold": {
        "subreddits": ["Gold", "investing", "commodities"],
        "keywords":   ["gold price", "XAU", "gold futures"],
        "start_date": None,
    },
}
# ─────────────────────────────────────────────────────────────────────────────


def _search_subreddit(subreddit: str, keyword: str,
                      sort: str = "new", time_filter: str = "month",
                      limit: int = 100) -> list:
    """Hit the public Reddit search endpoint; return raw children list."""
    url  = f"https://www.reddit.com/r/{subreddit}/search.json"
    resp = requests.get(
        url,
        headers=REDDIT_HEADERS,
        params={"q": keyword, "restrict_sr": "true",
                "sort": sort, "t": time_filter, "limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("children", [])


def fetch_posts(
    subreddits: list,
    keywords: list,
    topic: str = "general",
    start_date: Optional[datetime] = None,
    sort: str = "new",
    time_filter: str = "month",
    post_limit: int = 100,
) -> list:
    """
    Fetch Reddit posts matching any keyword across all subreddits.

    Parameters
    ----------
    subreddits  : list of subreddit names (without r/)
    keywords    : search terms — posts matching ANY keyword are included
    topic       : label stored in the 'topic' column
    start_date  : drop posts published before this UTC datetime (or None)
    sort        : "new" | "hot" | "top" | "relevance"
    time_filter : "day" | "week" | "month" | "year" | "all" (only for sort=top)
    post_limit  : max results per (subreddit, keyword) pair — Reddit caps at 100

    Returns
    -------
    list of dicts, sorted newest-first, deduplicated by post ID
    """
    seen_ids = set()
    rows     = []

    for sub in subreddits:
        for keyword in keywords:
            print(f"  [{topic}] r/{sub}  ← '{keyword}'")
            try:
                children = _search_subreddit(sub, keyword, sort, time_filter, post_limit)
            except Exception as e:
                print(f"    [warn] {e}")
                time.sleep(2)
                continue

            for child in children:
                post = child.get("data", {})
                pid  = post.get("id", "")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                pub_dt = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)
                if start_date and pub_dt < start_date:
                    continue

                rows.append({
                    "topic":         topic,
                    "published_utc": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "subreddit":     post.get("subreddit", sub),
                    "title":         post.get("title", ""),
                    "selftext":      (post.get("selftext", "") or "")[:500].replace("\n", " "),
                    "score":         post.get("score", 0),
                    "num_comments":  post.get("num_comments", 0),
                    "upvote_ratio":  post.get("upvote_ratio", 0),
                    "url":           post.get("url", ""),
                    "permalink":     "https://reddit.com" + post.get("permalink", ""),
                })

            time.sleep(1)  # stay within Reddit's rate limit

    rows.sort(key=lambda r: r["published_utc"], reverse=True)
    return rows


def save_raw(rows: list, topic: str) -> Path:
    """
    Append new rows to data/raw/reddit/{topic}.csv.
    Deduplicates by permalink — existing posts are never overwritten.

    Returns the path to the CSV file.
    """
    out_dir = Path(DATA_RAW_DIR) / "reddit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{topic}.csv"

    existing_permalinks: set = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            existing_permalinks = {r["permalink"] for r in csv.DictReader(f)}

    new_rows  = [r for r in rows if r["permalink"] not in existing_permalinks]
    write_hdr = not out_path.exists()

    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_hdr:
            writer.writeheader()
        writer.writerows(new_rows)

    total = len(existing_permalinks) + len(new_rows)
    print(f"  Saved {len(new_rows)} new posts (total {total}) → {out_path}")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Reddit posts by topic")
    parser.add_argument("--topic",      default="oil",
                        help="Topic label, e.g. oil, crypto, gold (default: oil)")
    parser.add_argument("--subreddits", nargs="*",
                        help="Override subreddit list, e.g. --subreddits investing stocks")
    parser.add_argument("--keywords",   nargs="*",
                        help="Override keyword list, e.g. --keywords 'crude oil' WTI")
    parser.add_argument("--start",      default=None,
                        help="Start date YYYY-MM-DD (default: topic default)")
    parser.add_argument("--sort",       default="new",
                        choices=["new", "hot", "top", "relevance"])
    args = parser.parse_args()

    cfg        = TOPIC_DEFAULTS.get(args.topic, {"subreddits": [], "keywords": [], "start_date": None})
    subreddits = args.subreddits or cfg["subreddits"]
    keywords   = args.keywords   or cfg["keywords"]
    start_date = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc) if args.start else cfg["start_date"]

    if not subreddits or not keywords:
        parser.error(f"Unknown topic '{args.topic}' — provide --subreddits/--keywords or use: {list(TOPIC_DEFAULTS)}")

    print(f"\nFetching Reddit — topic={args.topic}  sort={args.sort}")
    rows = fetch_posts(subreddits, keywords, topic=args.topic,
                       start_date=start_date, sort=args.sort)
    save_raw(rows, topic=args.topic)

    if rows:
        print("\nLatest 5 posts:")
        for r in rows[:5]:
            print(f"  [{r['published_utc']}]  r/{r['subreddit']}  {r['title'][:70]}")
