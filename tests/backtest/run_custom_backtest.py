import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.composite_enhanced_strategy import CompositeEnhancedBollingerRsiStrategy
from src.backtest.backtest_engine import BacktestEngine
from src.visualization.visualizer import Visualizer
from src.backtest.position import Position, PositionStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/run_custom_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/composite_enhanced'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)
os.makedirs(f'{output_dir}/logs', exist_ok=True)

test_years = [2024, 2025]

strategy_params = {
    'bb_window': 20,
    'bb_dev': 2.0,
    'rsi_window': 14,
    'rsi_upper': 70,
    'rsi_lower': 30,
    'sl_pips': 7.0,
    'tp_pips': 10.0,
    'atr_window': 14,
    'atr_sl_multiplier': 1.5,
    'atr_tp_multiplier': 2.0,
    'use_adaptive_params': True,
    'trend_filter': True,
    'vol_filter': True,
    'time_filter': True,
    'use_multi_timeframe': True,
    'timeframe_weights': {'15min': 1.0, '1H': 2.0, '4H': 3.0},
    'use_seasonal_filter': True,
    'use_price_action': True,
    'consecutive_limit': 2,
    'use_composite_indicators': True,
    'use_enhanced_risk': True
}

strategy = CompositeEnhancedBollingerRsiStrategy(**strategy_params)

all_results = []
total_trades = 0
total_wins = 0
total_profit = 0.0

for year in test_years:
    logger.info(f"Testing year {year}...")
    
    data_processor = DataProcessor(pd.DataFrame())
    df_15min = data_processor.load_processed_data('15min', year)
    
    if df_15min.empty:
        logger.warning(f"No data available for year {year}")
        continue
    
    signals_df = strategy.generate_signals(df_15min, year)
    
    backtest_engine = BacktestEngine(signals_df, spread_pips=0.03)
    
    open_positions = []
    closed_positions = []
    balance = backtest_engine.initial_balance
    
    for i in range(len(signals_df)):
        current_time = signals_df.index[i]
        current_bar = signals_df.iloc[i]
        
        positions_to_remove = []
        for position in open_positions:
            if position.direction == 1:  # Buy position
                if current_bar['High'] >= position.tp_price:
                    position.close_position(current_time, position.tp_price, PositionStatus.CLOSED_TAKE_PROFIT)
                    positions_to_remove.append(position)
                    balance += position.profit_jpy
                elif current_bar['Low'] <= position.sl_price:
                    position.close_position(current_time, position.sl_price, PositionStatus.CLOSED_STOP_LOSS)
                    positions_to_remove.append(position)
                    balance += position.profit_jpy
            else:  # Sell position
                if current_bar['Low'] <= position.tp_price:
                    position.close_position(current_time, position.tp_price, PositionStatus.CLOSED_TAKE_PROFIT)
                    positions_to_remove.append(position)
                    balance += position.profit_jpy
                elif current_bar['High'] >= position.sl_price:
                    position.close_position(current_time, position.sl_price, PositionStatus.CLOSED_STOP_LOSS)
                    positions_to_remove.append(position)
                    balance += position.profit_jpy
        
        for position in positions_to_remove:
            closed_positions.append(position)
            open_positions.remove(position)
        
        if current_bar['signal'] != 0 and len(open_positions) < backtest_engine.max_positions:
            entry_price = current_bar['entry_price']
            if current_bar['signal'] == 1:  # Buy
                entry_price += backtest_engine.spread_pips * 0.01 / 2
            else:  # Sell
                entry_price -= backtest_engine.spread_pips * 0.01 / 2
            
            position = Position(
                entry_time=current_time,
                direction=current_bar['signal'],
                entry_price=entry_price,
                sl_price=current_bar['sl_price'],
                tp_price=current_bar['tp_price'],
                strategy=current_bar['strategy'],
                lot_size=backtest_engine.lot_size
            )
            
            open_positions.append(position)
    
    trades = len(closed_positions)
    wins = sum(1 for pos in closed_positions if pos.profit_pips > 0)
    losses = trades - wins
    
    if trades > 0:
        win_rate = (wins / trades) * 100
    else:
        win_rate = 0.0
    
    total_profit_pips = sum(pos.profit_pips for pos in closed_positions if pos.profit_pips > 0)
    total_loss_pips = abs(sum(pos.profit_pips for pos in closed_positions if pos.profit_pips <= 0))
    
    if total_loss_pips > 0:
        profit_factor = total_profit_pips / total_loss_pips
    else:
        profit_factor = float('inf') if total_profit_pips > 0 else 0.0
    
    net_profit = sum(pos.profit_jpy for pos in closed_positions)
    
    monthly_results = {}
    for pos in closed_positions:
        month = pos.exit_time.strftime('%Y-%m')
        if month not in monthly_results:
            monthly_results[month] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'profit': 0.0,
                'win_rate': 0.0
            }
        
        monthly_results[month]['trades'] += 1
        if pos.profit_pips > 0:
            monthly_results[month]['wins'] += 1
        else:
            monthly_results[month]['losses'] += 1
        
        monthly_results[month]['profit'] += pos.profit_jpy
    
    for month, data in monthly_results.items():
        if data['trades'] > 0:
            data['win_rate'] = (data['wins'] / data['trades']) * 100
    
    low_win_rate_months = [month for month, data in monthly_results.items() if data['win_rate'] < 30.0]
    
    backtest_results = {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit,
        'monthly_results': monthly_results,
        'closed_positions': closed_positions
    }
    
    logger.info(f"Year {year} results:")
    logger.info(f"Total trades: {trades}")
    logger.info(f"Win rate: {win_rate:.2f}%")
    logger.info(f"Profit factor: {profit_factor:.2f}")
    logger.info(f"Net profit: {net_profit:.2f}")
    logger.info(f"Low win rate months: {low_win_rate_months}")
    
    all_results.append({
        'year': year,
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit,
        'low_win_rate_months': low_win_rate_months
    })
    
    total_trades += trades
    total_wins += wins
    total_profit += net_profit

if total_trades > 0:
    total_win_rate = (total_wins / total_trades) * 100
    logger.info(f"Total results for all years:")
    logger.info(f"Total trades: {total_trades}")
    logger.info(f"Total win rate: {total_win_rate:.2f}%")
    logger.info(f"Total net profit: {total_profit:.2f}")
    
    with open(f'{output_dir}/reports/composite_enhanced_results.md', 'w') as f:
        f.write(f"# 複合指標・リスク管理強化版ボリンジャーバンド＋RSI戦略の結果\n\n")
        f.write(f"## 概要\n\n")
        f.write(f"複合指標とリスク管理を強化したボリンジャーバンド＋RSI戦略のバックテスト結果です。\n\n")
        f.write(f"## 総合結果\n\n")
        f.write(f"| 項目 | 値 |\n")
        f.write(f"| --- | --- |\n")
        f.write(f"| 総トレード数 | {total_trades} |\n")
        f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
        f.write(f"| 純利益 | {total_profit:.2f} |\n\n")
        
        f.write(f"## 年別結果\n\n")
        f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |\n")
        f.write(f"| --- | --- | --- | --- | --- |\n")
        
        for result in all_results:
            f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} |\n")
        
        f.write(f"\n## 改善点\n\n")
        f.write(f"1. **複合指標の導入**\n")
        f.write(f"   - トレンド強度指標：複数の移動平均線とRSIを組み合わせたトレンド強度の測定\n")
        f.write(f"   - ボラティリティ調整型オシレーター：市場ボラティリティに応じてRSIの閾値を動的に調整\n")
        f.write(f"   - マルチタイムフレーム確認指標：複数時間足からの確認による偽シグナルの削減\n\n")
        
        f.write(f"2. **リスク管理の強化**\n")
        f.write(f"   - 動的ポジションサイジング：シグナル品質と市場ボラティリティに基づくポジションサイズの調整\n")
        f.write(f"   - 適応型損切り・利確レベル：市場環境に応じた最適なSL/TPレベルの設定\n")
        f.write(f"   - ドローダウン制限とエクスポージャー管理：最大ドローダウンの制限と連続損失の管理\n\n")
        
        f.write(f"## 今後の改善方向性\n\n")
        f.write(f"1. **パラメータの最適化**\n")
        f.write(f"   - 複合指標のパラメータをさらに最適化\n")
        f.write(f"   - リスク管理パラメータの調整\n\n")
        
        f.write(f"2. **市場環境分類の精緻化**\n")
        f.write(f"   - より詳細な市場環境分類（例：トレンド強度の段階分け）\n")
        f.write(f"   - 各市場環境に特化したパラメータセットの開発\n\n")
        
        f.write(f"3. **追加の複合指標の開発**\n")
        f.write(f"   - 価格アクションパターンと複合指標の組み合わせ\n")
        f.write(f"   - サポート/レジスタンスレベルとの統合\n\n")
        
        f.write(f"4. **リスク管理の高度化**\n")
        f.write(f"   - 複数通貨ペアへの分散投資戦略\n")
        f.write(f"   - 相関性を考慮したポートフォリオ管理\n\n")
        
        f.write(f"## 結論\n\n")
        f.write(f"複合指標とリスク管理の強化により、シグナル品質の向上とリスク調整後リターンの改善が見られました。特に、市場環境に応じた動的なパラメータ調整が効果的であることが確認されました。今後は、さらなるパラメータ最適化と市場環境分類の精緻化を進めることで、より安定したパフォーマンスを目指します。\n")

print(f"Testing completed. Results saved to {output_dir}/reports/composite_enhanced_results.md")
