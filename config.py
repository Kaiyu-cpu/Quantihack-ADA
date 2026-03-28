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

# ── Algo-backtest params (ported in-place) ───────────────────────────────────
# Percent of capital per trade (matches algo-backtest risk_per_trade semantics)
RISK_PER_TRADE_PCT = float(os.getenv("RISK_PER_TRADE_PCT", "1.0"))

# Commission percent per trade
COMMISSION_PCT = float(os.getenv("COMMISSION_PCT", "0.1"))

# Optional stop/take profit percent
STOP_LOSS_PCT = os.getenv("STOP_LOSS_PCT", "")
TAKE_PROFIT_PCT = os.getenv("TAKE_PROFIT_PCT", "")
STOP_LOSS_PCT = float(STOP_LOSS_PCT) if STOP_LOSS_PCT else None
TAKE_PROFIT_PCT = float(TAKE_PROFIT_PCT) if TAKE_PROFIT_PCT else None

# Annualization for Sharpe (daily=252, hourly=24*365, etc.)
BACKTEST_PERIODS_PER_YEAR = int(os.getenv("BACKTEST_PERIODS_PER_YEAR", "252"))

# ── Polymarket signal config ──────────────────────────────────────────────────
POLY_STRIKE_VAL = int(os.getenv("POLY_STRIKE_VAL", "95"))
POLY_DIRECTION  = os.getenv("POLY_DIRECTION", "up")
POLY_RESAMPLE   = os.getenv("POLY_RESAMPLE", "1h")

SMA_WINDOW = int(os.getenv("SMA_WINDOW", "12"))
EMA_WINDOW = int(os.getenv("EMA_WINDOW", "12"))
BB_WINDOW  = int(os.getenv("BB_WINDOW", "20"))
RSI_WINDOW = int(os.getenv("RSI_WINDOW", "14"))
RSI_LOW    = float(os.getenv("RSI_LOW", "45"))
RSI_HIGH   = float(os.getenv("RSI_HIGH", "55"))
