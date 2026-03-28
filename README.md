# Quantihack-ADA

**Quantihack 2026 — Team ADA**

Python project for quantitative workflows around **Polymarket** prediction-market prices and **GitHub** issue history: ingest data, derive features (including survival-based “agility” scores from issue lifetimes), generate trading signals, backtest, and explore results in a small Streamlit dashboard.

## What it does

- **Ingestion** — Pulls GitHub issues (open/close times) for survival analysis; fetches historical YES-token prices for all markets in a Polymarket **event** via the Gamma metadata API and CLOB price history (`ingestion/` + `api/polymarket/`).
- **Processing** — Computes an **engineering agility score** from issue durations with Kaplan–Meier and Cox models (`lifelines`); builds **market features** (returns, volatility, momentum, mean-reversion, sentiment) from price time series (`processing/`).
- **Execution** — Converts model probabilities into long/short/flat signals and runs a **trade-by-trade backtest** with position sizing, commission, and optional stops (`execution/`). `main.py` still uses **placeholder random signals** until real model outputs are wired in.
- **Models** — Optional **LSTM** and **XGBoost** modules live under `processing/model/` for future signal generation.
- **Dashboard** — Streamlit UI for KPIs, equity curve, and signal distribution (currently demo data; intended to connect to the same pipeline).

## Repository layout

| Path | Role |
|------|------|
| `main.py` | End-to-end pipeline: GitHub + Polymarket ingest → features → backtest |
| `config.py` | Central settings (env overrides for GitHub, Polymarket, backtest params) |
| `ingestion/` | GitHub and Polymarket fetchers |
| `processing/` | Survival analysis, market features, ML models |
| `execution/` | Signal generation and backtester |
| `api/polymarket/` | Gamma / CLOB / websocket helpers |
| `dashboard/` | Streamlit app |
| `tests/polymarket/` | Scripts and sample JSON for Polymarket API experiments |

## Setup

1. Python 3.11+ recommended (TensorFlow in `requirements.txt`).

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set:

   - `GITHUB_TOKEN` (optional but raises rate limits)
   - `GITHUB_REPO` (e.g. `owner/repo`)
   - `POLYMARKET_API_KEY` if your CLOB usage requires it

3. Raw data paths are under `data/raw/` (see `config.py`). Create directories if needed when running fetchers.

## Running

- **Full pipeline (after configuring `.env` and a real event slug):**

  ```bash
  python main.py
  ```

  Edit `main.py` and replace `EXAMPLE_EVENT_SLUG` with a Polymarket event slug (same style as in `ingestion/polymarket_fetcher.py`, e.g. crude-oil examples in `tests/polymarket/`).

- **Polymarket fetcher only:**

  ```bash
  python ingestion/polymarket_fetcher.py
  ```

- **Dashboard:**

  ```bash
  streamlit run dashboard/app.py
  ```

## Dependencies

Core stack: `pandas`, `numpy`, `scipy`, `lifelines`, `scikit-learn`, `xgboost`, `tensorflow`, `requests`, `python-dotenv`, `streamlit`, `plotly`, `pytest`, `jupyter` (see `requirements.txt`).

## Team

Quantihack 2026 — Team ADA.
