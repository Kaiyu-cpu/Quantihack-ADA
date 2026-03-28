"""
True Price signal from Polymarket distribution.
Builds CDF from all strikes, smooths it, derives expected value,
and computes basis gap vs futures for a Z-score signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.stats import lognorm, norm


def _cdf_points(pm_raw: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    past = pm_raw[pm_raw["timestamp"] <= t]
    if len(past) < 2:
        return pd.DataFrame(columns=["strike", "cdf_value"])

    latest = (
        past.sort_values("timestamp")
        .groupby(["strike_val", "direction"], as_index=False)
        .last()[["strike_val", "direction", "price"]]
    )

    rows = []
    for _, row in latest.iterrows():
        p = float(row["price"])
        cdf_v = (1.0 - p) if row["direction"] == "up" else p
        rows.append({"strike": float(row["strike_val"]), "cdf_value": cdf_v})

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # If both up and down at same strike, average
    df = df.groupby("strike", as_index=False)["cdf_value"].mean()
    df = df.sort_values("strike")

    # enforce monotonicity
    df["cdf_value"] = np.maximum.accumulate(df["cdf_value"].values)
    return df


def _fit_smooth_cdf(df_cdf: pd.DataFrame, x_min: float = 35.0, x_max: float = 230.0, n_grid: int = 1000):
    K = df_cdf["strike"].values.astype(float)
    F_obs = df_cdf["cdf_value"].values.astype(float)

    valid = (F_obs > 0.02) & (F_obs < 0.98)
    if valid.sum() >= 3:
        z_vals = norm.ppf(F_obs[valid])
        ln_K = np.log(K[valid])
        coeffs = np.polyfit(ln_K, z_vals, 1)
        mu = -coeffs[1] / coeffs[0]
        sigma = 1.0 / coeffs[0]
    else:
        mu, sigma = np.log(np.median(K)), 0.4

    # Anchor boundaries
    k_min = K.min()
    k_max = K.max()
    anchored_K = np.concatenate([[0.4 * k_min], K, [1.6 * k_max]])
    anchored_F = np.concatenate([[0.0], F_obs, [1.0]])

    # PCHIP inside anchors
    pchip = PchipInterpolator(anchored_K, anchored_F, extrapolate=False)
    x_grid = np.linspace(x_min, x_max, n_grid)
    cdf = pchip(x_grid)

    # Fill NaNs using lognormal tails
    ln_cdf = lognorm.cdf(x_grid, s=sigma, scale=np.exp(mu))
    cdf = np.where(np.isnan(cdf), ln_cdf, cdf)
    cdf = np.clip(cdf, 0, 1)

    pdf = np.gradient(cdf, x_grid)
    pdf = np.clip(pdf, 0, None)
    pdf = pdf / (np.trapz(pdf, x_grid) + 1e-12)

    ev = np.trapz(x_grid * pdf, x_grid)
    return x_grid, cdf, pdf, ev


def compute_true_price_series(pm_raw: pd.DataFrame, times: pd.DatetimeIndex) -> pd.Series:
    ev_values = []
    for t in times:
        snap = _cdf_points(pm_raw, t)
        if snap.empty:
            ev_values.append(np.nan)
            continue
        _, _, _, ev = _fit_smooth_cdf(snap)
        ev_values.append(ev)
    return pd.Series(ev_values, index=times, name="true_price").ffill()


def zscore_signal(series: pd.Series, window: int = 72, threshold: float = 1.0) -> pd.Series:
    roll = series.rolling(window)
    z = (series - roll.mean()) / (roll.std(ddof=1) + 1e-9)
    sig = pd.Series(0, index=series.index, name="signal", dtype=int)
    sig[z > threshold] = 1
    sig[z < -threshold] = -1
    return sig
