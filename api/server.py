"""
FastAPI backend for the React frontend.
Exposes fetch, EDA, signal, backtest, and AI summary endpoints.

Run with:
    uvicorn api.server:app --reload --port 8000
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from ingestion.polymarket_fetcher import fetch_event_prices, save_raw as save_poly
from ingestion.news_fetcher import fetch_news, save_raw as save_news, TOPIC_DEFAULTS as NEWS_DEFAULTS
from ingestion.reddit_fetcher import fetch_posts, save_raw as save_reddit, TOPIC_DEFAULTS as REDDIT_DEFAULTS
from ingestion.github_fetcher import fetch_issues, save_raw as save_issues
from processing.indicators import build_signals_from_event_df
from processing.true_price_signal import compute_true_price_series, zscore_signal
from processing.price_align import align_to_index, shift_signals
from execution.backtester import run_backtest
from config import DATA_RAW_DIR, FUTURES_CSV_PATH

app = FastAPI(title="QuantiHack ADA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class FetchRequest(BaseModel):
    topic: str = "oil"
    event_slug: Optional[str] = None
    fast: bool = False


class SignalRequest(BaseModel):
    strike_val: int
    direction: str = "up"
    resample_rule: str = "1h"
    rsi_low: float = 45
    rsi_high: float = 55
    rsi_window: int = 14
    sma_window: int = 12
    ema_window: int = 12
    bb_window: int = 20
    signal_type: str = "rsi"


class BacktestRequest(SignalRequest):
    trade_on: str = "polymarket"  # or "futures"


def _load_polymarket_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Missing Polymarket CSV: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["strike_val"] = df["strike"].str.replace("$", "", regex=False).astype(int)
    return df


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "openai_configured": bool(
            config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here"
        ),
        "model": config.OPENAI_MODEL,
    }


@app.post("/fetch/polymarket")
def fetch_polymarket(req: FetchRequest):
    slug = req.event_slug or "will-crude-oil-cl-hit-by-end-of-march"
    df = fetch_event_prices(slug)
    save_poly(df, f"{slug}_prices")
    return {"rows": len(df), "slug": slug}


@app.post("/fetch/news")
def fetch_news_endpoint(req: FetchRequest):
    cfg = NEWS_DEFAULTS.get(req.topic)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown topic")
    rows = fetch_news(cfg["tickers"], topic=req.topic, start_date=cfg["start_date"])
    save_news(rows, topic=req.topic)
    return {"rows": len(rows), "topic": req.topic}


@app.post("/fetch/reddit")
def fetch_reddit_endpoint(req: FetchRequest):
    cfg = REDDIT_DEFAULTS.get(req.topic)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown topic")
    subreddits = cfg["subreddits"]
    keywords = cfg["keywords"]
    if req.fast:
        subreddits = subreddits[:2]
        keywords = keywords[:2]
        post_limit = 25
        time_filter = "week"
    else:
        post_limit = 100
        time_filter = "month"
    rows = fetch_posts(
        subreddits, keywords, topic=req.topic,
        start_date=cfg["start_date"],
        post_limit=post_limit, time_filter=time_filter,
    )
    save_reddit(rows, topic=req.topic)
    return {"rows": len(rows), "topic": req.topic}


@app.post("/fetch/github")
def fetch_github_endpoint():
    try:
        df = fetch_issues()
        save_issues(df)
        return {"rows": len(df)}
    except Exception as exc:
        return {"rows": 0, "error": str(exc), "repo": config.GITHUB_REPO}


@app.get("/eda/polymarket")
def eda_polymarket():
    path = os.path.join(DATA_RAW_DIR, "polymarket", "crude_oil_prices.csv")
    df = _load_polymarket_csv(path)
    counts = df.groupby(["direction", "strike_val"]).size().sort_values(ascending=False)
    top_dir, top_strike = counts.index[0]
    return {
        "rows": len(df),
        "strikes": int(df["strike_val"].nunique()),
        "range_start": str(df["timestamp"].min().date()),
        "range_end": str(df["timestamp"].max().date()),
        "top_strike": int(top_strike),
        "top_direction": str(top_dir),
    }


@app.post("/signals/preview")
def signals_preview(req: SignalRequest):
    path = os.path.join(DATA_RAW_DIR, "polymarket", "crude_oil_prices.csv")
    df = _load_polymarket_csv(path)
    if req.signal_type == "true_price":
        times = df["timestamp"].drop_duplicates().sort_values()
        true_price = compute_true_price_series(df, pd.DatetimeIndex(times))
        signals = zscore_signal(true_price)
        prices = true_price
    else:
        prices, signals, _ind = build_signals_from_event_df(
            df,
            strike_val=req.strike_val,
            direction=req.direction,
            resample_rule=req.resample_rule,
            sma_w=req.sma_window,
            ema_w=req.ema_window,
            bb_w=req.bb_window,
            rsi_w=req.rsi_window,
            rsi_low=req.rsi_low,
            rsi_high=req.rsi_high,
        )
    return {
        "signal_counts": signals.value_counts().to_dict(),
        "last_signal": int(signals.iloc[-1]) if len(signals) else 0,
        "last_price": float(prices.iloc[-1]) if len(prices) else 0.0,
    }


@app.post("/signals/suggest")
def signals_suggest(req: SignalRequest):
    return {"rsi_low": 45, "rsi_high": 55, "note": "Baseline RSI thresholds"}


@app.post("/backtest")
def backtest_api(req: BacktestRequest):
    path = os.path.join(DATA_RAW_DIR, "polymarket", "crude_oil_prices.csv")
    df = _load_polymarket_csv(path)
    prices, signals, _ind = build_signals_from_event_df(
        df,
        strike_val=req.strike_val,
        direction=req.direction,
        resample_rule=req.resample_rule,
        sma_w=req.sma_window,
        ema_w=req.ema_window,
        bb_w=req.bb_window,
        rsi_w=req.rsi_window,
        rsi_low=req.rsi_low,
        rsi_high=req.rsi_high,
    )

    trade_prices = prices
    if req.trade_on == "futures":
        if not os.path.exists(FUTURES_CSV_PATH):
            raise HTTPException(status_code=404, detail="Missing futures CSV")
        fut = pd.read_csv(FUTURES_CSV_PATH, parse_dates=["timestamp"])
        fut["timestamp"] = pd.to_datetime(fut["timestamp"], utc=True)
        fut_series = fut.set_index("timestamp")["close"]
        trade_prices = align_to_index(fut_series, prices.index)

    result = run_backtest(trade_prices, signals)
    return result


@app.get("/summary")
def summary_static():
    return {
        "summary": (
            "Polymarket prices react quickly to narrative shifts. Using RSI mean-reversion "
            "signals and applying them to futures prices provides a timing overlay that can "
            "outperform buy-and-hold in short windows. News and Reddit volume can be layered "
            "as lead/lag filters for additional edge."
        )
    }


# ── AI Summary endpoints ──────────────────────────────────────────────────────

@app.get("/api/news", response_model=list[NewsItem])
def get_news_live(
    topic: str = Query("oil", description="Topic: oil | crypto | gold"),
    limit: int = Query(20, ge=1, le=100),
):
    """Fetch latest news headlines via yfinance for the given topic."""
    cfg = NEWS_DEFAULTS.get(topic)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{topic}'. Available: {list(NEWS_DEFAULTS)}",
        )
    try:
        rows = fetch_news(cfg["tickers"], topic=topic, start_date=None)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"News fetch failed: {exc}")
    return rows[:limit]


@app.get("/api/reddit", response_model=list[RedditItem])
def get_reddit_live(
    topic: str = Query("oil", description="Topic: oil | crypto | gold"),
    limit: int = Query(20, ge=1, le=100),
):
    """Fetch recent Reddit posts for the given topic."""
    cfg = REDDIT_DEFAULTS.get(topic)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{topic}'. Available: {list(REDDIT_DEFAULTS)}",
        )
    try:
        rows = fetch_posts(
            cfg["subreddits"], cfg["keywords"],
            topic=topic, start_date=None,
            sort="new", time_filter="week", post_limit=25,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reddit fetch failed: {exc}")
    return rows[:limit]


@app.post("/api/summary", response_model=AISummaryResponse)
def generate_ai_summary(req: AISummaryRequest):
    """
    Generate an AI analysis of news + Reddit data using OpenAI.
    Requires OPENAI_API_KEY in .env.
    """
    api_key = config.OPENAI_API_KEY
    if not api_key or api_key == "your_openai_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Please add it to your .env file.",
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(status_code=503, detail="openai package not installed. Run: pip install openai")

    model = req.model or config.OPENAI_MODEL or "gpt-4o-mini"
    topic_label = req.topic.upper()

    news_lines = []
    for i, n in enumerate(req.news[:30], 1):
        title   = n.get("title", "").strip()
        summary = n.get("summary", "").strip()
        source  = n.get("source", "")
        pub     = n.get("published_utc", "")[:10]
        line = f"{i}. [{pub}] {title}"
        if summary:
            line += f" — {summary[:120]}"
        if source:
            line += f" ({source})"
        news_lines.append(line)

    reddit_lines = []
    for i, r in enumerate(req.reddit[:30], 1):
        title    = r.get("title", "").strip()
        selftext = r.get("selftext", "").strip()
        sub      = r.get("subreddit", "")
        score    = r.get("score", 0)
        comments = r.get("num_comments", 0)
        pub      = r.get("published_utc", "")[:10]
        line = f"{i}. [r/{sub} | {pub} | ↑{score} 💬{comments}] {title}"
        if selftext:
            line += f"\n   {selftext[:150]}"
        reddit_lines.append(line)

    news_block   = "\n".join(news_lines)   if news_lines   else "No news data provided."
    reddit_block = "\n".join(reddit_lines) if reddit_lines else "No Reddit data provided."

    system_prompt = (
        "You are an expert quantitative finance analyst specializing in alternative data. "
        "Your job is to synthesize news and social media signals into actionable market intelligence. "
        "Be concise, data-driven, and highlight what actually matters for trading decisions."
    )

    user_prompt = f"""Analyze the following alternative data for {topic_label} markets.

## NEWS HEADLINES ({len(req.news)} articles)
{news_block}

## REDDIT POSTS ({len(req.reddit)} posts)
{reddit_block}

---

Provide a structured analysis with these exact sections:

### 📊 Overall Sentiment
State Bullish / Bearish / Neutral with a confidence level (e.g. 72% Bullish). Explain in 2-3 sentences.

### 🔑 Key Themes
List the top 3-5 recurring themes across both news and Reddit. One line each.

### 📰 Notable News Signals
Highlight 2-3 specific news items that could have the most market impact and why.

### 💬 Reddit Sentiment Signals
Summarize retail investor mood. Note any unusual activity, high-engagement posts, or sentiment divergence from news.

### 📈 Trading Implications
Give 2-3 concrete, actionable insights for trading {topic_label}. What does this alternative data suggest about positioning?

### ⚠️ Key Risks
List 2-3 risks or uncertainties the data reveals.

### 🔮 Lead/Lag Assessment
Does any source appear to be leading or lagging? Are there early-mover signals?

Keep each section tight and actionable. No filler."""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        summary_text = response.choices[0].message.content.strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc}")

    return AISummaryResponse(
        summary=summary_text,
        model=model,
        news_count=len(req.news),
        reddit_count=len(req.reddit),
    )
