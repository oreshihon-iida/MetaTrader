import pandas as pd
import numpy as np
import logging
import os
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.dual_strategy_manager import DualStrategyManager
from custom_backtest_engine import CustomBacktestEngine
from src.visualization.visualizer import Visualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_dual_strategy_15min_only.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_dual_strategy_15min_only'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_year = 2025  # Just test 2025 for now to get quick results

logger.info(f"デュアル戦略（短期:15分足のみ+長期:1時間足+4時間足）のテスト開始 - {test_year}年のみ")

try:
    logger.info(f"テスト年: {test_year}")
    
    data_processor = DataProcessor(pd.DataFrame())
    df_15min = data_processor.load_processed_data('15min', test_year)
    df_1h = data_processor.load_processed_data('1H', test_year)
    
    if df_15min.empty or df_1h.empty:
        logger.error(f"必要なデータが見つかりません: {test_year}年")
        exit(1)
    
    df_4h = data_processor.load_processed_data('4H', test_year)
    
    logger.info(f"データ読み込み成功: 15分足={len(df_15min)}行, 1時間足={len(df_1h)}行")
    logger.info(f"追加データ: 4時間足={len(df_4h) if not df_4h.empty else 0}行")
    
    short_term_params = {
        'timeframe_weights': {'15min': 1.0},
        'rsi_upper': 60,  # RSIの閾値を緩和して売りシグナルを増やす
        'rsi_lower': 40,  # RSIの閾値を緩和して買いシグナルを増やす
    }
    
    long_term_params = {
        'timeframe_weights': {'1H': 1.0} if df_4h.empty else {'1H': 1.0, '4H': 3.0}
    }
    
    strategy_manager = DualStrategyManager(
        short_term_strategy_params=short_term_params,
        long_term_strategy_params=long_term_params,
        max_short_term_positions=2,
        max_long_term_positions=1,
        short_term_capital_ratio=0.3,
        long_term_capital_ratio=0.7
    )
    
    logger.info("シグナル生成開始")
    short_term_signals, long_term_signals = strategy_manager.generate_signals(df_15min, df_1h, test_year)
    
    short_term_signal_count = (short_term_signals['signal'] != 0).sum()
    logger.info(f"短期戦略シグナル数: {short_term_signal_count}")
    
    long_term_signal_count = (long_term_signals['signal'] != 0).sum()
    logger.info(f"長期戦略シグナル数: {long_term_signal_count}")
    
    if short_term_signal_count == 0 and long_term_signal_count == 0:
        logger.warning(f"{test_year}年のシグナルが生成されませんでした。パラメータを調整してください。")
        exit(1)
    
    short_term_results = None
    if short_term_signal_count > 0:
        logger.info("短期戦略のバックテスト実行開始")
        short_term_backtest = CustomBacktestEngine(short_term_signals, spread_pips=0.03)
        short_term_results = short_term_backtest.run()
    
    long_term_results = None
    if long_term_signal_count > 0:
        logger.info("長期戦略のバックテスト実行開始")
        long_term_backtest = CustomBacktestEngine(long_term_signals, spread_pips=0.03)
        long_term_results = long_term_backtest.run()
    
    short_term_trades = short_term_results['trades'] if short_term_results else 0
    short_term_wins = short_term_results['wins'] if short_term_results else 0
    short_term_profit = short_term_results['net_profit'] if short_term_results else 0
    short_term_win_rate = short_term_results['win_rate'] if short_term_results else 0
    short_term_profit_factor = short_term_results['profit_factor'] if short_term_results else 0
    
    long_term_trades = long_term_results['trades'] if long_term_results else 0
    long_term_wins = long_term_results['wins'] if long_term_results else 0
    long_term_profit = long_term_results['net_profit'] if long_term_results else 0
    long_term_win_rate = long_term_results['win_rate'] if long_term_results else 0
    long_term_profit_factor = long_term_results['profit_factor'] if long_term_results else 0
    
    total_trades = short_term_trades + long_term_trades
    total_wins = short_term_wins + long_term_wins
    total_profit = short_term_profit + long_term_profit
    
    total_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    logger.info(f"{test_year}年のデュアル戦略バックテスト結果:")
    logger.info(f"短期戦略: トレード数={short_term_trades}, 勝率={short_term_win_rate:.2f}%, 純利益={short_term_profit:.2f}")
    logger.info(f"長期戦略: トレード数={long_term_trades}, 勝率={long_term_win_rate:.2f}%, 純利益={long_term_profit:.2f}")
    logger.info(f"合計: トレード数={total_trades}, 勝率={total_win_rate:.2f}%, 純利益={total_profit:.2f}")
    
    if total_trades > 0:
        start_date = min(
            short_term_signals.index.min() if not short_term_signals.empty else pd.Timestamp('2099-01-01'),
            long_term_signals.index.min() if not long_term_signals.empty else pd.Timestamp('2099-01-01')
        )
        end_date = max(
            short_term_signals.index.max() if not short_term_signals.empty else pd.Timestamp('1970-01-01'),
            long_term_signals.index.max() if not long_term_signals.empty else pd.Timestamp('1970-01-01')
        )
        days = (end_date - start_date).days + 1
        trades_per_day = total_trades / days
        logger.info(f"1日あたりの平均取引回数: {trades_per_day:.2f}")
    
    if total_trades > 0:
        visualizer = Visualizer(output_dir=f'{output_dir}/charts')
        
        if short_term_results and long_term_results:
            short_term_equity = short_term_results['equity_curve']['equity']
            long_term_equity = long_term_results['equity_curve']['equity']
            
            common_dates = short_term_equity.index.intersection(long_term_equity.index)
            
            if len(common_dates) > 0:
                combined_equity = pd.DataFrame(index=common_dates)
                combined_equity['short_term'] = short_term_equity.loc[common_dates]
                combined_equity['long_term'] = long_term_equity.loc[common_dates]
                combined_equity['total'] = combined_equity['short_term'] + combined_equity['long_term']
                
                visualizer.plot_equity_curves(combined_equity, f'デュアル戦略_エクイティカーブ_{test_year}')
            else:
                logger.warning("短期戦略と長期戦略のエクイティカーブに共通する日付がありません")
    
    with open(f'{output_dir}/reports/dual_strategy_15min_only_results.md', 'w') as f:
        f.write(f"# デュアル戦略（短期:15分足のみ+長期:1時間足+4時間足）のバックテスト結果 - {test_year}年\n\n")
        f.write(f"## 概要\n\n")
        f.write(f"短期戦略（15分足のみ）と長期戦略（1時間足+4時間足）を組み合わせたデュアル戦略のバックテスト結果です。\n")
        f.write(f"1分足データの処理に時間がかかるため、短期戦略は15分足のみで実行しました。\n\n")
        f.write(f"## 結果\n\n")
        f.write(f"| 項目 | 短期戦略 | 長期戦略 | 合計 |\n")
        f.write(f"| --- | --- | --- | --- |\n")
        f.write(f"| トレード数 | {short_term_trades} | {long_term_trades} | {total_trades} |\n")
        f.write(f"| 勝率 | {short_term_win_rate:.2f}% | {long_term_win_rate:.2f}% | {total_win_rate:.2f}% |\n")
        f.write(f"| プロフィットファクター | {short_term_profit_factor:.2f} | {long_term_profit_factor:.2f} | - |\n")
        f.write(f"| 純利益 | {short_term_profit:.2f} | {long_term_profit:.2f} | {total_profit:.2f} |\n")
        
        if total_trades > 0:
            f.write(f"| 1日あたりの平均取引回数 | - | - | {trades_per_day:.2f} |\n\n")
        
        f.write(f"\n## 戦略設定\n\n")
        f.write(f"### 短期戦略（15分足のみ）\n\n")
        f.write(f"| パラメータ | 値 | 説明 |\n")
        f.write(f"| --- | --- | --- |\n")
        f.write(f"| bb_dev | 1.4 | 標準偏差を小さくしてバンド幅を狭める |\n")
        f.write(f"| rsi_upper | 60 | RSIの閾値を緩和して売りシグナルを増やす |\n")
        f.write(f"| rsi_lower | 40 | RSIの閾値を緩和して買いシグナルを増やす |\n")
        f.write(f"| sl_pips | 3.0 | 損切り幅を小さくする |\n")
        f.write(f"| tp_pips | 6.0 | 利確幅も小さくする |\n")
        f.write(f"| timeframe_weights | {{'15min': 1.0}} | 15分足のみを使用 |\n")
        f.write(f"| 資金配分 | 30% | 総資金の30%を短期戦略に配分 |\n\n")
        
        f.write(f"### 長期戦略（1時間足+4時間足）\n\n")
        f.write(f"| パラメータ | 値 | 説明 |\n")
        f.write(f"| --- | --- | --- |\n")
        f.write(f"| bb_dev | 2.0 | 標準偏差を大きくしてバンド幅を広める |\n")
        f.write(f"| rsi_upper | 80 | RSIの閾値を厳格化して高品質シグナルに限定 |\n")
        f.write(f"| rsi_lower | 20 | RSIの閾値を厳格化して高品質シグナルに限定 |\n")
        f.write(f"| sl_pips | 10.0 | 損切り幅を大きくする |\n")
        f.write(f"| tp_pips | 25.0 | 利確幅も大きくする |\n")
        f.write(f"| timeframe_weights | {{'1H': 1.0, '4H': 3.0}} | 4時間足の重みを大きくする |\n")
        f.write(f"| 資金配分 | 70% | 総資金の70%を長期戦略に配分 |\n\n")
        
        f.write(f"## 結論\n\n")
        
        if total_win_rate >= 70 and total_profit > 0:
            f.write(f"デュアル戦略は目標の勝率70%以上を達成し、プラスの純利益を生み出しました。\n")
            f.write(f"短期戦略と長期戦略を組み合わせることで、取引頻度を高めながらも高い勝率を維持できています。\n")
            f.write(f"短期戦略は頻繁な取引機会を提供し、長期戦略は大きな利益を狙うという役割分担が効果的に機能しています。\n")
        else:
            f.write(f"デュアル戦略は目標の勝率70%以上を達成できませんでした。\n")
            f.write(f"以下の点を検討してください：\n\n")
            f.write(f"1. 短期戦略と長期戦略のパラメータの最適化\n")
            f.write(f"2. 資金配分比率の調整\n")
            f.write(f"3. 各戦略の最大ポジション数の調整\n")
            f.write(f"4. 時間足の組み合わせの最適化\n")
            f.write(f"5. 1分足データの処理方法の改善\n")
    
    logger.info(f"テスト完了: 結果は {output_dir}/reports/dual_strategy_15min_only_results.md に保存されました")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
