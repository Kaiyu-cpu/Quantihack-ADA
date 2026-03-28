"""
AI Summary Reporter
Computes descriptive statistics from Polymarket price data and GitHub issues,
then calls an LLM to produce a plain-English analyst report.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np
import pandas as pd


# ── Stats helpers ─────────────────────────────────────────────────────────────

def compute_price_stats(df: pd.DataFrame) -> dict:
    """
    Accepts the raw Polymarket CSV DataFrame (with columns:
    event_slug, market_slug, direction, strike, strike_val, timestamp, price).
    Returns a stats dict suitable for LLM summarisation.
    """
    stats: dict = {}

    stats["total_rows"] = int(len(df))
    stats["date_range"] = {
        "start": str(df["timestamp"].min().date()),
        "end":   str(df["timestamp"].max().date()),
    }
    stats["n_strikes"]   = int(df["strike_val"].nunique())
    stats["n_directions"] = int(df["direction"].nunique())

    per_strike = []
    for (direction, strike), grp in df.groupby(["direction", "strike_val"]):
        prices = grp.sort_values("timestamp")["price"]
        returns = prices.pct_change().dropna()
        per_strike.append({
            "direction": direction,
            "strike":    int(strike),
            "n_points":  int(len(prices)),
            "price_min": round(float(prices.min()), 4),
            "price_max": round(float(prices.max()), 4),
            "price_last": round(float(prices.iloc[-1]), 4),
            "volatility_1h": round(float(returns.std()), 4) if len(returns) > 1 else 0.0,
            "momentum_7":    round(float(prices.iloc[-1] - prices.iloc[max(0, len(prices)-7)]), 4),
            "sentiment":     "YES" if float(prices.iloc[-1]) > 0.5 else "NO",
        })

    per_strike.sort(key=lambda x: x["n_points"], reverse=True)
    stats["markets"] = per_strike[:10]  # top-10 by liquidity

    # Overall sentiment
    last_prices = df.groupby(["direction", "strike_val"])["price"].last()
    stats["pct_yes_leaning"] = round(float((last_prices > 0.5).mean() * 100), 1)

    # Volatility regime
    all_vol = []
    for _, grp in df.groupby(["direction", "strike_val"]):
        r = grp.sort_values("timestamp")["price"].pct_change().dropna()
        if len(r) > 1:
            all_vol.append(float(r.std()))
    if all_vol:
        avg_vol = float(np.mean(all_vol))
        stats["avg_volatility"] = round(avg_vol, 4)
        stats["volatility_regime"] = "HIGH" if avg_vol > 0.05 else "MEDIUM" if avg_vol > 0.02 else "LOW"
    else:
        stats["avg_volatility"] = 0.0
        stats["volatility_regime"] = "UNKNOWN"

    return stats


def compute_github_stats(issues_df: pd.DataFrame) -> dict:
    """
    Accepts the GitHub issues DataFrame (columns: number, state, created_at,
    closed_at, duration_days, agility_score, hazard_rate).
    """
    stats: dict = {}
    stats["total_issues"] = int(len(issues_df))
    stats["open_issues"]   = int((issues_df["state"] == "open").sum())
    stats["closed_issues"] = int((issues_df["state"] == "closed").sum())

    closed = issues_df[issues_df["duration_days"].notna()]
    if len(closed):
        stats["median_resolution_days"] = round(float(closed["duration_days"].median()), 1)
        stats["p90_resolution_days"]    = round(float(closed["duration_days"].quantile(0.9)), 1)
    else:
        stats["median_resolution_days"] = None
        stats["p90_resolution_days"]    = None

    if "agility_score" in issues_df.columns:
        stats["agility_score"] = round(float(issues_df["agility_score"].iloc[0]), 6)

    return stats


# ── LLM call ──────────────────────────────────────────────────────────────────

def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return "[openai package not installed — run: pip install openai]"

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[OPENAI_API_KEY not set in environment]"

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a quantitative analyst specialising in prediction markets. "
                    "Write clear, concise, and insightful reports. Use bullet points where appropriate. "
                    "Avoid generic filler — every sentence should add value."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=900,
    )
    return response.choices[0].message.content.strip()


def _build_prompt(price_stats: dict, github_stats: Optional[dict] = None) -> str:
    sections = [
        "You are given the following statistics for a Polymarket crude oil prediction-market event.",
        "",
        "## Price / Market Statistics",
        f"- Date range: {price_stats['date_range']['start']} → {price_stats['date_range']['end']}",
        f"- Total strikes: {price_stats['n_strikes']}",
        f"- Markets leaning YES: {price_stats['pct_yes_leaning']}%",
        f"- Average volatility: {price_stats['avg_volatility']} ({price_stats['volatility_regime']} regime)",
        "",
        "Top markets by data volume:",
    ]
    for m in price_stats["markets"][:5]:
        sections.append(
            f"  • {m['direction'].upper()} ${m['strike']}: last={m['price_last']}, "
            f"vol={m['volatility_1h']}, momentum7={m['momentum_7']}, sentiment={m['sentiment']}"
        )

    if github_stats:
        sections += [
            "",
            "## GitHub Issue Health",
            f"- Total issues: {github_stats['total_issues']} "
            f"(open: {github_stats['open_issues']}, closed: {github_stats['closed_issues']})",
            f"- Median resolution: {github_stats['median_resolution_days']} days",
            f"- P90 resolution: {github_stats['p90_resolution_days']} days",
        ]
        if "agility_score" in github_stats:
            sections.append(f"- Engineering agility score: {github_stats['agility_score']}")

    sections += [
        "",
        "## Your Task",
        "Write a 3-section analyst report:",
        "1. **Market Overview** — summarise the current market condition and sentiment.",
        "2. **Key Risks & Opportunities** — highlight the most important signals.",
        "3. **Recommended Next Steps** — suggest what the trading strategy should focus on.",
        "Be specific and reference the numbers above. Keep it under 400 words.",
    ]
    return "\n".join(sections)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report(
    price_df: pd.DataFrame,
    issues_df: Optional[pd.DataFrame] = None,
    model: str = "gpt-4o-mini",
) -> tuple[str, dict]:
    """
    Main entry point.

    Parameters
    ----------
    price_df   : raw Polymarket CSV DataFrame (must have strike_val column)
    issues_df  : optional GitHub issues DataFrame
    model      : OpenAI model name

    Returns
    -------
    (report_text, stats_dict)
    """
    if "strike_val" not in price_df.columns:
        price_df = price_df.copy()
        price_df["strike_val"] = (
            price_df["strike"].str.replace("$", "", regex=False).astype(int)
        )

    price_stats  = compute_price_stats(price_df)
    github_stats = compute_github_stats(issues_df) if issues_df is not None else None
    prompt       = _build_prompt(price_stats, github_stats)
    report       = _call_openai(prompt, model=model)

    combined_stats = {"price": price_stats}
    if github_stats:
        combined_stats["github"] = github_stats

    return report, combined_stats
