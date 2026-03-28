"""
Bayesian Parameter Optimiser (Optuna) + LLM Post-Run Narrative
Wraps run_backtest() as an Optuna objective and maximises Sharpe ratio.
After the search, an optional LLM call interprets the best result.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from execution.backtester import _calculate_metrics
from config import (
    INITIAL_CAPITAL,
    BACKTEST_PERIODS_PER_YEAR,
    COMMISSION_PCT,
)


# ── Core backtest for optimiser (params passed explicitly, not from config) ───

def _backtest_with_params(
    prices: pd.Series,
    signals: pd.Series,
    risk_pct: float,
    commission_pct: float,
    stop_loss_pct: Optional[float],
    take_profit_pct: Optional[float],
) -> dict:
    """Lightweight backtest that accepts params directly (no global config)."""
    from dataclasses import dataclass

    @dataclass
    class _Pos:
        entry_price: float
        shares: float
        sl: Optional[float]
        tp: Optional[float]

        def val(self, p): return self.shares * p
        def stop(self, p): return self.sl and p <= self.entry_price * (1 - self.sl / 100)
        def take(self, p): return self.tp and p >= self.entry_price * (1 + self.tp / 100)

    df = pd.DataFrame({"close": prices, "signal": signals}).dropna()
    capital = float(INITIAL_CAPITAL)
    pos = None
    equity = []

    for _, row in df.iterrows():
        price, signal = row["close"], row["signal"]
        if pos:
            if pos.stop(price) or pos.take(price) or signal == -1:
                proceeds = pos.val(price)
                capital += proceeds - proceeds * (commission_pct / 100)
                pos = None
        if signal == 1 and pos is None:
            invest = capital * (risk_pct / 100)
            capital -= invest
            pos = _Pos(price, (invest * (1 - commission_pct / 100)) / price, stop_loss_pct, take_profit_pct)
        equity.append(capital + (pos.val(price) if pos else 0))

    values = pd.Series(equity)
    if len(values) < 2:
        return {"sharpe_ratio": 0.0, "max_drawdown_pct": 0.0, "total_return_pct": 0.0, "final_value": float(INITIAL_CAPITAL)}
    return _calculate_metrics([{"value": v} for v in values], INITIAL_CAPITAL, BACKTEST_PERIODS_PER_YEAR)


# ── Optuna objective ──────────────────────────────────────────────────────────

def run_optimisation(
    prices: pd.Series,
    signals_fn,
    n_trials: int = 100,
    rsi_low_range: tuple = (20, 50),
    rsi_high_range: tuple = (50, 80),
    risk_pct_range: tuple = (0.5, 5.0),
    stop_loss_range: tuple = (1.0, 10.0),
    take_profit_range: tuple = (1.0, 15.0),
    progress_callback=None,
) -> tuple[dict, pd.DataFrame]:
    """
    Bayesian search over signal thresholds and backtest parameters.

    Parameters
    ----------
    prices        : price Series
    signals_fn    : callable(rsi_low, rsi_high) -> signals Series
    n_trials      : number of Optuna trials
    *_range       : (min, max) search bounds for each parameter
    progress_callback : optional callable(trial_num, n_trials, best_so_far)

    Returns
    -------
    (best_params_dict, all_trials_DataFrame)
    """
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        raise ImportError("optuna not installed — run: pip install optuna")

    records = []

    def objective(trial: "optuna.Trial") -> float:
        rsi_low       = trial.suggest_float("rsi_low",        *rsi_low_range)
        rsi_high      = trial.suggest_float("rsi_high",       *rsi_high_range)
        risk_pct      = trial.suggest_float("risk_pct",       *risk_pct_range)
        stop_loss     = trial.suggest_float("stop_loss_pct",  *stop_loss_range)
        take_profit   = trial.suggest_float("take_profit_pct",*take_profit_range)
        commission    = trial.suggest_float("commission_pct", 0.05, 0.3)

        if rsi_low >= rsi_high:
            return -999.0

        try:
            sigs = signals_fn(rsi_low=rsi_low, rsi_high=rsi_high)
            if sigs.sum() == 0:
                return -999.0
            m = _backtest_with_params(prices, sigs, risk_pct, commission, stop_loss, take_profit)
        except Exception:
            return -999.0

        sharpe = m["sharpe_ratio"]
        records.append({
            "trial":            trial.number,
            "rsi_low":          round(rsi_low, 2),
            "rsi_high":         round(rsi_high, 2),
            "risk_pct":         round(risk_pct, 2),
            "stop_loss_pct":    round(stop_loss, 2),
            "take_profit_pct":  round(take_profit, 2),
            "commission_pct":   round(commission, 3),
            "sharpe":           round(sharpe, 3),
            "total_return_pct": round(m["total_return_pct"], 2),
            "max_drawdown_pct": round(m["max_drawdown_pct"], 2),
            "final_value":      round(m["final_value"], 2),
        })

        if progress_callback:
            best = max(r["sharpe"] for r in records)
            progress_callback(trial.number + 1, n_trials, best)

        return float(sharpe)

    study = optuna.create_study(direction="maximize",
                                 sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_params
    best["sharpe"]           = round(study.best_value, 3)
    best["total_return_pct"] = next(
        (r["total_return_pct"] for r in records if r["trial"] == study.best_trial.number), None
    )
    best["max_drawdown_pct"] = next(
        (r["max_drawdown_pct"] for r in records if r["trial"] == study.best_trial.number), None
    )

    trials_df = pd.DataFrame(records).sort_values("sharpe", ascending=False).reset_index(drop=True)
    return best, trials_df


# ── LLM narrative ─────────────────────────────────────────────────────────────

def llm_interpret_results(best_params: dict, trials_df: pd.DataFrame) -> str:
    """
    Sends the top-5 trial results to an LLM and asks for a strategy narrative.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return "[openai package not installed — run: pip install openai]"

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[OPENAI_API_KEY not set in environment]"

    top5 = trials_df.head(5).to_dict(orient="records")

    prompt = f"""You are a quantitative trading strategist.

I ran a Bayesian optimisation over {len(trials_df)} backtests of a mean-reversion strategy
on Polymarket crude oil prediction-market prices.

**Best parameters found:**
{best_params}

**Top 5 configurations by Sharpe ratio:**
{top5}

Please provide:
1. **What worked** — which parameter ranges drove the best Sharpe ratios and why.
2. **Risk assessment** — comment on the drawdowns and whether the best Sharpe is robust.
3. **Next steps** — what would you change or test next to improve the strategy?

Be concise, specific, and quantitative. Max 350 words."""

    client   = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise quantitative trading analyst."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()
