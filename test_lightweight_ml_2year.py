#!/usr/bin/env python3
"""
Lightweight ML Predictor Strategy 2年学習テスト
学習データを2年分に拡張した版
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backtest.trade_executor import TradeExecutor

def test_lightweight_ml_2year():
    """2年分学習データテスト"""
    
    print("=" * 60)
    print("Lightweight ML Predictor Strategy - 2年学習テスト")
    print("学習期間: 2023-2024年（2年分）")
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
        confidence_threshold=0.55,  # 閾値を少し下げて取引数増加
        max_positions=3,
        risk_per_trade=0.01,
        model_type='random_forest'
    )
    
    print("\nモデル学習開始...")
    
    # 初回学習（最初の3ヶ月分 = 約6000本）
    training_size = min(6000, len(data) // 8)
    training_data = data.iloc[:training_size]
    strategy.train_model(training_data)
    
    print(f"初回学習完了（{training_size}レコード使用）。取引シミュレーション開始...")
    
    signals_generated = 0
    trades_executed = 0
    retraining_count = 0
    
    # メインループ（10本ごと = 2.5時間ごと）
    for i in range(training_size, len(data), 10):
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        current_price = data['Close'].iloc[i] if 'Close' in data.columns else data['close'].iloc[i]
        
        # 既存ポジションチェック
        executor.check_positions(current_price, current_time)
        
        # 月次再学習（約4000本ごと = 約40日ごと）
        if (i - training_size) % 4000 == 0 and i > training_size:
            retraining_count += 1
            print(f"再学習 #{retraining_count}: {current_time.date()}")
            # 直近3ヶ月分で再学習
            recent_data = data.iloc[max(0, i-6000):i+1]
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
            
            # TP/SL設定（予測の大きさに基づく）
            if abs(analysis['prediction']) > 0.003:
                tp_pips = 25
                sl_pips = 12
            elif abs(analysis['prediction']) > 0.002:
                tp_pips = 20
                sl_pips = 10
            else:
                tp_pips = 15
                sl_pips = 8
            
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
                if trades_executed <= 10:  # 最初の10取引のみ表示
                    print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} @ {current_price:.3f} "
                          f"予測:{analysis['prediction']:.4f} 信頼度:{analysis['confidence']:.2f}")
        
        # 資産更新
        executor.update_equity(current_price)
        
        # 進捗表示（約3ヶ月ごと）
        if i % 6000 == 0:
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
        
        # 月別詳細（最初と最後の数ヶ月のみ表示）
        print("\n【月別パフォーマンス（抜粋）】")
        if len(monthly_perf) > 6:
            # 最初の3ヶ月
            for _, row in monthly_perf.head(3).iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>3}取引)")
            print("...")
            # 最後の3ヶ月
            for _, row in monthly_perf.tail(3).iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>3}取引)")
        else:
            for _, row in monthly_perf.iterrows():
                print(f"{row['year']}-{row['month']:02d}: "
                      f"{row['profit']:>10,.0f}円 "
                      f"({row['trade_count']:>3}取引)")
    
    return executor, final_stats

if __name__ == "__main__":
    print(f"実行開始: {datetime.now()}")
    
    executor, stats = test_lightweight_ml_2year()
    
    if stats:
        print(f"\n実行完了: {datetime.now()}")
        print("\n【戦略評価】")
        
        # 年間換算
        if stats['total_trades'] > 0:
            print(f"取引頻度: 月平均{stats['total_trades']/24:.1f}回")
            
            if stats['total_return'] > 0:
                print(f"年換算収益率: {stats['total_return']/2:.1f}%")
                print(f"年換算利益: {stats['total_pnl']/2:,.0f}円")
            
            if stats['win_rate'] >= 50:
                print("✅ 勝率50%以上達成")
            
            if stats['max_drawdown'] < 20:
                print("✅ 最大DD20%以内")
        
        print("\n戦略ステータス: 2年学習版テスト完了")