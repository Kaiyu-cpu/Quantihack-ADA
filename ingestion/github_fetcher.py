"""
GitHub Issue Fetcher
Pulls bug/issue history for survival analysis.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root

import requests
import pandas as pd
from config import GITHUB_TOKEN, GITHUB_REPO, DATA_RAW_DIR


def fetch_issues(state: str = "all", max_pages: int = 10) -> pd.DataFrame:
    """Return a DataFrame of issues with opened/closed timestamps."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    issues = []

    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        resp = requests.get(url, headers=headers, params={"state": state, "per_page": 100, "page": page})
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        issues.extend(batch)

    if not issues:
        return pd.DataFrame(columns=["number", "state", "created_at", "closed_at", "labels", "duration_days"])

    df = pd.json_normalize(issues)[["number", "state", "created_at", "closed_at", "labels"]]
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["closed_at"]  = pd.to_datetime(df["closed_at"])
    df["duration_days"] = (df["closed_at"] - df["created_at"]).dt.days
    return df


def save_raw(df: pd.DataFrame, filename: str = "issues.parquet") -> None:
    path = Path(f"{DATA_RAW_DIR}/github/{filename}")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"Saved {len(df)} issues → {path}")


if __name__ == "__main__":
    df = fetch_issues()
    save_raw(df)
