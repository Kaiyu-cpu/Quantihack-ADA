"""
LSTM Model — sequential feature fusion for time-series prediction.
"""
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from config import LSTM_LOOKBACK, RANDOM_SEED

tf.random.set_seed(RANDOM_SEED)


def build_lstm(input_dim: int, units: int = 64) -> Sequential:
    model = Sequential([
        LSTM(units, input_shape=(LSTM_LOOKBACK, input_dim), return_sequences=True),
        Dropout(0.2),
        LSTM(units // 2),
        Dropout(0.2),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def make_sequences(X: np.ndarray, y: np.ndarray, lookback: int = LSTM_LOOKBACK):
    Xs, ys = [], []
    for i in range(lookback, len(X)):
        Xs.append(X[i - lookback:i])
        ys.append(y[i])
    return np.array(Xs), np.array(ys)
