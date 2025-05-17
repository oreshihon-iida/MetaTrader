import os
import pandas as pd
import numpy as np
import logging
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.optimization.parameter_optimizer import ParameterOptimizer
from src.utils.logger import Logger
from src.utils.config import Config
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_file = os.path.join(log_dir, f'optimization_2020_{timestamp}.log')
    
    logger = Logger(log_file)
    logger.log_info("2020年データを使用したボリンジャーバンド＋RSI戦略の最適化を開始")
    
    return logger

def save_optimization_results(results_df, best_params, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    results_path = os.path.join(output_dir, f'optimization_results_2020_{timestamp}.csv')
    results_df.to_csv(results_path)
    
    params_path = os.path.join(output_dir, f'best_params_2020_{timestamp}.json')
    with open(params_path, 'w', encoding='utf-8') as f:
        json.dump(best_params, f, ensure_ascii=False, indent=4)
    
    return results_path, params_path

def create_performance_visualizations(results_df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        results_df['win_rate'], 
        results_df['profit_factor'],
        c=results_df['total_profit'],
        cmap='viridis',
        alpha=0.7,
        s=100
    )
    plt.colorbar(scatter, label='総利益')
    plt.title('勝率 vs プロフィットファクター (2020年データ)')
    plt.xlabel('勝率 (%)')
    plt.ylabel('プロフィットファクター')
    plt.tight_layout()
    
    scatter_path = os.path.join(output_dir, f'performance_scatter_2020_{timestamp}.png')
    plt.savefig(scatter_path)
    
    param_columns = [col for col in results_df.columns if col not in ['combination_id', 'trades', 'win_rate', 'profit_factor', 'total_profit']]
    
    for param in param_columns:
        plt.figure(figsize=(10, 6))
        sns.boxplot(x=param, y='win_rate', data=results_df)
        plt.title(f'パラメータ {param} と勝率の関係 (2020年データ)')
        plt.tight_layout()
        
        param_path = os.path.join(output_dir, f'param_{param}_vs_winrate_2020_{timestamp}.png')
        plt.savefig(param_path)
        plt.close()
    
    return scatter_path

def main():
    logger = setup_logging()
    logger.log_info("2020年データの最適化を開始")
    
    config = Config()
    processed_dir = config.get('data', 'processed_dir')
    
    year = 2020
    data_processor = DataProcessor(pd.DataFrame())
    data_15min = data_processor.load_processed_data('15min', year, processed_dir)
    
    if data_15min.empty:
        logger.log_error(f"{year}年の15分足データが見つかりません")
        return
    
    logger.log_info(f"{year}年の15分足データを読み込みました。行数: {len(data_15min)}")
    
    param_grid = {
        'bb_window': [10, 15, 20, 25, 30],
        'bb_dev': [1.5, 2.0, 2.5, 3.0],
        'rsi_window': [7, 10, 14, 21],
        'rsi_upper': [65, 70, 75, 80],
        'rsi_lower': [20, 25, 30, 35],
        'atr_window': [10, 14, 21],
        'atr_sl_multiplier': [1.0, 1.5, 2.0],
        'atr_tp_multiplier': [1.5, 2.0, 2.5, 3.0],
        'use_adaptive_params': [True],
        'trend_filter': [True],
        'vol_filter': [True],
        'time_filter': [True],
        'use_multi_timeframe': [True],
    }
    
    
    optimizer = ParameterOptimizer(data_15min, logger)
    best_params, results_df = optimizer.grid_search(
        strategy_class=BollingerRsiEnhancedMTStrategy,
        param_grid=param_grid,
        eval_metric='win_rate',  # 勝率で最適化
        initial_balance=200000,
        lot_size=0.01,
        max_positions=1,
        spread_pips=0.2
    )
    
    output_dir = 'results/optimization'
    results_path, params_path = save_optimization_results(results_df, best_params, output_dir)
    logger.log_info(f"最適化結果を保存しました: {results_path}, {params_path}")
    
    vis_path = create_performance_visualizations(results_df, output_dir)
    logger.log_info(f"パフォーマンス可視化を保存しました: {vis_path}")
    
    logger.log_info("2020年データの最適化が完了しました")

if __name__ == "__main__":
    main()
