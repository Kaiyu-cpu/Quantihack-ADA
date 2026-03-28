"""
Backtesting Engine
Simulates strategy P&L and computes Sharpe ratio, max drawdown, and other stats.
"""
import pandas as pd
import numpy as np
from config import INITIAL_CAPITAL, TRANSACTION_COST


def run_backtest(prices: pd.Series, signals: pd.Series) -> dict:
    """
    prices:  asset price series (indexed by date)
    signals: {1, -1, 0} position signals aligned with prices
    Returns: dict of performance metrics + equity curve DataFrame
    """
    df = pd.DataFrame({"price": prices, "signal": signals}).dropna()
    df["position"] = df["signal"].shift(1).fillna(0)   # trade next bar
    df["returns"]  = df["price"].pct_change().fillna(0)
    df["strategy"] = df["position"] * df["returns"] - abs(df["position"].diff().fillna(0)) * TRANSACTION_COST

    df["equity"] = INITIAL_CAPITAL * (1 + df["strategy"]).cumprod()

    metrics = {
        "sharpe_ratio":  _sharpe(df["strategy"]),
        "max_drawdown":  _max_drawdown(df["equity"]),
        "total_return":  df["equity"].iloc[-1] / INITIAL_CAPITAL - 1,
        "n_trades":      int((df["position"].diff() != 0).sum()),
    }
    return {"metrics": metrics, "equity_curve": df}


def _sharpe(returns: pd.Series, periods: int = 252) -> float:
    excess = returns.mean() * periods
    vol    = returns.std() * np.sqrt(periods)
    return excess / vol if vol != 0 else 0.0


def _max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    return float(drawdown.min())


if __name__ == "__main__":
    np.random.seed(42)
    prices  = pd.Series(100 * (1 + np.random.randn(500) * 0.01).cumprod())
    signals = pd.Series(np.random.choice([-1, 0, 1], 500))
    result  = run_backtest(prices, signals)
    print(result["metrics"])
