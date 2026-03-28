"""
Pipeline entry point — wire ingestion → processing → execution together.
"""
from ingestion.github_fetcher    import fetch_issues, save_raw as save_issues
from ingestion.polymarket_fetcher import fetch_markets, fetch_timeseries, save_raw as save_poly
from processing.survival_analysis import compute_agility_score
from processing.market_features   import compute_market_features
from execution.backtester         import run_backtest


def run_pipeline(market_id: str) -> None:
    print("=== 1. Ingestion ===")
    issues_df  = fetch_issues()
    save_issues(issues_df)

    price_df = fetch_timeseries(market_id)
    save_poly(price_df, f"{market_id}_prices.parquet")

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
    run_pipeline(market_id="EXAMPLE_MARKET_ID")
