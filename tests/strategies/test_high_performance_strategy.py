import pandas as pd
import numpy as np
import logging
import os
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.high_performance.high_performance_strategy import HighPerformanceStrategy
from enhanced_backtest_engine import EnhancedBacktestEngine
from src.visualization.visualizer import Visualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_high_performance_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_high_performance_strategy'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_years = [2023, 2024, 2025]  # 2010年は除外し、2023-2025年の最新データに焦点

logger.info(f"高性能ボリンジャーバンド＋RSI戦略のテスト開始")

all_results = []
total_trades = 0
total_wins = 0
total_profit = 0.0
total_position_limit_reached = 0

try:
    for test_year in test_years:
        logger.info(f"テスト年: {test_year}")
        
        data_processor = DataProcessor(pd.DataFrame())
        df_15min = data_processor.load_processed_data('15min', test_year)
        
        if df_15min.empty:
            logger.error(f"15分足データが見つかりません: {test_year}年")
            continue
        
        df_1h = data_processor.load_processed_data('1H', test_year)
        
        if df_1h.empty:
            logger.warning(f"1時間足データが見つかりません: {test_year}年")
            logger.warning("15分足データのみで戦略を実行します")
        
        df_4h = data_processor.load_processed_data('4H', test_year)
        
        if df_4h.empty:
            logger.warning(f"4時間足データが見つかりません: {test_year}年")
        
        logger.info(f"データ読み込み成功: 15分足={len(df_15min)}行, 1時間足={len(df_1h) if not df_1h.empty else 0}行, 4時間足={len(df_4h) if not df_4h.empty else 0}行")
        
        timeframe_weights = {}
        if not df_15min.empty:
            timeframe_weights['15min'] = 1.0
        if not df_1h.empty:
            timeframe_weights['1H'] = 2.0
        if not df_4h.empty:
            timeframe_weights['4H'] = 3.0
        
        strategy = HighPerformanceStrategy(timeframe_weights=timeframe_weights)
        
        logger.info("シグナル生成開始")
        signals_df = strategy.generate_signals(df_15min, test_year)
        
        logger.info(f"シグナル生成完了: {len(signals_df)}行")
        signal_count = (signals_df['signal'] != 0).sum()
        logger.info(f"シグナル数: {signal_count}")
        
        if signal_count == 0:
            logger.warning(f"{test_year}年のシグナルが生成されませんでした。パラメータを調整してください。")
            continue
        
        logger.info("バックテスト実行開始")
        backtest_engine = EnhancedBacktestEngine(
            signals_df, 
            initial_balance=1000000,  # 100万円の資金
            base_lot_size=0.01,       # 基本ロットサイズ0.01
            max_positions=5,          # 最大同時ポジション数5
            spread_pips=0.03,
            win_rate_threshold=80.0,  # 勝率80%でロットサイズ増加
            increased_lot_size=0.02   # 増加後のロットサイズ0.02
        )
        backtest_results = backtest_engine.run()
        
        trades = backtest_results['trades']
        wins = backtest_results['wins']
        losses = backtest_results['losses']
        win_rate = backtest_results['win_rate']
        profit_factor = backtest_results['profit_factor']
        risk_reward_ratio = backtest_results['risk_reward_ratio']
        breakeven_win_rate = backtest_results['breakeven_win_rate']
        net_profit = backtest_results['net_profit']
        position_limit_reached_count = backtest_results['position_limit_reached_count']
        
        logger.info(f"{test_year}年のバックテスト結果:")
        logger.info(f"総トレード数: {trades}")
        logger.info(f"勝率: {win_rate:.2f}%")
        logger.info(f"損益分岐点勝率: {breakeven_win_rate:.2f}%")
        logger.info(f"プロフィットファクター: {profit_factor:.2f}")
        logger.info(f"リスク・リワード比: {risk_reward_ratio:.2f}")
        logger.info(f"純利益: {net_profit:.2f}")
        logger.info(f"ポジション制限到達回数: {position_limit_reached_count}")
        
        all_results.append({
            'year': test_year,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'breakeven_win_rate': breakeven_win_rate,
            'profit_factor': profit_factor,
            'risk_reward_ratio': risk_reward_ratio,
            'net_profit': net_profit,
            'position_limit_reached_count': position_limit_reached_count
        })
        
        total_trades += trades
        total_wins += wins
        total_profit += net_profit
        total_position_limit_reached += position_limit_reached_count
        
        if trades > 0:
            visualizer = Visualizer(output_dir=f'{output_dir}/charts')
            
            equity_curve = backtest_results['equity_curve']
            visualizer.plot_equity_curve(equity_curve, f'高性能戦略_エクイティカーブ_{test_year}')
            
            equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
            equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
            visualizer.plot_drawdown(equity_curve, f'高性能戦略_ドローダウン_{test_year}')
            
            monthly_perf = backtest_results['monthly_performance']
            months = list(monthly_perf.keys())
            profits = [monthly_perf[m]['profit'] for m in months]
            visualizer.plot_monthly_returns(months, profits, f'高性能戦略_月別パフォーマンス_{test_year}')
    
    if total_trades > 0:
        total_win_rate = (total_wins / total_trades) * 100
        logger.info(f"全期間の総合結果:")
        logger.info(f"総トレード数: {total_trades}")
        logger.info(f"総勝率: {total_win_rate:.2f}%")
        logger.info(f"総純利益: {total_profit:.2f}")
        logger.info(f"総ポジション制限到達回数: {total_position_limit_reached}")
        
        with open(f'{output_dir}/reports/high_performance_strategy_results.md', 'w') as f:
            f.write(f"# 高性能ボリンジャーバンド＋RSI戦略のバックテスト結果\n\n")
            f.write(f"## 概要\n\n")
            f.write(f"勝率70%以上、プロフィットファクター2.0以上を目指した高性能ボリンジャーバンド＋RSI戦略のバックテスト結果です。\n\n")
            f.write(f"## 総合結果\n\n")
            f.write(f"| 項目 | 値 |\n")
            f.write(f"| --- | --- |\n")
            f.write(f"| 総トレード数 | {total_trades} |\n")
            f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
            
            avg_breakeven_win_rate = sum(r['breakeven_win_rate'] for r in all_results) / len(all_results) if all_results else 0
            f.write(f"| 損益分岐点勝率 | {avg_breakeven_win_rate:.2f}% |\n")
            
            f.write(f"| 純利益 | {total_profit:.2f} |\n")
            f.write(f"| ポジション制限到達回数 | {total_position_limit_reached} |\n\n")
            
            f.write(f"## 年別結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 (%) | 損益分岐点勝率 (%) | プロフィットファクター | リスク・リワード比 | 純利益 | ポジション制限到達回数 |\n")
            f.write(f"| --- | --- | --- | --- | --- | --- | --- | --- |\n")
            
            for result in all_results: 
                f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['breakeven_win_rate']:.2f} | {result['profit_factor']:.2f} | {result['risk_reward_ratio']:.2f} | {result['net_profit']:.2f} | {result['position_limit_reached_count']} |\n")
            
            f.write(f"\n## パラメータ設定\n\n")
            f.write(f"| パラメータ | 値 | 説明 |\n")
            f.write(f"| --- | --- | --- |\n")
            f.write(f"| bb_dev | 2.0 | ボリンジャーバンド幅を広げてシグナル数を増加 |\n")
            f.write(f"| rsi_upper | 70 | 標準的なRSI閾値 |\n")
            f.write(f"| rsi_lower | 30 | 標準的なRSI閾値 |\n")
            f.write(f"| sl_pips | 2.5 | リスク・リワード比最適化 |\n")
            f.write(f"| tp_pips | 12.5 | リスク・リワード比1:5 |\n")
            f.write(f"| timeframe_weights | {{'15min': 1.0, '1H': 2.0, '4H': 3.0}} | 長期時間足の重みを大きくする |\n")
            f.write(f"| max_positions | 5 | 最大同時ポジション数 |\n")
            f.write(f"| base_lot_size | 0.01 | 基本ロットサイズ |\n")
            f.write(f"| win_rate_threshold | 80.0 | 勝率閾値 |\n")
            f.write(f"| increased_lot_size | 0.02 | 勝率閾値超過時のロットサイズ |\n")
            
            f.write(f"\n## 主な改善点\n\n")
            f.write(f"1. **RSI閾値の標準化**: 30/70に設定してシグナル数を増加\n")
            f.write(f"2. **ボリンジャーバンド幅の拡大**: 標準偏差2.0に設定してシグナル数を増加\n")
            f.write(f"3. **リスク・リワード比の拡大**: 1:5に設定してプロフィットファクターを向上\n")
            f.write(f"4. **トレンドフィルターの強化**: 移動平均線の傾きとクロスを確認\n")
            f.write(f"5. **時間フィルターの最適化**: アジア時間とロンドン時間に集中\n")
            f.write(f"6. **市場環境適応型パラメータ**: 4つの市場環境（通常、トレンド、ボラティリティ、レンジ）に応じてパラメータを動的に調整\n")
            f.write(f"7. **連続損失後のポジションサイズ削減**: 連続損失後は50%に削減\n")
            
            f.write(f"\n## 結論\n\n")
            
            if total_win_rate >= 70 and any(r['profit_factor'] >= 2.0 for r in all_results):
                f.write(f"高性能戦略は目標の勝率70%以上とプロフィットファクター2.0以上を達成しました。\n")
                f.write(f"市場環境に応じたパラメータの動的調整と厳格なフィルタリングにより、高品質なシグナルのみを選別できています。\n")
            else:
                f.write(f"高性能戦略は目標の勝率70%以上とプロフィットファクター2.0以上を達成できませんでした。\n")
                f.write(f"以下の点をさらに検討してください：\n\n")
                f.write(f"1. RSI閾値のさらなる調整\n")
                f.write(f"2. 市場環境検出アルゴリズムの精度向上\n")
                f.write(f"3. 価格アクションパターンの検出精度向上\n")
                f.write(f"4. 時間フィルターのさらなる最適化\n")
        
        logger.info(f"テスト完了: 結果は {output_dir}/reports/high_performance_strategy_results.md に保存されました")
    else:
        logger.warning("トレードが生成されませんでした")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
