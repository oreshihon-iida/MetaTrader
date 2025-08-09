#!/usr/bin/env python3
"""
統合戦略V1のデバッグ用テスト
シグナル生成が0になる問題を特定・修正
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.integrated_strategy_v1 import IntegratedStrategyV1
from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2
from quick_test_helper import quick_test_setup

def debug_signal_generation():
    """
    シグナル生成のデバッグ
    """
    print("=" * 60)
    print("INTEGRATED STRATEGY V1 SIGNAL GENERATION DEBUG")
    print("=" * 60)
    
    # データ準備
    print("\n1. Setting up test data...")
    data, executor, metadata = quick_test_setup()
    print(f"Data size: {len(data)} records")
    print(f"Data range: {data.index[0]} to {data.index[-1]}")
    print(f"Columns: {list(data.columns)}")
    
    # 統合戦略V1初期化
    print("\n2. Initializing Integrated Strategy V1...")
    v1_strategy = IntegratedStrategyV1(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth',
        target_rr_ratio=2.8
    )
    
    # V2戦略初期化（比較用）
    print("\n3. Initializing V2 Strategy for comparison...")
    v2_strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'
    )
    
    # シグナル生成テスト
    print("\n4. Testing signal generation...")
    
    v1_signals = 0
    v2_signals = 0
    test_points = 0
    
    for i in range(200, min(1500, len(data))):  # 最初の1300ポイントをテスト
        if i % 5 == 0:
            test_points += 1
            window_data = data.iloc[:i+1]
            current_time = window_data.index[-1]
            
            # V1シグナル生成
            try:
                # 市況検出
                market_condition = v1_strategy.detect_market_condition(window_data)
                
                # デバッグ：詳細シグナル生成プロセス
                if i % 5 == 0 and i == 1000:  # index 1000で詳細デバッグ
                    print(f"\n=== DETAILED V1 DEBUG at index {i} ===")
                    
                    # 時間チェック
                    is_good_time = v1_strategy.is_good_trading_time(current_time)
                    print(f"Good trading time: {is_good_time}")
                    
                    if is_good_time:
                        # トレンドチェック
                        trend = v1_strategy.check_trend_alignment(window_data)
                        print(f"Trend: {trend}")
                        
                        # テクニカル指標チェック
                        close_col = 'Close' if 'Close' in window_data.columns else 'close'
                        current_price = window_data[close_col].iloc[-1]
                        
                        # BB計算
                        sma = window_data[close_col].rolling(20).mean()
                        std = window_data[close_col].rolling(20).std()
                        upper_band = sma + (v1_strategy.bb_width * std)
                        lower_band = sma - (v1_strategy.bb_width * std)
                        
                        # RSI計算
                        delta = window_data[close_col].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        current_rsi = rsi.iloc[-1]
                        
                        # RSI調整
                        rsi_threshold_adjustment = 0
                        if market_condition == "volatile":
                            rsi_threshold_adjustment = 5
                        elif market_condition == "trending":
                            rsi_threshold_adjustment = -3
                        
                        adjusted_oversold = v1_strategy.rsi_oversold + rsi_threshold_adjustment
                        adjusted_overbought = v1_strategy.rsi_overbought - rsi_threshold_adjustment
                        
                        print(f"Price: {current_price:.3f}")
                        print(f"BB Lower: {lower_band.iloc[-1]:.3f}, BB Upper: {upper_band.iloc[-1]:.3f}")
                        print(f"RSI: {current_rsi:.2f}")
                        print(f"Adjusted oversold: {adjusted_oversold}")
                        print(f"Adjusted overbought: {adjusted_overbought}")
                        
                        # 条件チェック
                        buy_conditions = (
                            current_price < lower_band.iloc[-1] and 
                            current_rsi < adjusted_oversold
                        )
                        
                        sell_conditions = (
                            current_price > upper_band.iloc[-1] and 
                            current_rsi > adjusted_overbought
                        )
                        
                        print(f"Buy conditions: price<BB_lower({current_price:.3f}<{lower_band.iloc[-1]:.3f}={current_price < lower_band.iloc[-1]}) AND RSI<threshold({current_rsi:.2f}<{adjusted_oversold}={current_rsi < adjusted_oversold}) = {buy_conditions}")
                        print(f"Sell conditions: {sell_conditions}")
                        
                        if buy_conditions:
                            trend_ok = (trend == 1 or 
                                       (trend == 0 and current_rsi < adjusted_oversold) or
                                       (current_rsi < adjusted_oversold - 8))
                            print(f"Trend check for BUY: trend={trend}, condition={trend_ok}")
                        
                        if sell_conditions:
                            trend_ok = (trend == -1 or 
                                       (trend == 0 and current_rsi > adjusted_overbought) or
                                       (current_rsi > adjusted_overbought + 8))
                            print(f"Trend check for SELL: trend={trend}, condition={trend_ok}")
                    print("=== END DETAILED DEBUG ===\n")
                
                # コアシグナル生成
                v1_signal = v1_strategy.generate_core_signal(window_data)
                if v1_signal != 0:
                    v1_signals += 1
                    tp_pips, sl_pips = v1_strategy.calculate_optimized_tp_sl(window_data, market_condition)
                    print(f"  V1 Signal at {current_time}: {v1_signal} (TP: {tp_pips:.1f}, SL: {sl_pips:.1f}, Market: {market_condition})")
                    
            except Exception as e:
                print(f"  V1 Error at {current_time}: {e}")
            
            # V2シグナル生成（比較用）
            try:
                if v2_strategy.is_good_trading_time(current_time):
                    trend = v2_strategy.check_trend_alignment(window_data)
                    if trend != 0:
                        v2_signal = v2_strategy.generate_core_signal(window_data)
                        if v2_signal != 0:
                            v2_signals += 1
                            tp_pips, sl_pips = v2_strategy.calculate_dynamic_tp_sl(window_data)
                            print(f"  V2 Signal at {current_time}: {v2_signal} (TP: {tp_pips:.1f}, SL: {sl_pips:.1f}, Trend: {trend})")
                            
            except Exception as e:
                print(f"  V2 Error at {current_time}: {e}")
            
            if test_points >= 20 and v1_signals == 0 and v2_signals == 0:
                print(f"  ... Testing more points ({test_points} tested so far)")
            
            if test_points >= 180:  # 180ポイントテスト（index 1000まで）
                break
    
    print(f"\n5. Signal Generation Results:")
    print(f"   Test Points: {test_points}")
    print(f"   V1 Signals: {v1_signals}")
    print(f"   V2 Signals: {v2_signals}")
    
    if v1_signals == 0 and v2_signals == 0:
        print(f"\n6. Both strategies generated 0 signals. Investigating...")
        investigate_filter_conditions(data, v1_strategy, v2_strategy)
    elif v1_signals == 0:
        print(f"\n6. V1 generated 0 signals while V2 generated {v2_signals}. Investigating V1...")
        investigate_v1_filters(data, v1_strategy)
    else:
        print(f"\n6. Signal generation successful!")
    
    return v1_signals, v2_signals

def investigate_filter_conditions(data, v1_strategy, v2_strategy):
    """
    フィルター条件を詳しく調査
    """
    print("\nInvestigating filter conditions...")
    
    # サンプルポイントでの詳細チェック
    for i in [500, 1000, 2000]:
        if i >= len(data):
            continue
            
        print(f"\n--- Analysis at index {i} ({data.index[i]}) ---")
        window_data = data.iloc[:i+1]
        current_time = window_data.index[-1]
        
        # 時間帯チェック
        hour = current_time.hour
        is_good_time_v1 = v1_strategy.is_good_trading_time(current_time)
        is_good_time_v2 = v2_strategy.is_good_trading_time(current_time)
        
        print(f"Time: {hour}:00, V1 Good Time: {is_good_time_v1}, V2 Good Time: {is_good_time_v2}")
        
        # トレンド確認
        try:
            trend_v1 = v1_strategy.check_trend_alignment(window_data)
            trend_v2 = v2_strategy.check_trend_alignment(window_data)
            print(f"Trend: V1={trend_v1}, V2={trend_v2}")
        except Exception as e:
            print(f"Trend check error: {e}")
        
        # 市況検出（V1のみ）
        try:
            market_condition = v1_strategy.detect_market_condition(window_data)
            print(f"Market Condition (V1): {market_condition}")
        except Exception as e:
            print(f"Market condition error: {e}")
        
        # テクニカル指標チェック
        close_col = 'Close' if 'Close' in window_data.columns else 'close'
        current_price = window_data[close_col].iloc[-1]
        
        if len(window_data) >= 20:
            # RSI計算
            delta = window_data[close_col].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # BB計算
            sma = window_data[close_col].rolling(20).mean()
            std = window_data[close_col].rolling(20).std()
            upper_band = sma + (2.2 * std)  # V1のBB幅
            lower_band = sma - (2.2 * std)
            
            print(f"RSI: {current_rsi:.2f} (V1 thresholds: {v1_strategy.rsi_oversold}/{v1_strategy.rsi_overbought})")
            print(f"Price: {current_price:.3f}, BB Lower: {lower_band.iloc[-1]:.3f}, BB Upper: {upper_band.iloc[-1]:.3f}")
            print(f"Price vs BB: Below lower={current_price < lower_band.iloc[-1]}, Above upper={current_price > upper_band.iloc[-1]}")

def investigate_v1_filters(data, v1_strategy):
    """
    V1戦略の特定フィルターを調査
    """
    print("\nInvestigating V1-specific issues...")
    
    # V1とV2のパラメータ比較
    print(f"V1 RSI thresholds: {v1_strategy.rsi_oversold}/{v1_strategy.rsi_overbought}")
    print(f"V1 BB width: {v1_strategy.bb_width}")
    print(f"V1 Target R/R: {v1_strategy.target_rr_ratio}")
    
    # 市況検出の問題チェック
    for i in [500, 1000, 2000]:
        if i >= len(data):
            continue
            
        window_data = data.iloc[:i+1]
        try:
            market_condition = v1_strategy.detect_market_condition(window_data)
            print(f"Market condition at {i}: {market_condition}")
        except Exception as e:
            print(f"Market condition error at {i}: {e}")

if __name__ == "__main__":
    v1_signals, v2_signals = debug_signal_generation()
    
    if v1_signals == 0:
        print(f"\n[CONCLUSION] V1 signal generation needs fixing")
    else:
        print(f"\n[CONCLUSION] V1 signal generation working: {v1_signals} signals")