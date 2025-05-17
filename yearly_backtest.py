import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategies.tokyo_london import TokyoLondonStrategy
from src.strategies.bollinger_rsi import BollingerRsiStrategy
from src.strategies.support_resistance_strategy import SupportResistanceStrategy
from src.strategies.support_resistance_strategy_improved import SupportResistanceStrategy as SupportResistanceStrategyImproved
from src.strategies.support_resistance_strategy_v2 import SupportResistanceStrategyV2
from src.strategies.bollinger_rsi_enhanced import BollingerRsiEnhancedStrategy
from src.backtest.backtest_engine import BacktestEngine
from src.utils.logger import Logger
from src.utils.config import Config
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator

def run_yearly_backtest(year, max_positions=1, strategies=['tokyo_london', 'bollinger_rsi']):
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
    config = Config()
    
    year_dir = f"results/yearly/{year}"
    os.makedirs(f"{year_dir}/logs", exist_ok=True)
    os.makedirs(f"{year_dir}/charts", exist_ok=True)
    
    logger = Logger(f"{year_dir}/logs")
    logger.log_info(f"{year}年 FXトレードシステム バックテスト開始")
    
    config = Config()
    timeframe = config.get('data', 'timeframe')
    processed_dir = config.get('data', 'processed_dir')
    
    logger.log_info(f"{year}年の処理済みデータの読み込みを試みています（{timeframe}）...")
    from src.data.data_processor_enhanced import DataProcessor as EnhancedDataProcessor
    data_processor = EnhancedDataProcessor(pd.DataFrame())  # 空のDataFrameで初期化
    year_data = data_processor.load_processed_data(timeframe, year, processed_dir)
    
    h1_data = None
    if 'support_resistance' in strategies:
        logger.log_info(f"{year}年の1時間足データの読み込みを試みています...")
        h1_data = data_processor.load_processed_data('1H', year, processed_dir)
    
    if year_data.empty:
        logger.log_info(f"処理済みデータが見つかりません。{year}年の生データから処理します...")
        data_loader = DataLoader(config.get('data', 'raw_dir'))
        data = data_loader.load_year_data(year)
        
        if data.empty:
            logger.log_warning(f"{year}年のデータがありません")
            return {
                'year': year,
                'has_data': False,
                'trades': 0,
                'profit': 0,
                'win_rate': 0,
                'initial_balance': config.get('backtest', 'initial_balance'),
                'final_balance': config.get('backtest', 'initial_balance')
            }
        
        logger.log_info(f"データ読み込み完了: {len(data)} 行")
        
        logger.log_info("データ処理中...")
        data_processor = DataProcessor(data)
        
        resampled_data = data_processor.resample(timeframe)
        logger.log_info(f"リサンプリング完了: {len(resampled_data)} 行")
        
        resampled_data = data_processor.add_technical_indicators(resampled_data)
        
        resampled_data = data_processor.get_tokyo_session_range(resampled_data)
        logger.log_info("テクニカル指標の計算完了")
        
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        year_data = resampled_data.loc[start_date:end_date]
    else:
        logger.log_info(f"処理済みデータ読み込み完了: {len(year_data)} 行")
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        year_data = year_data.loc[start_date:end_date]
    if year_data.empty:
        logger.log_warning(f"{year}年のデータがありません")
        return {
            "year": year,
            "has_data": False,
            "trades": 0,
            "profit": 0,
            "win_rate": 0,
            "initial_balance": config.get('backtest', 'initial_balance'),
            "final_balance": config.get('backtest', 'initial_balance')
        }
    
    logger.log_info(f"バックテスト期間: {start_date} から {end_date}")
    logger.log_info(f"データ件数: {len(year_data)} 行")
    
    backtest_engine = BacktestEngine(
        data=year_data,
        initial_balance=config.get('backtest', 'initial_balance'),
        lot_size=config.get('backtest', 'lot_size'),
        max_positions=max_positions,  # 同時ポジション数を指定値に設定
        spread_pips=config.get('backtest', 'spread_pips')
    )
    
    tokyo_london = TokyoLondonStrategy()
    bollinger_rsi = BollingerRsiStrategy()
    support_resistance = SupportResistanceStrategy()
    support_resistance_improved = SupportResistanceStrategyImproved()
    support_resistance_v2 = SupportResistanceStrategyV2()
    bollinger_rsi_enhanced = BollingerRsiEnhancedStrategy()
    
    if 'support_resistance' in strategies and h1_data is not None and not h1_data.empty:
        logger.log_info("複数時間足のサポート/レジスタンスレベルを統合中...")
        enhanced_processor = EnhancedDataProcessor(pd.DataFrame())
        year_data = enhanced_processor.merge_multi_timeframe_levels(year_data, h1_data)
    
    if 'tokyo_london' in strategies:
        logger.log_info("東京レンジ・ロンドンブレイクアウト戦略を適用中...")
        year_data = tokyo_london.generate_signals(year_data)
    
    if 'bollinger_rsi' in strategies:
        logger.log_info("ボリンジャーバンド＋RSI逆張り戦略を適用中...")
        year_data = bollinger_rsi.generate_signals(year_data)
    
    if 'support_resistance' in strategies:
        logger.log_info("サポート/レジスタンス戦略を適用中...")
        year_data = support_resistance.generate_signals(year_data)
        
    if 'support_resistance_improved' in strategies:
        logger.log_info("改良版サポート/レジスタンス戦略を適用中...")
        year_data = support_resistance_improved.generate_signals(year_data)
        
    if 'support_resistance_v2' in strategies:
        logger.log_info("改良版サポート/レジスタンス戦略V2を適用中...")
        year_data = support_resistance_v2.generate_signals(year_data)
        
    if 'bollinger_rsi_enhanced' in strategies:
        logger.log_info("拡張版ボリンジャーバンド＋RSI逆張り戦略を適用中...")
        year_data = bollinger_rsi_enhanced.generate_signals(year_data)
    
    logger.log_info("バックテスト実行中...")
    strategy_list = []
    if 'tokyo_london' in strategies:
        strategy_list.append('tokyo_london')
    if 'bollinger_rsi' in strategies:
        strategy_list.append('bollinger_rsi')
    if 'support_resistance' in strategies:
        strategy_list.append('support_resistance')
    if 'support_resistance_improved' in strategies:
        strategy_list.append('support_resistance_improved')
    if 'support_resistance_v2' in strategies:
        strategy_list.append('support_resistance_v2')
    if 'bollinger_rsi_enhanced' in strategies:
        strategy_list.append('bollinger_rsi_enhanced')
        
    trade_history = backtest_engine.run(strategy_list)
    logger.log_info(f"バックテスト完了: {len(trade_history)} トレード")
    
    logger.log_trade_history(trade_history)
    
    equity_curve = backtest_engine.get_equity_curve()
    
    trade_log = backtest_engine.get_trade_log()
    
    logger.log_info("チャート生成中...")
    chart_generator = ChartGenerator(f"{year_dir}/charts")
    chart_generator.plot_equity_curve(equity_curve)
    chart_generator.plot_monthly_returns(trade_history)
    chart_generator.plot_drawdown(equity_curve)
    chart_generator.plot_strategy_comparison(trade_history)
    logger.log_info("チャート生成完了")
    
    logger.log_info("レポート生成中...")
    report_generator = ReportGenerator(f"{year_dir}/logs")
    metrics = report_generator.calculate_performance_metrics(trade_history, equity_curve)
    report_path = report_generator.generate_summary_report(metrics, trade_history, equity_curve)
    logger.log_info(f"レポート生成完了: {report_path}")
    
    logger.log_performance_metrics(metrics)
    
    logger.log_info(f"{year}年 FXトレードシステム バックテスト終了")
    
    result = {
        "year": year,
        "has_data": True,
        "trades": len(trade_history),
        "profit": metrics.get('総利益 (円)', 0),
        "win_rate": metrics.get('勝率 (%)', 0),
        "initial_balance": equity_curve['balance'].iloc[0] if not equity_curve.empty else config.get('backtest', 'initial_balance'),
        "final_balance": equity_curve['balance'].iloc[-1] if not equity_curve.empty else config.get('backtest', 'initial_balance')
    }
    
    return result

def main():
    """
    2000年から2025年までの各年のバックテストを実行し、結果をまとめる
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='FXトレードシステムのバックテスト')
    parser.add_argument('--year', type=int, help='バックテスト対象の年（指定しない場合は2000-2025年）')
    parser.add_argument('--strategies', type=str, default='tokyo_london,bollinger_rsi',
                        help='使用する戦略（カンマ区切り、例: tokyo_london,bollinger_rsi,bollinger_rsi_enhanced,support_resistance,support_resistance_improved,support_resistance_v2）')
    parser.add_argument('--max-positions', type=int, default=1, help='同時に保有できる最大ポジション数')
    
    args = parser.parse_args()
    
    strategy_list = args.strategies.split(',')
    print(f"使用する戦略: {', '.join(strategy_list)}")
    
    results = []
    
    if args.year:
        year = args.year
        print(f"=== {year}年のバックテスト実行中 ===")
        result = run_yearly_backtest(year, max_positions=args.max_positions, strategies=strategy_list)
        results.append(result)
        print(f"=== {year}年のバックテスト完了 ===")
        print(f"トレード数: {result['trades']}")
        print(f"総利益: {result['profit']}円")
        print(f"勝率: {result['win_rate']:.2f}%")
        print(f"最終残高: {result['final_balance']}円")
        print()
    else:
        # 2000年から2025年までバックテスト
        for year in range(2000, 2026):
            print(f"=== {year}年のバックテスト実行中 ===")
            result = run_yearly_backtest(year, max_positions=args.max_positions, strategies=strategy_list)
            results.append(result)
            print(f"=== {year}年のバックテスト完了 ===")
            print(f"トレード数: {result['trades']}")
            print(f"総利益: {result['profit']}円")
            print(f"勝率: {result['win_rate']:.2f}%")
            print(f"最終残高: {result['final_balance']}円")
            print()
    
    results_df = pd.DataFrame(results)
    
    os.makedirs("results/yearly", exist_ok=True)
    results_df.to_csv("results/yearly/yearly_results.csv", index=False)
    
    with open("results/yearly/yearly_results.md", "w") as f:
        f.write("# 年別バックテスト結果\n\n")
        f.write("同時ポジション数: 1\n\n")
        f.write("| 年 | データ有無 | トレード数 | 総利益 (円) | 勝率 (%) | 初期残高 (円) | 最終残高 (円) | 年間リターン (%) |\n")
        f.write("|-----|----------|------------|------------|----------|--------------|--------------|----------------|\n")
        
        for result in results:
            year = result["year"]
            has_data = "あり" if result["has_data"] else "なし"
            trades = result["trades"]
            profit = result["profit"]
            win_rate = result["win_rate"]
            initial_balance = result["initial_balance"]
            final_balance = result["final_balance"]
            annual_return = (final_balance / initial_balance - 1) * 100 if initial_balance > 0 else 0
            
            f.write(f"| {year} | {has_data} | {trades} | {profit:,.0f} | {win_rate:.2f} | {initial_balance:,.0f} | {final_balance:,.0f} | {annual_return:.2f} |\n")
    
    print("=== 年別バックテスト結果 ===")
    print("| 年 | データ有無 | トレード数 | 総利益 (円) | 勝率 (%) | 初期残高 (円) | 最終残高 (円) | 年間リターン (%) |")
    print("|-----|----------|------------|------------|----------|--------------|--------------|----------------|")
    
    for result in results:
        year = result["year"]
        has_data = "あり" if result["has_data"] else "なし"
        trades = result["trades"]
        profit = result["profit"]
        win_rate = result["win_rate"]
        initial_balance = result["initial_balance"]
        final_balance = result["final_balance"]
        annual_return = (final_balance / initial_balance - 1) * 100 if initial_balance > 0 else 0
        
        print(f"| {year} | {has_data} | {trades} | {profit:,.0f} | {win_rate:.2f} | {initial_balance:,.0f} | {final_balance:,.0f} | {annual_return:.2f} |")
    
    plt.figure(figsize=(12, 6))
    
    valid_results = [r for r in results if r["has_data"]]
    
    if valid_results:
        years = [r["year"] for r in valid_results]
        final_balances = [r["final_balance"] for r in valid_results]
        
        plt.plot(years, final_balances, marker='o')
        plt.title('年別最終残高の推移')
        plt.xlabel('年')
        plt.ylabel('最終残高 (円)')
        plt.grid(True)
        plt.xticks(years, rotation=45)
        
        os.makedirs("results/yearly", exist_ok=True)
        plt.tight_layout()
        plt.savefig("results/yearly/yearly_balance.png", dpi=300)
    
    return results

if __name__ == "__main__":
    main()
