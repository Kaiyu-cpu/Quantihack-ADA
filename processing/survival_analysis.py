"""
Survival Analysis → Engineering Agility Score
Uses Kaplan-Meier and Cox Proportional Hazards on issue lifetime data.
"""
import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter, CoxPHFitter


def compute_agility_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input:  DataFrame with columns [duration_days, event (1=closed, 0=censored)]
    Output: DataFrame enriched with [hazard_rate, agility_score]
    """
    df = df.copy()
    df["event"] = df["duration_days"].notna().astype(int)
    df["duration_days"] = df["duration_days"].fillna(
        (pd.Timestamp.now() - df["created_at"]).dt.days
    )

    # Kaplan-Meier for survival curve
    kmf = KaplanMeierFitter()
    kmf.fit(df["duration_days"], event_observed=df["event"])

    # Cox PH for hazard rate (add covariates as needed)
    cph = CoxPHFitter()
    cph_df = df[["duration_days", "event"]].dropna()
    cph.fit(cph_df, duration_col="duration_days", event_col="event")

    # Agility score: inverse of median survival time (faster close = more agile)
    median_survival = kmf.median_survival_time_
    agility = 1.0 / (median_survival + 1e-9)

    df["agility_score"] = agility
    df["hazard_rate"]   = cph.baseline_hazard_.values.mean() if not cph.baseline_hazard_.empty else np.nan
    return df


if __name__ == "__main__":
    # Quick smoke test with synthetic data
    test = pd.DataFrame({
        "duration_days": np.random.exponential(10, 100),
        "created_at": pd.Timestamp.now(),
    })
    result = compute_agility_score(test)
    print(result[["duration_days", "agility_score", "hazard_rate"]].head())
