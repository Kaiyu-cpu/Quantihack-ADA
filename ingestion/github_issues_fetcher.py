from github import Github, Auth
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from datetime import datetime, timezone

# ── 1. AUTHENTICATION ──────────────────────────────────────────────
auth = Auth.Token("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")
g = Github(auth=auth)

# ── 2. DEFINE REPOS ────────────────────────────────────────────────
repos = [
    #"microsoft/vscode",
    #"facebook/react",
    #"tensorflow/tensorflow",
    #"netflix/zuul",
    #"uber/cadence" 
    "pallets/flask",
    "psf/requests",
    "scrapy/scrapy",
    "pytest-dev/pytest",
    "tornadoweb/tornado",
    "microsoft/playwright",      # Microsoft — MSFT
    "aws/aws-cli",               # Amazon — AMZN
    "meta-llama/llama-stack",    # Meta — META
    "apple/swift",
]

# ── 3. PULL ISSUE DATA ─────────────────────────────────────────────
all_issues = []

for repo_name in repos:
    print(f"Pulling {repo_name}...")
    repo = g.get_repo(repo_name)
    issues = repo.get_issues(state='closed')
    
    cutoff = datetime(2026, 1, 28, tzinfo=timezone.utc)
    
    count = 0
    for issue in issues:
        try:
            if issue.pull_request:
                continue
                
            if issue.created_at < cutoff:
                break
                
            created = issue.created_at
            closed = issue.closed_at
            duration = (closed - created).days

            all_issues.append({
                'repo': repo_name,
                'issue_number': issue.number,
                'created_at': created,
                'closed_at': closed,
                'duration_days': duration,
                'labels': [l.name for l in issue.labels],
                'comments': issue.comments,
                'event': 1
            })

            count += 1
            if count >= 1000:
                break
        except:
            continue
    
    print(f"  → {count} issues collected from {repo_name}")

df = pd.DataFrame(all_issues)
df.to_csv('github_issues.csv', index=False)
print(f"Done. {len(df)} issues collected.")
print(df.head())
print(df.tail())

# ── 4. REAL SURVIVAL CURVES ────────────────────────────────────────
kmf = KaplanMeierFitter()
fig, ax = plt.subplots(figsize=(10, 6))

for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf.fit(
        durations=subset['duration_days'],
        event_observed=subset['event'],
        label=repo
    )
    kmf.plot_survival_function(ax=ax)

plt.title('ADA — Engineering Agility: Issue Survival Curves')
plt.xlabel('Days')
plt.ylabel('Probability Issue Still Open')
plt.tight_layout()
plt.savefig('survival_curves.png')
plt.show()

# ── 5. AGILITY SCORES ──────────────────────────────────────────────
agility_scores = []

for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(durations=subset['duration_days'], event_observed=subset['event'])
    
    median_survival = kmf.median_survival_time_
    agility_scores.append({
        'repo': repo,
        'median_survival_days': median_survival,
        'agility_score': round(1 / (median_survival + 1), 4)
    })

agility_df = pd.DataFrame(agility_scores)
print(agility_df.sort_values('agility_score', ascending=False))
agility_df.to_csv('agility_scores.csv', index=False)

# ── 6. SYNTHETIC STRESS TESTS ──────────────────────────────────────
healthy = pd.DataFrame({
    'duration_days': np.random.exponential(scale=5, size=200),
    'event': 1,
    'scenario': 'healthy_team'
})

stressed = pd.DataFrame({
    'duration_days': np.random.exponential(scale=60, size=200),
    'event': 1,
    'scenario': 'stressed_team'
})

crisis = pd.DataFrame({
    'duration_days': np.random.exponential(scale=120, size=200),
    'event': np.random.choice([0, 1], size=200, p=[0.4, 0.6]),
    'scenario': 'crisis_team'
})

synthetic = pd.concat([healthy, stressed, crisis])

fig, ax = plt.subplots(figsize=(10, 6))
for scenario in synthetic['scenario'].unique():
    subset = synthetic[synthetic['scenario'] == scenario]
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=subset['duration_days'],
        event_observed=subset['event'],
        label=scenario
    )
    kmf.plot_survival_function(ax=ax)

plt.title('ADA — Synthetic Stress Test Survival Curves')
plt.xlabel('Days')
plt.ylabel('Probability Issue Still Open')
plt.tight_layout()
plt.savefig('synthetic_survival.png')
plt.show()

# ── 7. POLISHED FINAL PLOT ─────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

ax1 = axes[0]
for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=subset['duration_days'],
        event_observed=subset['event'],
        label=repo.split('/')[1]
    )
    kmf.plot_survival_function(ax=ax1)

ax1.set_title('Real Company Agility', fontsize=14, fontweight='bold')
ax1.set_xlabel('Days Until Issue Resolved')
ax1.set_ylabel('Probability Issue Still Open')

ax2 = axes[1]
for scenario in synthetic['scenario'].unique():
    subset = synthetic[synthetic['scenario'] == scenario]
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=subset['duration_days'],
        event_observed=subset['event'],
        label=scenario.replace('_', ' ').title()
    )
    kmf.plot_survival_function(ax=ax2)

ax2.set_title('Stress Test Scenarios', fontsize=14, fontweight='bold')
ax2.set_xlabel('Days Until Issue Resolved')
ax2.set_ylabel('Probability Issue Still Open')

plt.suptitle('ADA — Signal Half-Life: Engineering Agility Analysis',
             fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('ADA_final_plots.png', dpi=150)
plt.show()

# ── 8. DONE ────────────────────────────────────────────────────────
print("\nAll done. Files saved:")
print("  github_issues.csv")
print("  agility_scores.csv")
print("  survival_curves.png")
print("  synthetic_survival.png")
print("  ADA_final_plots.png")

df = pd.read_csv('github_issues.csv')

for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    # creates a clean filename like "flask_issues.csv"
    filename = repo.split('/')[1] + '_issues.csv'
    subset.to_csv(filename, index=False)
    print(f"Saved {filename} — {len(subset)} issues")
df = pd.read_csv('github_issues.csv')
agility_scores = []

for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(durations=subset['duration_days'], event_observed=subset['event'])
    
    median_survival = kmf.median_survival_time_
    agility_scores.append({
        'repo': repo,
        'median_survival_days': median_survival,
        'agility_score': round(1 / (median_survival + 1), 4)
    })

agility_scores = []
agility_df = pd.DataFrame(agility_scores)
agility_df.to_csv('agility_scores.csv', index=False)
print("Done — agility_scores.csv saved")

df = pd.read_csv('github_issues.csv')
for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(durations=subset['duration_days'], event_observed=subset['event'])
    
    median_survival = kmf.median_survival_time_
    agility_scores.append({
        'repo': repo,
        'median_survival_days': median_survival,
        'agility_score': round(1 / (median_survival + 1), 4)
    })

agility_df = pd.DataFrame(agility_scores)
agility_df.to_csv('agility_scores.csv', index=False)
print("Done — agility_scores.csv saved")
print(agility_df)


'''

Section 1  — logs into GitHub with your token
Section 2  — defines which repos to pull from
Section 3  — pulls 500 closed issues per repo, saves to CSV
Section 4  — plots survival curves for real companies
Section 5  — calculates one agility score per company
Section 6  — generates fake stress test data and plots it
Section 7  — combines everything into one clean final plot
Section 8  — confirms all files are saved

'''