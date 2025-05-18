import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from src.strategies.improved_short_term_strategy import ImprovedShortTermStrategy
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger
import argparse

parser = argparse.ArgumentParser(description='5分足を使用する改良版短期戦略のバックテストを実行する')
parser.add_argument('--years', type=str, default='2023,2024,2025', help='テスト対象年（カンマ区切り、例：2023,2024,2025）')
args = parser.parse_args()

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info("5分足を使用する改良版短期戦略のバックテスト開始")

strategy = ImprovedShortTermStrategy(
    bb_window=20,
    bb_dev=1.6,
    rsi_window=14,
    rsi_upper=55,
    rsi_lower=45,
    sl_pips=2.5,
    tp_pips=12.5,
    timeframe_weights={'5min': 2.0, '15min': 1.0}
)

years = [int(year) for year in args.years.split(',')]
logger.log_info(f"対象年: {years}")

results = []
all_data = []

for year in years:
    logger.log_info(f"{year}年のデータを処理中...")
    
    data_dir = f"data/processed/15min/{year}"
    if not os.path.exists(data_dir):
        logger.log_warning(f"{data_dir} が見つかりません")
        continue
    
    data_file = f"{data_dir}/USDJPY_15min_{year}.csv"
    if not os.path.exists(data_file):
        logger.log_warning(f"{data_file} が見つかりません")
        continue
    
    data = pd.read_csv(data_file, index_col=0, parse_dates=True)
    logger.log_info(f"{len(data)} 行のデータを読み込みました")
    
    signals = strategy.generate_signals(data, year, 'data/processed')
    
    backtest = CustomBacktestEngine(
        data=signals,
        initial_balance=100000,
        lot_size=0.01,
        max_positions=5,
        spread_pips=0.2
    )
    
    result = backtest.run()
    
    trades = len(result)
    wins = len(result[result['profit_pips'] > 0]) if not result.empty else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    if not result.empty:
        total_profit = result[result['profit_pips'] > 0]['profit_pips'].sum()
        total_loss = abs(result[result['profit_pips'] < 0]['profit_pips'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        net_profit = result['profit_jpy'].sum()
    else:
        profit_factor = 0
        net_profit = 0
    
    logger.log_info(f"{year}年の結果:")
    logger.log_info(f"トレード数: {trades}")
    logger.log_info(f"勝率: {win_rate:.2f}%")
    logger.log_info(f"プロフィットファクター: {profit_factor:.2f}")
    logger.log_info(f"純利益: {net_profit:.2f}")
    
    results.append({
        'year': year,
        'trades': trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit
    })
    
    all_data.append(backtest.get_equity_curve())

total_trades = sum(r['trades'] for r in results)
total_wins = sum(r['trades'] * r['win_rate'] / 100 for r in results)
total_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
total_net_profit = sum(r['net_profit'] for r in results)

logger.log_info(f"総合結果:")
logger.log_info(f"総トレード数: {total_trades}")
logger.log_info(f"総合勝率: {total_win_rate:.2f}%")
logger.log_info(f"総純利益: {total_net_profit:.2f}")

logger.log_info("5分足を使用する改良版短期戦略のバックテスト完了")
