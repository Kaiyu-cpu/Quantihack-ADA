"""
Fetch a Polymarket event by slug.
Target: "Will Crude Oil (CL) hit__ by end of March?"
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

from api.polymarket.gemma import GammaClient

# Polymarket slugs are lower-kebab-case. Try the most likely variations here;
# the script will print whichever one returns data.
CANDIDATE_SLUGS = [
    "will-crude-oil-cl-hit-by-end-of-march",
    "will-crude-oil-cl-hit-by-end-of-march-2025",
    "will-crude-oil-cl-hit-by-end-of-march-2026",
]

OUTPUT_FILE = Path(__file__).parent / "crude_oil_event.json"


def main():
    client = GammaClient()

    for slug in CANDIDATE_SLUGS:
        print(f"Trying slug: {slug}")
        data = client.get_events(slug=slug)

        if data:
            print(f"Found event with slug: {slug}")
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Saved to {OUTPUT_FILE}")
            return

    # Fallback: search by keyword so we can discover the real slug
    print("\nNo exact slug match — searching for 'crude oil' events...")
    all_events = client.get_events(limit=100)
    if not all_events:
        print("Failed to reach Gamma API.")
        return

    events_list = all_events if isinstance(all_events, list) else all_events.get("data", all_events.get("events", []))
    matches = [e for e in events_list if "crude" in e.get("title", "").lower() or "crude" in e.get("slug", "").lower()]

    if matches:
        print(f"Found {len(matches)} crude oil event(s):")
        for m in matches:
            print(f"  slug={m.get('slug')}  title={m.get('title')}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=4)
        print(f"Saved to {OUTPUT_FILE}")
    else:
        print("No crude oil events found in the first 100 results.")


if __name__ == "__main__":
    main()
