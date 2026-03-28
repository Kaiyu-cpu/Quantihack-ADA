"""
Central configuration — override via environment variables or a .env file.
"""
import os

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "owner/repo")   # e.g. "torvalds/linux"

# ── Polymarket ────────────────────────────────────────────────────────────────
POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
POLYMARKET_BASE_URL = "https://clob.polymarket.com"

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_RAW_DIR       = "data/raw"
DATA_PROCESSED_DIR = "data/processed"

# ── Model ─────────────────────────────────────────────────────────────────────
LSTM_LOOKBACK      = 30   # days
XGBOOST_N_ESTIMATORS = 200
RANDOM_SEED        = 42

# ── Backtesting ───────────────────────────────────────────────────────────────
INITIAL_CAPITAL    = 10_000
TRANSACTION_COST   = 0.001   # 10 bps
