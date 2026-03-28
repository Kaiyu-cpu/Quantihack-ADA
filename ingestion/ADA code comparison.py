import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter

df = pd.read_csv('github_issues.csv')

# ── REPO TO COMPANY MAPPING ────────────────────────────────────────
repo_to_company = {
    'flask':        'Flask (Pallets)',
    'requests':     'Requests (PSF)',
    'scrapy':       'Scrapy',
    'pytest':       'Pytest',
    'tornado':      'Tornado',
    'playwright':   'Playwright (Microsoft)',
    'aws-cli':      'AWS CLI (Amazon)',
    'llama-stack':  'Llama Stack (Meta)',
    'swift':        'Swift (Apple)',
    'openai-python':'OpenAI',
}

def get_label(repo):
    short = repo.split('/')[1]
    return repo_to_company.get(short, short)

# ── 1. SUMMARY TABLE ──────────────────────────────────────────────
summary = []

for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(durations=subset['duration_days'], event_observed=subset['event'])
    
    median_survival = kmf.median_survival_time_
    summary.append({
        'company': get_label(repo),
        'repo': repo,
        'total_issues': len(subset),
        'median_days_to_fix': median_survival,
        'agility_score': round(1 / (median_survival + 1), 4),
        'avg_days_to_fix': round(subset['duration_days'].mean(), 1),
        'fastest_fix_days': subset['duration_days'].min(),
        'slowest_fix_days': subset['duration_days'].max(),
    })

summary_df = pd.DataFrame(summary).sort_values('agility_score', ascending=False)
summary_df.to_csv('company_comparison.csv', index=False)

print("\n── INVESTMENT SIGNAL RANKING ──────────────────────────────")
print(f"{'Company':<30} {'Issues':<10} {'Median Fix':<15} {'Agility Score':<15}")
print("-" * 70)
for _, row in summary_df.iterrows():
    print(f"{row['company']:<30} {row['total_issues']:<10} {row['median_days_to_fix']:<15} {row['agility_score']:<15}")

# ── 2. BAR CHART — AGILITY SCORES ─────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(20, 7))

ax1 = axes[0]
bars = ax1.bar(summary_df['company'], summary_df['agility_score'],
               color='steelblue', edgecolor='black')
ax1.set_title('Agility Score by Company\n(higher = faster fixes = better signal)',
              fontweight='bold')
ax1.set_xlabel('Company')
ax1.set_ylabel('Agility Score')
ax1.tick_params(axis='x', rotation=45)
for bar, val in zip(bars, summary_df['agility_score']):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
             str(val), ha='center', va='bottom', fontsize=9)

# ── 3. BAR CHART — TOTAL ISSUES ───────────────────────────────────
ax2 = axes[1]
bars2 = ax2.bar(summary_df['company'], summary_df['total_issues'],
                color='coral', edgecolor='black')
ax2.set_title('Total Issues in Last 2 Months\n(fewer = healthier codebase)',
              fontweight='bold')
ax2.set_xlabel('Company')
ax2.set_ylabel('Number of Issues')
ax2.tick_params(axis='x', rotation=45)
for bar, val in zip(bars2, summary_df['total_issues']):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             str(val), ha='center', va='bottom', fontsize=9)

# ── 4. BAR CHART — MEDIAN DAYS TO FIX ────────────────────────────
ax3 = axes[2]
bars3 = ax3.bar(summary_df['company'], summary_df['median_days_to_fix'],
                color='mediumseagreen', edgecolor='black')
ax3.set_title('Median Days to Fix an Issue\n(lower = more agile team)',
              fontweight='bold')
ax3.set_xlabel('Company')
ax3.set_ylabel('Days')
ax3.tick_params(axis='x', rotation=45)
for bar, val in zip(bars3, summary_df['median_days_to_fix']):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
             str(val), ha='center', va='bottom', fontsize=9)

plt.suptitle('ADA — Company Comparison: Who Should You Invest In?',
             fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('company_comparison.png', dpi=150)
plt.show()

# ── 5. SURVIVAL CURVES ALL TOGETHER ───────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
for repo in df['repo'].unique():
    subset = df[df['repo'] == repo]
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=subset['duration_days'],
        event_observed=subset['event'],
        label=get_label(repo)
    )
    kmf.plot_survival_function(ax=ax)

ax.set_title('ADA — All Companies: Issue Survival Curves',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Days Until Issue Resolved')
ax.set_ylabel('Probability Issue Still Open')
plt.tight_layout()
plt.savefig('all_companies_survival.png', dpi=150)
plt.show()

print("\nFiles saved:")
print("  company_comparison.csv")
print("  company_comparison.png")
print("  all_companies_survival.png")