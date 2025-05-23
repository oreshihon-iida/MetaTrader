import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.optimization.parameter_optimizer import ParameterOptimizer
from src.utils.logger import Logger

log_dir = "logs/optimization"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info("2024-2025年データに対するボリンジャーバンド＋RSI戦略最適化開始")

data_dir = "data/processed"
data_processor = DataProcessor(pd.DataFrame())

df_2024 = data_processor.load_processed_data('15min', 2024, data_dir)
if df_2024.empty:
    logger.log_warning("2024年の15分足データが見つかりません")

df_2025 = data_processor.load_processed_data('15min', 2025, data_dir)
if df_2025.empty:
    logger.log_warning("2025年の15分足データが見つかりません")

combined_data = pd.concat([df_2024, df_2025]) if not df_2024.empty and not df_2025.empty else df_2024 if not df_2024.empty else df_2025

if combined_data.empty:
    logger.log_error("2024-2025年のデータが見つかりません。最適化を中止します。")
    exit(1)

logger.log_info(f"データ読み込み完了: {len(combined_data)} 行")

param_grid = {
    'bb_window': [10, 15, 20, 25, 30],
    'bb_dev': [1.5, 2.0, 2.5, 3.0],
    'rsi_window': [7, 14, 21],
    'rsi_upper': [65, 70, 75, 80],
    'rsi_lower': [20, 25, 30, 35],
    'use_seasonal_filter': [True, False],
    'use_price_action': [True, False]
}

optimizer = ParameterOptimizer(combined_data, logger)
best_params, results_df = optimizer.grid_search(
    strategy_class=BollingerRsiEnhancedMTStrategy,
    param_grid=param_grid,
    eval_metric='win_rate',
    initial_balance=200000,
    lot_size=0.01,
    max_positions=1,
    spread_pips=0.2
)

results_dir = "results/optimization/2024_2025"
os.makedirs(results_dir, exist_ok=True)
results_df.to_csv(f"{results_dir}/optimization_results.csv", index=False)

with open(f"{results_dir}/best_params.txt", "w") as f:
    for param, value in best_params.items():
        f.write(f"{param}: {value}\n")

plt.figure(figsize=(10, 8))
for param in param_grid.keys():
    if param in ['use_seasonal_filter', 'use_price_action']:
        continue  # ブール値は視覚化しない
    if len(param_grid[param]) > 1:  # パラメータに複数の値がある場合のみ
        plt.figure(figsize=(10, 6))
        plt.scatter(results_df[param], results_df['win_rate'])
        plt.title(f'{param} vs Win Rate')
        plt.xlabel(param)
        plt.ylabel('Win Rate (%)')
        plt.grid(True)
        plt.savefig(f"{results_dir}/{param}_vs_winrate.png")

top_results = results_df.sort_values('win_rate', ascending=False).head(10)
top_results.to_csv(f"{results_dir}/top_10_params.csv", index=False)

logger.log_info("2024-2025年データに対するボリンジャーバンド＋RSI戦略最適化完了")
logger.log_info(f"最適なパラメータ: {best_params}")
logger.log_info(f"最適パラメータの結果: 勝率={results_df.loc[results_df['win_rate'].idxmax(), 'win_rate']:.2f}%")

print("最適化完了")
print(f"最適なパラメータ: {best_params}")
print(f"最適パラメータの勝率: {results_df.loc[results_df['win_rate'].idxmax(), 'win_rate']:.2f}%")
