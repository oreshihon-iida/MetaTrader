#!/usr/bin/env python3
"""
developブランチのマクロ長期戦略を自動テストシステムで検証
V2戦略との直接比較を実行
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_test_runner import AutoTestRunner
from src.backtest.trade_executor import TradeExecutor
from src.strategies.macro_based_long_term_strategy import MacroBasedLongTermStrategy
from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2
from src.utils.logger import Logger

def macro_strategy_wrapper(data):
    """
    マクロ長期戦略のラッパー関数
    AutoTestRunnerで使用するため、単一データフレームから複数時間足データを生成
    """
    # マクロ長期戦略初期化（初期資金を3M円に調整）
    strategy = MacroBasedLongTermStrategy(
        initial_balance=3000000,  # V2と同じ初期資金
        sl_pips=50.0,
        tp_pips=150.0,
        quality_threshold=0.2  # 品質閾値を低くして取引数増加
    )
    
    # 単一データフレームから複数時間足を模擬
    # 実際の長期戦略では複数時間足が必要だが、テスト用に15分足から日足を近似
    data_dict = {
        '15min': data,
        '1H': data.resample('1H').agg({
            'Open': 'first',
            'High': 'max', 
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum' if 'Volume' in data.columns else 'mean'
        }).dropna() if isinstance(data.index, pd.DatetimeIndex) else data,
        '4H': data.resample('4H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min', 
            'Close': 'last',
            'Volume': 'sum' if 'Volume' in data.columns else 'mean'
        }).dropna() if isinstance(data.index, pd.DatetimeIndex) else data.iloc[::16],
        '1D': data.resample('1D').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum' if 'Volume' in data.columns else 'mean'
        }).dropna() if isinstance(data.index, pd.DatetimeIndex) else data.iloc[::96]
    }
    
    print(f"データ準備完了:")
    for tf, df in data_dict.items():
        print(f"  {tf}: {len(df)} 行")
    
    # シグナル生成
    signal_df = strategy.generate_signals(data_dict)
    
    return signal_df

def v2_strategy_wrapper(data):
    """
    V2戦略のラッパー関数（比較用）
    """
    strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'
    )
    
    # V2戦略用のシグナル生成
    signal_data = []
    for i in range(200, len(data)):
        window_data = data.iloc[:i+1]
        current_time = window_data.index[-1]
        
        # 5本ごとにシグナル生成
        if i % 5 == 0:
            if strategy.is_good_trading_time(current_time):
                trend = strategy.check_trend_alignment(window_data)
                if trend != 0:
                    signal = strategy.generate_core_signal(window_data)
                    if signal != 0:
                        tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                        
                        signal_data.append({
                            'timestamp': current_time,
                            'signal': signal,
                            'signal_quality': 0.8,  # V2の高品質シグナル
                            'tp_pips': tp_pips,
                            'sl_pips': sl_pips,
                            'strategy': 'V2_core'
                        })
    
    # DataFrameに変換
    if signal_data:
        signals_df = pd.DataFrame(signal_data)
        signals_df.set_index('timestamp', inplace=True)
        
        # 元データと結合
        result_df = data.copy()
        result_df['signal'] = 0.0
        result_df['signal_quality'] = 0.0
        result_df['sl_pips'] = 0.0
        result_df['tp_pips'] = 0.0
        result_df['strategy'] = 'V2'
        
        for idx, row in signals_df.iterrows():
            if idx in result_df.index:
                result_df.loc[idx, 'signal'] = row['signal']
                result_df.loc[idx, 'signal_quality'] = row['signal_quality']
                result_df.loc[idx, 'sl_pips'] = row['sl_pips']
                result_df.loc[idx, 'tp_pips'] = row['tp_pips']
        
        return result_df
    else:
        # シグナルがない場合
        result_df = data.copy()
        result_df['signal'] = 0.0
        result_df['signal_quality'] = 0.0
        result_df['sl_pips'] = 0.0
        result_df['tp_pips'] = 0.0
        result_df['strategy'] = 'V2'
        return result_df

def run_strategy_comparison():
    """
    マクロ長期戦略とV2戦略の比較テスト実行
    """
    print("\n" + "=" * 60)
    print("developブランチ長期戦略 vs V2戦略 比較テスト")
    print("=" * 60)
    
    auto_tester = AutoTestRunner()
    
    # 1. マクロ長期戦略のテスト
    print("\n【1. マクロ長期戦略テスト】")
    print("-" * 40)
    
    try:
        macro_executor, macro_stats = auto_tester.run_strategy_test(
            macro_strategy_wrapper, 
            "MacroBasedLongTermStrategy"
        )
        
        print(f"マクロ長期戦略結果:")
        print(f"  最終資金: {macro_stats['final_balance']:,.0f}円")
        print(f"  総損益: {macro_stats['total_pnl']:,.0f}円")
        print(f"  取引数: {macro_stats['total_trades']}")
        print(f"  勝率: {macro_stats['win_rate']:.2f}%")
        print(f"  プロフィットファクター: {macro_stats['profit_factor']:.2f}")
        print(f"  最大ドローダウン: {macro_stats['max_drawdown']:.2f}%")
        
    except Exception as e:
        print(f"マクロ長期戦略テストでエラー: {e}")
        macro_executor = None
        macro_stats = None
    
    # 2. V2戦略のテスト
    print("\n【2. V2戦略テスト】")
    print("-" * 40)
    
    try:
        v2_executor, v2_stats = auto_tester.run_strategy_test(
            v2_strategy_wrapper,
            "ProfitTargetStrategyV2_Comparison"
        )
        
        print(f"V2戦略結果:")
        print(f"  最終資金: {v2_stats['final_balance']:,.0f}円")
        print(f"  総損益: {v2_stats['total_pnl']:,.0f}円")
        print(f"  取引数: {v2_stats['total_trades']}")
        print(f"  勝率: {v2_stats['win_rate']:.2f}%")
        print(f"  プロフィットファクター: {v2_stats['profit_factor']:.2f}")
        print(f"  最大ドローダウン: {v2_stats['max_drawdown']:.2f}%")
        
    except Exception as e:
        print(f"V2戦略テストでエラー: {e}")
        v2_executor = None
        v2_stats = None
    
    # 3. 比較分析
    print("\n【3. 比較分析】")
    print("=" * 60)
    
    if macro_stats and v2_stats:
        create_comparison_analysis(macro_stats, v2_stats, macro_executor, v2_executor)
    else:
        print("比較分析をスキップします（一方または両方のテストが失敗）")
    
    return macro_executor, macro_stats, v2_executor, v2_stats

def create_comparison_analysis(macro_stats, v2_stats, macro_executor, v2_executor):
    """
    詳細な比較分析を実行
    """
    print("\n📊 **戦略比較結果**")
    print("-" * 50)
    
    # 基本パフォーマンス比較
    comparison_table = pd.DataFrame({
        'マクロ長期戦略': [
            f"{macro_stats['final_balance']:,.0f}円",
            f"{macro_stats['total_pnl']:,.0f}円",
            f"{macro_stats['total_return']:.2f}%",
            f"{macro_stats['total_trades']}",
            f"{macro_stats['win_rate']:.2f}%",
            f"{macro_stats['profit_factor']:.2f}",
            f"{macro_stats['max_drawdown']:.2f}%"
        ],
        'V2戦略': [
            f"{v2_stats['final_balance']:,.0f}円",
            f"{v2_stats['total_pnl']:,.0f}円",
            f"{v2_stats['total_return']:.2f}%",
            f"{v2_stats['total_trades']}",
            f"{v2_stats['win_rate']:.2f}%",
            f"{v2_stats['profit_factor']:.2f}",
            f"{v2_stats['max_drawdown']:.2f}%"
        ]
    }, index=[
        '最終資金', '総損益', 'リターン率', '取引数', '勝率', 
        'プロフィットファクター', '最大ドローダウン'
    ])
    
    print(comparison_table.to_string())
    
    # 勝者判定
    print("\n🏆 **各指標での優位性**")
    print("-" * 30)
    
    metrics = {
        '総損益': (macro_stats['total_pnl'], v2_stats['total_pnl']),
        'リターン率': (macro_stats['total_return'], v2_stats['total_return']),
        '勝率': (macro_stats['win_rate'], v2_stats['win_rate']),
        'プロフィットファクター': (macro_stats['profit_factor'], v2_stats['profit_factor']),
        '最大ドローダウン': (-macro_stats['max_drawdown'], -v2_stats['max_drawdown']),  # 低い方が良い
        '取引数': (macro_stats['total_trades'], v2_stats['total_trades'])
    }
    
    macro_wins = 0
    v2_wins = 0
    
    for metric, (macro_val, v2_val) in metrics.items():
        if macro_val > v2_val:
            winner = "マクロ長期戦略 🎯"
            macro_wins += 1
        elif v2_val > macro_val:
            winner = "V2戦略 🎯"
            v2_wins += 1
        else:
            winner = "引き分け ⚖️"
        
        print(f"{metric}: {winner}")
    
    # 総合判定
    print(f"\n🎖️ **総合優位性**")
    if macro_wins > v2_wins:
        print("**マクロ長期戦略の勝利!** 📈")
        print(f"優位指標数: {macro_wins}/{len(metrics)}")
    elif v2_wins > macro_wins:
        print("**V2戦略の勝利!** 🚀") 
        print(f"優位指標数: {v2_wins}/{len(metrics)}")
    else:
        print("**引き分け** ⚖️")
    
    # 推奨事項
    print(f"\n💡 **戦略推奨事項**")
    print("-" * 30)
    
    if macro_stats['total_pnl'] > v2_stats['total_pnl'] * 1.5:
        print("✅ マクロ長期戦略を主力戦略として採用を推奨")
        print("   理由: 圧倒的な収益性")
    elif v2_stats['win_rate'] > macro_stats['win_rate'] + 10:
        print("✅ V2戦略を主力戦略として採用を推奨")
        print("   理由: 高い勝率と安定性")
    elif abs(macro_stats['total_pnl'] - v2_stats['total_pnl']) < 100000:
        print("✅ 両戦略のハイブリッド運用を推奨")
        print("   理由: 相補的な特性で分散効果を期待")
    else:
        print("✅ より詳細な分析が必要")
    
    # 結果保存
    save_comparison_results(macro_stats, v2_stats, comparison_table, macro_executor, v2_executor)

def save_comparison_results(macro_stats, v2_stats, comparison_table, macro_executor, v2_executor):
    """
    比較結果をファイルに保存
    """
    output_dir = "results/strategy_comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    # 比較レポート作成
    report = f"""# 戦略比較分析レポート

## 実行日時
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## 比較対象
1. **マクロ長期戦略** (developブランチから)
2. **V2戦略** (改良版コア戦略)

## 比較結果サマリー

{comparison_table.to_string()}

## パフォーマンス分析

### 収益性
- マクロ長期戦略: {macro_stats['total_pnl']:,.0f}円 ({macro_stats['total_return']:.2f}%)
- V2戦略: {v2_stats['total_pnl']:,.0f}円 ({v2_stats['total_return']:.2f}%)

### 安定性
- マクロ長期戦略 DD: {macro_stats['max_drawdown']:.2f}%
- V2戦略 DD: {v2_stats['max_drawdown']:.2f}%

### 取引効率
- マクロ長期戦略: {macro_stats['total_trades']}取引, 勝率{macro_stats['win_rate']:.2f}%
- V2戦略: {v2_stats['total_trades']}取引, 勝率{v2_stats['win_rate']:.2f}%

## 結論

両戦略の詳細な特性分析により、最適な戦略選択または統合アプローチを決定する必要がある。

---
🤖 Generated with Claude Code - Strategy Comparison System
"""
    
    # レポート保存
    with open(f'{output_dir}/comparison_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 統計データをJSON保存
    combined_stats = {
        'macro_strategy': macro_stats,
        'v2_strategy': v2_stats,
        'comparison_date': datetime.now().isoformat()
    }
    
    with open(f'{output_dir}/comparison_statistics.json', 'w') as f:
        json.dump(combined_stats, f, indent=2, default=str)
    
    print(f"\n📁 比較結果を保存: {output_dir}/")

if __name__ == "__main__":
    print("🚀 戦略比較システム起動")
    print("自動データ収集 → マクロ長期戦略テスト → V2戦略テスト → 比較分析")
    
    macro_executor, macro_stats, v2_executor, v2_stats = run_strategy_comparison()
    
    print("\n✅ 戦略比較完了!")
    print("結果は results/strategy_comparison/ に保存されました")