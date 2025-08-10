#!/usr/bin/env python3
"""
最適化ML予測戦略テスト
月20万円目標の品質重視戦略
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backtest.trade_executor import TradeExecutor
from src.strategies.optimized_ml_predictor_strategy import optimized_ml_wrapper

def test_optimized_ml():
    """最適化ML戦略テスト"""
    
    print("=" * 60)
    print("最適化ML予測戦略テスト - 月20万円目標")
    print("特徴: 品質重視・高速処理・2年学習")
    print("=" * 60)
    
    # 2年分のデータ読み込み
    data_list = []
    years = [2023, 2024]
    
    for year in years:
        data_path = f"data/processed/15min/{year}/USDJPY_15min_{year}.csv"
        
        if not os.path.exists(data_path):
            print(f"データファイルが見つかりません: {data_path}")
            continue
        
        year_data = pd.read_csv(data_path, index_col='Datetime', parse_dates=True)
        data_list.append(year_data)
        print(f"{year}年データ読み込み完了: {len(year_data)}レコード")
    
    if len(data_list) == 0:
        print("データが読み込めませんでした")
        return None, None
    
    # データ結合
    data = pd.concat(data_list, axis=0).sort_index()
    print(f"\n統合データ: {len(data)}レコード")
    print(f"期間: {data.index[0]} - {data.index[-1]}")
    
    # TradeExecutor初期化
    executor = TradeExecutor(initial_balance=3000000)
    
    # 最適化戦略実行
    print("\n戦略実行開始...")
    optimized_ml_wrapper(data, executor, {})
    
    # 最終結果
    final_stats = executor.get_statistics()
    monthly_perf = executor.get_monthly_performance()
    
    print("\n" + "=" * 60)
    print("最終テスト結果（2023-2024年）")
    print("=" * 60)
    print(f"総取引数: {final_stats['total_trades']}")
    print(f"総損益: {final_stats['total_pnl']:,.0f}円 ({final_stats['total_return']:.2f}%)")
    print(f"勝率: {final_stats['win_rate']:.1f}%")
    print(f"最大DD: {final_stats['max_drawdown']:.2f}%")
    print(f"PF: {final_stats['profit_factor']:.2f}")
    
    if not monthly_perf.empty:
        avg_monthly = monthly_perf['profit'].mean()
        print(f"\n月平均利益: {avg_monthly:,.0f}円")
        
        if avg_monthly >= 200000:
            print("🎉 月20万円目標達成！")
        elif avg_monthly >= 100000:
            print("⭕ 月10万円レベル")
        elif avg_monthly >= 50000:
            print("△ 月5万円レベル")
        else:
            print(f"目標まで: {200000-avg_monthly:,.0f}円/月")
        
        # 月別詳細（最初と最後の数ヶ月）
        print("\n【月別パフォーマンス（抜粋）】")
        if len(monthly_perf) > 6:
            for _, row in monthly_perf.head(3).iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>2}取引)")
            print("...")
            for _, row in monthly_perf.tail(3).iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>2}取引)")
        else:
            for _, row in monthly_perf.iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>2}取引)")
    
    # 戦略評価
    print("\n" + "=" * 50)
    print("戦略評価")
    print("=" * 50)
    
    if final_stats['total_trades'] > 0:
        print(f"取引頻度: 月平均{final_stats['total_trades']/24:.1f}回")
        
        if final_stats['win_rate'] >= 60:
            print("✅ 勝率60%以上達成")
        elif final_stats['win_rate'] >= 50:
            print("⭕ 勝率50%以上")
        
        if final_stats['max_drawdown'] < 15:
            print("✅ 最大DD15%以内")
        elif final_stats['max_drawdown'] < 25:
            print("⭕ 最大DD25%以内")
        
        if final_stats['profit_factor'] >= 1.5:
            print("✅ PF1.5以上")
        elif final_stats['profit_factor'] >= 1.2:
            print("⭕ PF1.2以上")
        
        # 年間収益率
        annual_return = final_stats['total_return'] / 2
        if annual_return >= 30:
            print("✅ 年間30%以上の収益")
        elif annual_return >= 20:
            print("⭕ 年間20%以上の収益")
    
    return executor, final_stats

if __name__ == "__main__":
    print(f"実行開始: {datetime.now()}")
    
    executor, stats = test_optimized_ml()
    
    if stats:
        print(f"\n実行完了: {datetime.now()}")
        print("戦略ステータス: 最適化版テスト完了")