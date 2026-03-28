"""
Fetch oil-related Reddit posts using Reddit's public JSON API.

No credentials or app setup required — uses only requests + a User-Agent header.

Searches across key subreddits for posts mentioning crude oil, WTI, OPEC, etc.
Output: tests/reddit/oil_reddit_posts.csv

Columns: published_utc, subreddit, title, selftext, score,
         num_comments, upvote_ratio, url, permalink
"""
import sys
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

import requests

# ── Config ────────────────────────────────────────────────────────────────────
SUBREDDITS  = ["crudeoil", "investing", "stocks", "commodities", "wallstreetbets"]
KEYWORDS    = ["crude oil", "WTI", "oil price", "OPEC", "CL futures"]
POST_LIMIT  = 100        # max per request (Reddit caps at 100)
SORT        = "new"      # "new" | "hot" | "top" | "relevance"
TIME_FILTER = "month"    # only applies when sort="top": day|week|month|year|all
START_DATE  = datetime(2026, 2, 28, tzinfo=timezone.utc)

OUTPUT_FILE = Path(__file__).parent / "oil_reddit_posts.csv"
FIELDNAMES  = ["published_utc", "subreddit", "title", "selftext",
               "score", "num_comments", "upvote_ratio", "url", "permalink"]

# Reddit requires a descriptive User-Agent to avoid 429s
HEADERS = {"User-Agent": "oil-research-fetcher/1.0 (data analysis, no login)"}
# ─────────────────────────────────────────────────────────────────────────────


def search_subreddit(subreddit: str, keyword: str) -> list:
    """Call the public Reddit search JSON endpoint for one subreddit + keyword."""
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        "q":           keyword,
        "restrict_sr": "true",   # stay within this subreddit
        "sort":        SORT,
        "t":           TIME_FILTER,
        "limit":       POST_LIMIT,
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", {}).get("children", [])


def fetch_posts() -> list:
    seen_ids = set()
    rows     = []

    for sub in SUBREDDITS:
        for keyword in KEYWORDS:
            print(f"  r/{sub}  ← '{keyword}'")
            try:
                children = search_subreddit(sub, keyword)
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
                if START_DATE and pub_dt < START_DATE:
                    continue

                rows.append({
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

            time.sleep(1)   # be polite — Reddit rate limit is ~60 req/min

    rows.sort(key=lambda r: r["published_utc"], reverse=True)
    return rows


def load_existing_permalinks() -> set:
    if not OUTPUT_FILE.exists():
        return set()
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return {r["permalink"] for r in csv.DictReader(f)}


def main():
    print("Fetching Reddit posts (no login required)…")
    rows = fetch_posts()

    if not rows:
        print("No posts found in the requested period.")
        return

    existing = load_existing_permalinks()
    new_rows = [r for r in rows if r["permalink"] not in existing]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUTPUT_FILE.exists()

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    total = len(existing) + len(new_rows)
    print(f"\nAdded {len(new_rows)} new posts  |  Total in file: {total}  →  {OUTPUT_FILE}")

    if new_rows:
        print("\nLatest 5 posts:")
        for r in new_rows[:5]:
            print(f"  [{r['published_utc']}]  r/{r['subreddit']}  {r['title'][:70]}")


if __name__ == "__main__":
    main()
