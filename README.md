# Quantihack-ADA

> **Quantihack 2026 — Team ADA**
> Theme: **Alternative Data Alpha**

## TL;DR

We treat **Polymarket prediction-market prices** as real-time alternative data, reconstruct the crowd-implied **True Price** of WTI Crude Oil, and prove it **leads NYMEX CL futures by ~2 hours** — then backtest a trading strategy that exploits the lead. The entire workflow lives inside a full-stack product with a **React dashboard**, a **Streamlit analytics console**, and an **AI-powered market assistant**.

---

## Why Polymarket Is Alternative Data

Traditional quant pipelines consume price feeds, filings, and order-book data. Polymarket binary options (Will crude oil hit $X by end of March?) encode **discrete crowd probability assessments** across 21 strike buckets — a structure that does not exist in any conventional data source.

We do not just read prediction market prices. We **reverse-engineer** them into a continuous probability distribution, derive a model-free Expected Value, and use the spread vs futures as an alpha signal.

---

## Core Research Pipeline

### 1. Data Ingestion — 4 Alternative Sources

| Source | What We Collect | Volume |
|--------|----------------|--------|
| **Polymarket** CLOB API | YES-token prices for 21 strike x 2 directions | 69,342 rows |
| **NYMEX** CL Futures | 30-min OHLCV bars | 920 bars |
| **News** headlines | Scraped oil-related articles | 37 articles |
| **Reddit** r/oil + r/energy | Posts with scores, comments | 221 posts |

### 2. True Price Derivation (Technical Complexity)

> What price does the crowd actually believe in?

We transform 21 discrete binary option prices into a full continuous price distribution:

```
Binary Options -> Discrete CDF -> PCHIP Monotonic Spline -> Smooth CDF
                                  Log-Normal Tail Fitting
Smooth CDF -> Numerical Gradient -> PDF -> integral x*f(x) dx = Expected Value
```

**Key techniques:**
- **PCHIP Interpolation** (Piecewise Cubic Hermite) — monotone cubic spline that preserves the shape of a CDF (no Runge oscillation, no negative probabilities)
- **Probit regression** on ln(K) for log-normal tail estimation
- **Boundary anchoring** at 0.4x and 1.6x strike range to handle unobserved tails
- **Trapezoid-normalised PDF** with non-negativity enforcement
- **90% Credible Interval** from the implied CDF

**Result at Mar 20 16:00 UTC:**

| Metric | Value |
|--------|-------|
| NYMEX Futures | $97.54 |
| PM Implied EV (True Price) | **$104.91** |
| Basis Gap | **+$7.37** |
| Log-Normal fit | mu=4.650, sigma=0.166 |
| 90% Credible Interval | [$81, $134] |

### 3. Lead-Lag Discovery

Cross-correlation of first-differenced dEV vs dFutures reveals:

| Metric | Value |
|--------|-------|
| Peak cross-correlation | **r = +0.386 at lag +2h** |
| 95% CI band | +/-0.110 |
| Verdict | **PM Implied EV leads NYMEX by ~2 hours** |

The prediction market crowd prices in new information before the futures market converges. This 2-hour lead is statistically significant (3.5x the 95% CI).

### 4. Signal and Backtest

We tested four signal designs exploiting the 2-hour lead:

| Signal | Return | Sharpe | Trades | Win Rate |
|--------|--------|--------|--------|----------|
| Z-Score (baseline) | +0.10% | 0.300 | 2 | 100% |
| EV Momentum | +0.06% | 0.230 | 71 | 52% |
| **Basis Gap Direction** | **+0.26%** | **0.590** | **4** | **75%** |
| Combined (AND) | +0.24% | 0.560 | 3 | 67% |

The **Basis Gap Direction** strategy — simply buy when EV > Futures, sell when EV < Futures — is the best signal. The backtester 1-bar execution delay naturally matches the 2-hour lead.

### 5. Polymarket Leads the News Cycle

Separate analysis in polymarket_lead.ipynb confirms:

- **PM vs NYMEX** Pearson r = **-0.87** (strong inverse correlation for binary strike=65, direction=down)
- Pre-news price movements are larger than post-news: Polymarket prices informationally before headlines break

---

## The Product

### React Dashboard (Vite + Chart.js)

A full-stack SPA with 5 pages:

| Page | Function |
|------|----------|
| **Fetch Data** | One-click ingestion from all 4 sources (Polymarket, News, Reddit, GitHub) |
| **EDA** | Auto-profiling of Polymarket dataset — row counts, strike distribution, liquidity snapshot |
| **Signal Generator** | Manual RSI-based signal tuning + **AI-assisted parameter suggestion** via GPT-4o |
| **Backtest** | Full equity curve, Sharpe/MaxDD/Win Rate KPIs, signal distribution chart, trade log |
| **AI Summary** | Aggregates live News + Reddit data -> **OpenAI-powered market analysis** with bullish/bearish sentiment detection |

### Streamlit Analytics Console

Live interactive dashboard with sidebar controls for strike, direction, resampling, RSI windows, and SMA/EMA/BB indicators. Renders equity curves, signal overlays, and NYMEX comparison charts.

### Jupyter Research Notebooks

| Notebook | Purpose |
|----------|---------|
| polymarket_lead.ipynb | Lead-lag analysis: does Polymarket predict the news cycle? |
| true_price.ipynb | PCHIP CDF -> PDF -> Expected Value derivation + alpha signal |
| backtest_ev_lead.ipynb | Formal backtest of the 2-hour EV lead strategy |
| oil.ipynb | Exploratory data analysis across all sources |

---

## Output Gallery

### Analysis Charts (outputs/)

| Chart | Description |
|-------|-------------|
| true_price_cdf.png | PCHIP-interpolated CDF with log-normal tails |
| true_price_pdf.png | Derived PDF with EV marker and 90% CI band |
| true_price_alpha_spread.png | Rolling EV vs Futures spread over time |
| true_price_lead_lag.png | Cross-correlogram showing 2-hour lead |
| pm_vs_nymex.png | Polymarket probability vs NYMEX price overlay |
| xcorr_pm_nymex.png | Cross-correlation: PM binary vs NYMEX |

### Backtest Charts (data/raw/outputs/)

| Chart | Description |
|-------|-------------|
| backtest_ev_lead_equity.png | Equity curve for Z-score baseline strategy |
| backtest_signal_comparison.png | 4-signal side-by-side equity comparison |
| backtest_direct_gap.png | Direct Gap strategy with 3-panel analysis |
| backtest_ev_lead_sensitivity.png | Z-threshold sensitivity sweep (0.5-2.0 sigma) |

---

## Repository Layout

```
api/polymarket/       Gamma / CLOB / WebSocket API helpers
ingestion/            Fetchers: Polymarket, NYMEX, News, Reddit, GitHub
processing/           Feature engineering, survival analysis, ML models
execution/            Signal generator + trade-by-trade backtester
notebooks/            Research notebooks (4)
frontend/             React SPA (Vite + Chart.js)
dashboard/            Streamlit analytics console
data/raw/             Ingested data (polymarket, nymex, news, reddit)
outputs/              Generated charts and PNGs
config.py             Central configuration (env-driven)
main.py               End-to-end pipeline entry point
```

---

## Quick Start

```bash
# 1. Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # Set OPENAI_API_KEY for AI features

# 3. Ingest data
python ingestion/polymarket_fetcher.py
python ingestion/nymex_fetcher.py

# 4. Run notebooks (research and backtest)
jupyter notebook notebooks/

# 5. Launch product
streamlit run dashboard/app.py             # Analytics console
cd frontend && npm install && npm run dev  # React dashboard
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Data** | Polymarket CLOB API, NYMEX CSV, Reddit API, NewsAPI |
| **Math** | SciPy (PCHIP, lognorm, probit), NumPy (gradient, trapz, cross-correlation) |
| **ML/AI** | OpenAI GPT-4o (AI assistant + signal suggestions), XGBoost, LSTM |
| **Backend** | FastAPI, Python 3.9 |
| **Frontend** | React (Vite), Chart.js, Streamlit |
| **Analysis** | Pandas, Matplotlib, Jupyter |

---

## Key Findings

1. **Polymarket is a leading indicator** — the crowd-implied EV leads NYMEX CL futures by 2 hours (r = +0.386, p < 0.001)
2. **The simplest signal wins** — sign(EV - Futures) produces a Sharpe of 0.59, nearly 2x the Z-score baseline
3. **Prediction markets price information before news breaks** — pre-headline price change > post-headline price change
4. **The True Price framework is generalizable** — any set of binary options on a continuous outcome can be inverted into an implied distribution and expected value

---

## Team ADA — Quantihack 2026
