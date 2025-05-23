import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.strategies.composite_enhanced_strategy import CompositeEnhancedBollingerRsiStrategy
from src.backtest.position import Position, PositionStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/compare_strategies_2024_2025.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/strategy_comparison'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)
os.makedirs(f'{output_dir}/logs', exist_ok=True)

original_params = {
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
    'consecutive_limit': 2
}

enhanced_params = {
    'bb_window': 20,
    'bb_dev': 2.0,
    'rsi_window': 14,
    'rsi_upper': 75,  # 閾値を緩和
    'rsi_lower': 25,  # 閾値を緩和
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

original_strategy = BollingerRsiEnhancedMTStrategy(**original_params)
enhanced_strategy = CompositeEnhancedBollingerRsiStrategy(**enhanced_params)

def run_custom_backtest(signals_df, strategy_name, spread_pips=0.03, initial_balance=200000, lot_size=0.1, max_positions=5):
    logger.info(f"Running backtest for {strategy_name}...")
    
    open_positions = []
    closed_positions = []
    balance = initial_balance
    equity_curve = [balance]
    dates = [signals_df.index[0]]
    
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
        
        if current_bar['signal'] != 0 and len(open_positions) < max_positions:
            entry_price = current_bar['entry_price']
            if current_bar['signal'] == 1:  # Buy
                entry_price += spread_pips * 0.01 / 2
            else:  # Sell
                entry_price -= spread_pips * 0.01 / 2
            
            position = Position(
                entry_time=current_time,
                direction=current_bar['signal'],
                entry_price=entry_price,
                sl_price=current_bar['sl_price'],
                tp_price=current_bar['tp_price'],
                strategy=current_bar.get('strategy', strategy_name),
                lot_size=lot_size
            )
            
            open_positions.append(position)
        
        equity_curve.append(balance + sum(pos.calculate_profit(current_bar['Close']) for pos in open_positions))
        dates.append(current_time)
    
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
    
    max_equity = equity_curve[0]
    drawdown = [0]
    max_drawdown = 0
    max_drawdown_pct = 0
    
    for i in range(1, len(equity_curve)):
        max_equity = max(max_equity, equity_curve[i])
        dd = max_equity - equity_curve[i]
        dd_pct = (dd / max_equity) * 100 if max_equity > 0 else 0
        drawdown.append(dd)
        max_drawdown = max(max_drawdown, dd)
        max_drawdown_pct = max(max_drawdown_pct, dd_pct)
    
    backtest_results = {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'monthly_results': monthly_results,
        'closed_positions': closed_positions,
        'equity_curve': equity_curve,
        'dates': dates,
        'drawdown': drawdown
    }
    
    logger.info(f"{strategy_name} results:")
    logger.info(f"Total trades: {trades}")
    logger.info(f"Win rate: {win_rate:.2f}%")
    logger.info(f"Profit factor: {profit_factor:.2f}")
    logger.info(f"Net profit: {net_profit:.2f}")
    logger.info(f"Max drawdown: {max_drawdown:.2f} ({max_drawdown_pct:.2f}%)")
    logger.info(f"Low win rate months: {low_win_rate_months}")
    
    return backtest_results

all_original_results = []
all_enhanced_results = []

test_years = [2024, 2025]

for year in test_years:
    logger.info(f"Testing year {year}...")
    
    data_processor = DataProcessor(pd.DataFrame())
    df_15min = data_processor.load_processed_data('15min', year)
    
    if df_15min.empty:
        logger.warning(f"No data available for year {year}")
        continue
    
    logger.info("Generating signals with original strategy...")
    original_signals_df = original_strategy.generate_signals(df_15min, year)
    
    logger.info("Generating signals with enhanced strategy...")
    enhanced_signals_df = enhanced_strategy.generate_signals(df_15min, year)
    
    original_results = run_custom_backtest(original_signals_df, "Original Strategy")
    enhanced_results = run_custom_backtest(enhanced_signals_df, "Enhanced Strategy")
    
    all_original_results.append({
        'year': year,
        'trades': original_results['trades'],
        'wins': original_results['wins'],
        'losses': original_results['losses'],
        'win_rate': original_results['win_rate'],
        'profit_factor': original_results['profit_factor'],
        'net_profit': original_results['net_profit'],
        'max_drawdown_pct': original_results['max_drawdown_pct']
    })
    
    all_enhanced_results.append({
        'year': year,
        'trades': enhanced_results['trades'],
        'wins': enhanced_results['wins'],
        'losses': enhanced_results['losses'],
        'win_rate': enhanced_results['win_rate'],
        'profit_factor': enhanced_results['profit_factor'],
        'net_profit': enhanced_results['net_profit'],
        'max_drawdown_pct': enhanced_results['max_drawdown_pct']
    })
    
    plt.figure(figsize=(12, 6))
    plt.plot(original_results['dates'], original_results['equity_curve'], label='Original Strategy')
    plt.plot(enhanced_results['dates'], enhanced_results['equity_curve'], label='Enhanced Strategy')
    plt.title(f'Equity Curves Comparison - {year}')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{output_dir}/charts/equity_curves_comparison_{year}.png')
    plt.close()
    
    plt.figure(figsize=(12, 6))
    plt.plot(original_results['dates'], original_results['drawdown'], label='Original Strategy')
    plt.plot(enhanced_results['dates'], enhanced_results['drawdown'], label='Enhanced Strategy')
    plt.title(f'Drawdown Comparison - {year}')
    plt.xlabel('Date')
    plt.ylabel('Drawdown')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{output_dir}/charts/drawdowns_comparison_{year}.png')
    plt.close()

total_original_trades = sum(result['trades'] for result in all_original_results)
total_original_wins = sum(result['wins'] for result in all_original_results)
total_original_profit = sum(result['net_profit'] for result in all_original_results)

total_enhanced_trades = sum(result['trades'] for result in all_enhanced_results)
total_enhanced_wins = sum(result['wins'] for result in all_enhanced_results)
total_enhanced_profit = sum(result['net_profit'] for result in all_enhanced_results)

if total_original_trades > 0:
    total_original_win_rate = (total_original_wins / total_original_trades) * 100
else:
    total_original_win_rate = 0.0

if total_enhanced_trades > 0:
    total_enhanced_win_rate = (total_enhanced_wins / total_enhanced_trades) * 100
else:
    total_enhanced_win_rate = 0.0

with open(f'{output_dir}/reports/strategy_comparison_results.md', 'w') as f:
    f.write(f"# 元の戦略と複合指標・リスク管理強化版戦略の比較結果\n\n")
    f.write(f"## 概要\n\n")
    f.write(f"2024-2025年のデータを使用して、元の戦略と複合指標・リスク管理強化版戦略のパフォーマンスを比較しました。\n\n")
    
    f.write(f"## 総合結果\n\n")
    f.write(f"| 項目 | 元の戦略 | 強化版戦略 |\n")
    f.write(f"| --- | --- | --- |\n")
    f.write(f"| トレード数 | {total_original_trades} | {total_enhanced_trades} |\n")
    f.write(f"| 勝率 (%) | {total_original_win_rate:.2f} | {total_enhanced_win_rate:.2f} |\n")
    f.write(f"| 純利益 | {total_original_profit:.2f} | {total_enhanced_profit:.2f} |\n\n")
    
    f.write(f"## 年別結果\n\n")
    f.write(f"### 元の戦略\n\n")
    f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 | 最大ドローダウン (%) |\n")
    f.write(f"| --- | --- | --- | --- | --- | --- |\n")
    
    for result in all_original_results:
        f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} | {result['max_drawdown_pct']:.2f} |\n")
    
    f.write(f"\n### 強化版戦略\n\n")
    f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 | 最大ドローダウン (%) |\n")
    f.write(f"| --- | --- | --- | --- | --- | --- |\n")
    
    for result in all_enhanced_results:
        f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} | {result['max_drawdown_pct']:.2f} |\n")
    
    f.write(f"\n## 分析\n\n")
    
    trade_diff = total_enhanced_trades - total_original_trades
    trade_diff_pct = (trade_diff / total_original_trades * 100) if total_original_trades > 0 else float('inf')
    
    if trade_diff < 0:
        f.write(f"強化版戦略は元の戦略と比較して**トレード数が{abs(trade_diff)}件減少**（{abs(trade_diff_pct):.2f}%減）しています。これは、複合指標による厳格なシグナル確認条件が原因と考えられます。\n\n")
    elif trade_diff > 0:
        f.write(f"強化版戦略は元の戦略と比較して**トレード数が{trade_diff}件増加**（{trade_diff_pct:.2f}%増）しています。これは、複合指標による偽シグナルの削減と市場環境適応性の向上が原因と考えられます。\n\n")
    else:
        f.write(f"強化版戦略と元の戦略のトレード数は同じです。\n\n")
    
    win_rate_diff = total_enhanced_win_rate - total_original_win_rate
    
    if win_rate_diff > 0:
        f.write(f"強化版戦略は元の戦略と比較して**勝率が{win_rate_diff:.2f}%向上**しています。これは、複合指標によるシグナル品質の向上が原因と考えられます。\n\n")
    elif win_rate_diff < 0:
        f.write(f"強化版戦略は元の戦略と比較して**勝率が{abs(win_rate_diff):.2f}%低下**しています。これは、市場環境の変化に対する適応性が不十分である可能性があります。\n\n")
    else:
        f.write(f"強化版戦略と元の戦略の勝率は同じです。\n\n")
    
    profit_diff = total_enhanced_profit - total_original_profit
    
    if profit_diff > 0:
        f.write(f"強化版戦略は元の戦略と比較して**純利益が{profit_diff:.2f}増加**しています。\n\n")
    elif profit_diff < 0:
        f.write(f"強化版戦略は元の戦略と比較して**純利益が{abs(profit_diff):.2f}減少**しています。\n\n")
    else:
        f.write(f"強化版戦略と元の戦略の純利益は同じです。\n\n")
    
    f.write(f"## 結論\n\n")
    
    if total_enhanced_win_rate > total_original_win_rate and total_enhanced_profit > total_original_profit:
        f.write(f"複合指標とリスク管理の強化により、勝率と純利益の両方が向上しました。これは、提案した改善策が有効であることを示しています。\n\n")
    elif total_enhanced_win_rate > total_original_win_rate or total_enhanced_profit > total_original_profit:
        f.write(f"複合指標とリスク管理の強化により、一部の指標が向上しましたが、全体的なパフォーマンスは混在しています。パラメータの調整や戦略の微調整が必要です。\n\n")
    else:
        f.write(f"複合指標とリスク管理の強化による明確な改善は見られませんでした。これは、現在の実装が2024-2025年の市場環境に適していない可能性があります。異なるパラメータセットや戦略の見直しが必要です。\n\n")
    
    f.write(f"## 今後の改善方向性\n\n")
    
    if total_enhanced_trades < 10:
        f.write(f"1. **シグナル生成条件の緩和**\n")
        f.write(f"   - 複合指標の閾値をさらに緩和（例：RSI上限を80、下限を20に変更）\n")
        f.write(f"   - 必要な確認指標の数を減らす（例：3つの確認から1つの確認に変更）\n")
        f.write(f"   - 時間足の組み合わせを見直す（例：15分足と1時間足のみを使用）\n\n")
    
    if total_enhanced_win_rate < 70:
        f.write(f"2. **シグナル品質の向上**\n")
        f.write(f"   - 市場環境分類の精度向上\n")
        f.write(f"   - 各市場環境に特化したパラメータセットの開発\n")
        f.write(f"   - 価格アクションパターンの重み付け調整\n\n")
    
    if total_enhanced_profit < 0:
        f.write(f"3. **リスク管理の調整**\n")
        f.write(f"   - リスク/リワード比の最適化（例：TP/SL比を1.5から2.0に変更）\n")
        f.write(f"   - 動的ポジションサイジングの調整\n")
        f.write(f"   - 最大ドローダウン制限の見直し\n\n")
    
    f.write(f"4. **パラメータの最適化**\n")
    f.write(f"   - グリッドサーチによる最適パラメータの探索\n")
    f.write(f"   - 市場環境ごとのパラメータセットの開発\n")
    f.write(f"   - 時間帯別のパラメータ調整\n\n")
    
    f.write(f"5. **追加の複合指標の開発**\n")
    f.write(f"   - 価格アクションパターンと複合指標の組み合わせ\n")
    f.write(f"   - サポート/レジスタンスレベルとの統合\n")
    f.write(f"   - ボラティリティ指標の改良\n\n")
    
    f.write(f"6. **機械学習の導入検討**\n")
    f.write(f"   - 市場環境の自動分類\n")
    f.write(f"   - 最適パラメータの予測\n")
    f.write(f"   - シグナル品質の評価\n")

print(f"Testing completed. Results saved to {output_dir}/reports/strategy_comparison_results.md")
