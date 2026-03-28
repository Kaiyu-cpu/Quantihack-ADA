"""
Streamlit Live Dashboard
Run with: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from execution.backtester import run_backtest
from processing.indicators import build_signals_from_event_df
from processing.price_align import align_to_index
from config import (
    POLY_STRIKE_VAL,
    POLY_DIRECTION,
    POLY_RESAMPLE,
    SMA_WINDOW,
    EMA_WINDOW,
    BB_WINDOW,
    RSI_WINDOW,
    RSI_LOW,
    RSI_HIGH,
    TRADE_ON,
    FUTURES_CSV_PATH,
)

st.set_page_config(page_title="QuantiHack ADA", layout="wide")
st.title("QuantiHack ADA — Predictive Performance Dashboard")

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.header("Settings")

# ── Load Polymarket CSV ───────────────────────────────────────────────────────
CSV = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "polymarket", "crude_oil_prices.csv")
if not os.path.exists(CSV):
    st.error(f"Missing data file: {CSV}")
    st.stop()

df = pd.read_csv(CSV, parse_dates=["timestamp"])
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df["strike_val"] = df["strike"].str.replace("$", "", regex=False).astype(int)

# Available options from data
strike_counts = df.groupby(["direction", "strike_val"]).size().sort_values(ascending=False)
available_strikes = sorted(df["strike_val"].unique())
available_dirs = sorted(df["direction"].unique())

# Default to most liquid strike/direction
default_dir, default_strike = strike_counts.index[0]

strike_val = st.sidebar.selectbox(
    "Strike ($)",
    options=available_strikes,
    index=available_strikes.index(int(default_strike)) if int(default_strike) in available_strikes else 0,
)
direction = st.sidebar.selectbox(
    "Direction",
    options=available_dirs,
    index=available_dirs.index(str(default_dir)) if str(default_dir) in available_dirs else 0,
)
resample_rule = st.sidebar.selectbox("Resample", ["1h", "30m", "15m", "1d"], index=0)
trade_on = st.sidebar.selectbox("Trade On", ["polymarket", "futures"], index=0 if TRADE_ON == "polymarket" else 1)

st.sidebar.subheader("Indicators")
rsi_low = st.sidebar.slider("RSI Low", 10, 50, int(RSI_LOW))
rsi_high = st.sidebar.slider("RSI High", 50, 90, int(RSI_HIGH))

st.sidebar.subheader("Windows")
sma_w = st.sidebar.number_input("SMA Window", value=SMA_WINDOW, step=1)
ema_w = st.sidebar.number_input("EMA Window", value=EMA_WINDOW, step=1)
bb_w = st.sidebar.number_input("BB Window", value=BB_WINDOW, step=1)
rsi_w = st.sidebar.number_input("RSI Window", value=RSI_WINDOW, step=1)

st.caption(
    f"Data rows: {len(df):,} | Strikes: {df['strike_val'].nunique()} | "
    f"Range: {df['timestamp'].min().date()} → {df['timestamp'].max().date()}"
)

try:
    prices, signals, ind = build_signals_from_event_df(
        df,
        strike_val=int(strike_val),
        direction=direction,
        resample_rule=resample_rule,
        sma_w=int(sma_w),
        ema_w=int(ema_w),
        bb_w=int(bb_w),
        rsi_w=int(rsi_w),
        rsi_low=float(rsi_low),
        rsi_high=float(rsi_high),
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

# Optionally trade on futures prices instead of Polymarket prices
futures_available = os.path.exists(FUTURES_CSV_PATH)
futures_series = None
if futures_available:
    futures_df = pd.read_csv(FUTURES_CSV_PATH, parse_dates=["timestamp"])
    futures_df["timestamp"] = pd.to_datetime(futures_df["timestamp"], utc=True)
    futures_series = futures_df.set_index("timestamp")["close"]

trade_prices = prices
if trade_on == "futures":
    if not futures_available:
        st.error(f"Missing futures CSV: {FUTURES_CSV_PATH}")
        st.stop()
    trade_prices = align_to_index(futures_series, prices.index)

result = run_backtest(trade_prices, signals)
metrics = result["metrics"]
eq      = pd.DataFrame(result["equity_curve"])

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Return",   f"{metrics['total_return_pct']:.2f}%")
col2.metric("Sharpe Ratio",   f"{metrics['sharpe_ratio']:.2f}")
col3.metric("Max Drawdown",   f"{metrics['max_drawdown_pct']:.2f}%")
col4.metric("Final Value",    f"{metrics['final_value']:.2f}")

st.caption(f"Buy & Hold Return: {metrics.get('buy_hold_return_pct', 0.0):.2f}%  |  Trades: {metrics.get('n_trades', 0)}")

# ── Equity Curve ──────────────────────────────────────────────────────────────
st.subheader("Equity Curve")
st.line_chart(eq.set_index("date")["value"])

# ── Comparison: Polymarket vs Futures (same signals) ─────────────────────────
if futures_available:
    pm_result = run_backtest(prices, signals)
    fut_prices = align_to_index(futures_series, prices.index)
    fut_result = run_backtest(fut_prices, signals)

    pm_eq = pd.DataFrame(pm_result["equity_curve"]).set_index("date")["value"]
    fut_eq = pd.DataFrame(fut_result["equity_curve"]).set_index("date")["value"]
    compare = pd.DataFrame({
        "Polymarket": pm_eq,
        "Futures (CL=F)": fut_eq,
    })
    st.subheader("Equity Curve Comparison")
    st.line_chart(compare)

# ── Signal Distribution ───────────────────────────────────────────────────────
st.subheader("Signal Distribution")
st.bar_chart(signals.value_counts().sort_index())

# ── Price + Signals Overlay ───────────────────────────────────────────────────
st.subheader("Price With Signals")
overlay = pd.DataFrame({
    "price": trade_prices,
    "signal": signals,
})
st.line_chart(overlay["price"])

# Markers table for quick inspection
st.write("Recent signals")
st.dataframe(
    overlay[overlay["signal"] != 0]
    .tail(50)
    .reset_index()
    .rename(columns={"index": "timestamp"})
)
