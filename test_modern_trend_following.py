#!/usr/bin/env python3
"""
Modern Trend Following Strategy テスト
2024-2025年の市場研究に基づく現代的アルゴリズム戦略の実装と検証
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.modern_trend_following_strategy import modern_trend_following_wrapper
from auto_test_runner import auto_test, compare_tests

def run_modern_trend_following_test():
    """Modern Trend Following Strategy の完全テスト実行"""
    
    print("=" * 60)
    print("Modern Trend Following Strategy テスト")
    print("研究ベース: 2024-2025年市場でのアルゴリズム取引戦略")
    print("期待リターン: 15%+ 年利、シャープレシオ 0.82")
    print("=" * 60)
    
    # テスト設定
    test_config = {
        'strategy_func': modern_trend_following_wrapper,
        'test_name': 'modern_trend_following_2024',
        'strategy_config': {
            'approach': 'multi_timeframe_trend_following',
            'base_risk': 0.015,  # 1.5%
            'max_positions': 5,
            'min_trend_strength': 0.65,
            'market_regime_filter': True,
            'adaptive_position_sizing': True,
            'dynamic_stops': True
        },
        'timeframe': '15min',
        'additional_timeframes': ['1H', '4H']  # 多時間軸分析用
    }
    
    try:
        # 自動テスト実行
        executor, stats = auto_test(**test_config)
        
        # 詳細分析
        analyze_modern_strategy_results(executor, stats)
        
        return executor, stats
        
    except Exception as e:
        print(f"[ERROR] テスト実行エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def analyze_modern_strategy_results(executor, stats):
    """Modern Trend Following Strategy の結果詳細分析"""
    
    print("\n" + "=" * 50)
    print("詳細分析: Modern Trend Following Strategy")
    print("=" * 50)
    
    # 基本統計
    print(f"\n【基本パフォーマンス】")
    print(f"初期資金: {stats['initial_balance']:,.0f}円")
    print(f"最終資金: {stats['final_balance']:,.0f}円")
    print(f"総損益: {stats['total_pnl']:,.0f}円 ({stats['total_return']:.2f}%)")
    print(f"年平均リターン: {(stats['total_return'] / 3):.2f}%")
    print(f"最大ドローダウン: {stats['max_drawdown']:.2f}%")
    
    # 取引効率分析
    print(f"\n【取引効率】")
    print(f"総取引数: {stats['total_trades']}")
    print(f"勝ちトレード: {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
    print(f"負けトレード: {stats['losing_trades']}")
    print(f"平均利益: {stats['avg_win']:,.0f}円")
    print(f"平均損失: {stats['avg_loss']:,.0f}円")
    print(f"プロフィットファクター: {stats['profit_factor']:.2f}")
    
    # Risk/Reward分析
    if stats['avg_loss'] != 0:
        rr_ratio = abs(stats['avg_win'] / stats['avg_loss'])
        print(f"Risk/Reward比率: {rr_ratio:.2f}")
        
        if rr_ratio >= 2.5:
            rr_assessment = "優秀"
        elif rr_ratio >= 2.0:
            rr_assessment = "良好"
        elif rr_ratio >= 1.5:
            rr_assessment = "普通"
        else:
            rr_assessment = "改善要"
        
        print(f"R/R評価: {rr_assessment}")
    
    # 研究目標との比較
    print(f"\n【研究目標との比較】")
    annual_return = stats['total_return'] / 3
    target_annual_return = 15.0
    
    print(f"年平均リターン: {annual_return:.1f}% (目標: {target_annual_return}%)")
    
    if annual_return >= target_annual_return * 0.9:  # 90%以上達成
        performance_rating = "目標達成"
    elif annual_return >= target_annual_return * 0.7:  # 70%以上達成
        performance_rating = "概ね良好"
    elif annual_return >= target_annual_return * 0.5:  # 50%以上達成
        performance_rating = "改善余地あり"
    else:
        performance_rating = "要見直し"
    
    print(f"目標達成度: {(annual_return/target_annual_return)*100:.1f}% - {performance_rating}")
    
    # シャープレシオ推定
    if stats['total_trades'] > 50:
        # 月次リターンから推定シャープレシオ計算
        monthly_perf = executor.get_monthly_performance()
        if not monthly_perf.empty and len(monthly_perf) > 12:
            monthly_returns = monthly_perf['profit'] / stats['initial_balance'] * 100
            monthly_return_mean = monthly_returns.mean()
            monthly_return_std = monthly_returns.std()
            
            if monthly_return_std > 0:
                sharpe_ratio = (monthly_return_mean / monthly_return_std) * np.sqrt(12)  # 年換算
                print(f"推定シャープレシオ: {sharpe_ratio:.2f} (目標: 0.82)")
                
                if sharpe_ratio >= 0.75:
                    sharpe_rating = "優秀"
                elif sharpe_ratio >= 0.5:
                    sharpe_rating = "良好"
                elif sharpe_ratio >= 0.3:
                    sharpe_rating = "普通"
                else:
                    sharpe_rating = "改善要"
                
                print(f"シャープ評価: {sharpe_rating}")
    
    # 月別パフォーマンス
    monthly_perf = executor.get_monthly_performance()
    if not monthly_perf.empty:
        print(f"\n【月別パフォーマンス（直近12ヶ月）】")
        
        recent_months = monthly_perf.tail(12)
        profitable_months = len(recent_months[recent_months['profit'] > 0])
        
        print(f"収益月数: {profitable_months}/12ヶ月 ({profitable_months/12*100:.1f}%)")
        
        # 月20万円目標達成分析
        months_200k = len(recent_months[recent_months['profit'] >= 200000])
        months_100k = len(recent_months[recent_months['profit'] >= 100000])
        
        avg_monthly_profit = recent_months['profit'].mean()
        print(f"月平均利益: {avg_monthly_profit:,.0f}円")
        print(f"月20万円達成: {months_200k}/12ヶ月 ({months_200k/12*100:.1f}%)")
        print(f"月10万円以上: {months_100k}/12ヶ月 ({months_100k/12*100:.1f}%)")
        
        # 目標達成能力評価
        if avg_monthly_profit >= 200000:
            monthly_assessment = "月20万円目標達成"
        elif avg_monthly_profit >= 150000:
            monthly_assessment = "月20万円目標に近い"
        elif avg_monthly_profit >= 100000:
            monthly_assessment = "月10万円レベル"
        else:
            monthly_assessment = "月目標未達成"
        
        print(f"月間目標評価: {monthly_assessment}")
    
    # トレンドフォロー戦略の特徴分析
    print(f"\n【トレンドフォロー戦略の特徴】")
    
    if executor.trade_history:
        trades_df = pd.DataFrame(executor.trade_history)
        
        # 勝ちトレードと負けトレードの期間分析
        if not trades_df.empty:
            win_trades = trades_df[trades_df['pnl_amount'] > 0]
            loss_trades = trades_df[trades_df['pnl_amount'] < 0]
            
            if not win_trades.empty:
                avg_win_pips = win_trades['pnl_pips'].mean()
                print(f"平均勝ちトレード: {avg_win_pips:.1f}pips")
                
            if not loss_trades.empty:
                avg_loss_pips = abs(loss_trades['pnl_pips'].mean())
                print(f"平均負けトレード: {avg_loss_pips:.1f}pips")
            
            # 戦略別分析
            if 'strategy' in trades_df.columns:
                strategy_performance = trades_df.groupby('strategy').agg({
                    'pnl_amount': ['count', 'sum', 'mean'],
                    'pnl_pips': 'mean'
                }).round(1)
                
                print(f"\n戦略別パフォーマンス:")
                for strategy in strategy_performance.index:
                    count = strategy_performance.loc[strategy, ('pnl_amount', 'count')]
                    total_pnl = strategy_performance.loc[strategy, ('pnl_amount', 'sum')]
                    avg_pnl = strategy_performance.loc[strategy, ('pnl_amount', 'mean')]
                    print(f"  {strategy}: {count}取引, {total_pnl:,.0f}円, 平均{avg_pnl:,.0f}円")

def compare_with_previous_strategies():
    """過去の戦略と比較分析"""
    
    print("\n" + "=" * 50)
    print("戦略比較分析")
    print("=" * 50)
    
    # 比較対象の特定
    strategy_names = []
    
    # 結果ディレクトリから利用可能な戦略を検索
    results_dir = "results"
    if os.path.exists(results_dir):
        for item in os.listdir(results_dir):
            if os.path.isdir(os.path.join(results_dir, item)):
                # statistics.jsonが存在する戦略のみ
                if os.path.exists(os.path.join(results_dir, item, "statistics.json")):
                    strategy_names.append(item)
    
    # Modern Trend Following を含める
    strategy_names.append('modern_trend_following_2024')
    
    if len(strategy_names) > 1:
        try:
            comparison_df = compare_tests(strategy_names)
            if not comparison_df.empty:
                print("\n=== 戦略ランキング（総損益順） ===")
                print(comparison_df.to_string(index=False))
                
                # トップ戦略の特定
                top_strategy = comparison_df.iloc[0]['Test Name']
                top_pnl = comparison_df.iloc[0]['Total PnL (JPY)']
                
                print(f"\n最優秀戦略: {top_strategy} ({top_pnl:,.0f}円)")
                
                # Modern Trend Following の位置確認
                if 'modern_trend_following_2024' in comparison_df['Test Name'].values:
                    mtf_row = comparison_df[comparison_df['Test Name'] == 'modern_trend_following_2024'].iloc[0]
                    mtf_rank = comparison_df[comparison_df['Test Name'] == 'modern_trend_following_2024'].index[0] + 1
                    print(f"Modern Trend Following 順位: {mtf_rank}/{len(comparison_df)}")
                    print(f"  - 損益: {mtf_row['Total PnL (JPY)']:,.0f}円")
                    print(f"  - 勝率: {mtf_row['Win Rate (%)']:.1f}%")
                    print(f"  - 取引数: {int(mtf_row['Total Trades'])}")
        except Exception as e:
            print(f"比較分析エラー: {str(e)}")
    else:
        print("比較対象の戦略が見つかりません")

if __name__ == "__main__":
    print("Modern Trend Following Strategy 総合テスト開始")
    print(f"実行時刻: {datetime.now().isoformat()}")
    
    # メインテスト実行
    executor, stats = run_modern_trend_following_test()
    
    if executor and stats:
        # 過去戦略との比較
        compare_with_previous_strategies()
        
        print("\n" + "=" * 60)
        print("Modern Trend Following Strategy テスト完了")
        print("=" * 60)
        
        # 最終評価サマリー
        annual_return = stats['total_return'] / 3
        monthly_perf = executor.get_monthly_performance()
        avg_monthly = monthly_perf['profit'].mean() if not monthly_perf.empty else 0
        
        print(f"\n【最終評価サマリー】")
        print(f"年平均リターン: {annual_return:.1f}% (目標: 15%)")
        print(f"月平均利益: {avg_monthly:,.0f}円 (目標: 200,000円)")
        print(f"最大ドローダウン: {stats['max_drawdown']:.1f}%")
        print(f"プロフィットファクター: {stats['profit_factor']:.2f}")
        print(f"勝率: {stats['win_rate']:.1f}%")
        
        # 総合評価
        score = 0
        if annual_return >= 15: score += 25
        elif annual_return >= 10: score += 15
        elif annual_return >= 5: score += 10
        
        if avg_monthly >= 200000: score += 25
        elif avg_monthly >= 150000: score += 20
        elif avg_monthly >= 100000: score += 15
        elif avg_monthly >= 50000: score += 10
        
        if stats['max_drawdown'] <= 10: score += 20
        elif stats['max_drawdown'] <= 15: score += 15
        elif stats['max_drawdown'] <= 20: score += 10
        
        if stats['profit_factor'] >= 2.0: score += 15
        elif stats['profit_factor'] >= 1.5: score += 10
        elif stats['profit_factor'] >= 1.2: score += 5
        
        if stats['win_rate'] >= 50: score += 15
        elif stats['win_rate'] >= 40: score += 10
        elif stats['win_rate'] >= 35: score += 5
        
        if score >= 90:
            grade = "A (優秀)"
        elif score >= 75:
            grade = "B (良好)"
        elif score >= 60:
            grade = "C (普通)"
        elif score >= 45:
            grade = "D (改善要)"
        else:
            grade = "F (再検討)"
        
        print(f"\n総合評価: {score}/100点 - {grade}")
        
    else:
        print("\n[ERROR] テストが正常に完了しませんでした")