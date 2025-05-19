import os
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
from src.strategies.macro_based_long_term_strategy import MacroBasedLongTermStrategy
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.data.data_processor_enhanced import DataProcessor
from src.data.multi_timeframe_data_manager import MultiTimeframeDataManager
from src.utils.logger import Logger
from src.utils.visualizer import Visualizer

parser = argparse.ArgumentParser(description='マクロ経済要因に基づく長期戦略のバックテスト')
parser.add_argument('--years', type=str, default='2023,2024', help='テスト対象年（カンマ区切り、例：2023,2024）')
args = parser.parse_args()

output_dir = "results/macro_long_term"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/charts", exist_ok=True)

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info("マクロ経済要因に基づく長期戦略のバックテスト開始")

strategy = MacroBasedLongTermStrategy(
    bb_window=20,
    bb_dev=2.0,
    rsi_window=14,
    rsi_upper=70,
    rsi_lower=30,
    sl_pips=50.0,
    tp_pips=150.0,
    timeframe_weights={'1D': 3.0, '1W': 2.0, '1M': 1.0, '4H': 0.5},
    quality_threshold=0.7,
    use_macro_analysis=True,
    macro_weight=2.0
)

data_manager = MultiTimeframeDataManager(base_timeframe="1D")

years = [int(year) for year in args.years.split(',')]
data_processor = DataProcessor(pd.DataFrame())  # 空のデータフレームで初期化

total_trades = 0
total_wins = 0
total_profit = 0.0
total_profit_factor = 0.0

for test_year in years:
    logger.log_info(f"{test_year}年のデータを処理中...")
    
    timeframes = ['4H', '1D', '1W', '1M']
    data_dict = data_manager.load_data(timeframes, [test_year])
    
    if not data_dict:
        logger.log_error(f"{test_year}年のデータが見つかりません")
        continue
    
    data_dict = data_manager.calculate_indicators(data_dict)
    
    data_dict = data_manager.synchronize_timeframes(data_dict)
    
    logger.log_info("シグナル生成開始")
    try:
        signals_df = strategy.generate_signals(data_dict)
        if signals_df.empty:
            logger.log_warning("シグナルが生成されませんでした")
            continue
            
        logger.log_info(f"シグナル生成完了: {len(signals_df)}行")
        
        logger.log_info("バックテスト実行中...")
        backtest_engine = CustomBacktestEngine(signals_df, initial_balance=2000000)
        backtest_results = backtest_engine.run()
        
        trades = backtest_results['trades']
        if not trades.empty:
            wins = trades[trades['profit'] > 0]
            losses = trades[trades['profit'] < 0]
            
            win_rate = len(wins) / len(trades) * 100 if len(trades) > 0 else 0
            profit_factor = abs(wins['profit'].sum() / losses['profit'].sum()) if losses['profit'].sum() != 0 else float('inf')
            
            logger.log_info(f"バックテスト結果: {len(trades)}トレード, 勝率 {win_rate:.2f}%, プロフィットファクター {profit_factor:.2f}")
            logger.log_info(f"純利益: {trades['profit'].sum():.2f}円")
            
            total_trades += len(trades)
            total_wins += len(wins)
            total_profit += trades['profit'].sum()
            
            if profit_factor != float('inf'):
                total_profit_factor += profit_factor
            
            visualizer = Visualizer()
            
            equity_curve = backtest_results['equity_curve']
            visualizer.plot_equity_curve(equity_curve, f'マクロ長期戦略_エクイティカーブ_{test_year}', output_dir=f"{output_dir}/charts")
            
            equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
            equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
            visualizer.plot_drawdown(equity_curve, f'マクロ長期戦略_ドローダウン_{test_year}', output_dir=f"{output_dir}/charts")
            
            monthly_perf = backtest_results['monthly_performance']
            months = list(monthly_perf.keys())
            profits = [monthly_perf[m]['profit'] for m in months]
            visualizer.plot_monthly_returns(months, profits, f'マクロ長期戦略_月別パフォーマンス_{test_year}', output_dir=f"{output_dir}/charts")
    except Exception as e:
        logger.log_error(f"バックテスト中にエラーが発生しました: {e}")
        continue

if total_trades > 0:
    total_win_rate = (total_wins / total_trades) * 100
    avg_profit_factor = total_profit_factor / len(years)
    
    logger.log_info(f"総合結果: {total_trades}トレード, 勝率 {total_win_rate:.2f}%, 平均プロフィットファクター {avg_profit_factor:.2f}")
    logger.log_info(f"総純利益: {total_profit:.2f}円")
    
    annual_return = (total_profit / 2000000) * 100
    logger.log_info(f"年利: {annual_return:.2f}%")
    
    with open(f"{output_dir}/backtest_report.md", "w") as f:
        f.write(f"# マクロ経済要因に基づく長期戦略バックテスト結果\n\n")
        f.write(f"テスト期間: {min(years)}年 - {max(years)}年\n\n")
        
        f.write(f"## 総合パフォーマンス\n\n")
        f.write(f"| 指標 | 値 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 総トレード数 | {total_trades} |\n")
        f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
        f.write(f"| 平均プロフィットファクター | {avg_profit_factor:.2f} |\n")
        f.write(f"| 総純利益 | {total_profit:.2f}円 |\n")
        f.write(f"| 年利 | {annual_return:.2f}% |\n")
        
        f.write(f"\n## 戦略パラメータ\n\n")
        f.write(f"| パラメータ | 値 | 説明 |\n")
        f.write(f"|------|------|------|\n")
        f.write(f"| bb_window | 20 | ボリンジャーバンドの期間 |\n")
        f.write(f"| bb_dev | 2.0 | ボリンジャーバンドの標準偏差 |\n")
        f.write(f"| rsi_window | 14 | RSIの期間 |\n")
        f.write(f"| rsi_upper | 70 | RSI上限閾値 |\n")
        f.write(f"| rsi_lower | 30 | RSI下限閾値 |\n")
        f.write(f"| sl_pips | 50.0 | ストップロス幅（pips） |\n")
        f.write(f"| tp_pips | 150.0 | テイクプロフィット幅（pips） |\n")
        f.write(f"| quality_threshold | 0.7 | シグナル品質閾値 |\n")
        f.write(f"| macro_weight | 2.0 | マクロ要因の重み |\n")
        
        f.write(f"\n## マクロ経済指標の重み\n\n")
        f.write(f"| 指標 | 重み | 説明 |\n")
        f.write(f"|------|------|------|\n")
        f.write(f"| GDP成長率 | 30% | 経済成長の指標 |\n")
        f.write(f"| 政策金利 | 25% | 中央銀行の金融政策 |\n")
        f.write(f"| インフレ率 | 20% | 物価上昇率 |\n")
        f.write(f"| 雇用統計 | 15% | 労働市場の状況 |\n")
        f.write(f"| 貿易収支 | 10% | 国際収支の状況 |\n")
        
        f.write(f"\n## 結論\n\n")
        if annual_return >= 5.0:
            f.write(f"マクロ経済要因に基づく長期戦略は目標年利5-15%を達成し、有効な戦略であることが確認されました。\n")
        else:
            f.write(f"マクロ経済要因に基づく長期戦略は目標年利5-15%に達していないため、さらなる最適化が必要です。\n")
        
        f.write(f"\n## 今後の改善点\n\n")
        f.write(f"1. マクロ経済指標の自動更新機能の実装\n")
        f.write(f"2. 市場レジームに応じたパラメータの動的調整\n")
        f.write(f"3. 複数通貨ペアへの拡張によるリスク分散\n")
        f.write(f"4. 季節性・周期性分析の統合\n")

logger.log_info("マクロ経済要因に基づく長期戦略のバックテスト完了")
