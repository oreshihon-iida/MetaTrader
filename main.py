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

def main():
    """
    メイン関数
    """
    config = Config()
    
    logger = Logger(config.get('output', 'log_dir'))
    logger.log_info("FXトレードシステム バックテスト開始")
    
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
    
    start_date = config.get('backtest', 'start_date')
    end_date = config.get('backtest', 'end_date')
    backtest_data = resampled_data.loc[start_date:end_date]
    logger.log_info(f"バックテスト期間: {start_date} から {end_date}")
    
    backtest_engine = BacktestEngine(
        data=backtest_data,
        initial_balance=config.get('backtest', 'initial_balance'),
        lot_size=config.get('backtest', 'lot_size'),
        max_positions=config.get('backtest', 'max_positions'),
        spread_pips=config.get('backtest', 'spread_pips')
    )
    
    logger.log_info("バックテスト実行中...")
    trade_history = backtest_engine.run()
    logger.log_info(f"バックテスト完了: {len(trade_history)} トレード")
    
    logger.log_trade_history(trade_history)
    
    equity_curve = backtest_engine.get_equity_curve()
    
    trade_log = backtest_engine.get_trade_log()
    
    logger.log_info("チャート生成中...")
    chart_generator = ChartGenerator(config.get('output', 'chart_dir'))
    
    if equity_curve is not None and not equity_curve.empty:
        chart_generator.plot_equity_curve(equity_curve)
        chart_generator.plot_drawdown(equity_curve)
        logger.log_info("資産推移グラフとドローダウングラフを生成しました")
    else:
        logger.log_warning("資産推移データがないため、資産推移グラフとドローダウングラフを生成できませんでした")
    
    if trade_history is not None and not trade_history.empty:
        chart_generator.plot_monthly_returns(trade_history)
        chart_generator.plot_strategy_comparison(trade_history)
        logger.log_info("月別リターングラフと戦略比較グラフを生成しました")
    else:
        logger.log_warning("トレード履歴がないため、月別リターングラフと戦略比較グラフを生成できませんでした")
    
    logger.log_info("チャート生成完了")
    
    logger.log_info("レポート生成中...")
    report_generator = ReportGenerator(config.get('output', 'log_dir'))
    metrics = report_generator.calculate_performance_metrics(trade_history, equity_curve)
    report_path = report_generator.generate_summary_report(metrics, trade_history, equity_curve)
    logger.log_info(f"レポート生成完了: {report_path}")
    
    logger.log_performance_metrics(metrics)
    
    logger.log_info("FXトレードシステム バックテスト終了")
    
    return {
        'trade_history': trade_history,
        'equity_curve': equity_curve,
        'metrics': metrics
    }

if __name__ == "__main__":
    main()
