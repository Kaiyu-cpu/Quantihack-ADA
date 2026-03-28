"""
Pipeline entry point — wire ingestion → processing → execution together.
"""
from ingestion.github_fetcher    import fetch_issues, save_raw as save_issues
from ingestion.polymarket_fetcher import fetch_event_prices, save_raw as save_poly
from processing.survival_analysis import compute_agility_score
from processing.market_features   import compute_market_features
from processing.indicators        import build_signals_from_event_df
from execution.backtester         import run_backtest
from config import (
    POLY_STRIKE_VAL,
    POLY_DIRECTION,
    POLY_RESAMPLE,
    SMA_WINDOW,
    EMA_WINDOW,
    BB_WINDOW,
    RSI_WINDOW,
    RSI_LOW,
    RSI_HIGH,
)


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

    print("=== 3. Execution (mean-reversion signals) ===")
    # Choose the most liquid strike/direction if configured pair has no data.
    try:
        prices, signals, _ind = build_signals_from_event_df(
            market_df,
            strike_val=POLY_STRIKE_VAL,
            direction=POLY_DIRECTION,
            resample_rule=POLY_RESAMPLE,
            sma_w=SMA_WINDOW,
            ema_w=EMA_WINDOW,
            bb_w=BB_WINDOW,
            rsi_w=RSI_WINDOW,
            rsi_low=RSI_LOW,
            rsi_high=RSI_HIGH,
        )
    except ValueError:
        counts = market_df.groupby(["direction", "strike_val"]).size().sort_values(ascending=False)
        top_dir, top_strike = counts.index[0]
        print(f"[warn] No data for strike={POLY_STRIKE_VAL} dir={POLY_DIRECTION}. "
              f"Falling back to strike={top_strike} dir={top_dir}.")
        prices, signals, _ind = build_signals_from_event_df(
            market_df,
            strike_val=int(top_strike),
            direction=str(top_dir),
            resample_rule=POLY_RESAMPLE,
            sma_w=SMA_WINDOW,
            ema_w=EMA_WINDOW,
            bb_w=BB_WINDOW,
            rsi_w=RSI_WINDOW,
            rsi_low=RSI_LOW,
            rsi_high=RSI_HIGH,
        )

    result = run_backtest(prices, signals)
    print("Backtest metrics:", result["metrics"])


if __name__ == "__main__":
    # Polymarket event slug, e.g. "will-crude-oil-cl-hit-by-end-of-march"
    run_pipeline(event_slug="EXAMPLE_EVENT_SLUG")
