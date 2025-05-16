import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategies.tokyo_london import TokyoLondonStrategy
from src.strategies.bollinger_rsi import BollingerRsiStrategy
from src.backtest.backtest_engine import BacktestEngine
from src.utils.logger import Logger
from src.utils.config import Config
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator

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
    config = Config()
    
    year_dir = f"results/yearly/{year}"
    os.makedirs(f"{year_dir}/logs", exist_ok=True)
    os.makedirs(f"{year_dir}/charts", exist_ok=True)
    
    logger = Logger(f"{year_dir}/logs")
    logger.log_info(f"{year}年 FXトレードシステム バックテスト開始")
    
    logger.log_info("データ読み込み中...")
    data_loader = DataLoader(config.get('data', 'raw_dir'))
    data = data_loader.load_all_data()
    logger.log_info(f"データ読み込み完了: {len(data)} 行")
    
    logger.log_info("データ処理中...")
    data_processor = DataProcessor(data)
    
    resampled_data = data_processor.resample(config.get('data', 'timeframe'))
    logger.log_info(f"リサンプリング完了: {len(resampled_data)} 行")
    
    resampled_data = data_processor.add_technical_indicators(resampled_data)
    
    resampled_data = data_processor.get_tokyo_session_range(resampled_data)
    logger.log_info("テクニカル指標の計算完了")
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    year_data = resampled_data.loc[start_date:end_date]
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
    
    logger.log_info("バックテスト実行中...")
    trade_history = backtest_engine.run()
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
    results = []
    
    for year in range(2000, 2026):
        print(f"=== {year}年のバックテスト実行中 ===")
        result = run_yearly_backtest(year, max_positions=1)
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
