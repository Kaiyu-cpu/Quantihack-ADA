import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from lifelines import KaplanMeierFitter
from scipy import stats
from datetime import timedelta
from dataclasses import dataclass

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
INITIAL_CAPITAL           = 10_000
RISK_PER_TRADE_PCT        = 10
COMMISSION_PCT            = 0.1
STOP_LOSS_PCT             = 5
TAKE_PROFIT_PCT           = 10
BACKTEST_PERIODS_PER_YEAR = 365
SIGNAL_THRESHOLD          = 0.1

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

COMPANY_COLORS = {
    'Flask (Pallets)':        '#e6194b',
    'Requests (PSF)':         '#3cb44b',
    'Scrapy':                 '#4363d8',
    'Pytest':                 '#f58231',
    'Tornado':                '#911eb4',
    'Playwright (Microsoft)': '#42d4f4',
    'AWS CLI (Amazon)':       '#f032e6',
    'Llama Stack (Meta)':     '#bfef45',
    'Swift (Apple)':          '#fabed4',
    'OpenAI':                 '#469990',
}

def get_label(repo):
    short = repo.split('/')[1]
    return repo_to_company.get(short, short)

def get_color(company):
    return COMPANY_COLORS.get(company, '#aaaaaa')

# ══════════════════════════════════════════════════════════════════
# PART 1 — ROLLING GITHUB SIGNAL
# ══════════════════════════════════════════════════════════════════
print("Loading GitHub issues...")
df = pd.read_csv('github_issues.csv')
df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
df['closed_at']  = pd.to_datetime(df['closed_at'],  utc=True)

def compute_signal(subset):
    if len(subset) < 3:
        return None
    kmf = KaplanMeierFitter()
    kmf.fit(durations=subset['duration_days'], event_observed=subset['event'])
    median_survival = kmf.median_survival_time_
    agility  = 1 / (median_survival + 1)
    avg_fix  = subset['duration_days'].mean()
    slope    = stats.linregress(np.arange(len(subset)),
                                subset['duration_days'].values)[0] if len(subset) > 2 else 0.0
    cv       = subset['duration_days'].std() / (avg_fix + 1)
    backlog  = (subset['duration_days'] > 7).sum() / len(subset)
    return dict(agility=agility, avg_fix=avg_fix,
                trend_slope=slope, cv=cv, backlog=backlog,
                volume=len(subset))

def normalise_cross_section(day_df):
    def norm(s):
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5]*len(s), index=s.index)
        return (s - mn) / (mx - mn)
    day_df['n_agility']     = norm(day_df['agility'])
    day_df['n_fix_speed']   = 1 - norm(day_df['avg_fix'])
    day_df['n_trend']       = 1 - norm(day_df['trend_slope'])
    day_df['n_consistency'] = 1 - norm(day_df['cv'])
    day_df['n_backlog']     = 1 - norm(day_df['backlog'])
    day_df['n_volume']      = 1 - norm(day_df['volume'])
    weights = dict(n_agility=0.30, n_fix_speed=0.20,
                   n_consistency=0.15, n_backlog=0.15,
                   n_trend=0.10, n_volume=0.10)
    day_df['raw_signal'] = sum(w * day_df[col] for col, w in weights.items())
    day_df['investment_signal'] = (day_df['raw_signal'] * 2 - 1).round(4)
    return day_df

print("Computing rolling daily signals (14-day window)...")
start_date = df['created_at'].min().normalize()
end_date   = df['created_at'].max().normalize()
date_range = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')

all_signals = []
for current_date in date_range:
    window_start = current_date - timedelta(days=14)
    day_rows = []
    for repo in df['repo'].unique():
        subset = df[
            (df['repo'] == repo) &
            (df['created_at'] >= window_start) &
            (df['created_at'] <= current_date)
        ].copy()
        metrics = compute_signal(subset)
        if metrics is None:
            continue
        metrics['repo']    = repo
        metrics['company'] = get_label(repo)
        metrics['date']    = current_date
        day_rows.append(metrics)
    if len(day_rows) < 2:
        continue
    day_df = normalise_cross_section(pd.DataFrame(day_rows))
    all_signals.append(day_df)

signals_df = pd.concat(all_signals, ignore_index=True)
signals_df.to_csv('rolling_signals.csv', index=False)

best_per_day = (
    signals_df.sort_values('investment_signal', ascending=False)
              .groupby('date').first().reset_index()
              [['date', 'company', 'investment_signal']]
)
best_per_day.columns = ['date', 'best_company', 'best_signal']
best_per_day['date'] = pd.to_datetime(best_per_day['date'], utc=True)

# ── average signal per company for matrix ─────────────────────────
final_signal = (
    signals_df.groupby('company')['investment_signal']
    .agg(['mean', 'std']).rename(columns={'mean':'avg_signal','std':'signal_std'})
    .reset_index()
)
final_signal['avg_signal'] = final_signal['avg_signal'].round(3)
final_signal['confidence'] = (1 - final_signal['signal_std'].fillna(0)).round(3)
final_signal = final_signal.sort_values('avg_signal', ascending=False)

# ══════════════════════════════════════════════════════════════════
# PART 2 — LOAD POLYMARKET CRUDE OIL PRICES
# ══════════════════════════════════════════════════════════════════
print("Loading Polymarket crude oil data...")
prices_raw = pd.read_csv('crude_oil_prices.csv')
prices_raw['timestamp'] = pd.to_datetime(prices_raw['timestamp'], utc=True, errors='coerce')
prices_raw = prices_raw.dropna(subset=['timestamp', 'price']).sort_values('timestamp')
prices_daily = (
    prices_raw.groupby(prices_raw['timestamp'].dt.normalize())['price']
              .last().reset_index()
)
prices_daily.columns = ['date', 'price']
prices_daily['date'] = pd.to_datetime(prices_daily['date'], utc=True)

# ══════════════════════════════════════════════════════════════════
# PART 3 — MERGE SIGNAL + PRICES
# ══════════════════════════════════════════════════════════════════
merged = pd.merge(prices_daily, best_per_day, on='date', how='inner')
merged = merged.sort_values('date').reset_index(drop=True)
merged['signal'] = np.where(merged['best_signal'] >  SIGNAL_THRESHOLD,  1,
               np.where(merged['best_signal'] < -SIGNAL_THRESHOLD, -1, 0))

# ══════════════════════════════════════════════════════════════════
# PART 4 — BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════
@dataclass
class Position:
    entry_price: float
    shares: float
    stop_loss_pct: float
    take_profit_pct: float
    def current_value(self, price):   return self.shares * price
    def should_stop_loss(self, price):   return price <= self.entry_price * (1 - self.stop_loss_pct/100)
    def should_take_profit(self, price): return price >= self.entry_price * (1 + self.take_profit_pct/100)

def run_backtest(price_series, signal_series):
    df_bt = pd.DataFrame({'close': price_series, 'signal': signal_series}).dropna().sort_index()
    df_bt['signal_prev'] = df_bt['signal'].shift(1).fillna(0)
    capital, position, current_trade = INITIAL_CAPITAL, None, None
    trades, equity_curve = [], []
    for date, row in df_bt.iterrows():
        price, signal = row['close'], row['signal_prev']
        if position and current_trade:
            exit_reason = None
            if position.should_stop_loss(price):   exit_reason = 'stop_loss'
            elif position.should_take_profit(price): exit_reason = 'take_profit'
            elif signal == -1:                       exit_reason = 'signal'
            if exit_reason:
                proceeds   = position.current_value(price)
                commission = proceeds * (COMMISSION_PCT / 100)
                capital   += proceeds - commission
                current_trade.update({
                    'exit_date':  str(date), 'exit_price': round(price, 6),
                    'pnl':        round(proceeds - position.entry_price * position.shares, 6),
                    'reason':     exit_reason,
                })
                trades.append(current_trade)
                position, current_trade = None, None
        if signal == 1 and position is None:
            amount     = capital * (RISK_PER_TRADE_PCT / 100)
            commission = amount * (COMMISSION_PCT / 100)
            shares     = (amount - commission) / price
            capital   -= amount
            position   = Position(price, shares, STOP_LOSS_PCT, TAKE_PROFIT_PCT)
            company_on_date = merged.loc[merged['date'] == date, 'best_company']
            current_trade = {
                'entry_date':  str(date), 'entry_price': round(price, 6),
                'shares':      round(shares, 6),
                'company':     company_on_date.values[0] if len(company_on_date) else 'unknown',
            }
        portfolio_value = capital + (position.current_value(price) if position else 0)
        equity_curve.append({'date': str(date), 'value': round(portfolio_value, 6)})
    return trades, equity_curve, capital

prices_indexed  = merged.set_index('date')['price']
signals_indexed = merged.set_index('date')['signal']
trades, equity_curve, final_capital = run_backtest(prices_indexed, signals_indexed)

# ══════════════════════════════════════════════════════════════════
# PART 5 — METRICS
# ══════════════════════════════════════════════════════════════════
equity_values = pd.Series([e['value'] for e in equity_curve])
total_return  = (equity_values.iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
daily_returns = equity_values.pct_change().dropna()
sharpe        = (daily_returns.mean() / daily_returns.std()) * np.sqrt(BACKTEST_PERIODS_PER_YEAR) \
                if daily_returns.std() != 0 else 0
max_drawdown  = ((equity_values - equity_values.cummax()) / equity_values.cummax()).min() * 100
buy_hold      = (merged['price'].iloc[-1] / merged['price'].iloc[0] - 1) * 100
trades_df     = pd.DataFrame(trades) if trades else pd.DataFrame()
win_rate      = (trades_df['pnl'] > 0).mean() * 100 if len(trades_df) > 0 else 0

print("\n══ ADA BACKTEST RESULTS ══════════════════════════════════")
print(f"  Initial Capital:    £{INITIAL_CAPITAL:,.2f}")
print(f"  Final Capital:      £{equity_values.iloc[-1]:,.2f}")
print(f"  Total Return:       {total_return:.2f}%")
print(f"  Buy & Hold Return:  {buy_hold:.2f}%")
print(f"  Sharpe Ratio:       {sharpe:.2f}")
print(f"  Max Drawdown:       {max_drawdown:.2f}%")
print(f"  Total Trades:       {len(trades)}")
print(f"  Win Rate:           {win_rate:.1f}%")
print("══════════════════════════════════════════════════════════")

equity_df = pd.DataFrame(equity_curve)
equity_df.to_csv('equity_curve.csv', index=False)
if len(trades_df) > 0:
    trades_df.to_csv('trades.csv', index=False)

# ══════════════════════════════════════════════════════════════════
# PART 6 — PLOTS
# ══════════════════════════════════════════════════════════════════

# ── shared x-axis tick helper ─────────────────────────────────────
def set_date_ticks(ax, dates, max_ticks=10):
    dates = pd.to_datetime(dates)
    step  = max(1, len(dates) // max_ticks)
    ticks = list(range(0, len(dates), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [dates.iloc[i].strftime('%d %b %Y') for i in ticks],
        rotation=45, ha='right', fontsize=8
    )

fig = plt.figure(figsize=(18, 22))
fig.suptitle('ADA — Signal Half-Life: Full Backtest Results',
             fontsize=16, fontweight='bold', y=0.98)

# ── PLOT 1: Equity Curve ──────────────────────────────────────────
ax1 = fig.add_subplot(4, 1, 1)
ax1.plot(range(len(equity_df)), equity_df['value'],
         color='steelblue', linewidth=2, label='ADA Strategy')
ax1.axhline(y=INITIAL_CAPITAL, color='grey', linestyle='--',
            linewidth=1, label=f'Initial Capital £{INITIAL_CAPITAL:,}')
ax1.fill_between(range(len(equity_df)), INITIAL_CAPITAL, equity_df['value'],
                 where=equity_df['value'] >= INITIAL_CAPITAL,
                 alpha=0.15, color='green', label='Above initial')
ax1.fill_between(range(len(equity_df)), INITIAL_CAPITAL, equity_df['value'],
                 where=equity_df['value'] < INITIAL_CAPITAL,
                 alpha=0.15, color='red', label='Below initial')
ax1.set_title(f'Equity Curve   |   Return: {total_return:.2f}%   '
              f'Sharpe: {sharpe:.2f}   Max Drawdown: {max_drawdown:.2f}%',
              fontsize=11, fontweight='bold')
ax1.set_ylabel('Portfolio Value (£)', fontsize=10)
ax1.legend(fontsize=9)
set_date_ticks(ax1, equity_df['date'])

# ── PLOT 2: Crude Oil Price + Coloured Trade Signals ─────────────
ax2 = fig.add_subplot(4, 1, 2)
ax2.plot(range(len(merged)), merged['price'],
         color='black', linewidth=1.2, label='Crude Oil Price', zorder=2)

# colour each buy dot by which company triggered it
for i, row in merged[merged['signal'] == 1].iterrows():
    color = get_color(row['best_company'])
    ax2.scatter(i, row['price'], color=color, marker='^',
                s=80, zorder=5, edgecolors='black', linewidths=0.5)

for i, row in merged[merged['signal'] == -1].iterrows():
    ax2.scatter(i, row['price'], color='red', marker='v',
                s=80, zorder=5, edgecolors='black', linewidths=0.5,
                label='Sell Signal')

# company colour legend for buy dots
company_patches = [
    mpatches.Patch(color=get_color(c), label=c)
    for c in signals_df['company'].unique()
    if c in COMPANY_COLORS
]
sell_patch = mpatches.Patch(color='red', label='Sell Signal (exit)')
ax2.legend(handles=company_patches + [sell_patch],
           fontsize=7, loc='upper left',
           title='Buy triggered by:', title_fontsize=8,
           ncol=2, framealpha=0.9)
ax2.set_title('Crude Oil Price   |   Buy Signals Coloured by Triggering Company',
              fontsize=11, fontweight='bold')
ax2.set_ylabel('Price', fontsize=10)
set_date_ticks(ax2, merged['date'])

# ── PLOT 3: Signal per company over time ─────────────────────────
ax3 = fig.add_subplot(4, 1, 3)
for company in signals_df['company'].unique():
    subset = signals_df[signals_df['company'] == company].sort_values('date')
    ax3.plot(range(len(subset)), subset['investment_signal'],
             label=company, color=get_color(company), linewidth=1.4, alpha=0.85)
ax3.axhline(y=SIGNAL_THRESHOLD,  color='green', linestyle=':', linewidth=1,
            label=f'Buy threshold ({SIGNAL_THRESHOLD})')
ax3.axhline(y=-SIGNAL_THRESHOLD, color='red',   linestyle=':', linewidth=1,
            label=f'Sell threshold (-{SIGNAL_THRESHOLD})')
ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.4)
ax3.set_title('Investment Signal Over Time — All Companies (14-day rolling window)',
              fontsize=11, fontweight='bold')
ax3.set_ylabel('Signal (-1 to 1)', fontsize=10)
ax3.legend(fontsize=7, ncol=3, loc='upper left', framealpha=0.9)
ax3.set_ylim(-1.1, 1.1)
# x ticks from signals date range
signal_dates = signals_df['date'].sort_values().unique()
signal_dates = pd.Series(signal_dates)
step = max(1, len(signal_dates) // 10)
ax3.set_xticks(range(0, len(signal_dates), step))
ax3.set_xticklabels(
    [pd.Timestamp(signal_dates.iloc[i]).strftime('%d %b %Y')
     for i in range(0, len(signal_dates), step)],
    rotation=45, ha='right', fontsize=8
)

# ── PLOT 4: Company Matrix Heatmap ───────────────────────────────
ax4 = fig.add_subplot(4, 1, 4)
metric_cols   = ['n_agility','n_fix_speed','n_consistency','n_backlog','n_trend','n_volume']
metric_labels = ['Agility','Fix Speed','Consistency','Backlog','Trend','Issue Vol']

avg_metrics = signals_df.groupby('company')[metric_cols].mean()
avg_metrics['avg_signal'] = final_signal.set_index('company')['avg_signal']
avg_metrics = avg_metrics.sort_values('avg_signal', ascending=False)

matrix_data  = avg_metrics[metric_cols + ['avg_signal']].values
companies_list = avg_metrics.index.tolist()
all_labels   = metric_labels + ['AVG SIGNAL']

im = ax4.imshow(matrix_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
ax4.set_xticks(range(len(all_labels)))
ax4.set_xticklabels(all_labels, fontsize=10, fontweight='bold')
ax4.set_yticks(range(len(companies_list)))
ax4.set_yticklabels(companies_list, fontsize=9)

for i in range(len(companies_list)):
    for j in range(len(all_labels)):
        val = matrix_data[i][j]
        ax4.text(j, i, f'{val:.2f}', ha='center', va='center',
                 fontsize=8, fontweight='bold',
                 color='black' if 0.2 < val < 0.8 else 'white')

plt.colorbar(im, ax=ax4, label='Score (0 = worst, 1 = best)', shrink=0.8)
ax4.set_title('Company Signal Matrix — Averaged Across All Daily Windows',
              fontsize=11, fontweight='bold')

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig('ADA_backtest_results.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nAll files saved:")
print("  rolling_signals.csv")
print("  equity_curve.csv")
print("  trades.csv")
print("  ADA_backtest_results.png")