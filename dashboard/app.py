"""
Streamlit Live Dashboard
Run with: streamlit run dashboard/app.py
Tabs: Backtest | AI Report | Optimiser | Stress Test
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env so OPENAI_API_KEY and others are available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

from config import (
    BB_WINDOW,
    EMA_WINDOW,
    RSI_HIGH,
    RSI_LOW,
    RSI_WINDOW,
    SMA_WINDOW,
    POLY_DIRECTION,
    POLY_RESAMPLE,
    POLY_STRIKE_VAL,
)
from execution.backtester import run_backtest
from processing.indicators import build_signals_from_event_df, generate_mean_reversion_signals, add_indicators, get_series

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuantiHack ADA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 QuantiHack ADA — Predictive Performance Dashboard")

# ── Load data ─────────────────────────────────────────────────────────────────
CSV = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "polymarket", "crude_oil_prices.csv")

@st.cache_data(show_spinner="Loading market data…")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"]  = pd.to_datetime(df["timestamp"], utc=True)
    df["strike_val"] = df["strike"].str.replace("$", "", regex=False).astype(int)
    return df

if not os.path.exists(CSV):
    st.error(f"Missing data file: `{CSV}`\n\nRun `python ingestion/polymarket_fetcher.py` first.")
    st.stop()

df = load_data(CSV)

# ── Shared sidebar ────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Settings")

strike_counts    = df.groupby(["direction", "strike_val"]).size().sort_values(ascending=False)
available_strikes = sorted(df["strike_val"].unique())
available_dirs    = sorted(df["direction"].unique())
default_dir, default_strike = strike_counts.index[0]

strike_val = st.sidebar.selectbox(
    "Strike ($)", options=available_strikes,
    index=available_strikes.index(int(default_strike)) if int(default_strike) in available_strikes else 0,
)
direction = st.sidebar.selectbox(
    "Direction", options=available_dirs,
    index=available_dirs.index(str(default_dir)) if str(default_dir) in available_dirs else 0,
)
resample_rule = st.sidebar.selectbox("Resample", ["1h", "30m", "15m", "1d"], index=0)

st.sidebar.subheader("Indicators")
rsi_low  = st.sidebar.slider("RSI Low",  10, 50, int(RSI_LOW))
rsi_high = st.sidebar.slider("RSI High", 50, 90, int(RSI_HIGH))

st.sidebar.subheader("Windows")
sma_w = st.sidebar.number_input("SMA", value=SMA_WINDOW, step=1, min_value=2)
ema_w = st.sidebar.number_input("EMA", value=EMA_WINDOW, step=1, min_value=2)
bb_w  = st.sidebar.number_input("BB",  value=BB_WINDOW,  step=1, min_value=2)
rsi_w = st.sidebar.number_input("RSI", value=RSI_WINDOW, step=1, min_value=2)

st.sidebar.caption(
    f"Rows: {len(df):,} | Strikes: {df['strike_val'].nunique()} | "
    f"{df['timestamp'].min().date()} → {df['timestamp'].max().date()}"
)

# ── Build prices & signals (shared across tabs) ───────────────────────────────
try:
    prices, signals, ind = build_signals_from_event_df(
        df,
        strike_val=int(strike_val),
        direction=direction,
        resample_rule=resample_rule,
        sma_w=int(sma_w), ema_w=int(ema_w), bb_w=int(bb_w), rsi_w=int(rsi_w),
        rsi_low=float(rsi_low), rsi_high=float(rsi_high),
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

result  = run_backtest(prices, signals)
metrics = result["metrics"]
eq      = pd.DataFrame(result["equity_curve"])
eq["date"] = pd.to_datetime(eq["date"])

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_bt, tab_ai, tab_opt, tab_stress = st.tabs([
    "📊 Backtest",
    "🤖 AI Report",
    "🔍 Optimiser",
    "⚡ Stress Test",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════
with tab_bt:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return",  f"{metrics['total_return_pct']:.2f}%")
    c2.metric("Sharpe Ratio",  f"{metrics['sharpe_ratio']:.2f}")
    c3.metric("Max Drawdown",  f"{metrics['max_drawdown_pct']:.2f}%")
    c4.metric("Final Value",   f"${metrics['final_value']:,.2f}")

    # Equity curve
    st.subheader("Equity Curve")
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=eq["date"], y=eq["value"],
        mode="lines", name="Portfolio",
        line=dict(color="#00c2ff", width=2),
        fill="tozeroy", fillcolor="rgba(0,194,255,0.08)",
    ))
    fig_eq.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="", yaxis_title="Value ($)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_eq, width="stretch")

    # Price + indicators + signals
    st.subheader("Price & Indicators")
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=ind.index, y=ind["price"],   name="Price",    line=dict(color="#ffffff", width=1.5)))
    fig_p.add_trace(go.Scatter(x=ind.index, y=ind["sma"],     name="SMA",      line=dict(color="#f5a623", width=1, dash="dot")))
    fig_p.add_trace(go.Scatter(x=ind.index, y=ind["ema"],     name="EMA",      line=dict(color="#7ed321", width=1, dash="dot")))
    fig_p.add_trace(go.Scatter(x=ind.index, y=ind["bb_upper"],name="BB Upper", line=dict(color="#9b59b6", width=1, dash="dash")))
    fig_p.add_trace(go.Scatter(x=ind.index, y=ind["bb_lower"],name="BB Lower", line=dict(color="#9b59b6", width=1, dash="dash"),
                               fill="tonexty", fillcolor="rgba(155,89,182,0.05)"))

    longs  = ind[signals == 1]
    shorts = ind[signals == -1]
    fig_p.add_trace(go.Scatter(x=longs.index,  y=longs["price"],  mode="markers",
                               name="Long ▲",  marker=dict(symbol="triangle-up",   color="#2ecc71", size=9)))
    fig_p.add_trace(go.Scatter(x=shorts.index, y=shorts["price"], mode="markers",
                               name="Short ▼", marker=dict(symbol="triangle-down", color="#e74c3c", size=9)))

    fig_p.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig_p, width="stretch")

    # RSI
    st.subheader("RSI")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=ind.index, y=ind["rsi"], name="RSI", line=dict(color="#00c2ff")))
    fig_rsi.add_hline(y=rsi_high, line_dash="dash", line_color="#e74c3c", annotation_text="Overbought")
    fig_rsi.add_hline(y=rsi_low,  line_dash="dash", line_color="#2ecc71", annotation_text="Oversold")
    fig_rsi.add_hrect(y0=rsi_low, y1=rsi_high, fillcolor="rgba(255,255,0,0.04)", line_width=0)
    fig_rsi.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis=dict(range=[0, 100]),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_rsi, width="stretch")

    # Signal distribution + recent trades
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Signal Distribution")
        sc = signals.value_counts().sort_index()
        fig_sc = go.Figure(go.Bar(
            x=["Short (-1)", "Flat (0)", "Long (+1)"],
            y=[sc.get(-1, 0), sc.get(0, 0), sc.get(1, 0)],
            marker_color=["#e74c3c", "#95a5a6", "#2ecc71"],
        ))
        fig_sc.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sc, width="stretch")
    with col_r:
        st.subheader("Recent Trades")
        trades_df = pd.DataFrame(result["trades"])
        if not trades_df.empty:
            st.dataframe(trades_df.tail(20), width="stretch", height=260)
        else:
            st.info("No completed trades for this configuration.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 AI-Powered Market Analysis")
    st.caption("Computes descriptive statistics and asks an LLM to write an analyst report.")

    openai_key = st.text_input(
        "OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Set OPENAI_API_KEY in your .env or paste here.",
    )
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], index=0)

    if st.button("🚀 Generate AI Report", type="primary"):
        from reporting.ai_reporter import generate_report
        with st.spinner("Analysing data and calling LLM…"):
            try:
                report_text, stats = generate_report(df, model=model_choice)
                st.session_state["ai_report"]  = report_text
                st.session_state["ai_stats"]   = stats
            except Exception as e:
                st.error(f"Error: {e}")

    if "ai_report" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["ai_report"])
        st.markdown("---")
        with st.expander("📊 Raw Statistics Used"):
            st.json(st.session_state["ai_stats"])
    else:
        st.info("Press **Generate AI Report** to analyse the current market data.")

        # Show stats preview without LLM
        with st.expander("Preview computed statistics (no LLM needed)"):
            from reporting.ai_reporter import compute_price_stats
            stats_preview = compute_price_stats(df)
            st.json(stats_preview)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — OPTIMISER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_opt:
    st.subheader("🔍 Bayesian Parameter Optimisation (Optuna)")
    st.caption("Searches for the best RSI thresholds, position size, stops, and commission to maximise Sharpe.")

    col_a, col_b = st.columns(2)
    with col_a:
        n_trials    = st.number_input("Trials", min_value=10, max_value=500, value=80, step=10)
        rsi_l_min, rsi_l_max = st.slider("RSI Low range",   10, 49, (20, 45))
        rsi_h_min, rsi_h_max = st.slider("RSI High range",  51, 90, (55, 80))
    with col_b:
        risk_min, risk_max   = st.slider("Risk % range",    0.1, 10.0, (0.5, 5.0))
        sl_min, sl_max       = st.slider("Stop Loss % range",  1.0, 20.0, (1.0, 10.0))
        tp_min, tp_max       = st.slider("Take Profit % range",1.0, 30.0, (2.0, 15.0))

    use_llm_opt = st.checkbox("✨ LLM narrative after optimisation", value=True,
                               help="Calls GPT to interpret the top results. Requires OPENAI_API_KEY.")

    run_opt = st.button("▶ Run Optimisation", type="primary")

    if run_opt:
        from execution.optimizer import run_optimisation, llm_interpret_results

        progress_bar = st.progress(0, text="Starting Bayesian search…")
        status_text  = st.empty()

        def _progress(done, total, best):
            pct = int(done / total * 100)
            progress_bar.progress(pct, text=f"Trial {done}/{total} — best Sharpe so far: {best:.3f}")

        try:
            # signals_fn wraps the indicator pipeline for the optimiser
            raw_series = get_series(df, int(strike_val), direction, resample_rule)

            def _signals_fn(rsi_low, rsi_high, prices_override=None):
                s = prices_override if prices_override is not None else raw_series
                i = add_indicators(s, sma_w=int(sma_w), ema_w=int(ema_w),
                                   bb_w=int(bb_w), rsi_w=int(rsi_w))
                return generate_mean_reversion_signals(i, rsi_low=rsi_low, rsi_high=rsi_high)

            best_params, trials_df = run_optimisation(
                prices,
                signals_fn=_signals_fn,
                n_trials=int(n_trials),
                rsi_low_range=(rsi_l_min, rsi_l_max),
                rsi_high_range=(rsi_h_min, rsi_h_max),
                risk_pct_range=(risk_min, risk_max),
                stop_loss_range=(sl_min, sl_max),
                take_profit_range=(tp_min, tp_max),
                progress_callback=_progress,
            )
            progress_bar.progress(100, text="✅ Optimisation complete!")
            st.session_state["opt_best"]   = best_params
            st.session_state["opt_trials"] = trials_df

        except ImportError as e:
            st.error(str(e))

    if "opt_best" in st.session_state:
        best   = st.session_state["opt_best"]
        trials = st.session_state["opt_trials"]

        st.markdown("### Best Parameters Found")
        bp1, bp2, bp3, bp4 = st.columns(4)
        bp1.metric("Sharpe",       f"{best.get('sharpe', 0):.3f}")
        bp2.metric("RSI Low",      f"{best.get('rsi_low', 0):.1f}")
        bp3.metric("RSI High",     f"{best.get('rsi_high', 0):.1f}")
        bp4.metric("Risk %",       f"{best.get('risk_pct', 0):.2f}%")

        bp5, bp6, bp7, _ = st.columns(4)
        bp5.metric("Stop Loss %",    f"{best.get('stop_loss_pct', 0):.2f}%")
        bp6.metric("Take Profit %",  f"{best.get('take_profit_pct', 0):.2f}%")
        bp7.metric("Commission %",   f"{best.get('commission_pct', 0):.3f}%")

        # Sharpe distribution chart
        st.markdown("### Sharpe Distribution Across Trials")
        fig_opt = go.Figure()
        fig_opt.add_trace(go.Histogram(
            x=trials["sharpe"], nbinsx=30,
            marker_color="#00c2ff", opacity=0.8,
        ))
        fig_opt.add_vline(x=best.get("sharpe", 0), line_dash="dash",
                          line_color="#f5a623", annotation_text="Best")
        fig_opt.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                               xaxis_title="Sharpe", yaxis_title="Count",
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_opt, width="stretch")

        # Top trials table
        with st.expander("Top 20 trials"):
            st.dataframe(trials.head(20), width="stretch")

        # LLM narrative
        if use_llm_opt and os.getenv("OPENAI_API_KEY"):
            if st.button("🤖 Get LLM Strategy Narrative"):
                from execution.optimizer import llm_interpret_results
                with st.spinner("Asking LLM to interpret results…"):
                    narrative = llm_interpret_results(best, trials)
                    st.session_state["opt_narrative"] = narrative

        if "opt_narrative" in st.session_state:
            st.markdown("### 🤖 LLM Strategy Interpretation")
            st.markdown(st.session_state["opt_narrative"])

    elif not run_opt:
        st.info("Configure the search bounds above and press **Run Optimisation**.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STRESS TEST
# ═══════════════════════════════════════════════════════════════════════════════
with tab_stress:
    st.subheader("⚡ Stress Testing")

    st.markdown("**Monte Carlo** simulates hundreds of synthetic price paths. "
                "**Scenario Stress** applies named market shocks to the real data.")

    col_mc, col_sc = st.columns(2)

    with col_mc:
        st.markdown("#### Monte Carlo")
        n_paths = st.number_input("Paths", min_value=20, max_value=1000, value=200, step=20)
        run_mc  = st.button("▶ Run Monte Carlo", type="primary")

    with col_sc:
        st.markdown("#### Scenario Stress")
        use_llm_sc = st.checkbox("✨ AI-generated scenarios", value=True,
                                  help="Asks GPT to define 5 stress scenarios. Falls back to built-in defaults if no API key.")
        run_sc = st.button("▶ Run Scenario Stress", type="secondary")

    # ── Monte Carlo ────────────────────────────────────────────────────────────
    if run_mc:
        from execution.stress_test import run_monte_carlo, summarise_monte_carlo
        from processing.indicators import add_indicators, generate_mean_reversion_signals, get_series

        raw_s = get_series(df, int(strike_val), direction, resample_rule)

        def _mc_signals(p: pd.Series) -> pd.Series:
            i = add_indicators(p, sma_w=int(sma_w), ema_w=int(ema_w),
                               bb_w=int(bb_w), rsi_w=int(rsi_w))
            return generate_mean_reversion_signals(i, rsi_low=float(rsi_low), rsi_high=float(rsi_high))

        mc_bar = st.progress(0, text="Running Monte Carlo…")

        def _mc_progress(done, total):
            mc_bar.progress(int(done / total * 100), text=f"Path {done}/{total}…")

        with st.spinner("Simulating price paths…"):
            mc_df   = run_monte_carlo(raw_s, _mc_signals, n_paths=int(n_paths), progress_callback=_mc_progress)
            mc_summary = summarise_monte_carlo(mc_df)
            st.session_state["mc_df"]      = mc_df
            st.session_state["mc_summary"] = mc_summary
        mc_bar.progress(100, text="✅ Monte Carlo complete!")

    if "mc_summary" in st.session_state:
        summary = st.session_state["mc_summary"]
        mc_df   = st.session_state["mc_df"]

        st.markdown(f"### Monte Carlo Results — {summary['n_paths']} paths  |  {summary['pct_profitable']}% profitable")

        mc1, mc2, mc3, mc4 = st.columns(4)
        def _mc_metric(col, label, key):
            s = summary[key]
            col.metric(label, f"{s['p50']:.2f}", f"P5: {s['p5']:.2f} | P95: {s['p95']:.2f}")
        _mc_metric(mc1, "Sharpe (P50)",      "sharpe")
        _mc_metric(mc2, "Return % (P50)",    "total_return_pct")
        _mc_metric(mc3, "Drawdown % (P50)",  "max_drawdown_pct")
        _mc_metric(mc4, "Final Value (P50)", "final_value")

        # Distribution charts
        fig_mc = go.Figure()
        for col, color, label in [
            ("sharpe", "#00c2ff", "Sharpe"),
            ("total_return_pct", "#2ecc71", "Return %"),
            ("max_drawdown_pct", "#e74c3c", "Drawdown %"),
        ]:
            fig_mc.add_trace(go.Histogram(x=mc_df[col], name=label,
                                          marker_color=color, opacity=0.6, nbinsx=30))
        fig_mc.update_layout(
            barmode="overlay", height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_mc, width="stretch")

    # ── Scenario Stress ────────────────────────────────────────────────────────
    if run_sc:
        from execution.stress_test import run_scenario_stress
        from processing.indicators import add_indicators, generate_mean_reversion_signals, get_series

        raw_s = get_series(df, int(strike_val), direction, resample_rule)

        def _sc_signals(p: pd.Series) -> pd.Series:
            i = add_indicators(p, sma_w=int(sma_w), ema_w=int(ema_w),
                               bb_w=int(bb_w), rsi_w=int(rsi_w))
            return generate_mean_reversion_signals(i, rsi_low=float(rsi_low), rsi_high=float(rsi_high))

        with st.spinner("Running scenario stress tests…"):
            sc_df = run_scenario_stress(raw_s, _sc_signals, use_llm=use_llm_sc)
            st.session_state["sc_df"] = sc_df

    if "sc_df" in st.session_state:
        sc_df = st.session_state["sc_df"]
        st.markdown("### Scenario Results vs Baseline")

        # Add baseline row
        baseline_row = pd.DataFrame([{
            "scenario":         "Baseline (Real Data)",
            "description":      "Unmodified historical prices",
            "sharpe":           metrics["sharpe_ratio"],
            "total_return_pct": metrics["total_return_pct"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
            "final_value":      metrics["final_value"],
            "n_trades":         metrics["n_trades"],
        }])
        combined = pd.concat([baseline_row, sc_df], ignore_index=True)

        # Colour-coded bar chart
        colors = ["#f5a623"] + [
            "#2ecc71" if v >= metrics["sharpe_ratio"] * 0.8 else
            "#e67e22" if v >= 0 else "#e74c3c"
            for v in sc_df["sharpe"].fillna(0)
        ]
        fig_sc = go.Figure(go.Bar(
            x=combined["scenario"],
            y=combined["sharpe"].fillna(0),
            marker_color=colors,
            text=[f"{v:.2f}" if pd.notna(v) else "ERR" for v in combined["sharpe"]],
            textposition="outside",
        ))
        fig_sc.update_layout(
            height=320, margin=dict(l=0, r=0, t=30, b=80),
            yaxis_title="Sharpe Ratio",
            xaxis_tickangle=-20,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sc, width="stretch")

        # Detailed table
        st.dataframe(
            combined[["scenario", "description", "sharpe", "total_return_pct",
                       "max_drawdown_pct", "final_value", "n_trades"]]
            .rename(columns={
                "total_return_pct": "return%",
                "max_drawdown_pct": "drawdown%",
                "final_value":      "final_val",
                "n_trades":         "trades",
            }),
            width="stretch",
        )

    if not run_mc and not run_sc and "mc_df" not in st.session_state and "sc_df" not in st.session_state:
        st.info("Use the buttons above to run Monte Carlo simulation or scenario stress tests.")
