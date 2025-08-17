#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue #002 v10.0 詳細月別損益・PF分析
v9.0問題（月損益-37万円、PF 0.333）からの改善確認
"""

import pandas as pd
import numpy as np
from datetime import datetime

def v10_detailed_analysis():
    print("=== Issue #002 v10.0 Emergency Profit Fix Analysis ===")
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("v9.0問題解決確認: 月損益-370,580円、PF 0.333からの改善")
    
    v10_csv = "C:/Users/iida/AppData/Roaming/MetaQuotes/Tester/D0E8209F77C8CF37AD8BF550E51FF075/Agent-127.0.0.1-3000/MQL5/Files/Issue002_v10_ProfitFix_2022.01.01.csv"
    
    try:
        df = pd.read_csv(v10_csv, encoding='utf-16le', sep='\t')
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
=== v10.0 EMERGENCY PROFIT FIX RESULTS ===

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

=== v9.0 vs v10.0 COMPARISON ===
                    v9.0 Problem      v10.0 Fix         Improvement
Monthly P&L:        -370,580 JPY      {total_profit/len(monthly_stats):+,.0f} JPY      {total_profit/len(monthly_stats) - (-370580):+,.0f} JPY
Profit Factor:      0.333             {profit_factor:.3f}             {profit_factor - 0.333:+.3f}
Win Rate:           8.7%              {win_rate:.1f}%             {win_rate - 8.7:+.1f}%
Total Trades:       23 (3 months)     {len(df)} ({len(monthly_stats)} months)     {len(df) - 23:+d}

RISK METRICS:
  Max Lot Used: {df['Lot'].max():.2f} (vs v9.0: 3.50)
  Avg Lot Size: {df['Lot'].mean():.2f}
  Risk Reduction: {((3.5 - df['Lot'].max()) / 3.5 * 100):+.1f}%

=== v10.0 IMPROVEMENTS ===
1. TP/SL Ratio: 6.0:0.8 = 7.5:1 (vs v9.0: 4.5:1.0 = 4.5:1)
2. Quality Focus: Stricter filters (RSI 25-75, ADX 15+)
3. Trade Frequency: Reduced interval (15 vs 10)
4. Risk Management: Safer position sizing (3.0 vs 3.5 max lots)
5. Confluence Thresholds: Much stricter (15/10/5 vs 7/4/2)

=== REQUIRED REPORTING METRICS ===
Monthly P&L: {total_profit/len(monthly_stats):+,.0f} JPY/month
Profit Factor: {profit_factor:.3f}
Win Rate: {win_rate:.1f}%
Total Trades: {len(df)}
Test Duration: {len(monthly_stats)} months

=== SUCCESS STATUS ===
v10.0 Emergency Fix: {'SUCCESSFUL' if profit_factor > 0.333 and win_rate > 8.7 else 'NEEDS MORE WORK'}
Problem Resolution: {'ACHIEVED' if profit_factor > 1.0 else 'PARTIAL IMPROVEMENT'}
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
            }
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    v10_detailed_analysis()