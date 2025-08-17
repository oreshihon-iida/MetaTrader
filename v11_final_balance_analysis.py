#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue #002 v11.0 最終バランス版詳細分析
v9.0(-37万円) v10.0(-53万円)からの最終改善確認
"""

import pandas as pd
import numpy as np
from datetime import datetime

def v11_final_balance_analysis():
    print("=== Issue #002 v11.0 Final Balanced Solution Analysis ===")
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("v9.0(-37万円) v10.0(-53万円)の最終改善確認")
    
    v11_csv = "C:/Users/iida/AppData/Roaming/MetaQuotes/Tester/D0E8209F77C8CF37AD8BF550E51FF075/Agent-127.0.0.1-3000/MQL5/Files/Issue002_v11_FinalBalance_2022.01.01.csv"
    
    try:
        df = pd.read_csv(v11_csv, encoding='utf-16le', sep='\t')
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        print(f"Total Trades Loaded: {len(df)}")
        
        # 基本統計
        initial_balance = 3000000.0
        final_balance = df['Balance'].iloc[-1]
        total_profit = final_balance - initial_balance
        
        # 月別分析用にバランス差分計算
        df = df.copy()  # pandas警告回避
        df.loc[:, 'Balance_Change'] = df['Balance'].diff()
        df.loc[0, 'Balance_Change'] = df['Balance'].iloc[0] - initial_balance
        
        # 月別グループ化
        df['Year_Month'] = df['DateTime'].dt.to_period('M')
        monthly_stats = df.groupby('Year_Month').agg({
            'Balance_Change': 'sum',
            'Signal': 'count',
            'Lot': 'mean'
        }).round(2)
        
        # 勝敗分析（バランス増加を勝ち）
        df['Win'] = df['Balance_Change'] > 0
        total_wins = df['Win'].sum()
        total_losses = len(df) - total_wins
        win_rate = (total_wins / len(df)) * 100 if len(df) > 0 else 0
        
        # 粗利益・損失計算
        gross_profit = df[df['Balance_Change'] > 0]['Balance_Change'].sum()
        gross_loss = abs(df[df['Balance_Change'] < 0]['Balance_Change'].sum())
        
        # プロフィットファクター計算
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        print(f"""
=== v11.0 FINAL BALANCED SOLUTION RESULTS ===

OVERALL PERFORMANCE:
  Initial Balance: {initial_balance:,.0f} JPY
  Final Balance: {final_balance:,.0f} JPY
  Total Profit/Loss: {total_profit:+,.0f} JPY
  Total Return: {(total_profit/initial_balance)*100:+.2f}%

PROFIT FACTOR ANALYSIS:
  Total Trades: {len(df)}
  Winning Trades: {total_wins} ({win_rate:.1f}%)
  Losing Trades: {total_losses} ({100-win_rate:.1f}%)
  Gross Profit: {gross_profit:+,.0f} JPY
  Gross Loss: {gross_loss:+,.0f} JPY
  PROFIT FACTOR: {profit_factor:.3f}

MONTHLY BREAKDOWN:
        """)
        
        monthly_cumulative = 0
        for month, stats in monthly_stats.iterrows():
            monthly_profit = stats['Balance_Change']
            monthly_trades = stats['Signal']
            avg_lot = stats['Lot']
            monthly_cumulative += monthly_profit
            
            print(f"  {month}: {monthly_profit:+,.0f} JPY ({monthly_trades} trades, {avg_lot:.2f} lot avg)")
        
        print(f"""
MONTHLY AVERAGES:
  Avg Monthly P&L: {total_profit/len(monthly_stats):+,.0f} JPY
  Avg Monthly Trades: {len(df)/len(monthly_stats):.1f}
  Total Test Period: {len(monthly_stats)} months

=== v9.0 vs v10.0 vs v11.0 COMPARISON ===
                    v9.0 Problem      v10.0 Worse       v11.0 Final
Monthly P&L:        -370,580 JPY      -534,490 JPY      {total_profit/len(monthly_stats):+,.0f} JPY
Profit Factor:      0.333             0.283             {profit_factor:.3f}
Win Rate:           8.7%              4.9%              {win_rate:.1f}%
Total Trades:       23 (3 months)     41 (3 months)     {len(df)} ({len(monthly_stats)} months)

IMPROVEMENT ANALYSIS:
  vs v9.0: {total_profit/len(monthly_stats) - (-370580):+,.0f} JPY monthly improvement
  vs v10.0: {total_profit/len(monthly_stats) - (-534490):+,.0f} JPY monthly improvement
  PF vs v9.0: {profit_factor - 0.333:+.3f}
  PF vs v10.0: {profit_factor - 0.283:+.3f}
  Win Rate vs v9.0: {win_rate - 8.7:+.1f}%
  Win Rate vs v10.0: {win_rate - 4.9:+.1f}%

RISK METRICS:
  Max Lot Used: {df['Lot'].max():.2f} (v9.0: 3.50, v10.0: 3.00, v11.0 Target: 3.25)
  Avg Lot Size: {df['Lot'].mean():.2f}
  TP/SL Ratio: 5.0:0.9 = 5.6:1 (v9.0: 4.5:1, v10.0: 7.5:1)

=== v11.0 FINAL BALANCE OPTIMIZATIONS ===
1. Risk Management: 0.9% (v9.0: 1.0%, v10.0: 0.8%) - Balanced
2. RSI Range: 20-80 (v9.0: 15-85, v10.0: 25-75) - Middle ground
3. ADX Minimum: 12.0 (v9.0: 8.0, v10.0: 15.0) - Balanced filter
4. TP/SL Ratio: 5.0:0.9 (v9.0: 4.5:1.0, v10.0: 6.0:0.8) - Optimal balance
5. Force Interval: 12 (v9.0: 10, v10.0: 15) - Frequency balance
6. Monthly Trades: 90 max (v9.0: 100, v10.0: 80) - Volume balance

=== REQUIRED REPORTING METRICS ===
Monthly P&L: {total_profit/len(monthly_stats):+,.0f} JPY/month
Profit Factor: {profit_factor:.3f}
Win Rate: {win_rate:.1f}%
Total Trades: {len(df)}
Test Duration: {len(monthly_stats)} months

=== SUCCESS STATUS ===
v11.0 Final Balance: {'SUCCESSFUL' if profit_factor > 0.333 and profit_factor > 0.283 else 'NEEDS MORE WORK'}
Problem Resolution: {'ACHIEVED' if profit_factor > 1.0 else 'PARTIAL IMPROVEMENT' if profit_factor > 0.333 else 'STILL PROBLEMATIC'}

=== FINAL ASSESSMENT ===
v11.0 vs Previous Versions:
- 最良改善: {'月損益プラス転換' if total_profit/len(monthly_stats) > 0 else '月損益は依然マイナス'}
- PF改善: {'大幅改善' if profit_factor > 0.5 else '小幅改善' if profit_factor > 0.333 else '改善不足'}
- 勝率改善: {'大幅改善' if win_rate > 30 else '中程度改善' if win_rate > 15 else '改善不足'}
        """)
        
        return {
            'monthly_pnl': total_profit/len(monthly_stats),
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': len(df),
            'total_profit': total_profit,
            'months': len(monthly_stats),
            'improvement_from_v9': {
                'monthly_pnl_improvement': total_profit/len(monthly_stats) - (-370580),
                'pf_improvement': profit_factor - 0.333,
                'win_rate_improvement': win_rate - 8.7
            },
            'improvement_from_v10': {
                'monthly_pnl_improvement': total_profit/len(monthly_stats) - (-534490),
                'pf_improvement': profit_factor - 0.283,
                'win_rate_improvement': win_rate - 4.9
            }
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    v11_final_balance_analysis()