import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.backtest.backtest_engine import BacktestEngine
from src.utils.logger import Logger
from src.utils.config import Config
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator

def run_2020_backtest_mt():
    """
    2020年データに対して複数時間足ボリンジャーバンド＋RSI戦略のバックテストを実行
    """
    year = 2020
    year_dir = f"results/yearly/{year}/mt"
    os.makedirs(f"{year_dir}/logs", exist_ok=True)
    os.makedirs(f"{year_dir}/charts", exist_ok=True)
    
    logger = Logger(f"{year_dir}/logs")
    logger.log_info(f"{year}年 複数時間足ボリンジャーバンド＋RSI戦略 バックテスト開始")
    
    config = Config()
    timeframe = config.get('data', 'timeframe')
    processed_dir = config.get('data', 'processed_dir')
    
    logger.log_info(f"{year}年の処理済みデータの読み込みを試みています（{timeframe}）...")
    data_processor = DataProcessor(pd.DataFrame())
    year_data = data_processor.load_processed_data(timeframe, year, processed_dir)
    
    if year_data.empty:
        logger.log_error(f"{year}年のデータが見つかりません")
        return
    
    logger.log_info(f"処理済みデータ読み込み完了: {len(year_data)} 行")
    
    h1_data = data_processor.load_processed_data('1H', year, processed_dir)
    h4_data = data_processor.load_processed_data('4H', year, processed_dir)
    
    if h1_data.empty or h4_data.empty:
        logger.log_warning("1時間足または4時間足のデータが見つかりません")
    else:
        logger.log_info(f"1時間足データ: {len(h1_data)} 行, 4時間足データ: {len(h4_data)} 行")
    
    strategy_params = {
        'bb_window': 20,
        'bb_dev': 2.0,
        'rsi_window': 14,
        'rsi_upper': 70,
        'rsi_lower': 30,
        'atr_window': 14,
        'atr_sl_multiplier': 1.5,
        'atr_tp_multiplier': 2.0,
        'use_adaptive_params': True,
        'trend_filter': True,
        'vol_filter': True,
        'time_filter': True,
        'use_multi_timeframe': True,
        'timeframe_weights': {
            '15min': 1.0,
            '1H': 2.0,
            '4H': 3.0
        }
    }
    
    bollinger_rsi_mt = BollingerRsiEnhancedMTStrategy(**strategy_params)
    
    logger.log_info("複数時間足ボリンジャーバンド＋RSI戦略を適用中...")
    year_data = bollinger_rsi_mt.generate_signals(year_data, year=year, processed_dir=processed_dir)
    
    backtest_engine = BacktestEngine(
        data=year_data,
        initial_balance=config.get('backtest', 'initial_balance'),
        lot_size=config.get('backtest', 'lot_size'),
        max_positions=1,
        spread_pips=config.get('backtest', 'spread_pips')
    )
    
    logger.log_info("バックテスト実行中...")
    trade_history = backtest_engine.run(['bollinger_rsi_enhanced_mt'])
    logger.log_info(f"バックテスト完了: {len(trade_history)} トレード")
    
    logger.log_trade_history(trade_history)
    
    equity_curve = backtest_engine.get_equity_curve()
    
    logger.log_info("チャート生成中...")
    chart_generator = ChartGenerator(f"{year_dir}/charts")
    chart_generator.plot_equity_curve(equity_curve)
    chart_generator.plot_monthly_returns(trade_history)
    chart_generator.plot_drawdown(equity_curve)
    logger.log_info("チャート生成完了")
    
    logger.log_info("レポート生成中...")
    report_generator = ReportGenerator(f"{year_dir}/logs")
    metrics = report_generator.calculate_performance_metrics(trade_history, equity_curve)
    report_path = report_generator.generate_summary_report(metrics, trade_history, equity_curve)
    logger.log_info(f"レポート生成完了: {report_path}")
    
    logger.log_performance_metrics(metrics)
    
    print("=== 2020年 複数時間足ボリンジャーバンド＋RSI戦略 バックテスト結果 ===")
    print(f"トレード数: {len(trade_history)}")
    print(f"総利益: {metrics.get('総利益 (円)', 0):,.0f}円")
    print(f"勝率: {metrics.get('勝率 (%)', 0):.2f}%")
    print(f"プロフィットファクター: {metrics.get('プロフィットファクター', 0):.2f}")
    print(f"最終残高: {equity_curve['balance'].iloc[-1] if not equity_curve.empty else config.get('backtest', 'initial_balance'):,.0f}円")
    
    results_df = pd.DataFrame([{
        "year": year,
        "strategy": "bollinger_rsi_enhanced_mt",
        "trades": len(trade_history),
        "profit": metrics.get('総利益 (円)', 0),
        "win_rate": metrics.get('勝率 (%)', 0),
        "profit_factor": metrics.get('プロフィットファクター', 0),
        "max_drawdown": metrics.get('最大ドローダウン (%)', 0),
        "initial_balance": equity_curve['balance'].iloc[0] if not equity_curve.empty else config.get('backtest', 'initial_balance'),
        "final_balance": equity_curve['balance'].iloc[-1] if not equity_curve.empty else config.get('backtest', 'initial_balance')
    }])
    
    results_df.to_csv(f"{year_dir}/mt_results.csv", index=False)
    
    with open(f"{year_dir}/mt_results.md", "w") as f:
        f.write(f"# 2020年 複数時間足ボリンジャーバンド＋RSI戦略 バックテスト結果\n\n")
        f.write(f"## パラメータ設定\n\n")
        f.write("| パラメータ | 値 |\n")
        f.write("|------------|----|\n")
        for param, value in strategy_params.items():
            if param != 'timeframe_weights':
                f.write(f"| {param} | {value} |\n")
        
        f.write("\n## 時間足の重み\n\n")
        f.write("| 時間足 | 重み |\n")
        f.write("|--------|------|\n")
        for tf, weight in strategy_params['timeframe_weights'].items():
            f.write(f"| {tf} | {weight} |\n")
        
        f.write("\n## パフォーマンス指標\n\n")
        f.write("| 指標 | 値 |\n")
        f.write("|------|----|\n")
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                f.write(f"| {metric} | {value:,.2f} |\n")
            else:
                f.write(f"| {metric} | {value} |\n")
    
    logger.log_info(f"{year}年 複数時間足ボリンジャーバンド＋RSI戦略 バックテスト終了")
    
    return metrics

if __name__ == "__main__":
    run_2020_backtest_mt()
