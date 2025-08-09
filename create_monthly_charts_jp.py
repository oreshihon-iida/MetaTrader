#!/usr/bin/env python3
"""
月別損益グラフ作成スクリプト（日本語対応版）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
import matplotlib.font_manager as fm

# matplotlibのバックエンドをAggに設定（GUI表示を回避）
plt.switch_backend('Agg')

# スタイル設定
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# 利用可能なフォントを確認
fonts = fm.findSystemFonts(fontpaths=None)
jp_font = None

# Windows日本語フォントを探す
for fpath in fonts:
    fname = fm.get_font(fpath).family_name
    if 'Gothic' in fname or 'Mincho' in fname or 'Meiryo' in fname:
        jp_font = fname
        break

# フォント設定
if jp_font:
    plt.rcParams['font.family'] = jp_font
    print(f"使用フォント: {jp_font}")
else:
    # フォントが見つからない場合はIPAexフォントをダウンロード
    try:
        import japanize_matplotlib
        print("japanize-matplotlibを使用")
    except:
        plt.rcParams['font.family'] = 'DejaVu Sans'
        print("日本語フォントが見つかりません。英語で表示します。")

plt.rcParams['axes.unicode_minus'] = False

# CSVファイル読み込み
df = pd.read_csv('results/with_execution/trade_history.csv')
df['exit_time'] = pd.to_datetime(df['exit_time'])
df['year_month'] = df['exit_time'].dt.to_period('M')

# 月別集計
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
    
    # リスクリワード比とプロフィットファクター
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

# グラフ作成
fig = plt.figure(figsize=(16, 12))

# 1. 月別損益棒グラフ（上段左）
ax1 = plt.subplot(2, 3, 1)
colors = ['green' if x > 0 else 'red' for x in monthly_df['total_pnl']]
bars = ax1.bar(range(len(monthly_df)), monthly_df['total_pnl']/10000, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)

# 目標ラインを追加
ax1.axhline(y=50, color='blue', linestyle='--', alpha=0.5, label='月目標(50万円)', linewidth=2)
ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)

ax1.set_title('月別損益推移', fontsize=14, fontweight='bold')
ax1.set_ylabel('損益（万円）', fontsize=12)
ax1.set_xlabel('期間', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# X軸ラベル（6ヶ月ごと）
months = [str(m) for m in monthly_df['month']]
ax1.set_xticks(range(0, len(months), 6))
ax1.set_xticklabels(months[::6], rotation=45, ha='right')

# 値を棒グラフの上に表示（プラスの月のみ）
for i, (bar, val) in enumerate(zip(bars, monthly_df['total_pnl']/10000)):
    if val > 0:
        ax1.text(bar.get_x() + bar.get_width()/2, val + 1, f'{val:.1f}', 
                ha='center', va='bottom', fontsize=8)

# 2. 累積損益曲線（上段中央）
ax2 = plt.subplot(2, 3, 2)
ax2.plot(range(len(monthly_df)), monthly_df['balance']/10000, color='darkblue', linewidth=2, label='残高')
ax2.fill_between(range(len(monthly_df)), 300, monthly_df['balance']/10000, 
                 where=(monthly_df['balance']/10000 >= 300), color='lightgreen', alpha=0.3, label='利益領域')
ax2.fill_between(range(len(monthly_df)), 300, monthly_df['balance']/10000, 
                 where=(monthly_df['balance']/10000 < 300), color='lightcoral', alpha=0.3, label='損失領域')

ax2.axhline(y=300, color='gray', linestyle='--', alpha=0.5, label='初期資金(300万円)')
ax2.set_title('累積残高推移', fontsize=14, fontweight='bold')
ax2.set_ylabel('残高（万円）', fontsize=12)
ax2.set_xlabel('期間', fontsize=12)
ax2.legend(loc='lower left')
ax2.grid(True, alpha=0.3)
ax2.set_xticks(range(0, len(months), 6))
ax2.set_xticklabels(months[::6], rotation=45, ha='right')

# 3. 勝率とプロフィットファクター（上段右）
ax3 = plt.subplot(2, 3, 3)
ax3_2 = ax3.twinx()

# 勝率（棒グラフ）
bars_wr = ax3.bar(range(len(monthly_df)), monthly_df['win_rate'], alpha=0.4, color='skyblue', label='勝率')
# プロフィットファクター（線グラフ）
line_pf = ax3_2.plot(range(len(monthly_df)), monthly_df['profit_factor'], color='orange', linewidth=2, marker='o', markersize=4, label='PF')
ax3_2.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, linewidth=1)

ax3.set_title('勝率とプロフィットファクター', fontsize=14, fontweight='bold')
ax3.set_ylabel('勝率（%）', fontsize=12, color='skyblue')
ax3_2.set_ylabel('プロフィットファクター', fontsize=12, color='orange')
ax3.set_xlabel('期間', fontsize=12)
ax3.tick_params(axis='y', labelcolor='skyblue')
ax3_2.tick_params(axis='y', labelcolor='orange')
ax3.set_ylim(0, 100)
ax3_2.set_ylim(0, 3)
ax3.grid(True, alpha=0.3)
ax3.set_xticks(range(0, len(months), 6))
ax3.set_xticklabels(months[::6], rotation=45, ha='right')

# 凡例を結合
lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3_2.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# 4. 年別集計（下段左）
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
ax4.axhline(y=600, color='blue', linestyle='--', alpha=0.5, label='年間目標(600万円)')

ax4.set_title('年別損益', fontsize=14, fontweight='bold')
ax4.set_ylabel('損益（万円）', fontsize=12)
ax4.set_xlabel('年', fontsize=12)
ax4.legend()
ax4.grid(True, alpha=0.3)

# 値を表示
for bar, val in zip(bars_year, yearly_pnl):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2, height + (10 if height > 0 else -20),
            f'{val:.1f}万円', ha='center', va='bottom' if height > 0 else 'top', fontsize=10, fontweight='bold')

# 5. リスクリワード比推移（下段中央）
ax5 = plt.subplot(2, 3, 5)
ax5.plot(range(len(monthly_df)), monthly_df['risk_reward'], color='purple', linewidth=2, marker='s', markersize=4)
ax5.axhline(y=2.0, color='green', linestyle='--', alpha=0.5, label='理想値(2.0)', linewidth=1)
ax5.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='最低値(1.0)', linewidth=1)
ax5.fill_between(range(len(monthly_df)), 2.0, monthly_df['risk_reward'], 
                 where=(monthly_df['risk_reward'] >= 2.0), color='lightgreen', alpha=0.3)

ax5.set_title('リスクリワード比推移', fontsize=14, fontweight='bold')
ax5.set_ylabel('R/R比', fontsize=12)
ax5.set_xlabel('期間', fontsize=12)
ax5.legend()
ax5.grid(True, alpha=0.3)
ax5.set_xticks(range(0, len(months), 6))
ax5.set_xticklabels(months[::6], rotation=45, ha='right')

# 6. 月別取引数と損益の散布図（下段右）
ax6 = plt.subplot(2, 3, 6)
scatter = ax6.scatter(monthly_df['trades'], monthly_df['total_pnl']/10000, 
                     c=monthly_df['win_rate'], s=100, cmap='RdYlGn', alpha=0.6, edgecolors='black', linewidth=1)
ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
ax6.axvline(x=50, color='gray', linestyle='--', alpha=0.3)

# カラーバー追加
cbar = plt.colorbar(scatter, ax=ax6)
cbar.set_label('勝率(%)', fontsize=10)

ax6.set_title('取引数 vs 損益（色:勝率）', fontsize=14, fontweight='bold')
ax6.set_xlabel('月間取引数', fontsize=12)
ax6.set_ylabel('月間損益（万円）', fontsize=12)
ax6.grid(True, alpha=0.3)

# 全体タイトル
fig.suptitle('MetaTrader 月別パフォーマンス分析（2022年8月～2025年8月）', fontsize=16, fontweight='bold', y=1.02)

# レイアウト調整
plt.tight_layout()

# 保存（GUI表示せずに直接保存）
plt.savefig('results/with_execution/monthly_performance_charts_jp.png', dpi=150, bbox_inches='tight')
print("グラフを results/with_execution/monthly_performance_charts_jp.png に保存しました")

# サマリー統計も出力
print("\n" + "="*60)
print("月別パフォーマンスサマリー")
print("="*60)
print(f"総取引期間: {len(monthly_df)}ヶ月")
print(f"プラス月: {len(monthly_df[monthly_df['total_pnl'] > 0])}ヶ月")
print(f"マイナス月: {len(monthly_df[monthly_df['total_pnl'] < 0])}ヶ月")
print(f"最高月: {monthly_df.loc[monthly_df['total_pnl'].idxmax(), 'month']} ({monthly_df['total_pnl'].max():,.0f}円)")
print(f"最悪月: {monthly_df.loc[monthly_df['total_pnl'].idxmin(), 'month']} ({monthly_df['total_pnl'].min():,.0f}円)")
print(f"月平均損益: {monthly_df['total_pnl'].mean():,.0f}円")
print(f"平均勝率: {monthly_df['win_rate'].mean():.1f}%")
print(f"平均R/R比: {monthly_df['risk_reward'].mean():.2f}")
print(f"平均PF: {monthly_df['profit_factor'].mean():.2f}")