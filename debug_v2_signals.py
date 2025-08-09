#!/usr/bin/env python3
"""
V2戦略のシグナル生成問題をデバッグ
なぜ0シグナルになるのかを調査
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2
from quick_test_helper import quick_test_setup

def debug_v2_signal_generation():
    """
    V2戦略のシグナル生成をデバッグ
    """
    print("=" * 60)
    print("V2 STRATEGY SIGNAL GENERATION DEBUG")
    print("=" * 60)
    
    # データ準備
    print("\n1. Setting up test data...")
    data, executor, metadata = quick_test_setup()
    print(f"Data size: {len(data)} records")
    print(f"Data range: {data.index[0]} to {data.index[-1]}")
    print(f"Columns: {list(data.columns)}")
    
    # V2戦略初期化
    print("\n2. Initializing V2 Strategy...")
    v2_strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'
    )
    
    # シグナル生成テスト
    print("\n3. Testing V2 signal generation...")
    
    v2_signals = 0
    time_filtered_out = 0
    trend_filtered_out = 0
    signal_generated_but_zero = 0
    test_points = 0
    
    for i in range(200, min(1500, len(data))):
        if i % 5 == 0:
            test_points += 1
            window_data = data.iloc[:i+1]
            current_time = window_data.index[-1]
            
            try:
                # 詳細デバッグをindex 1000で実行
                debug_mode = (i == 1000)
                
                if debug_mode:
                    print(f"\n=== DETAILED V2 DEBUG at index {i} ===")
                    print(f"Time: {current_time}")
                
                # 時間フィルター
                is_good_time = v2_strategy.is_good_trading_time(current_time)
                if debug_mode:
                    hour = current_time.hour
                    print(f"Hour: {hour}, Good time: {is_good_time}")
                
                if is_good_time:
                    # トレンドフィルター
                    trend = v2_strategy.check_trend_alignment(window_data)
                    if debug_mode:
                        print(f"Trend: {trend}")
                    
                    if trend != 0:
                        # コアシグナル生成
                        signal = v2_strategy.generate_core_signal(window_data)
                        if debug_mode:
                            print(f"Generated signal: {signal}")
                        
                        if signal != 0:
                            v2_signals += 1
                            tp_pips, sl_pips = v2_strategy.calculate_dynamic_tp_sl(window_data)
                            print(f"  V2 Signal at {current_time}: {signal} (TP: {tp_pips:.1f}, SL: {sl_pips:.1f}, Trend: {trend})")
                        else:
                            signal_generated_but_zero += 1
                            if debug_mode:
                                print("Signal generated but was 0")
                    else:
                        trend_filtered_out += 1
                        if debug_mode:
                            print("Filtered out by trend = 0")
                else:
                    time_filtered_out += 1
                    if debug_mode:
                        print("Filtered out by time")
                
                if debug_mode:
                    print("=== END DETAILED DEBUG ===\n")
                        
            except Exception as e:
                print(f"  V2 Error at {current_time}: {e}")
            
            if test_points >= 20 and v2_signals == 0:
                print(f"  ... Testing more points ({test_points} tested so far)")
            
            if test_points >= 180:  # 十分なテストポイント
                break
    
    print(f"\n4. V2 Signal Generation Results:")
    print(f"   Test Points: {test_points}")
    print(f"   V2 Signals: {v2_signals}")
    print(f"   Time filtered out: {time_filtered_out}")
    print(f"   Trend filtered out: {trend_filtered_out}")
    print(f"   Signal=0 cases: {signal_generated_but_zero}")
    
    # 成功率分析
    total_attempts = time_filtered_out + trend_filtered_out + signal_generated_but_zero + v2_signals
    print(f"\n5. Filter Analysis:")
    if total_attempts > 0:
        print(f"   Time filter pass rate: {(test_points - time_filtered_out)/test_points*100:.1f}%")
        print(f"   Trend filter pass rate: {(test_points - time_filtered_out - trend_filtered_out)/(test_points - time_filtered_out)*100:.1f}%" if test_points > time_filtered_out else "N/A")
        print(f"   Signal success rate: {v2_signals/(test_points - time_filtered_out - trend_filtered_out)*100:.1f}%" if test_points > time_filtered_out + trend_filtered_out else "N/A")
    
    if v2_signals == 0:
        print(f"\n[CONCLUSION] V2 signal generation completely blocked")
        if trend_filtered_out > test_points * 0.8:
            print("PRIMARY ISSUE: Trend filter is too strict (80%+ filtered)")
        elif time_filtered_out > test_points * 0.8:
            print("PRIMARY ISSUE: Time filter is too strict (80%+ filtered)")
        else:
            print("PRIMARY ISSUE: generate_core_signal is not producing signals")
    else:
        print(f"\n[CONCLUSION] V2 signal generation working: {v2_signals} signals")

    return v2_signals

if __name__ == "__main__":
    v2_signals = debug_v2_signal_generation()