#!/usr/bin/env python3
"""
Lightweight ML Predictor Strategy 2年学習テスト（高速版）
処理間隔を広げて高速化
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backtest.trade_executor import TradeExecutor

def test_lightweight_ml_2year_fast():
    """2年分学習データテスト（高速版）"""
    
    print("=" * 60)
    print("Lightweight ML Predictor Strategy - 2年学習テスト（高速版）")
    print("学習期間: 2023-2024年（2年分）")
    print("処理間隔: 40本ごと（10時間ごと）で高速化")
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
    
    # 軽量MLストラテジー実行
    from src.strategies.lightweight_ml_predictor_strategy import LightweightMLPredictor
    
    strategy = LightweightMLPredictor(
        initial_balance=3000000,
        lookback_periods=20,
        prediction_horizon=4,
        confidence_threshold=0.5,  # 閾値をさらに下げて取引数増加
        max_positions=3,
        risk_per_trade=0.01,
        model_type='random_forest'
    )
    
    print("\nモデル学習開始...")
    
    # 初回学習（最初の2ヶ月分 = 約4000本）
    training_size = min(4000, len(data) // 10)
    training_data = data.iloc[:training_size]
    strategy.train_model(training_data)
    
    print(f"初回学習完了（{training_size}レコード使用）。取引シミュレーション開始...")
    
    signals_generated = 0
    trades_executed = 0
    retraining_count = 0
    
    # メインループ（40本ごと = 10時間ごと、高速化のため）
    for i in range(training_size, len(data), 40):
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        current_price = data['Close'].iloc[i] if 'Close' in data.columns else data['close'].iloc[i]
        
        # 既存ポジションチェック
        executor.check_positions(current_price, current_time)
        
        # 2ヶ月ごとに再学習（約6000本ごと）
        if (i - training_size) % 6000 == 0 and i > training_size:
            retraining_count += 1
            print(f"再学習 #{retraining_count}: {current_time.date()}")
            # 直近2ヶ月分で再学習
            recent_data = data.iloc[max(0, i-4000):i+1]
            strategy.train_model(recent_data)
        
        # シグナル生成
        current_positions = len(executor.positions)
        signal, analysis = strategy.generate_signal(current_data, current_positions)
        
        if signal != 0:
            signals_generated += 1
            
            # ポジションサイズ計算
            lot_size = strategy.calculate_position_size(
                analysis['confidence'],
                executor.current_balance
            )
            
            # TP/SL設定（シンプル化）
            tp_pips = 20
            sl_pips = 10
            
            # ポジション開設
            position = executor.open_position(
                signal=signal,
                price=current_price,
                lot_size=lot_size,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                timestamp=current_time,
                strategy='lightweight_ml'
            )
            
            if position:
                trades_executed += 1
                if trades_executed <= 5:  # 最初の5取引のみ表示
                    print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} @ {current_price:.3f}")
        
        # 資産更新
        executor.update_equity(current_price)
        
        # 進捗表示（約4ヶ月ごと）
        if i % 8000 == 0:
            stats = executor.get_statistics()
            progress = (i / len(data)) * 100
            print(f"進捗: {progress:.1f}% - 取引: {trades_executed} - "
                  f"勝率: {stats['win_rate']:.1f}% - "
                  f"残高: {stats['final_balance']:,.0f}円")
    
    # 最終結果
    final_stats = executor.get_statistics()
    monthly_perf = executor.get_monthly_performance()
    
    print("\n" + "=" * 60)
    print("テスト結果（2023-2024年）")
    print("=" * 60)
    print(f"総取引数: {trades_executed}")
    print(f"シグナル生成数: {signals_generated}")
    print(f"再学習回数: {retraining_count}")
    print(f"総損益: {final_stats['total_pnl']:,.0f}円 ({final_stats['total_return']:.2f}%)")
    print(f"勝率: {final_stats['win_rate']:.1f}%")
    print(f"最大DD: {final_stats['max_drawdown']:.2f}%")
    print(f"PF: {final_stats['profit_factor']:.2f}")
    
    if not monthly_perf.empty:
        avg_monthly = monthly_perf['profit'].mean()
        print(f"\n月平均利益: {avg_monthly:,.0f}円")
        
        if avg_monthly >= 50000:
            print("✅ 月5万円目標達成！")
        elif avg_monthly >= 30000:
            print("⭕ 月3万円レベル")
        else:
            print(f"△ 目標まであと{50000-avg_monthly:,.0f}円/月")
    
    return executor, final_stats

if __name__ == "__main__":
    print(f"実行開始: {datetime.now()}")
    
    executor, stats = test_lightweight_ml_2year_fast()
    
    if stats:
        print(f"\n実行完了: {datetime.now()}")
        print("\n【戦略評価】")
        
        if stats['total_trades'] > 0:
            print(f"取引頻度: 月平均{stats['total_trades']/24:.1f}回")
            
            if stats['win_rate'] >= 50:
                print("✅ 勝率50%以上達成")
            
            if stats['max_drawdown'] < 20:
                print("✅ 最大DD20%以内")
        
        print("\n戦略ステータス: 2年学習版テスト完了")