# test_prices_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root

from api.polymarket.clob_and_relayer import ClobClient  # adjust import path if needed
import json
from pathlib import Path

def main():
    client = ClobClient()

    # Replace with an actual token ID
    token_id = "102368345966235769961429850340048566268287153097365435809509104072185388938128"

    # Fetch historical prices
    prices_data = client.get_prices_history(
        token_id=token_id,
        interval="all",
        fidelity=60  # resolution in minutes
    )

    if prices_data is None:
        print("Failed to fetch price history from CLOB API.")
        return

    # Save to JSON file in the same directory as this script
    output_file = Path(__file__).parent / "prices_history_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(prices_data, f, ensure_ascii=False, indent=4)

    print(f"Price history saved to {output_file}")

if __name__ == "__main__":
    main()