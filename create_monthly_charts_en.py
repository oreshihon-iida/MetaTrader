#!/usr/bin/env python3
"""
Monthly P&L Charts Creation Script (English Version)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns

# Font settings (avoid Japanese font issues)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# Style settings
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Load CSV file
df = pd.read_csv('results/with_execution/trade_history.csv')
df['exit_time'] = pd.to_datetime(df['exit_time'])
df['year_month'] = df['exit_time'].dt.to_period('M')

# Monthly aggregation
monthly_stats = []
for month in df['year_month'].unique():
    month_data = df[df['year_month'] == month]
    wins = month_data[month_data['pnl_amount'] > 0]
    losses = month_data[month_data['pnl_amount'] < 0]
    
    stats = {
        'month': month,
        'total_pnl': month_data['pnl_amount'].sum(),
        'trades': len(month_data),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(month_data) * 100 if len(month_data) > 0 else 0,
        'avg_win': wins['pnl_amount'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl_amount'].mean() if len(losses) > 0 else 0,
    }
    
    # Risk-Reward Ratio and Profit Factor
    if stats['avg_loss'] != 0:
        stats['risk_reward'] = abs(stats['avg_win'] / stats['avg_loss'])
    else:
        stats['risk_reward'] = 0
    
    if losses['pnl_amount'].sum() != 0:
        stats['profit_factor'] = wins['pnl_amount'].sum() / abs(losses['pnl_amount'].sum())
    else:
        stats['profit_factor'] = 0 if len(wins) == 0 else 999
    
    monthly_stats.append(stats)

monthly_df = pd.DataFrame(monthly_stats)
monthly_df['cumulative_pnl'] = monthly_df['total_pnl'].cumsum()
monthly_df['balance'] = 3000000 + monthly_df['cumulative_pnl']
monthly_df['month_str'] = monthly_df['month'].astype(str)

# Create graphs
fig = plt.figure(figsize=(16, 12))

# 1. Monthly P&L Bar Chart (Top Left)
ax1 = plt.subplot(2, 3, 1)
colors = ['green' if x > 0 else 'red' for x in monthly_df['total_pnl']]
bars = ax1.bar(range(len(monthly_df)), monthly_df['total_pnl']/10000, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)

# Add target line
ax1.axhline(y=50, color='blue', linestyle='--', alpha=0.5, label='Monthly Target (500K JPY)', linewidth=2)
ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)

ax1.set_title('Monthly P&L', fontsize=14, fontweight='bold')
ax1.set_ylabel('P&L (10K JPY)', fontsize=12)
ax1.set_xlabel('Period', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# X-axis labels (every 6 months)
months = [str(m) for m in monthly_df['month']]
ax1.set_xticks(range(0, len(months), 6))
ax1.set_xticklabels(months[::6], rotation=45, ha='right')

# Display values on bars (positive months only)
for i, (bar, val) in enumerate(zip(bars, monthly_df['total_pnl']/10000)):
    if val > 0:
        ax1.text(bar.get_x() + bar.get_width()/2, val + 1, f'{val:.1f}', 
                ha='center', va='bottom', fontsize=8)

# 2. Cumulative Balance Curve (Top Center)
ax2 = plt.subplot(2, 3, 2)
ax2.plot(range(len(monthly_df)), monthly_df['balance']/10000, color='darkblue', linewidth=2, label='Balance')
ax2.fill_between(range(len(monthly_df)), 300, monthly_df['balance']/10000, 
                 where=(monthly_df['balance']/10000 >= 300), color='lightgreen', alpha=0.3, label='Profit Zone')
ax2.fill_between(range(len(monthly_df)), 300, monthly_df['balance']/10000, 
                 where=(monthly_df['balance']/10000 < 300), color='lightcoral', alpha=0.3, label='Loss Zone')

ax2.axhline(y=300, color='gray', linestyle='--', alpha=0.5, label='Initial Capital (3M JPY)')
ax2.set_title('Cumulative Balance', fontsize=14, fontweight='bold')
ax2.set_ylabel('Balance (10K JPY)', fontsize=12)
ax2.set_xlabel('Period', fontsize=12)
ax2.legend(loc='lower left')
ax2.grid(True, alpha=0.3)
ax2.set_xticks(range(0, len(months), 6))
ax2.set_xticklabels(months[::6], rotation=45, ha='right')

# 3. Win Rate and Profit Factor (Top Right)
ax3 = plt.subplot(2, 3, 3)
ax3_2 = ax3.twinx()

# Win Rate (bar chart)
bars_wr = ax3.bar(range(len(monthly_df)), monthly_df['win_rate'], alpha=0.4, color='skyblue', label='Win Rate')
# Profit Factor (line chart)
line_pf = ax3_2.plot(range(len(monthly_df)), monthly_df['profit_factor'], color='orange', linewidth=2, marker='o', markersize=4, label='PF')
ax3_2.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, linewidth=1)

ax3.set_title('Win Rate & Profit Factor', fontsize=14, fontweight='bold')
ax3.set_ylabel('Win Rate (%)', fontsize=12, color='skyblue')
ax3_2.set_ylabel('Profit Factor', fontsize=12, color='orange')
ax3.set_xlabel('Period', fontsize=12)
ax3.tick_params(axis='y', labelcolor='skyblue')
ax3_2.tick_params(axis='y', labelcolor='orange')
ax3.set_ylim(0, 100)
ax3_2.set_ylim(0, 3)
ax3.grid(True, alpha=0.3)
ax3.set_xticks(range(0, len(months), 6))
ax3.set_xticklabels(months[::6], rotation=45, ha='right')

# Combine legends
lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3_2.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# 4. Yearly Summary (Bottom Left)
ax4 = plt.subplot(2, 3, 4)
yearly_pnl = []
years = []
for year in df['exit_time'].dt.year.unique():
    year_data = monthly_df[monthly_df['month'].astype(str).str.startswith(str(year))]
    yearly_pnl.append(year_data['total_pnl'].sum()/10000)
    years.append(str(year))

colors_year = ['green' if x > 0 else 'red' for x in yearly_pnl]
bars_year = ax4.bar(years, yearly_pnl, color=colors_year, alpha=0.7, edgecolor='black', linewidth=1)
ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
ax4.axhline(y=600, color='blue', linestyle='--', alpha=0.5, label='Annual Target (6M JPY)')

ax4.set_title('Yearly P&L', fontsize=14, fontweight='bold')
ax4.set_ylabel('P&L (10K JPY)', fontsize=12)
ax4.set_xlabel('Year', fontsize=12)
ax4.legend()
ax4.grid(True, alpha=0.3)

# Display values
for bar, val in zip(bars_year, yearly_pnl):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2, height + (10 if height > 0 else -20),
            f'{val:.1f}', ha='center', va='bottom' if height > 0 else 'top', fontsize=10, fontweight='bold')

# 5. Risk-Reward Ratio Trend (Bottom Center)
ax5 = plt.subplot(2, 3, 5)
ax5.plot(range(len(monthly_df)), monthly_df['risk_reward'], color='purple', linewidth=2, marker='s', markersize=4)
ax5.axhline(y=2.0, color='green', linestyle='--', alpha=0.5, label='Ideal (2.0)', linewidth=1)
ax5.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Minimum (1.0)', linewidth=1)
ax5.fill_between(range(len(monthly_df)), 2.0, monthly_df['risk_reward'], 
                 where=(monthly_df['risk_reward'] >= 2.0), color='lightgreen', alpha=0.3)

ax5.set_title('Risk-Reward Ratio Trend', fontsize=14, fontweight='bold')
ax5.set_ylabel('R/R Ratio', fontsize=12)
ax5.set_xlabel('Period', fontsize=12)
ax5.legend()
ax5.grid(True, alpha=0.3)
ax5.set_xticks(range(0, len(months), 6))
ax5.set_xticklabels(months[::6], rotation=45, ha='right')

# 6. Trades vs P&L Scatter (Bottom Right)
ax6 = plt.subplot(2, 3, 6)
scatter = ax6.scatter(monthly_df['trades'], monthly_df['total_pnl']/10000, 
                     c=monthly_df['win_rate'], s=100, cmap='RdYlGn', alpha=0.6, edgecolors='black', linewidth=1)
ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
ax6.axvline(x=50, color='gray', linestyle='--', alpha=0.3)

# Add colorbar
cbar = plt.colorbar(scatter, ax=ax6)
cbar.set_label('Win Rate (%)', fontsize=10)

ax6.set_title('Trades vs P&L (Color: Win Rate)', fontsize=14, fontweight='bold')
ax6.set_xlabel('Monthly Trades', fontsize=12)
ax6.set_ylabel('Monthly P&L (10K JPY)', fontsize=12)
ax6.grid(True, alpha=0.3)

# Overall title
fig.suptitle('MetaTrader Monthly Performance Analysis (Aug 2022 - Aug 2025)', fontsize=16, fontweight='bold', y=1.02)

# Layout adjustment
plt.tight_layout()

# Save
plt.savefig('results/with_execution/monthly_performance_charts_en.png', dpi=150, bbox_inches='tight')
print("Chart saved to results/with_execution/monthly_performance_charts_en.png")

# Display
plt.show()

# Output summary statistics
print("\n" + "="*60)
print("Monthly Performance Summary")
print("="*60)
print(f"Total Period: {len(monthly_df)} months")
print(f"Positive Months: {len(monthly_df[monthly_df['total_pnl'] > 0])} months")
print(f"Negative Months: {len(monthly_df[monthly_df['total_pnl'] < 0])} months")
print(f"Best Month: {monthly_df.loc[monthly_df['total_pnl'].idxmax(), 'month']} ({monthly_df['total_pnl'].max():,.0f} JPY)")
print(f"Worst Month: {monthly_df.loc[monthly_df['total_pnl'].idxmin(), 'month']} ({monthly_df['total_pnl'].min():,.0f} JPY)")
print(f"Monthly Average P&L: {monthly_df['total_pnl'].mean():,.0f} JPY")
print(f"Average Win Rate: {monthly_df['win_rate'].mean():.1f}%")
print(f"Average R/R Ratio: {monthly_df['risk_reward'].mean():.2f}")
print(f"Average PF: {monthly_df['profit_factor'].mean():.2f}")