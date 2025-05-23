import os
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
from src.strategies.dynamic_multi_timeframe_strategy import DynamicMultiTimeframeStrategy
from src.strategies.macro_based_long_term_strategy import MacroBasedLongTermStrategy
from src.portfolio.portfolio_manager import PortfolioManager
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.data.data_processor_enhanced import DataProcessor
from src.data.multi_timeframe_data_manager import MultiTimeframeDataManager
from src.utils.logger import Logger
from src.utils.visualizer import Visualizer

parser = argparse.ArgumentParser(description='ポートフォリオ戦略のバックテスト')
parser.add_argument('--years', type=str, default='2023,2024', help='テスト対象年（カンマ区切り、例：2023,2024）')
args = parser.parse_args()

output_dir = "results/portfolio"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/charts", exist_ok=True)

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info("ポートフォリオ戦略のバックテスト開始")

short_term_strategy = DynamicMultiTimeframeStrategy(
    bb_window=20,
    bb_dev=0.8,
    rsi_window=14,
    rsi_upper=50,
    rsi_lower=50,
    sl_pips=2.5,
    tp_pips=12.5,
    timeframe_weights={'5min': 2.0, '15min': 1.0, '30min': 0.5, '1H': 0.5, '1min': 0.5},
    market_regime_detection=True,
    dynamic_timeframe_weights=True,
    use_adx_filter=False,
    adx_threshold=15,
    use_pattern_filter=False,
    use_quality_filter=True,
    quality_threshold=0.3
)

long_term_strategy = MacroBasedLongTermStrategy(
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

portfolio = PortfolioManager({
    "short_term": {
        "strategy": short_term_strategy,
        "allocation": 0.15,  # 資金の15%
        "max_positions": 5,
        "volatility": 0.02,  # 初期ボラティリティ（標準偏差）
        "max_drawdown": 0.05  # 初期最大ドローダウン
    },
    "long_term": {
        "strategy": long_term_strategy,
        "allocation": 0.50,  # 資金の50%
        "max_positions": 3,
        "volatility": 0.01,  # 初期ボラティリティ（標準偏差）
        "max_drawdown": 0.03  # 初期最大ドローダウン
    }
}, initial_balance=2000000.0)

years = [int(year) for year in args.years.split(',')]
data_processor = DataProcessor(pd.DataFrame())  # 空のデータフレームで初期化

total_trades = 0
total_wins = 0
total_profit = 0.0
total_profit_factor = 0.0

for test_year in years:
    logger.log_info(f"{test_year}年のデータを処理中...")
    
    short_term_timeframes = ['1min', '5min', '15min', '30min', '1H']
    short_term_data = {}
    
    for timeframe in short_term_timeframes:
        df = data_processor.load_processed_data(timeframe, test_year)
        if not df.empty:
            logger.log_info(f"短期戦略: {timeframe}データ読み込み成功: {len(df)}行")
            short_term_data[timeframe] = df
        else:
            logger.log_warning(f"短期戦略: {timeframe}データが見つかりません: {test_year}年")
    
    long_term_timeframes = ['4H', '1D', '1W', '1M']
    long_term_data = data_manager.load_data(long_term_timeframes, [test_year])
    
    long_term_data = data_manager.calculate_indicators(long_term_data)
    
    long_term_data = data_manager.synchronize_timeframes(long_term_data)
    
    if not short_term_data or not long_term_data:
        logger.log_error(f"{test_year}年のデータが不足しています")
        continue
    
    logger.log_info("ポートフォリオシグナル生成開始")
    try:
        portfolio_data = {
            "short_term": short_term_data,
            "long_term": long_term_data
        }
        
        signals = portfolio.generate_portfolio_signals(portfolio_data)
        if not signals:
            logger.log_warning("シグナルが生成されませんでした")
            continue
            
        signals = portfolio.calculate_position_sizes(signals)
            
        correlation = portfolio.calculate_correlation(signals)
        logger.log_info(f"戦略間の相関係数: {correlation}")
        
        strategy_results = {}
        
        for name, signals_df in signals.items():
            if signals_df.empty:
                logger.log_warning(f"{name}のシグナルが空です")
                continue
                
            logger.log_info(f"{name}のバックテスト実行中...")
            strategy_balance = portfolio.strategies[name]["balance"]
            backtest_engine = CustomBacktestEngine(signals_df, initial_balance=strategy_balance)
            results = backtest_engine.run()
            
            trades = results['trades']
            if not trades.empty:
                wins = trades[trades['損益(円)'] > 0]
                losses = trades[trades['損益(円)'] <= 0]
                
                win_rate = len(wins) / len(trades) * 100 if len(trades) > 0 else 0
                profit_factor = abs(wins['損益(円)'].sum() / losses['損益(円)'].sum()) if losses['損益(円)'].sum() != 0 else float('inf')
                
                logger.log_info(f"{name}の結果: {len(trades)}トレード, 勝率 {win_rate:.2f}%, PF {profit_factor:.2f}")
                logger.log_info(f"{name}の純利益: {trades['損益(円)'].sum():.2f}円")
                
                strategy_results[name] = {
                    "trades": len(trades),
                    "wins": len(wins),
                    "losses": len(losses),
                    "profit": trades['損益(円)'].sum(),
                    "profit_factor": profit_factor,
                    "win_rate": win_rate,
                    "equity_curve": results['equity_curve']
                }
                
                total_trades += len(trades)
                total_wins += len(wins)
                total_profit += trades['損益(円)'].sum()
                
                if profit_factor != float('inf'):
                    total_profit_factor += profit_factor
        
        if strategy_results:
            portfolio.rebalance_portfolio({name: {
                "trades": res["trades"],
                "wins": res["wins"],
                "losses": res["losses"],
                "profit": res["profit"],
                "equity_curve": res["equity_curve"]
            } for name, res in strategy_results.items()})
            
            visualizer = Visualizer()
            
            combined_equity = pd.DataFrame()
            for name, res in strategy_results.items():
                equity = res["equity_curve"].copy()
                equity.columns = [f"{name}_{col}" for col in equity.columns]
                
                if combined_equity.empty:
                    combined_equity = equity
                else:
                    combined_equity = pd.merge(combined_equity, equity, left_index=True, right_index=True, how='outer')
            
            if not combined_equity.empty:
                equity_columns = [col for col in combined_equity.columns if col.endswith('_equity')]
                combined_equity['portfolio_equity'] = combined_equity[equity_columns].sum(axis=1)
                
                visualizer.plot_equity_curve(combined_equity[['portfolio_equity']], f'ポートフォリオ_エクイティカーブ_{test_year}', output_dir=f"{output_dir}/charts")
                
                combined_equity['drawdown'] = combined_equity['portfolio_equity'].cummax() - combined_equity['portfolio_equity']
                combined_equity['drawdown_pct'] = combined_equity['drawdown'] / combined_equity['portfolio_equity'].cummax() * 100
                visualizer.plot_drawdown(combined_equity, f'ポートフォリオ_ドローダウン_{test_year}', output_dir=f"{output_dir}/charts")
    except Exception as e:
        logger.log_error(f"ポートフォリオバックテスト中にエラーが発生しました: {e}")
        continue

if total_trades > 0:
    total_win_rate = (total_wins / total_trades) * 100
    avg_profit_factor = total_profit_factor / len(years)
    
    logger.log_info(f"ポートフォリオ総合結果: {total_trades}トレード, 勝率 {total_win_rate:.2f}%, 平均PF {avg_profit_factor:.2f}")
    logger.log_info(f"ポートフォリオ総純利益: {total_profit:.2f}円")
    
    annual_return = (total_profit / 2000000) * 100
    logger.log_info(f"ポートフォリオ年利: {annual_return:.2f}%")
    
    with open(f"{output_dir}/portfolio_report.md", "w") as f:
        f.write(f"# ポートフォリオ戦略バックテスト結果\n\n")
        f.write(f"テスト期間: {min(years)}年 - {max(years)}年\n\n")
        
        f.write(f"## ポートフォリオ構成\n\n")
        f.write(f"| 戦略 | 資金配分 | 最大ポジション数 |\n")
        f.write(f"|------|---------|----------------|\n")
        for name, strategy_info in portfolio.strategies.items():
            f.write(f"| {name} | {strategy_info['allocation']*100:.1f}% | {strategy_info['max_positions']} |\n")
        
        f.write(f"\n## 総合パフォーマンス\n\n")
        f.write(f"| 指標 | 値 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 総トレード数 | {total_trades} |\n")
        f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
        f.write(f"| 平均プロフィットファクター | {avg_profit_factor:.2f} |\n")
        f.write(f"| 総純利益 | {total_profit:.2f}円 |\n")
        f.write(f"| 年利 | {annual_return:.2f}% |\n")
        
        if strategy_results:
            f.write(f"\n## 戦略別パフォーマンス\n\n")
            f.write(f"| 戦略 | トレード数 | 勝率 | プロフィットファクター | 純利益 |\n")
            f.write(f"|------|------------|------|----------------------|--------|\n")
            for name, res in strategy_results.items():
                f.write(f"| {name} | {res['trades']} | {res['win_rate']:.2f}% | {res['profit_factor']:.2f} | {res['profit']:.2f}円 |\n")
        
        f.write(f"\n## 戦略間相関\n\n")
        if correlation:
            f.write(f"| 戦略A | 戦略B | 相関係数 |\n")
            f.write(f"|-------|-------|----------|\n")
            for name1, corrs in correlation.items():
                for name2, corr in corrs.items():
                    if name1 != name2:
                        f.write(f"| {name1} | {name2} | {corr:.2f} |\n")
        
        f.write(f"\n## 結論\n\n")
        if annual_return >= 5.0:
            f.write(f"ポートフォリオ戦略は目標年利5-15%を達成し、有効な戦略であることが確認されました。\n")
        else:
            f.write(f"ポートフォリオ戦略は目標年利5-15%に達していないため、さらなる最適化が必要です。\n")
        
        f.write(f"\n## 今後の改善点\n\n")
        f.write(f"1. 戦略間の相関を低減するための追加戦略の導入\n")
        f.write(f"2. 市場環境に応じた動的な資金配分調整\n")
        f.write(f"3. リスク管理の強化（特に最大ドローダウンの制限）\n")
        f.write(f"4. 複数通貨ペアへの拡張\n")

logger.log_info("ポートフォリオ戦略のバックテスト完了")
