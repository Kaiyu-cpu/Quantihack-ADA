"""
Backtesting Engine (ported from algo-backtest)
Simulates trade-by-trade P&L with position sizing and optional stops.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass

from config import (
    INITIAL_CAPITAL,
    RISK_PER_TRADE_PCT,
    COMMISSION_PCT,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    BACKTEST_PERIODS_PER_YEAR,
)


@dataclass
class Position:
    entry_price: float
    shares: float
    stop_loss_pct: float | None
    take_profit_pct: float | None

    def current_value(self, price: float) -> float:
        return self.shares * price

    def should_stop_loss(self, price: float) -> bool:
        if self.stop_loss_pct is None:
            return False
        return price <= self.entry_price * (1 - self.stop_loss_pct / 100)

    def should_take_profit(self, price: float) -> bool:
        if self.take_profit_pct is None:
            return False
        return price >= self.entry_price * (1 + self.take_profit_pct / 100)


def run_backtest(prices: pd.Series, signals: pd.Series) -> dict:
    """
    prices:  Polymarket price series (probabilities) indexed by timestamp
    signals: {1, -1, 0} aligned with prices
    Returns: dict with metrics + equity curve + trades
    """
    df = pd.DataFrame({"close": prices, "signal": signals}).dropna()
    df = df.sort_index()
    # Avoid lookahead: act on the prior bar's signal
    df["signal_prev"] = df["signal"].shift(1).fillna(0)

    capital = INITIAL_CAPITAL
    position = None
    current_trade = None
    trades = []
    equity_curve = []

    for date, row in df.iterrows():
        price = row["close"]
        signal = row["signal_prev"]

        if position and current_trade:
            exit_reason = None
            if position.should_stop_loss(price):
                exit_reason = "stop_loss"
            elif position.should_take_profit(price):
                exit_reason = "take_profit"
            elif signal == -1:
                exit_reason = "signal"

            if exit_reason:
                proceeds = position.current_value(price)
                commission = proceeds * (COMMISSION_PCT / 100)
                capital += proceeds - commission
                current_trade["exit_date"] = str(date)
                current_trade["exit_price"] = round(price, 6)
                current_trade["pnl"] = round(proceeds - (position.entry_price * position.shares), 6)
                current_trade["reason"] = exit_reason
                trades.append(current_trade)
                position = None
                current_trade = None

        if signal == 1 and position is None:
            amount_to_invest = capital * (RISK_PER_TRADE_PCT / 100)
            commission = amount_to_invest * (COMMISSION_PCT / 100)
            amount_after_commission = amount_to_invest - commission
            shares = amount_after_commission / price
            capital -= amount_to_invest
            position = Position(price, shares, STOP_LOSS_PCT, TAKE_PROFIT_PCT)
            current_trade = {
                "entry_date": str(date),
                "entry_price": round(price, 6),
                "shares": round(shares, 6),
            }

        portfolio_value = capital + (position.current_value(price) if position else 0)
        equity_curve.append({"date": str(date), "value": round(portfolio_value, 6)})

    metrics = _calculate_metrics(equity_curve, INITIAL_CAPITAL, BACKTEST_PERIODS_PER_YEAR)
    # Buy & hold benchmark over the same period
    if len(df) >= 2:
        bh = (df["close"].iloc[-1] / df["close"].iloc[0]) - 1
        metrics["buy_hold_return_pct"] = round(bh * 100, 2)
    else:
        metrics["buy_hold_return_pct"] = 0.0
    metrics["n_trades"] = len(trades)
    return {"metrics": metrics, "equity_curve": equity_curve, "trades": trades, "final_capital": round(capital, 2)}


def _calculate_metrics(equity_curve: list, initial_capital: float, periods_per_year: int) -> dict:
    values = pd.Series([e["value"] for e in equity_curve])
    total_return = (values.iloc[-1] - initial_capital) / initial_capital * 100

    daily_returns = values.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(periods_per_year) if daily_returns.std() != 0 else 0

    rolling_max = values.cummax()
    drawdown = (values - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    return {
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "final_value": round(values.iloc[-1], 2),
    }


if __name__ == "__main__":
    np.random.seed(42)
    prices = pd.Series(100 * (1 + np.random.randn(500) * 0.01).cumprod())
    signals = pd.Series(np.random.choice([-1, 0, 1], 500))
    result = run_backtest(prices, signals)
    print(result["metrics"])
