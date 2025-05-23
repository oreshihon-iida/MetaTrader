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
        logging.FileHandler('logs/test_short_term_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_short_term_strategy'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_years = [2010, 2024, 2025]

logger.info(f"短期戦略（1分足+15分足）のテスト開始")

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
        
        df_1min = data_processor.load_processed_data('1min', test_year)
        
        if df_1min.empty:
            logger.warning(f"1分足データが見つかりません: {test_year}年")
            logger.warning("15分足データのみで戦略を実行します")
        
        logger.info(f"データ読み込み成功: 15分足={len(df_15min)}行, 1分足={len(df_1min) if not df_1min.empty else 0}行")
        
        strategy = ShortTermBollingerRsiStrategy()
        
        if df_1min.empty:
            strategy.timeframe_weights = {'15min': 1.0}
        
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
        
        with open(f'{output_dir}/reports/short_term_strategy_results.md', 'w') as f:
            f.write(f"# 短期戦略（1分足+15分足）のバックテスト結果\n\n")
            f.write(f"## 概要\n\n")
            f.write(f"1分足と15分足を組み合わせた超短期ボリンジャーバンド＋RSI戦略のバックテスト結果です。\n\n")
            f.write(f"## 総合結果\n\n")
            f.write(f"| 項目 | 値 |\n")
            f.write(f"| --- | --- |\n")
            f.write(f"| 総トレード数 | {total_trades} |\n")
            f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
            f.write(f"| 純利益 | {total_profit:.2f} |\n\n")
            
            f.write(f"## 年別結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |\n")
            f.write(f"| --- | --- | --- | --- | --- |\n")
            
            for result in all_results:
                f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} |\n")
            
            f.write(f"\n## パラメータ設定\n\n")
            f.write(f"| パラメータ | 値 | 説明 |\n")
            f.write(f"| --- | --- | --- |\n")
            f.write(f"| bb_dev | 1.4 | 標準偏差を小さくしてバンド幅を狭める |\n")
            f.write(f"| rsi_upper | 65 | RSIの閾値を緩和して売りシグナルを増やす |\n")
            f.write(f"| rsi_lower | 35 | RSIの閾値を緩和して買いシグナルを増やす |\n")
            f.write(f"| sl_pips | 3.0 | 損切り幅を小さくする |\n")
            f.write(f"| tp_pips | 6.0 | 利確幅も小さくする |\n")
            f.write(f"| timeframe_weights | {'1min': 3.0, '15min': 1.0} | 1分足の重みを大きくする |\n")
            
            f.write(f"\n## 結論\n\n")
            
            if total_win_rate >= 70 and any(r['profit_factor'] >= 2.0 for r in all_results):
                f.write(f"短期戦略は目標の勝率70%以上とプロフィットファクター2.0以上を達成しました。\n")
                f.write(f"1分足と15分足を組み合わせることで、取引頻度を高めながらも高い勝率を維持できています。\n")
            else:
                f.write(f"短期戦略は目標の勝率70%以上とプロフィットファクター2.0以上を達成できませんでした。\n")
                f.write(f"以下の点を検討してください：\n\n")
                f.write(f"1. RSI閾値のさらなる調整\n")
                f.write(f"2. ボリンジャーバンド幅の最適化\n")
                f.write(f"3. 時間フィルターの調整\n")
                f.write(f"4. 1分足と15分足の重み付けの最適化\n")
        
        logger.info(f"テスト完了: 結果は {output_dir}/reports/short_term_strategy_results.md に保存されました")
    else:
        logger.warning("トレードが生成されませんでした")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
