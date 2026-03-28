# test_events.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

from api.polymarket.gemma import GammaClient  # adjust import path if needed
import json
from pathlib import Path

def main():
    client = GammaClient()

    # Fetch first 2 open events
    events_data = client.get_events(limit=20)

    if events_data is None:
        print("Failed to fetch events from Gamma API.")
        return

    # Save to JSON file in the same directory as this script
    output_file = Path(__file__).parent / "events_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(events_data, f, ensure_ascii=False, indent=4)

    print(f"Events saved to {output_file}")

if __name__ == "__main__":
    main()
