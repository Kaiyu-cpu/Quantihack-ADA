"""
Alpha Signal Generator
Converts model probability outputs into directional trading signals.
"""
import pandas as pd
import numpy as np


def generate_signals(proba: pd.Series, threshold_long: float = 0.6, threshold_short: float = 0.4) -> pd.Series:
    """
    proba: model predicted probability of positive outcome.
    Returns: Series of {1: long, -1: short, 0: flat}
    """
    signals = pd.Series(0, index=proba.index, dtype=int)
    signals[proba >= threshold_long]  =  1
    signals[proba <= threshold_short] = -1
    return signals


def combine_signals(lstm_proba: pd.Series, xgb_proba: pd.Series, weights=(0.5, 0.5)) -> pd.Series:
    """Ensemble: weighted average of LSTM + XGBoost probabilities."""
    combined = weights[0] * lstm_proba + weights[1] * xgb_proba
    return generate_signals(combined)
