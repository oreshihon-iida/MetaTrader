import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from src.strategies.dynamic_multi_timeframe_strategy import DynamicMultiTimeframeStrategy
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger
import argparse

parser = argparse.ArgumentParser(description='動的複数時間足戦略のバックテストを実行する')
parser.add_argument('--years', type=str, default='2023,2024', help='テスト対象年（カンマ区切り、例：2023,2024）')
args = parser.parse_args()

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info("動的複数時間足戦略のバックテスト開始")

strategy = DynamicMultiTimeframeStrategy(
    bb_window=20,
    bb_dev=0.8,    # 1.0から0.8に縮小してさらにバンドに触れる頻度を極限まで増加
    rsi_window=7,  # 14から7に短縮して反応速度を上げる
    rsi_upper=50,  # 50のまま維持
    rsi_lower=50,  # 50のまま維持
    sl_pips=2.5,
    tp_pips=12.5,
    timeframe_weights={'5min': 2.0, '15min': 1.0, '30min': 0.5, '1H': 0.5, '1min': 0.5},  # 1分足を追加
    market_regime_detection=True,
    dynamic_timeframe_weights=True,
    volatility_based_params=True,
    confirmation_threshold=0.2,  # 確認閾値を20%に維持
    expand_time_filter=True,     # 取引時間を拡大
    disable_time_filter=True,    # 時間フィルターを無効化して24時間取引を許可
    disable_multi_timeframe=True,  # 複数時間足確認を無効化して単一時間足でのシグナル生成を許可
    use_price_only_signals=True,   # 価格のみに基づくシグナル生成を有効化（新機能）
    use_moving_average=True,       # 移動平均クロスオーバーシグナルを有効化（新機能）
    ma_fast_period=5,              # 短期移動平均期間
    ma_slow_period=20              # 長期移動平均期間
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
    
    five_min_dir = f"data/processed/5min/{year}"
    five_min_file = f"{five_min_dir}/USDJPY_5min_{year}.csv"
    if not os.path.exists(five_min_file):
        logger.log_warning(f"5分足データが見つかりません: {five_min_file}")
        logger.log_info("5分足データを生成するには transform_data.py を実行してください")
    
    thirty_min_dir = f"data/processed/30min/{year}"
    thirty_min_file = f"{thirty_min_dir}/USDJPY_30min_{year}.csv"
    if not os.path.exists(thirty_min_file):
        logger.log_warning(f"30分足データが見つかりません: {thirty_min_file}")
        logger.log_info("30分足データを生成するには transform_data.py を実行してください")
    
    logger.log_info("シグナル生成開始...")
    logger.log_info(f"使用する時間足の重み: {strategy.timeframe_weights}")
    
    signals = strategy.generate_signals(data, year, 'data/processed')
    logger.log_info("シグナル生成完了、バックテスト開始...")
    
    backtest = CustomBacktestEngine(
        data=signals,
        initial_balance=2000000,  # 100000から2000000に変更
        lot_size=0.01,            # 0.02から0.01に戻す
        max_positions=5,          # 5のまま維持
        spread_pips=0.2
    )
    
    result = backtest.run()
    logger.log_info(f"バックテスト完了、結果: {len(result)} トレード")
    
    trades = len(result)
    wins = len(result[result['損益(pips)'] > 0]) if not result.empty else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    if not result.empty:
        total_profit = result[result['損益(pips)'] > 0]['損益(pips)'].sum()
        total_loss = abs(result[result['損益(pips)'] < 0]['損益(pips)'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        net_profit = result['損益(円)'].sum()
    else:
        profit_factor = 0
        net_profit = 0
        
    for _, trade in result.iterrows():
        is_win = trade['損益(pips)'] > 0
        strategy.update_consecutive_stats(is_win)
    
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

logger.log_info("動的複数時間足戦略のバックテスト完了")
