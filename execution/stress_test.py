"""
Stress Testing Engine
Two modes:
  A) Monte Carlo  — simulate N synthetic price paths from historical vol/drift,
                    run backtester on each, report P5/P50/P95 distribution.
  B) LLM Scenarios — ask an LLM to define stress scenarios in plain English,
                     apply them as price-path perturbations, re-run backtest.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from execution.backtester import run_backtest
from config import INITIAL_CAPITAL


# ── Monte Carlo ───────────────────────────────────────────────────────────────

def run_monte_carlo(
    prices: pd.Series,
    signals_fn,
    n_paths: int = 200,
    seed: int = 42,
    progress_callback=None,
) -> pd.DataFrame:
    """
    Generate `n_paths` synthetic price paths using geometric Brownian motion
    calibrated on `prices`, run the backtest on each, return a results DataFrame.

    Parameters
    ----------
    prices       : historical price Series (probabilities 0-1)
    signals_fn   : callable(prices_series) -> signals Series
    n_paths      : number of Monte Carlo paths
    seed         : random seed
    progress_callback : optional callable(i, n_paths)

    Returns
    -------
    DataFrame with columns: path, sharpe, total_return_pct, max_drawdown_pct, final_value, n_trades
    """
    rng = np.random.default_rng(seed)
    returns = prices.pct_change().dropna()
    mu  = float(returns.mean())
    sig = float(returns.std())
    T   = len(prices)
    p0  = float(prices.iloc[0])

    records = []
    for i in range(n_paths):
        shocks = rng.normal(mu, sig, T - 1)
        path   = np.empty(T)
        path[0] = p0
        for t in range(1, T):
            path[t] = path[t - 1] * (1 + shocks[t - 1])
        # Clamp to (0, 1] — Polymarket prices are probabilities
        path = np.clip(path, 1e-4, 1.0)

        sim_prices = pd.Series(path, index=prices.index)
        try:
            sigs = signals_fn(sim_prices)
            res  = run_backtest(sim_prices, sigs)
            m    = res["metrics"]
            records.append({
                "path":             i,
                "sharpe":           m["sharpe_ratio"],
                "total_return_pct": m["total_return_pct"],
                "max_drawdown_pct": m["max_drawdown_pct"],
                "final_value":      m["final_value"],
                "n_trades":         m["n_trades"],
            })
        except Exception:
            pass

        if progress_callback:
            progress_callback(i + 1, n_paths)

    return pd.DataFrame(records)


def summarise_monte_carlo(mc_df: pd.DataFrame) -> dict:
    """Return P5 / P50 / P95 summary stats from Monte Carlo results."""
    summary = {}
    for col in ["sharpe", "total_return_pct", "max_drawdown_pct", "final_value"]:
        summary[col] = {
            "p5":    round(float(mc_df[col].quantile(0.05)), 3),
            "p50":   round(float(mc_df[col].median()), 3),
            "p95":   round(float(mc_df[col].quantile(0.95)), 3),
            "mean":  round(float(mc_df[col].mean()), 3),
        }
    summary["pct_profitable"] = round(float((mc_df["total_return_pct"] > 0).mean() * 100), 1)
    summary["n_paths"] = len(mc_df)
    return summary


# ── LLM Scenario Stress ───────────────────────────────────────────────────────

_DEFAULT_SCENARIOS = [
    {
        "name": "Flash Crash",
        "description": "Price drops 35% in the first 5 candles then slowly recovers over 20 candles.",
        "perturbation": {"type": "crash", "drop_pct": 35, "crash_candles": 5, "recovery_candles": 20},
    },
    {
        "name": "Sustained Sell-off",
        "description": "Price drifts down 20% over the entire period with high volatility.",
        "perturbation": {"type": "drift", "drift_pct": -20, "vol_mult": 2.5},
    },
    {
        "name": "Low Liquidity Chop",
        "description": "Price oscillates ±5% every few candles with no clear trend.",
        "perturbation": {"type": "chop", "range_pct": 5, "period": 4},
    },
    {
        "name": "Slow Melt-Up",
        "description": "Price gradually rises 25% over the period with low volatility.",
        "perturbation": {"type": "drift", "drift_pct": 25, "vol_mult": 0.5},
    },
    {
        "name": "Black Swan Spike",
        "description": "Price jumps 40% in one candle then immediately reverts.",
        "perturbation": {"type": "spike", "spike_pct": 40, "spike_candle": 10},
    },
]


def _fetch_llm_scenarios() -> list[dict]:
    """Ask the LLM to define stress scenarios. Falls back to defaults on error."""
    try:
        from openai import OpenAI
    except ImportError:
        return _DEFAULT_SCENARIOS

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _DEFAULT_SCENARIOS

    client = OpenAI(api_key=api_key)
    prompt = """You are a market risk analyst. Define 5 distinct stress scenarios for
a Polymarket crude oil prediction-market price series (probabilities between 0 and 1).

Return a JSON array of exactly 5 objects with keys:
  name        (string, <=30 chars)
  description (string, 1 sentence)
  perturbation (object with "type" being one of: crash, drift, chop, spike)
    - crash:  drop_pct (int), crash_candles (int 1-10), recovery_candles (int 10-50)
    - drift:  drift_pct (int, negative=down), vol_mult (float)
    - chop:   range_pct (int), period (int 2-10)
    - spike:  spike_pct (int), spike_candle (int 1-50)

Only return valid JSON, no markdown, no extra text."""

    try:
        import json
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a quantitative risk analyst. Return only valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.5,
            max_tokens=600,
        )
        text = response.choices[0].message.content.strip()
        scenarios = json.loads(text)
        if isinstance(scenarios, list) and len(scenarios) == 5:
            return scenarios
    except Exception:
        pass
    return _DEFAULT_SCENARIOS


def _apply_perturbation(prices: pd.Series, perturb: dict) -> pd.Series:
    """Apply a named perturbation to a price series."""
    p = prices.values.copy().astype(float)
    T = len(p)
    kind = perturb.get("type", "drift")

    if kind == "crash":
        drop      = perturb.get("drop_pct", 30) / 100
        crash_n   = min(int(perturb.get("crash_candles", 5)), T // 4)
        recover_n = min(int(perturb.get("recovery_candles", 20)), T // 2)
        bottom    = p[0] * (1 - drop)
        step_down = (p[0] - bottom) / max(crash_n, 1)
        for i in range(min(crash_n, T)):
            p[i] = max(p[0] - step_down * (i + 1), 1e-4)
        if crash_n < T:
            step_up = (p[0] - p[crash_n - 1]) / max(recover_n, 1)
            for i in range(crash_n, min(crash_n + recover_n, T)):
                p[i] = min(p[i - 1] + step_up, 1.0)

    elif kind == "drift":
        drift   = perturb.get("drift_pct", -10) / 100
        vol_mul = perturb.get("vol_mult", 1.0)
        rng     = np.random.default_rng(0)
        baseline_vol = float(pd.Series(p).pct_change().dropna().std())
        for i in range(1, T):
            noise = rng.normal(0, baseline_vol * vol_mul)
            p[i]  = np.clip(p[i - 1] * (1 + drift / T + noise), 1e-4, 1.0)

    elif kind == "chop":
        rng_pct = perturb.get("range_pct", 5) / 100
        period  = max(int(perturb.get("period", 4)), 2)
        for i in range(T):
            direction = 1 if (i // period) % 2 == 0 else -1
            p[i] = np.clip(p[i] * (1 + direction * rng_pct * 0.5), 1e-4, 1.0)

    elif kind == "spike":
        spike_pct    = perturb.get("spike_pct", 40) / 100
        spike_candle = min(int(perturb.get("spike_candle", 10)), T - 2)
        p[spike_candle] = np.clip(p[spike_candle] * (1 + spike_pct), 1e-4, 1.0)
        if spike_candle + 1 < T:
            p[spike_candle + 1] = p[spike_candle - 1]

    return pd.Series(np.clip(p, 1e-4, 1.0), index=prices.index)


def run_scenario_stress(
    prices: pd.Series,
    signals_fn,
    use_llm: bool = True,
) -> pd.DataFrame:
    """
    Run the backtester under each stress scenario.

    Parameters
    ----------
    prices      : baseline price Series
    signals_fn  : callable(prices_series) -> signals Series
    use_llm     : if True, fetch scenarios from LLM; else use defaults

    Returns
    -------
    DataFrame with columns: scenario, sharpe, total_return_pct, max_drawdown_pct,
                             final_value, n_trades, description
    """
    scenarios = _fetch_llm_scenarios() if use_llm else _DEFAULT_SCENARIOS
    records   = []

    for sc in scenarios:
        perturb = sc.get("perturbation", {"type": "drift", "drift_pct": 0, "vol_mult": 1})
        try:
            stressed = _apply_perturbation(prices.copy(), perturb)
            sigs     = signals_fn(stressed)
            res      = run_backtest(stressed, sigs)
            m        = res["metrics"]
            records.append({
                "scenario":         sc.get("name", "Unknown"),
                "description":      sc.get("description", ""),
                "sharpe":           m["sharpe_ratio"],
                "total_return_pct": m["total_return_pct"],
                "max_drawdown_pct": m["max_drawdown_pct"],
                "final_value":      m["final_value"],
                "n_trades":         m["n_trades"],
            })
        except Exception as e:
            records.append({
                "scenario":         sc.get("name", "Unknown"),
                "description":      sc.get("description", ""),
                "sharpe": None, "total_return_pct": None,
                "max_drawdown_pct": None, "final_value": None, "n_trades": None,
            })

    return pd.DataFrame(records)
