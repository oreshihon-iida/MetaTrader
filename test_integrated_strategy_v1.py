#!/usr/bin/env python3
"""
統合戦略V1のテスト - Phase 1: R/R比最適化
V2戦略との直接比較でR/R比改良の効果を検証
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import json
import matplotlib.pyplot as plt

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_test_runner import AutoTestRunner
from src.strategies.integrated_strategy_v1 import IntegratedStrategyV1
from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2
from src.backtest.trade_executor import TradeExecutor

def integrated_v1_wrapper(data, executor, metadata):
    """
    統合戦略V1のラッパー関数
    """
    strategy = IntegratedStrategyV1(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth',
        target_rr_ratio=2.8  # 2.8:1 R/R比でテスト
    )
    
    # シグナル生成データフレーム準備
    result_df = data.copy()
    result_df['signal'] = 0.0
    result_df['signal_quality'] = 0.0
    result_df['sl_pips'] = 0.0
    result_df['tp_pips'] = 0.0
    result_df['strategy'] = 'integrated_v1'
    
    # V1統合戦略でシグナル生成と取引実行
    print("Executing Integrated Strategy V1...")
    signal_count = 0
    trade_count = 0
    
    for i in range(200, len(data)):
        current_time = data.index[i]
        current_price = data.iloc[i]['Close'] if 'Close' in data.columns else data.iloc[i]['close']
        
        # 既存ポジションのTP/SLチェック
        executor.check_positions(current_price, current_time)
        executor.update_equity(current_price)
        
        # 新規シグナル生成（5本ごと）
        if i % 5 == 0:
            window_data = data.iloc[:i+1]
            
            # 市況検出
            market_condition = strategy.detect_market_condition(window_data)
            
            # コアシグナル生成（改良版）
            signal = strategy.generate_core_signal(window_data)
            
            if signal != 0:
                signal_count += 1
                
                # 最適化されたTP/SL計算
                tp_pips, sl_pips = strategy.calculate_optimized_tp_sl(window_data, market_condition)
                
                # ロットサイズ計算
                lot_size = strategy.calculate_optimal_lot_size('core', sl_pips)
                
                # 取引実行
                position = executor.open_position(
                    signal=signal,
                    price=current_price,
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips,
                    timestamp=current_time,
                    strategy='integrated_v1_core'
                )
                
                if position:
                    trade_count += 1
    
    print(f"Generated {signal_count} signals, executed {trade_count} trades with Integrated V1")

def v2_comparison_wrapper(data, executor, metadata):
    """
    V2戦略の比較用ラッパー（前回と同様）
    """
    strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'
    )
    
    result_df = data.copy()
    result_df['signal'] = 0.0
    result_df['signal_quality'] = 0.0
    result_df['sl_pips'] = 0.0
    result_df['tp_pips'] = 0.0
    result_df['strategy'] = 'V2_comparison'
    
    signal_count = 0
    trade_count = 0
    
    for i in range(200, len(data)):
        current_time = data.index[i]
        current_price = data.iloc[i]['Close'] if 'Close' in data.columns else data.iloc[i]['close']
        
        # 既存ポジションのTP/SLチェック
        executor.check_positions(current_price, current_time)
        executor.update_equity(current_price)
        
        # 新規シグナル生成（5本ごと）
        if i % 5 == 0:
            window_data = data.iloc[:i+1]
            
            if strategy.is_good_trading_time(current_time):
                trend = strategy.check_trend_alignment(window_data)
                if trend != 0:
                    signal = strategy.generate_core_signal(window_data)
                    if signal != 0:
                        signal_count += 1
                        
                        tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                        lot_size = strategy.calculate_optimal_lot_size('core', sl_pips)
                        
                        # 取引実行
                        position = executor.open_position(
                            signal=signal,
                            price=current_price,
                            lot_size=lot_size,
                            stop_loss_pips=sl_pips,
                            take_profit_pips=tp_pips,
                            timestamp=current_time,
                            strategy='v2_core'
                        )
                        
                        if position:
                            trade_count += 1
    
    print(f"Generated {signal_count} signals, executed {trade_count} trades with V2 strategy")

def run_phase1_comparison():
    """
    Phase 1統合戦略とV2戦略の比較テスト
    """
    print("=" * 60)
    print("INTEGRATED STRATEGY V1 vs V2 COMPARISON TEST")
    print("Phase 1: R/R Ratio Optimization")
    print("=" * 60)
    
    auto_tester = AutoTestRunner()
    
    # 1. 統合戦略V1のテスト
    print("\n[1] Testing Integrated Strategy V1 (R/R Optimized)...")
    print("Features: Fixed 2.8:1 R/R + Market condition adaptation + V2 filters")
    
    try:
        v1_executor, v1_stats = auto_tester.run_strategy_test(
            integrated_v1_wrapper,
            "IntegratedStrategyV1_Phase1",
            timeout_hours=2.0
        )
        
        print("\nIntegrated Strategy V1 Results:")
        print(f"  Final Balance: {v1_stats['final_balance']:,.0f} JPY")
        print(f"  Total P&L: {v1_stats['total_pnl']:,.0f} JPY ({v1_stats['total_return']:.2f}%)")
        print(f"  Trades: {v1_stats['total_trades']}")
        print(f"  Win Rate: {v1_stats['win_rate']:.2f}%")
        print(f"  Profit Factor: {v1_stats['profit_factor']:.2f}")
        print(f"  Max DD: {v1_stats['max_drawdown']:.2f}%")
        print(f"  R/R Ratio: {abs(v1_stats['avg_win']/v1_stats['avg_loss']) if v1_stats['avg_loss'] != 0 else 0:.2f}")
        
    except Exception as e:
        print(f"ERROR: Integrated V1 test failed: {e}")
        v1_executor = None
        v1_stats = None
    
    # 2. V2戦略のテスト（比較用）
    print("\n[2] Testing V2 Strategy (Baseline)...")
    print("Features: Dynamic TP/SL + Time/Trend filters")
    
    try:
        v2_executor, v2_stats = auto_tester.run_strategy_test(
            v2_comparison_wrapper,
            "V2Strategy_Baseline",
            timeout_hours=2.0
        )
        
        print("\nV2 Strategy Results:")
        print(f"  Final Balance: {v2_stats['final_balance']:,.0f} JPY")
        print(f"  Total P&L: {v2_stats['total_pnl']:,.0f} JPY ({v2_stats['total_return']:.2f}%)")
        print(f"  Trades: {v2_stats['total_trades']}")
        print(f"  Win Rate: {v2_stats['win_rate']:.2f}%")
        print(f"  Profit Factor: {v2_stats['profit_factor']:.2f}")
        print(f"  Max DD: {v2_stats['max_drawdown']:.2f}%")
        print(f"  R/R Ratio: {abs(v2_stats['avg_win']/v2_stats['avg_loss']) if v2_stats['avg_loss'] != 0 else 0:.2f}")
        
    except Exception as e:
        print(f"ERROR: V2 test failed: {e}")
        v2_executor = None
        v2_stats = None
    
    # 3. Phase 1改良効果の分析
    if v1_stats and v2_stats:
        analyze_phase1_improvements(v1_stats, v2_stats, v1_executor, v2_executor)
    
    return v1_executor, v1_stats, v2_executor, v2_stats

def analyze_phase1_improvements(v1_stats, v2_stats, v1_executor, v2_executor):
    """
    Phase 1改良効果の詳細分析
    """
    print("\n" + "=" * 60)
    print("PHASE 1 IMPROVEMENT ANALYSIS")
    print("=" * 60)
    
    # 基本パフォーマンス比較
    print("\nPERFORMANCE COMPARISON")
    print("-" * 40)
    
    improvements = {}
    
    # 収益性
    pnl_improvement = ((v1_stats['total_pnl'] - v2_stats['total_pnl']) / abs(v2_stats['total_pnl'])) * 100 if v2_stats['total_pnl'] != 0 else 0
    improvements['profitability'] = pnl_improvement
    print(f"Profitability: {pnl_improvement:+.1f}% improvement")
    print(f"  V1: {v1_stats['total_pnl']:,.0f} JPY vs V2: {v2_stats['total_pnl']:,.0f} JPY")
    
    # R/R比
    v1_rr = abs(v1_stats['avg_win']/v1_stats['avg_loss']) if v1_stats['avg_loss'] != 0 else 0
    v2_rr = abs(v2_stats['avg_win']/v2_stats['avg_loss']) if v2_stats['avg_loss'] != 0 else 0
    rr_improvement = ((v1_rr - v2_rr) / v2_rr) * 100 if v2_rr != 0 else 0
    improvements['risk_reward'] = rr_improvement
    print(f"Risk/Reward: {rr_improvement:+.1f}% improvement")
    print(f"  V1: {v1_rr:.2f} vs V2: {v2_rr:.2f}")
    
    # 勝率
    winrate_diff = v1_stats['win_rate'] - v2_stats['win_rate']
    improvements['win_rate'] = winrate_diff
    print(f"Win Rate: {winrate_diff:+.1f}% difference")
    print(f"  V1: {v1_stats['win_rate']:.2f}% vs V2: {v2_stats['win_rate']:.2f}%")
    
    # 最大ドローダウン
    dd_improvement = v2_stats['max_drawdown'] - v1_stats['max_drawdown']  # 小さい方が良い
    improvements['drawdown'] = dd_improvement
    print(f"Max Drawdown: {dd_improvement:+.1f}% improvement (lower is better)")
    print(f"  V1: {v1_stats['max_drawdown']:.2f}% vs V2: {v2_stats['max_drawdown']:.2f}%")
    
    # 取引効率
    trade_efficiency_v1 = v1_stats['total_pnl'] / v1_stats['total_trades'] if v1_stats['total_trades'] > 0 else 0
    trade_efficiency_v2 = v2_stats['total_pnl'] / v2_stats['total_trades'] if v2_stats['total_trades'] > 0 else 0
    efficiency_improvement = ((trade_efficiency_v1 - trade_efficiency_v2) / abs(trade_efficiency_v2)) * 100 if trade_efficiency_v2 != 0 else 0
    improvements['trade_efficiency'] = efficiency_improvement
    print(f"Trade Efficiency: {efficiency_improvement:+.1f}% improvement")
    print(f"  V1: {trade_efficiency_v1:,.0f} JPY/trade vs V2: {trade_efficiency_v2:,.0f} JPY/trade")
    
    # 月間パフォーマンス比較
    print(f"\nMONTHLY PERFORMANCE")
    print("-" * 40)
    
    v1_monthly = v1_executor.get_monthly_performance()
    v2_monthly = v2_executor.get_monthly_performance()
    
    if not v1_monthly.empty and not v2_monthly.empty:
        v1_monthly_avg = v1_monthly['profit'].mean()
        v2_monthly_avg = v2_monthly['profit'].mean()
        
        monthly_improvement = ((v1_monthly_avg - v2_monthly_avg) / abs(v2_monthly_avg)) * 100 if v2_monthly_avg != 0 else 0
        
        print(f"Monthly Average: {monthly_improvement:+.1f}% improvement")
        print(f"  V1: {v1_monthly_avg:,.0f} JPY/month vs V2: {v2_monthly_avg:,.0f} JPY/month")
        print(f"Target Achievement (200K): V1 {v1_monthly_avg/200000*100:.1f}% vs V2 {v2_monthly_avg/200000*100:.1f}%")
    
    # 総合評価
    print(f"\nPHASE 1 OVERALL ASSESSMENT")
    print("-" * 40)
    
    positive_improvements = sum(1 for imp in improvements.values() if imp > 0)
    total_metrics = len(improvements)
    
    if positive_improvements >= total_metrics * 0.6:
        assessment = "SUCCESS - R/R optimization shows significant benefits"
    elif positive_improvements >= total_metrics * 0.4:
        assessment = "PARTIAL SUCCESS - Some improvements observed"
    else:
        assessment = "NEEDS REFINEMENT - Limited improvement"
    
    print(f"Assessment: {assessment}")
    print(f"Improved Metrics: {positive_improvements}/{total_metrics}")
    
    # 次のフェーズへの推奨
    print(f"\nRECOMMENDATIONS FOR PHASE 2")
    print("-" * 40)
    
    if pnl_improvement > 5:
        print("SUCCESS: R/R optimization successful - proceed to Phase 2 (Multi-timeframe)")
    elif pnl_improvement > 0:
        print("WARNING: Minor improvement - consider R/R ratio fine-tuning before Phase 2")
    else:
        print("ERROR: R/R optimization ineffective - analyze and refine before Phase 2")
    
    if rr_improvement > 10:
        print("SUCCESS: Risk/Reward ratio significantly improved")
    
    if winrate_diff > 2:
        print("SUCCESS: Win rate maintained or improved - good signal quality")
    elif winrate_diff < -5:
        print("WARNING: Win rate declined - may need signal filter adjustment")
    
    # 結果保存
    save_phase1_results(v1_stats, v2_stats, improvements, v1_executor, v2_executor)

def save_phase1_results(v1_stats, v2_stats, improvements, v1_executor, v2_executor):
    """
    Phase 1の結果を保存
    """
    output_dir = "results/integrated_strategy_phase1"
    os.makedirs(output_dir, exist_ok=True)
    
    # 改良効果データ
    phase1_results = {
        'test_date': datetime.now().isoformat(),
        'phase': 'Phase 1 - R/R Ratio Optimization',
        'v1_stats': v1_stats,
        'v2_stats': v2_stats,
        'improvements': improvements
    }
    
    with open(f'{output_dir}/phase1_comparison_results.json', 'w') as f:
        json.dump(phase1_results, f, indent=2, default=str)
    
    # レポート作成
    v1_monthly_avg = v1_executor.get_monthly_performance()['profit'].mean() if not v1_executor.get_monthly_performance().empty else 0
    v2_monthly_avg = v2_executor.get_monthly_performance()['profit'].mean() if not v2_executor.get_monthly_performance().empty else 0
    
    report = f"""# Integrated Strategy V1 - Phase 1 Results

## Test Overview
- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **Phase**: R/R Ratio Optimization (2.8:1 fixed ratio)
- **Baseline**: V2 Strategy (dynamic TP/SL)

## Performance Comparison

### Financial Results
| Metric | Integrated V1 | V2 Strategy | Improvement |
|--------|--------------|-------------|-------------|
| Total P&L | {v1_stats['total_pnl']:,.0f} JPY | {v2_stats['total_pnl']:,.0f} JPY | {improvements['profitability']:+.1f}% |
| Monthly Avg | {v1_monthly_avg:,.0f} JPY | {v2_monthly_avg:,.0f} JPY | - |
| Win Rate | {v1_stats['win_rate']:.2f}% | {v2_stats['win_rate']:.2f}% | {improvements['win_rate']:+.1f}% |
| Risk/Reward | {abs(v1_stats['avg_win']/v1_stats['avg_loss']) if v1_stats['avg_loss'] != 0 else 0:.2f} | {abs(v2_stats['avg_win']/v2_stats['avg_loss']) if v2_stats['avg_loss'] != 0 else 0:.2f} | {improvements['risk_reward']:+.1f}% |
| Max Drawdown | {v1_stats['max_drawdown']:.2f}% | {v2_stats['max_drawdown']:.2f}% | {improvements['drawdown']:+.1f}% |

## Key Improvements in V1
1. **Fixed R/R Ratio**: Consistent 2.8:1 ratio vs dynamic V2
2. **Market Condition Adaptation**: TP/SL adjustment based on volatility/trending
3. **Enhanced Signal Quality**: Market-aware RSI threshold adjustment

## Phase 1 Assessment
- R/R optimization shows {"significant" if improvements['profitability'] > 5 else "moderate" if improvements['profitability'] > 0 else "limited"} improvement
- {"Ready for Phase 2" if improvements['profitability'] > 0 else "Needs refinement before Phase 2"}

---
Generated with Claude Code - Integrated Strategy Development
"""
    
    with open(f'{output_dir}/phase1_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nPhase 1 results saved to: {output_dir}/")

if __name__ == "__main__":
    print("Integrated Strategy V1 Development - Phase 1 Testing")
    print("Focus: R/R Ratio Optimization (2.8:1 fixed ratio)")
    
    v1_executor, v1_stats, v2_executor, v2_stats = run_phase1_comparison()
    
    if v1_stats and v2_stats:
        print("\nPhase 1 testing completed successfully!")
        print("Check results/integrated_strategy_phase1/ for detailed analysis")
    else:
        print("\nPhase 1 testing failed - check logs for details")