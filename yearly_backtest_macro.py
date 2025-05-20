"""
マクロ経済要因に基づく長期戦略の年別バックテスト実行スクリプト
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from datetime import datetime
from src.strategies.macro_based_long_term_strategy import MacroBasedLongTermStrategy
from src.data.multi_timeframe_data_manager import MultiTimeframeDataManager
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger
from src.visualization.visualizer import Visualizer
from typing import Dict, List, Any

def run_yearly_backtest(year, max_positions=1):
    """
    指定された年のバックテストを実行する
    
    Parameters
    ----------
    year : int
        バックテスト対象の年
    max_positions : int, default 1
        同時に保有できる最大ポジション数
        
    Returns
    -------
    dict
        バックテスト結果
    """
    output_dir = f"results/yearly/{year}/macro_long_term"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/charts", exist_ok=True)
    
    log_dir = f"{output_dir}/logs"
    os.makedirs(log_dir, exist_ok=True)
    logger = Logger(log_dir)
    logger.log_info(f"{year}年 マクロ経済要因に基づく長期戦略 バックテスト開始")
    
    strategy = MacroBasedLongTermStrategy(
        bb_window=20,
        bb_dev=2.0,
        rsi_window=14,
        rsi_upper=70,
        rsi_lower=30,
        base_sl_pips=50.0,
        tp_pips=200.0,
        timeframe_weights={'1D': 3.0, '1W': 2.0, '1M': 1.0, '4H': 0.5},
        quality_threshold=0.01,  # 品質閾値を0.01に設定して取引数を増加
        use_macro_analysis=True,
        macro_weight=2.0
    )
    
    data_manager = MultiTimeframeDataManager(base_timeframe="1D")
    
    available_timeframes = []
    for tf in ['4H', '1D', '1W', '1M']:
        tf_dir = f"data/processed/{year}/USDJPY"
        tf_file = f"{tf_dir}/{tf}.csv"
        if os.path.exists(tf_file):
            available_timeframes.append(tf)
            logger.log_info(f"{tf}データが利用可能です: {year}年")
    
    if not available_timeframes:
        logger.log_warning(f"{year}年のデータが見つかりません")
        return {
            "year": year,
            "has_data": False,
            "trades": 0,
            "profit": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "annual_return": 0
        }
    
    if '1D' in available_timeframes:
        data_manager.base_timeframe = "1D"
    elif '4H' in available_timeframes:
        data_manager.base_timeframe = "4H"
    else:
        data_manager.base_timeframe = available_timeframes[0]
    
    logger.log_info(f"基準時間足を {data_manager.base_timeframe} に設定しました")
    
    data_dict = data_manager.load_data(available_timeframes, [year], currency_pair="USDJPY")
    
    if not data_dict:
        logger.log_warning(f"{year}年のデータが見つかりません")
        return {
            "year": year,
            "has_data": False,
            "trades": 0,
            "profit": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "annual_return": 0
        }
    
    adjusted_weights = {}
    for tf in available_timeframes:
        if tf in strategy.timeframe_weights:
            adjusted_weights[tf] = strategy.timeframe_weights[tf]
    
    if adjusted_weights:
        strategy.timeframe_weights = adjusted_weights
        logger.log_info(f"調整された時間足の重み: {strategy.timeframe_weights}")
    
    data_dict = data_manager.calculate_indicators(data_dict)
    data_dict = data_manager.synchronize_timeframes(data_dict)
    
    logger.log_info("シグナル生成開始")
    try:
        signals_df = strategy.generate_signals(data_dict)
        if signals_df.empty:
            logger.log_warning("シグナルが生成されませんでした")
            return {
                "year": year,
                "has_data": True,
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "annual_return": 0
            }
            
        logger.log_info(f"シグナル生成完了: {len(signals_df)}行")
        
        logger.log_info("バックテスト実行中...")
        backtest_engine = CustomBacktestEngine(
            signals_df, 
            initial_balance=2000000, 
            max_positions=max_positions
        )
        backtest_results = backtest_engine.run()
        
        trades = backtest_results['trades']
        if trades.empty:
            logger.log_warning("トレードがありませんでした")
            return {
                "year": year,
                "has_data": True,
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "annual_return": 0
            }
        
        wins = trades[trades['損益(円)'] > 0]
        losses = trades[trades['損益(円)'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100 if len(trades) > 0 else 0
        profit_factor = abs(wins['損益(円)'].sum() / losses['損益(円)'].sum()) if losses['損益(円)'].sum() != 0 else float('inf')
        annual_return = (trades['損益(円)'].sum() / 2000000) * 100
        
        logger.log_info(f"バックテスト結果: {len(trades)}トレード, 勝率 {win_rate:.2f}%, プロフィットファクター {profit_factor:.2f}")
        logger.log_info(f"純利益: {trades['損益(円)'].sum():.2f}円 (年利: {annual_return:.2f}%)")
        
        visualizer = Visualizer(output_dir=f"{output_dir}/charts")
        
        equity_curve = backtest_results['equity_curve']
        visualizer.plot_equity_curve(equity_curve, filename=f'マクロ長期戦略_エクイティカーブ_{year}')
        
        equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
        equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
        visualizer.plot_drawdown(equity_curve, filename=f'マクロ長期戦略_ドローダウン_{year}')
        
        monthly_perf = backtest_results['monthly_performance']
        if monthly_perf:
            months = list(monthly_perf.keys())
            profits = [monthly_perf[m]['profit'] for m in months]
            visualizer.plot_monthly_returns(months, profits, filename=f'マクロ長期戦略_月別パフォーマンス_{year}')
        
        return {
            "year": year,
            "has_data": True,
            "trades": len(trades),
            "profit": trades['損益(円)'].sum(),
            "win_rate": win_rate,
            "profit_factor": profit_factor if profit_factor != float('inf') else 999.99,
            "annual_return": annual_return
        }
    except Exception as e:
        logger.log_error(f"バックテスト中にエラーが発生しました: {e}")
        return {
            "year": year,
            "has_data": True,
            "trades": 0,
            "profit": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "annual_return": 0
        }

def main():
    """
    2020年から2025年までの各年のバックテストを実行し、結果をまとめる
    """
    parser = argparse.ArgumentParser(description='マクロ経済要因に基づく長期戦略のバックテスト')
    parser.add_argument('--years', type=str, default='2020,2021,2022,2023,2024,2025',
                        help='バックテスト対象の年（カンマ区切り、例: 2020,2021,2022,2023,2024,2025）')
    parser.add_argument('--max-positions', type=int, default=1, help='同時に保有できる最大ポジション数')
    
    args = parser.parse_args()
    
    years = [int(year) for year in args.years.split(',')]
    print(f"対象年: {years}")
    
    results = []
    
    for year in years:
        print(f"=== {year}年のバックテスト実行中 ===")
        result = run_yearly_backtest(year, max_positions=args.max_positions)
        results.append(result)
        print(f"=== {year}年のバックテスト完了 ===")
        print(f"トレード数: {result['trades']}")
        print(f"総利益: {result['profit']:.0f}円")
        print(f"勝率: {result['win_rate']:.2f}%")
        print(f"プロフィットファクター: {result['profit_factor']:.2f}")
        print(f"年利: {result['annual_return']:.2f}%")
        print()
    
    results_df = pd.DataFrame(results)
    
    os.makedirs("results/macro_long_term", exist_ok=True)
    results_df.to_csv("results/macro_long_term/yearly_results.csv", index=False)
    
    with open("results/macro_long_term/yearly_results.md", "w") as f:
        f.write("# マクロ経済要因に基づく長期戦略 年別バックテスト結果\n\n")
        f.write(f"同時ポジション数: {args.max_positions}\n\n")
        f.write("| 年 | トレード数 | 勝率 | PF | 純利益 | 年利 |\n")
        f.write("|------|----------|------|------|--------|------|\n")
        
        total_trades = 0
        total_wins = 0
        total_profit = 0
        total_pf = 0
        valid_years = 0
        
        for result in results:
            year = result["year"]
            has_data = result["has_data"]
            trades = result["trades"]
            profit = result["profit"]
            win_rate = result["win_rate"]
            profit_factor = result["profit_factor"]
            annual_return = result["annual_return"]
            
            if has_data and trades > 0:
                valid_years += 1
                total_trades += trades
                total_wins += trades * (win_rate / 100)
                total_profit += profit
                total_pf += profit_factor
                
                f.write(f"| {year} | {trades} | {win_rate:.2f}% | {profit_factor:.2f} | {profit:.0f}円 | {annual_return:.2f}% |\n")
        
        if valid_years > 0:
            avg_trades = total_trades / valid_years
            avg_win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
            avg_pf = total_pf / valid_years
            avg_annual_return = (total_profit / (2000000 * valid_years)) * 100
            
            f.write(f"| **平均/合計** | **{avg_trades:.0f}** | **{avg_win_rate:.2f}%** | **{avg_pf:.2f}** | **{total_profit:.0f}円** | **{avg_annual_return:.2f}%** |\n")
    
    print("=== 年別バックテスト結果 ===")
    print("| 年 | トレード数 | 勝率 | PF | 純利益 | 年利 |")
    print("|------|----------|------|------|--------|------|")
    
    total_trades = 0
    total_wins = 0
    total_profit = 0
    total_pf = 0
    valid_years = 0
    
    for result in results:
        year = result["year"]
        has_data = result["has_data"]
        trades = result["trades"]
        profit = result["profit"]
        win_rate = result["win_rate"]
        profit_factor = result["profit_factor"]
        annual_return = result["annual_return"]
        
        if has_data and trades > 0:
            valid_years += 1
            total_trades += trades
            total_wins += trades * (win_rate / 100)
            total_profit += profit
            total_pf += profit_factor
            
            print(f"| {year} | {trades} | {win_rate:.2f}% | {profit_factor:.2f} | {profit:.0f}円 | {annual_return:.2f}% |")
    
    if valid_years > 0:
        avg_trades = total_trades / valid_years
        avg_win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        avg_pf = total_pf / valid_years
        avg_annual_return = (total_profit / (2000000 * valid_years)) * 100
        
        print(f"| **平均/合計** | **{avg_trades:.0f}** | **{avg_win_rate:.2f}%** | **{avg_pf:.2f}** | **{total_profit:.0f}円** | **{avg_annual_return:.2f}%** |")
    
    return results

if __name__ == "__main__":
    main()
