import pandas as pd
import numpy as np
import logging
import os
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy
from custom_backtest_engine import CustomBacktestEngine
from src.visualization.visualizer import Visualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_short_term_15min_only.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_short_term_15min_only'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_years = [2025]  # Just test 2025 for now to get quick results

logger.info(f"短期戦略（15分足のみ）のテスト開始")

all_results = []
total_trades = 0
total_wins = 0
total_profit = 0.0

try:
    for test_year in test_years:
        logger.info(f"テスト年: {test_year}")
        
        data_processor = DataProcessor(pd.DataFrame())
        df_15min = data_processor.load_processed_data('15min', test_year)
        
        if df_15min.empty:
            logger.error(f"15分足データが見つかりません: {test_year}年")
            continue
        
        logger.info(f"データ読み込み成功: 15分足={len(df_15min)}行")
        
        strategy = ShortTermBollingerRsiStrategy()
        strategy.timeframe_weights = {'15min': 1.0}
        
        strategy.rsi_upper = 60  # 65から60に緩和
        strategy.rsi_lower = 40  # 35から40に緩和
        
        logger.info("シグナル生成開始")
        signals_df = strategy.generate_signals(df_15min, test_year)
        
        logger.info(f"シグナル生成完了: {len(signals_df)}行")
        signal_count = (signals_df['signal'] != 0).sum()
        logger.info(f"シグナル数: {signal_count}")
        
        if signal_count == 0:
            logger.warning(f"{test_year}年のシグナルが生成されませんでした。パラメータを調整してください。")
            continue
        
        logger.info("バックテスト実行開始")
        backtest_engine = CustomBacktestEngine(signals_df, spread_pips=0.03)
        backtest_results = backtest_engine.run()
        
        trades = backtest_results['trades']
        wins = backtest_results['wins']
        losses = backtest_results['losses']
        win_rate = backtest_results['win_rate']
        profit_factor = backtest_results['profit_factor']
        net_profit = backtest_results['net_profit']
        
        logger.info(f"{test_year}年のバックテスト結果:")
        logger.info(f"総トレード数: {trades}")
        logger.info(f"勝率: {win_rate:.2f}%")
        logger.info(f"プロフィットファクター: {profit_factor:.2f}")
        logger.info(f"純利益: {net_profit:.2f}")
        
        all_results.append({
            'year': test_year,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_profit': net_profit
        })
        
        total_trades += trades
        total_wins += wins
        total_profit += net_profit
        
        if trades > 0:
            start_date = signals_df.index.min()
            end_date = signals_df.index.max()
            days = (end_date - start_date).days + 1
            trades_per_day = trades / days
            logger.info(f"1日あたりの平均取引回数: {trades_per_day:.2f}")
            
            visualizer = Visualizer(output_dir=f'{output_dir}/charts')
            
            equity_curve = backtest_results['equity_curve']
            visualizer.plot_equity_curve(equity_curve, f'短期戦略_エクイティカーブ_{test_year}')
            
            equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
            equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
            visualizer.plot_drawdown(equity_curve, f'短期戦略_ドローダウン_{test_year}')
            
            monthly_perf = backtest_results['monthly_performance']
            months = list(monthly_perf.keys())
            profits = [monthly_perf[m]['profit'] for m in months]
            visualizer.plot_monthly_returns(months, profits, f'短期戦略_月別パフォーマンス_{test_year}')
    
    if total_trades > 0:
        total_win_rate = (total_wins / total_trades) * 100
        logger.info(f"全期間の総合結果:")
        logger.info(f"総トレード数: {total_trades}")
        logger.info(f"総勝率: {total_win_rate:.2f}%")
        logger.info(f"総純利益: {total_profit:.2f}")
        
        with open(f'{output_dir}/reports/short_term_15min_only_results.md', 'w') as f:
            f.write(f"# 短期戦略（15分足のみ）のバックテスト結果\n\n")
            f.write(f"## 概要\n\n")
            f.write(f"15分足のみを使用した短期ボリンジャーバンド＋RSI戦略のバックテスト結果です。\n")
            f.write(f"1分足データの処理に時間がかかるため、15分足のみで実行しました。\n\n")
            f.write(f"## 総合結果\n\n")
            f.write(f"| 項目 | 値 |\n")
            f.write(f"| --- | --- |\n")
            f.write(f"| 総トレード数 | {total_trades} |\n")
            f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
            f.write(f"| 純利益 | {total_profit:.2f} |\n")
            f.write(f"| 1日あたりの平均取引回数 | {trades_per_day:.2f} |\n\n")
            
            f.write(f"## 年別結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |\n")
            f.write(f"| --- | --- | --- | --- | --- |\n")
            
            for result in all_results:
                f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} |\n")
            
            f.write(f"\n## パラメータ設定\n\n")
            f.write(f"| パラメータ | 値 | 説明 |\n")
            f.write(f"| --- | --- | --- |\n")
            f.write(f"| bb_dev | 1.4 | 標準偏差を小さくしてバンド幅を狭める |\n")
            f.write(f"| rsi_upper | 60 | RSIの閾値を緩和して売りシグナルを増やす |\n")
            f.write(f"| rsi_lower | 40 | RSIの閾値を緩和して買いシグナルを増やす |\n")
            f.write(f"| sl_pips | 3.0 | 損切り幅を小さくする |\n")
            f.write(f"| tp_pips | 6.0 | 利確幅も小さくする |\n")
            f.write(f"| timeframe_weights | {{'15min': 1.0}} | 15分足のみを使用 |\n")
            
            f.write(f"\n## 結論\n\n")
            
            if total_win_rate >= 70 and profit_factor >= 2.0:
                f.write(f"短期戦略（15分足のみ）は目標の勝率70%以上とプロフィットファクター2.0以上を達成しました。\n")
                f.write(f"RSI閾値を緩和することで、取引頻度を高めながらも高い勝率を維持できています。\n")
            else:
                f.write(f"短期戦略（15分足のみ）は目標の勝率70%以上とプロフィットファクター2.0以上を達成できませんでした。\n")
                f.write(f"以下の点を検討してください：\n\n")
                f.write(f"1. RSI閾値のさらなる調整\n")
                f.write(f"2. ボリンジャーバンド幅の最適化\n")
                f.write(f"3. 時間フィルターの調整\n")
                f.write(f"4. 1分足データの処理方法の改善\n")
        
        logger.info(f"テスト完了: 結果は {output_dir}/reports/short_term_15min_only_results.md に保存されました")
    else:
        logger.warning("トレードが生成されませんでした")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
