import pandas as pd
import numpy as np
import logging
import os
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.balanced_optimized_strategy import BalancedOptimizedStrategy
from custom_backtest_engine import CustomBacktestEngine
from src.visualization.visualizer import Visualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_balanced_optimized_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_balanced_optimized_strategy'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_year = 2025

logger.info(f"バランス最適化版短期戦略のテスト開始")
logger.info(f"テスト年: {test_year}")

try:
    data_processor = DataProcessor(pd.DataFrame())
    df_15min = data_processor.load_processed_data('15min', test_year)
    
    if df_15min.empty:
        logger.error(f"15分足データが見つかりません: {test_year}年")
        exit(1)
    
    logger.info(f"データ読み込み成功: 15分足={len(df_15min)}行")
    
    strategy = BalancedOptimizedStrategy()
    
    logger.info("シグナル生成開始")
    signals_df = strategy.generate_signals(df_15min, test_year)
    
    logger.info(f"シグナル生成完了: {len(signals_df)}行")
    signal_count = (signals_df['signal'] != 0).sum()
    logger.info(f"シグナル数: {signal_count}")
    
    if signal_count == 0:
        logger.warning(f"{test_year}年のシグナルが生成されませんでした。パラメータを調整してください。")
        exit(1)
    
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
    
    unique_dates = pd.Series(pd.to_datetime(signals_df.index)).dt.date.nunique()
    avg_trades_per_day = trades / unique_dates if unique_dates > 0 else 0
    logger.info(f"1日あたりの平均取引回数: {avg_trades_per_day:.2f}")
    
    if trades > 0:
        visualizer = Visualizer(output_dir=f'{output_dir}/charts')
        
        equity_curve = backtest_results['equity_curve']
        visualizer.plot_equity_curve(equity_curve, f'balanced_optimized_strategy_equity_curve_{test_year}')
        
        equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
        equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
        visualizer.plot_drawdown(equity_curve, f'balanced_optimized_strategy_drawdown_{test_year}')
        
        monthly_perf = backtest_results['monthly_performance']
        months = list(monthly_perf.keys())
        profits = [monthly_perf[m]['profit'] for m in months]
        visualizer.plot_monthly_returns(months, profits, f'balanced_optimized_strategy_monthly_returns_{test_year}')
        
        with open(f'{output_dir}/reports/balanced_optimized_strategy_results.md', 'w') as f:
            f.write(f"# バランス最適化版短期戦略のバックテスト結果\n\n")
            f.write(f"## 概要\n\n")
            f.write(f"プロフィットファクター1.5を目標としたバランス最適化版短期ボリンジャーバンド＋RSI戦略のバックテスト結果です。\n\n")
            f.write(f"## 総合結果\n\n")
            f.write(f"| 項目 | 値 |\n")
            f.write(f"| --- | --- |\n")
            f.write(f"| 総トレード数 | {trades} |\n")
            f.write(f"| 勝率 | {win_rate:.2f}% |\n")
            f.write(f"| プロフィットファクター | {profit_factor:.2f} |\n")
            f.write(f"| 純利益 | {net_profit:.2f} |\n")
            f.write(f"| 1日あたりの平均取引回数 | {avg_trades_per_day:.2f} |\n\n")
            
            f.write(f"## 年別結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |\n")
            f.write(f"| --- | --- | --- | --- | --- |\n")
            f.write(f"| {test_year} | {trades} | {win_rate:.2f} | {profit_factor:.2f} | {net_profit:.2f} |\n\n")
            
            f.write(f"## パラメータ設定\n\n")
            f.write(f"| パラメータ | 改良版短期戦略 | バランス最適化版短期戦略 | 説明 |\n")
            f.write(f"| --- | --- | --- | --- |\n")
            f.write(f"| bb_dev | 1.6 | 1.7 | ボリンジャーバンド幅を適度に広げる |\n")
            f.write(f"| rsi_upper | 55 | 65 | RSI閾値を調整（強い過買い状態でのみ売り） |\n")
            f.write(f"| rsi_lower | 45 | 35 | RSI閾値を調整（強い過売り状態でのみ買い） |\n")
            f.write(f"| sl_pips | 3.0 | 3.0 | 損切り幅は維持 |\n")
            f.write(f"| tp_pips | 7.5 | 10.5 | 利確幅を拡大してリスク・リワード比を1:3.5に改善 |\n")
            f.write(f"| trend_filter | False | True | トレンドフィルターを有効化 |\n")
            f.write(f"| vol_filter | True | True | ボラティリティフィルターを維持 |\n")
            f.write(f"| time_filter | True | True | 時間フィルターを維持 |\n")
            f.write(f"| seasonal_filter | False | False | 季節性フィルターは無効化（シンプルに） |\n")
            f.write(f"| price_action | False | False | 価格アクションパターンは無効化（シンプルに） |\n\n")
            
            f.write(f"## 主な改善点\n\n")
            f.write(f"1. **RSI閾値の最適化**: 買いシグナルは35、売りシグナルは65に調整（強い過買い/過売り状態でのみ取引）\n")
            f.write(f"2. **リスク・リワード比の改善**: 1:2.5から1:3.5に拡大（SL:3.0, TP:10.5）\n")
            f.write(f"3. **トレンドフィルターの導入**: 移動平均線を使用してトレンドの方向性を確認\n")
            f.write(f"4. **ボリンジャーバンドの乖離率チェック**: バンドからの乖離が大きい場合のみ取引（強い過買い/過売り）\n")
            f.write(f"5. **ポジションサイズ管理の強化**: 連続損失時は50%まで削減し、連続勝利時は最大1.5倍まで増加\n\n")
            
            f.write(f"## 結論\n\n")
            
            if profit_factor >= 1.5:
                f.write(f"バランス最適化版短期戦略は中間目標のプロフィットファクター1.5以上を達成しました。\n")
                f.write(f"主な成功要因は以下の通りです：\n\n")
                f.write(f"1. リスク・リワード比の改善（1:3.5）\n")
                f.write(f"2. RSI閾値の最適化（35/65）\n")
                f.write(f"3. トレンドフィルターの導入\n")
                f.write(f"4. ボリンジャーバンドの乖離率チェックの導入\n\n")
                f.write(f"次のステップとして、勝率の向上（目標：70%以上）とプロフィットファクターのさらなる向上（目標：2.0以上）を目指すことをお勧めします。\n")
            else:
                f.write(f"バランス最適化版短期戦略は中間目標のプロフィットファクター1.5以上を達成できませんでした。\n")
                f.write(f"さらなる改善のために以下の点を検討してください：\n\n")
                f.write(f"1. RSI閾値のさらなる最適化\n")
                f.write(f"2. 市場環境に応じた動的パラメータ調整の実装\n")
                f.write(f"3. 複合指標の開発（RSI+ボリンジャーバンド+MACD等）\n")
                f.write(f"4. 取引時間帯のさらなる最適化\n")
        
        logger.info(f"テスト完了: 結果は {output_dir}/reports/balanced_optimized_strategy_results.md に保存されました")
    else:
        logger.warning("トレードが生成されませんでした")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
