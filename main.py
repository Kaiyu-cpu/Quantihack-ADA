"""
Pipeline entry point — wire ingestion → processing → execution together.
"""
from ingestion.github_fetcher    import fetch_issues, save_raw as save_issues
from ingestion.polymarket_fetcher import fetch_event_prices, save_raw as save_poly
from processing.survival_analysis import compute_agility_score
from processing.market_features   import compute_market_features
from execution.backtester         import run_backtest


def run_pipeline(event_slug: str) -> None:
    print("=== 1. Ingestion ===")
    issues_df  = fetch_issues()
    save_issues(issues_df)

    price_df = fetch_event_prices(event_slug)
    save_poly(price_df, f"{event_slug}_prices")

    print("=== 2. Processing ===")
    agility_df = compute_agility_score(issues_df)
    market_df  = compute_market_features(price_df)

    print(f"Agility score: {agility_df['agility_score'].iloc[0]:.4f}")

    print("=== 3. Execution (placeholder signals) ===")
    import pandas as pd, numpy as np
    prices  = market_df.set_index("timestamp")["price"]
    signals = pd.Series(np.random.choice([-1, 0, 1], len(prices)), index=prices.index)

    result = run_backtest(prices, signals)
    print("Backtest metrics:", result["metrics"])


if __name__ == "__main__":
    # Polymarket event slug, e.g. "will-crude-oil-cl-hit-by-end-of-march"
    run_pipeline(event_slug="EXAMPLE_EVENT_SLUG")
