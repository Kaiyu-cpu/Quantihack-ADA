"""
Helpers to align one price series to another index (e.g., signals to futures).
"""
from __future__ import annotations

import pandas as pd


def align_to_index(series: pd.Series, target_index: pd.DatetimeIndex, method: str = "ffill") -> pd.Series:
    """
    Align a price series to a target index using forward-fill (default).
    Assumes series is indexed by datetime.
    """
    s = series.copy()
    if s.index.tz is None:
        s.index = s.index.tz_localize("UTC")
    if target_index.tz is None:
        target_index = target_index.tz_localize("UTC")

    s = s.sort_index()
    # Reindex to target timestamps with a safe fill
    aligned = s.reindex(target_index, method=method)
    return aligned


def shift_signals(signals: pd.Series, hours: int) -> pd.Series:
    """
    Shift signals forward in time by N hours (lead-lag adjustment).
    """
    if signals.index.tz is None:
        signals.index = signals.index.tz_localize("UTC")
    return signals.shift(freq=pd.Timedelta(hours=hours))
