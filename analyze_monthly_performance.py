#!/usr/bin/env python3
"""
月別パフォーマンス詳細分析スクリプト
"""

import pandas as pd
import numpy as np

# CSVファイル読み込み
df = pd.read_csv('results/with_execution/trade_history.csv')

# exit_timeをdatetime型に変換
df['exit_time'] = pd.to_datetime(df['exit_time'])

# 月別グループ化
df['year_month'] = df['exit_time'].dt.to_period('M')

# 月別集計（詳細版）
monthly_stats = []

for month in df['year_month'].unique():
    month_data = df[df['year_month'] == month]
    
    wins = month_data[month_data['pnl_amount'] > 0]
    losses = month_data[month_data['pnl_amount'] < 0]
    
    stats = {
        'month': month,
        'trades': len(month_data),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(month_data) * 100 if len(month_data) > 0 else 0,
        'total_pnl': month_data['pnl_amount'].sum(),
        'avg_win': wins['pnl_amount'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl_amount'].mean() if len(losses) > 0 else 0,
        'total_win_amount': wins['pnl_amount'].sum() if len(wins) > 0 else 0,
        'total_loss_amount': losses['pnl_amount'].sum() if len(losses) > 0 else 0,
        'max_win': wins['pnl_amount'].max() if len(wins) > 0 else 0,
        'max_loss': losses['pnl_amount'].min() if len(losses) > 0 else 0,
    }
    
    # リスクリワード比（平均利益 / 平均損失の絶対値）
    if stats['avg_loss'] != 0:
        stats['risk_reward'] = abs(stats['avg_win'] / stats['avg_loss'])
    else:
        stats['risk_reward'] = 0
    
    # プロフィットファクター（総利益 / 総損失の絶対値）
    if stats['total_loss_amount'] != 0:
        stats['profit_factor'] = stats['total_win_amount'] / abs(stats['total_loss_amount'])
    else:
        stats['profit_factor'] = 0
    
    # ペイオフレシオ（勝率を考慮した期待値）
    stats['expected_value'] = (stats['win_rate']/100 * stats['avg_win']) + ((100-stats['win_rate'])/100 * stats['avg_loss'])
    
    monthly_stats.append(stats)

monthly_df = pd.DataFrame(monthly_stats)
monthly_df['cumulative_pnl'] = monthly_df['total_pnl'].cumsum()
monthly_df['balance'] = 3000000 + monthly_df['cumulative_pnl']

print('=' * 120)
print('月別取引パフォーマンス詳細分析（2022年8月 - 2025年8月）')
print('=' * 120)
print()

# 年ごとにグループ化して表示
for year in df['exit_time'].dt.year.unique():
    year_data = monthly_df[monthly_df['month'].astype(str).str.startswith(str(year))]
    if not year_data.empty:
        print(f'\n【{year}年】')
        print('-' * 115)
        print(f'{"月":<6} {"取引":>5} {"勝率":>6} {"R/R比":>6} {"PF":>6} {"平均利益":>10} {"平均損失":>10} {"期待値":>10} {"月間損益":>12} {"判定":<6}')
        print('-' * 115)
        
        for _, row in year_data.iterrows():
            month_str = str(row['month']).replace(str(year) + '-', '') + '月'
            win_rate_str = f"{row['win_rate']:.1f}%"
            rr_str = f"{row['risk_reward']:.2f}" if row['risk_reward'] > 0 else '-'
            pf_str = f"{row['profit_factor']:.2f}" if row['profit_factor'] > 0 else '-'
            avg_win_str = f"{row['avg_win']:+,.0f}" if row['avg_win'] != 0 else '-'
            avg_loss_str = f"{row['avg_loss']:+,.0f}" if row['avg_loss'] != 0 else '-'
            ev_str = f"{row['expected_value']:+,.0f}"
            pnl_str = f"{row['total_pnl']:+,.0f}円"
            
            # 判定（期待値がプラスなら○、実際の損益もプラスなら◎）
            if row['expected_value'] > 0 and row['total_pnl'] > 0:
                judge = '◎'
            elif row['expected_value'] > 0:
                judge = '○'
            elif row['total_pnl'] > 0:
                judge = '△'
            else:
                judge = '×'
            
            print(f'{month_str:<6} {int(row.trades):>5} {win_rate_str:>6} {rr_str:>6} {pf_str:>6} {avg_win_str:>10} {avg_loss_str:>10} {ev_str:>10} {pnl_str:>12} {judge:<6}')
        
        # 年間集計
        year_total_pnl = year_data['total_pnl'].sum()
        year_avg_rr = year_data['risk_reward'].mean()
        year_avg_pf = year_data['profit_factor'].mean()
        year_avg_ev = year_data['expected_value'].mean()
        
        print('-' * 115)
        print(f'{"年間":<6} {"平均":>5} {"":>6} {year_avg_rr:>5.2f}x {year_avg_pf:>5.2f}x {"":>10} {"":>10} {year_avg_ev:>9,.0f}円 {year_total_pnl:>11,.0f}円')

# 全期間分析
print()
print('=' * 120)
print('パフォーマンス指標の解説と全期間サマリー')
print('=' * 120)
print()
print('【指標の説明】')
print('• R/R比（リスクリワード比）: 平均利益÷平均損失の絶対値。1.0以上が望ましい')
print('• PF（プロフィットファクター）: 総利益÷総損失の絶対値。1.0以上で利益、1.5以上が優秀')
print('• 期待値: 1取引あたりの期待損益。プラスなら長期的に利益が期待できる')
print('• 判定: ◎=期待値も実績も黒字、○=期待値は黒字、△=実績のみ黒字、×=両方赤字')
print()

# 全期間の詳細統計
all_wins = df[df['pnl_amount'] > 0]
all_losses = df[df['pnl_amount'] < 0]

total_win_amount = all_wins['pnl_amount'].sum()
total_loss_amount = abs(all_losses['pnl_amount'].sum())
avg_win = all_wins['pnl_amount'].mean()
avg_loss = all_losses['pnl_amount'].mean()
overall_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
overall_pf = total_win_amount / total_loss_amount if total_loss_amount > 0 else 0
win_rate = len(all_wins) / len(df) * 100
expected_value = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

print('【全期間統計（34ヶ月）】')
print(f'総取引数: {len(df)}回')
print(f'勝率: {win_rate:.2f}%')
print(f'リスクリワード比: {overall_rr:.2f}')
print(f'プロフィットファクター: {overall_pf:.2f}')
print(f'平均利益: {avg_win:+,.0f}円')
print(f'平均損失: {avg_loss:+,.0f}円')
print(f'期待値（1取引あたり）: {expected_value:+,.0f}円')
print(f'総利益: {total_win_amount:+,.0f}円')
print(f'総損失: {-total_loss_amount:+,.0f}円')
print(f'最終損益: {total_win_amount - total_loss_amount:+,.0f}円')
print()

# 良好な月と改善が必要な月
good_months = monthly_df[monthly_df['profit_factor'] > 1.0]
poor_months = monthly_df[monthly_df['profit_factor'] < 1.0]

print(f'【月別パフォーマンス分布】')
print(f'PF > 1.0（利益月）: {len(good_months)}ヶ月')
print(f'PF < 1.0（損失月）: {len(poor_months)}ヶ月')
print(f'期待値プラス月: {len(monthly_df[monthly_df["expected_value"] > 0])}ヶ月')
print(f'期待値マイナス月: {len(monthly_df[monthly_df["expected_value"] < 0])}ヶ月')
print()

# トップ5とワースト5
print('【ベスト5月（プロフィットファクター）】')
top5 = monthly_df.nlargest(5, 'profit_factor')[['month', 'profit_factor', 'risk_reward', 'total_pnl']]
for _, row in top5.iterrows():
    print(f"  {row['month']}: PF={row['profit_factor']:.2f}, R/R={row['risk_reward']:.2f}, 損益={row['total_pnl']:+,.0f}円")

print()
print('【ワースト5月（プロフィットファクター）】')
bottom5 = monthly_df.nsmallest(5, 'profit_factor')[['month', 'profit_factor', 'risk_reward', 'total_pnl']]
for _, row in bottom5.iterrows():
    pf_str = f"{row['profit_factor']:.2f}" if row['profit_factor'] > 0 else '0.00'
    rr_str = f"{row['risk_reward']:.2f}" if row['risk_reward'] > 0 else '-'
    print(f"  {row['month']}: PF={pf_str}, R/R={rr_str}, 損益={row['total_pnl']:+,.0f}円")