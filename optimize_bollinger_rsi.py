import os
import pandas as pd
import numpy as np
import argparse
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategies.bollinger_rsi_enhanced import BollingerRsiEnhancedStrategy
from src.optimization.parameter_optimizer import ParameterOptimizer
from src.utils.logger import Logger
from src.utils.config import Config

def main():
    """
    ボリンジャーバンド＋RSI戦略のパラメータ最適化を実行する
    """
    parser = argparse.ArgumentParser(description='ボリンジャーバンド＋RSI戦略のパラメータ最適化')
    parser.add_argument('--year', type=int, default=2020, help='最適化に使用する年のデータ')
    parser.add_argument('--metric', type=str, default='profit_factor', choices=['win_rate', 'profit_factor', 'total_profit'],
                        help='最適化の評価指標')
    
    args = parser.parse_args()
    
    output_dir = f"results/optimization/{args.year}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/logs", exist_ok=True)
    
    logger = Logger(f"{output_dir}/logs")
    logger.log_info(f"{args.year}年 ボリンジャーバンド＋RSI戦略のパラメータ最適化開始")
    
    config = Config()
    
    logger.log_info(f"{args.year}年の処理済みデータの読み込みを試みています...")
    from src.data.data_processor_enhanced import DataProcessor as EnhancedDataProcessor
    data_processor = EnhancedDataProcessor(pd.DataFrame())
    year_data = data_processor.load_processed_data(config.get('data', 'timeframe'), args.year, config.get('data', 'processed_dir'))
    
    if year_data.empty:
        logger.log_info(f"処理済みデータが見つかりません。{args.year}年の生データから処理します...")
        data_loader = DataLoader(config.get('data', 'raw_dir'))
        data = data_loader.load_year_data(args.year)
        
        if data.empty:
            logger.log_warning(f"{args.year}年のデータがありません")
            return
        
        logger.log_info(f"データ読み込み完了: {len(data)} 行")
        
        logger.log_info("データ処理中...")
        data_processor = DataProcessor(data)
        
        resampled_data = data_processor.resample(config.get('data', 'timeframe'))
        logger.log_info(f"リサンプリング完了: {len(resampled_data)} 行")
        
        resampled_data = data_processor.add_technical_indicators(resampled_data)
        
        resampled_data = data_processor.get_tokyo_session_range(resampled_data)
        logger.log_info("テクニカル指標の計算完了")
        
        start_date = f"{args.year}-01-01"
        end_date = f"{args.year}-12-31"
        
        year_data = resampled_data.loc[start_date:end_date]
    else:
        logger.log_info(f"処理済みデータ読み込み完了: {len(year_data)} 行")
        start_date = f"{args.year}-01-01"
        end_date = f"{args.year}-12-31"
        year_data = year_data.loc[start_date:end_date]
    
    if year_data.empty:
        logger.log_warning(f"{args.year}年のデータがありません")
        return
    
    logger.log_info(f"最適化期間: {start_date} から {end_date}")
    logger.log_info(f"データ件数: {len(year_data)} 行")
    
    optimizer = ParameterOptimizer(year_data, logger)
    
    param_grid = {
        'bb_window': [10, 20, 30],
        'bb_dev': [1.5, 2.0, 2.5],
        'rsi_window': [7, 14, 21],
        'rsi_upper': [65, 70, 75, 80],
        'rsi_lower': [20, 25, 30, 35],
        'sl_pips': [5.0, 7.0, 10.0],
        'tp_pips': [7.0, 10.0, 15.0],
        'atr_window': [7, 14, 21],
        'atr_sl_multiplier': [1.0, 1.5, 2.0],
        'atr_tp_multiplier': [1.5, 2.0, 2.5],
        'use_adaptive_params': [True, False],
        'trend_filter': [True, False],
        'vol_filter': [True, False],
        'time_filter': [True, False]
    }
    
    logger.log_info("パラメータ最適化実行中...")
    best_params, results_df = optimizer.grid_search(
        BollingerRsiEnhancedStrategy,
        param_grid,
        eval_metric=args.metric,
        initial_balance=config.get('backtest', 'initial_balance'),
        lot_size=config.get('backtest', 'lot_size'),
        max_positions=config.get('backtest', 'max_positions'),
        spread_pips=config.get('backtest', 'spread_pips')
    )
    
    if not results_df.empty:
        results_df.to_csv(f"{output_dir}/optimization_results.csv", index=False)
        
        top_results = results_df.sort_values(by=args.metric, ascending=False).head(10)
        
        with open(f"{output_dir}/top_results.md", "w") as f:
            f.write(f"# {args.year}年 ボリンジャーバンド＋RSI戦略 パラメータ最適化結果\n\n")
            f.write(f"評価指標: {args.metric}\n\n")
            f.write("## 最適なパラメータ\n\n")
            
            for param, value in best_params.items():
                f.write(f"- {param}: {value}\n")
            
            f.write("\n## 最適パラメータの結果\n\n")
            best_row = results_df.sort_values(by=args.metric, ascending=False).iloc[0]
            f.write(f"- トレード数: {best_row['trades']}\n")
            f.write(f"- 勝率: {best_row['win_rate']:.2f}%\n")
            f.write(f"- プロフィットファクター: {best_row['profit_factor']:.2f}\n")
            f.write(f"- 総利益: {best_row['total_profit']:.0f}円\n\n")
            
            f.write("## 上位10件の結果\n\n")
            f.write("| 順位 | トレード数 | 勝率 (%) | プロフィットファクター | 総利益 (円) | パラメータ |\n")
            f.write("|------|------------|----------|------------------------|------------|------------|\n")
            
            for i, (_, row) in enumerate(top_results.iterrows(), 1):
                params_str = ", ".join([f"{k}={v}" for k, v in row.items() if k not in ['combination_id', 'trades', 'win_rate', 'profit_factor', 'total_profit']])
                f.write(f"| {i} | {row['trades']} | {row['win_rate']:.2f} | {row['profit_factor']:.2f} | {row['total_profit']:.0f} | {params_str} |\n")
        
        logger.log_info(f"最適化結果を保存しました: {output_dir}/optimization_results.csv, {output_dir}/top_results.md")
    
    logger.log_info(f"{args.year}年 ボリンジャーバンド＋RSI戦略のパラメータ最適化完了")

if __name__ == "__main__":
    main()
