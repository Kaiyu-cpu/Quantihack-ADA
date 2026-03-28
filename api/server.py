"""
FastAPI backend for the React frontend.
Exposes fetch, EDA, signal, backtest, and summary endpoints.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing modules that read config
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion.polymarket_fetcher import fetch_event_prices, save_raw as save_poly
from ingestion.news_fetcher import fetch_news, save_raw as save_news, TOPIC_DEFAULTS as NEWS_DEFAULTS
from ingestion.reddit_fetcher import fetch_posts, save_raw as save_reddit, TOPIC_DEFAULTS as REDDIT_DEFAULTS
from ingestion.github_fetcher import fetch_issues, save_raw as save_issues
from processing.indicators import build_signals_from_event_df
from processing.price_align import align_to_index
from execution.backtester import run_backtest
from config import DATA_RAW_DIR, FUTURES_CSV_PATH

app = FastAPI(title="QuantiHack ADA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class BacktestRequest(SignalRequest):
    trade_on: str = "polymarket"  # or "futures"


def _load_polymarket_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Missing Polymarket CSV: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["strike_val"] = df["strike"].str.replace("$", "", regex=False).astype(int)
    return df


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/fetch/polymarket")
def fetch_polymarket(req: FetchRequest):
    slug = req.event_slug or "will-crude-oil-cl-hit-by-end-of-march"
    df = fetch_event_prices(slug)
    save_poly(df, f"{slug}_prices")
    return {"rows": len(df), "slug": slug}


@app.post("/fetch/news")
def fetch_news_api(req: FetchRequest):
    cfg = NEWS_DEFAULTS.get(req.topic, None)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown topic")
    rows = fetch_news(cfg["tickers"], topic=req.topic, start_date=cfg["start_date"])
    save_news(rows, topic=req.topic)
    return {"rows": len(rows), "topic": req.topic}


@app.post("/fetch/reddit")
def fetch_reddit_api(req: FetchRequest):
    cfg = REDDIT_DEFAULTS.get(req.topic, None)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown topic")
    subreddits = cfg["subreddits"]
    keywords = cfg["keywords"]
    # Fast mode: reduce workload for UI responsiveness
    if req.fast:
        subreddits = subreddits[:2]
        keywords = keywords[:2]
        post_limit = 25
        time_filter = "week"
    else:
        post_limit = 100
        time_filter = "month"
    rows = fetch_posts(
        subreddits,
        keywords,
        topic=req.topic,
        start_date=cfg["start_date"],
        post_limit=post_limit,
        time_filter=time_filter,
    )
    save_reddit(rows, topic=req.topic)
    return {"rows": len(rows), "topic": req.topic}


@app.post("/fetch/github")
def fetch_github_api():
    try:
        df = fetch_issues()
        save_issues(df)
        return {"rows": len(df)}
    except Exception as exc:
        from config import GITHUB_REPO
        return {"rows": 0, "error": str(exc), "repo": GITHUB_REPO}


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
    """
    Simple heuristic: aim for balanced signal counts by nudging RSI thresholds.
    """
    # Default suggestion for now; can be improved with grid search.
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
def summary():
    return {
        "summary": (
            "Polymarket prices react quickly to narrative shifts. Using RSI mean-reversion "
            "signals and applying them to futures prices provides a timing overlay that can "
            "outperform buy-and-hold in short windows. News and Reddit volume can be layered "
            "as lead/lag filters for additional edge."
        )
    }
