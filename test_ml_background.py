#!/usr/bin/env python3
"""
ML Predictor テスト（バックグラウンド実行版）
長時間実行対応
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backtest.trade_executor import TradeExecutor
from src.strategies.lightweight_ml_predictor_strategy import LightweightMLPredictor

def test_ml_with_trades():
    """取引が発生するように調整したMLテスト"""
    
    print("=" * 60)
    print("ML Predictor - 取引発生テスト")
    print("信頼度閾値を下げて取引を生成")
    print("=" * 60)
    
    # 2024年データのみ使用（高速化）
    data_path = "data/processed/15min/2024/USDJPY_15min_2024.csv"
    
    if not os.path.exists(data_path):
        print(f"データファイルが見つかりません: {data_path}")
        return None, None
    
    data = pd.read_csv(data_path, index_col='Datetime', parse_dates=True)
    print(f"データ読み込み完了: {len(data)}レコード")
    print(f"期間: {data.index[0]} - {data.index[-1]}")
    
    # TradeExecutor初期化
    executor = TradeExecutor(initial_balance=3000000)
    
    # 軽量MLストラテジー（閾値を大幅に下げる）
    strategy = LightweightMLPredictor(
        initial_balance=3000000,
        lookback_periods=20,
        prediction_horizon=4,
        confidence_threshold=0.3,  # 大幅に下げる
        max_positions=3,
        risk_per_trade=0.01,
        model_type='random_forest'
    )
    
    # 予測閾値も下げる（ストラテジー内部で調整）
    # generate_signal内の閾値を下げるためにモンキーパッチ
    original_generate_signal = strategy.generate_signal
    
    def modified_generate_signal(data, current_positions=0):
        if current_positions >= strategy.max_positions:
            return 0, {'reason': 'max_positions_reached'}
        
        prediction, confidence = strategy.predict(data)
        
        analysis = {
            'prediction': prediction,
            'confidence': confidence,
            'threshold': strategy.confidence_threshold,
            'model_type': strategy.model_type
        }
        
        # 信頼度チェック（緩い）
        if confidence < strategy.confidence_threshold:
            return 0, {**analysis, 'reason': 'low_confidence'}
        
        # シグナル決定（閾値を大幅に下げる）
        if prediction > 0.0008:  # 0.08%以上の上昇予測
            signal = 1
        elif prediction < -0.0008:  # 0.08%以上の下落予測
            signal = -1
        else:
            signal = 0
            analysis['reason'] = 'prediction_too_small'
        
        return signal, analysis
    
    strategy.generate_signal = modified_generate_signal
    
    print("\nモデル学習開始...")
    
    # 初回学習（最初の1ヶ月分）
    training_size = 2000
    training_data = data.iloc[:training_size]
    strategy.train_model(training_data)
    
    print("初回学習完了。取引シミュレーション開始...")
    
    signals_generated = 0
    trades_executed = 0
    retraining_count = 0
    
    # メインループ（100本ごと = 約25時間ごと、高速化）
    for i in range(training_size, len(data), 100):
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        current_price = data['Close'].iloc[i] if 'Close' in data.columns else data['close'].iloc[i]
        
        # 既存ポジションチェック
        executor.check_positions(current_price, current_time)
        
        # 月次再学習
        if (i - training_size) % 3000 == 0 and i > training_size:
            retraining_count += 1
            print(f"再学習 #{retraining_count}: {current_time.date()}")
            recent_data = data.iloc[max(0, i-3000):i+1]
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
            
            # シンプルなTP/SL
            tp_pips = 15
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
                if trades_executed <= 10:
                    print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} @ {current_price:.3f} "
                          f"信頼度:{analysis['confidence']:.2f}")
        
        # 資産更新
        executor.update_equity(current_price)
        
        # 進捗表示
        if i % 3000 == 0:
            stats = executor.get_statistics()
            progress = (i / len(data)) * 100
            print(f"進捗: {progress:.1f}% - 取引: {trades_executed} - "
                  f"シグナル: {signals_generated}")
    
    # 最終結果
    final_stats = executor.get_statistics()
    monthly_perf = executor.get_monthly_performance()
    
    print("\n" + "=" * 60)
    print("テスト結果")
    print("=" * 60)
    print(f"総取引数: {trades_executed}")
    print(f"シグナル生成数: {signals_generated}")
    print(f"再学習回数: {retraining_count}")
    
    if trades_executed > 0:
        print(f"総損益: {final_stats['total_pnl']:,.0f}円")
        print(f"勝率: {final_stats['win_rate']:.1f}%")
        print(f"最大DD: {final_stats['max_drawdown']:.2f}%")
        print(f"PF: {final_stats['profit_factor']:.2f}")
        
        if not monthly_perf.empty:
            avg_monthly = monthly_perf['profit'].mean()
            print(f"\n月平均利益: {avg_monthly:,.0f}円")
    else:
        print("取引が発生しませんでした")
        print("閾値をさらに調整する必要があります")
    
    return executor, final_stats

if __name__ == "__main__":
    print(f"実行開始: {datetime.now()}")
    print("このスクリプトはバックグラウンド実行することを推奨します")
    print("実行コマンド例:")
    print("python test_ml_background.py > ml_test_result.txt 2>&1 &")
    print("")
    
    executor, stats = test_ml_with_trades()
    
    if stats:
        print(f"\n実行完了: {datetime.now()}")