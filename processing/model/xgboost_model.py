"""
XGBoost Model — gradient-boosted trees for feature fusion / alpha signal.
"""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from config import XGBOOST_N_ESTIMATORS, RANDOM_SEED


def build_xgboost() -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
        n_estimators=XGBOOST_N_ESTIMATORS,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=RANDOM_SEED,
    )


def train(X: pd.DataFrame, y: pd.Series) -> xgb.XGBClassifier:
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED)
    model = build_xgboost()
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    preds = model.predict(X_val)
    print(classification_report(y_val, preds))
    return model
