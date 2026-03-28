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

st.set_page_config(page_title="QuantiHack ADA", layout="wide")
st.title("QuantiHack ADA — Predictive Performance Dashboard")

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.header("Settings")
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10_000)
long_thresh     = st.sidebar.slider("Long signal threshold",  0.5, 1.0, 0.6)
short_thresh    = st.sidebar.slider("Short signal threshold", 0.0, 0.5, 0.4)

# ── Placeholder: load real data / signals here ────────────────────────────────
st.info("Connect `ingestion`, `processing`, and `execution` modules to replace synthetic data.")

np.random.seed(42)
prices  = pd.Series(100 * (1 + np.random.randn(300) * 0.01).cumprod(), name="price")
signals = pd.Series(np.random.choice([-1, 0, 1], 300), name="signal")

result = run_backtest(prices, signals)
metrics = result["metrics"]
eq      = result["equity_curve"]

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Return",   f"{metrics['total_return']:.2%}")
col2.metric("Sharpe Ratio",   f"{metrics['sharpe_ratio']:.2f}")
col3.metric("Max Drawdown",   f"{metrics['max_drawdown']:.2%}")
col4.metric("# Trades",       metrics['n_trades'])

# ── Equity Curve ──────────────────────────────────────────────────────────────
st.subheader("Equity Curve")
st.line_chart(eq["equity"])

# ── Signal Distribution ───────────────────────────────────────────────────────
st.subheader("Signal Distribution")
st.bar_chart(eq["signal"].value_counts().sort_index())
