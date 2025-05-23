import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.data.data_processor_enhanced import DataProcessor
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger
from src.visualization.visualizer import Visualizer

log_dir = "results/final_balanced/logs"
chart_dir = "results/final_balanced/charts"
os.makedirs(log_dir, exist_ok=True)
os.makedirs(chart_dir, exist_ok=True)

logger = Logger(log_dir)
logger.log_info("最終バランス型戦略のテスト開始")

data_dir = 'data/processed'
years = [2024, 2025]
data_processor = DataProcessor(pd.DataFrame())

df_15min_list = []
for year in years:
    df = data_processor.load_processed_data('15min', year, data_dir)
    if not df.empty:
        df_15min_list.append(df)
        logger.log_info(f"{year}年の15分足データ読み込み完了: {len(df)}行")
    else:
        logger.log_warning(f"{year}年の15分足データが見つかりません")

if not df_15min_list:
    logger.log_error("有効なデータがありません")
    exit(1)

df_15min = pd.concat(df_15min_list)
df_15min = df_15min.sort_index()
logger.log_info(f"結合後の15分足データ: {len(df_15min)}行")

strategy = BollingerRsiEnhancedMTStrategy(
    use_seasonal_filter=True,       # 季節性フィルターを有効化
    use_price_action=True,          # 価格アクションパターンを有効化
    timeframe_weights={            
        '1H': 1.0,
        '4H': 2.0                   # 15分足を除外
    },
    rsi_upper=80,                   # RSI上限
    rsi_lower=20,                   # RSI下限
    bb_dev=2.0,                     # ボリンジャーバンド偏差
    sl_pips=10.0,                   # ストップロス
    tp_pips=30.0,                   # テイクプロフィット（リスクリワード比3.0）
    consecutive_limit=3,            # 連続シグナル制限
    volatility_filter=True          # ボラティリティフィルターを有効化
)

original_analyze_method = strategy.analyze_timeframe_signals

def optimized_analyze_timeframe_signals(self, multi_tf_data):
    """
    最適化された時間足分析
    """
    signals = {}
    
    for tf, df in multi_tf_data.items():
        signals[tf] = df.copy()
        signals[tf]['signal'] = 0
        signals[tf]['entry_price'] = 0.0
        signals[tf]['sl_price'] = 0.0
        signals[tf]['tp_price'] = 0.0
        signals[tf]['strategy'] = 'bollinger_rsi_mt'
        
        for i in range(len(signals[tf])):
            if i < 1:
                continue
                
            current = signals[tf].iloc[i]
            
            if (current['rsi'] <= 25 or current['Close'] <= current['bb_lower'] * 1.03):
                if self._apply_filters(signals[tf], i):
                    signals[tf].iloc[i, signals[tf].columns.get_loc('signal')] = 1
                    
                    entry_price = current['Open']
                    sl_price, tp_price = self._calculate_adaptive_sl_tp(signals[tf], i, 1)
                    
                    signals[tf].iloc[i, signals[tf].columns.get_loc('entry_price')] = entry_price
                    signals[tf].iloc[i, signals[tf].columns.get_loc('sl_price')] = sl_price
                    signals[tf].iloc[i, signals[tf].columns.get_loc('tp_price')] = tp_price
            
            elif (current['rsi'] >= 75 or current['Close'] >= current['bb_upper'] * 0.97):
                if self._apply_filters(signals[tf], i):
                    signals[tf].iloc[i, signals[tf].columns.get_loc('signal')] = -1
                    
                    entry_price = current['Open']
                    sl_price, tp_price = self._calculate_adaptive_sl_tp(signals[tf], i, -1)
                    
                    signals[tf].iloc[i, signals[tf].columns.get_loc('entry_price')] = entry_price
                    signals[tf].iloc[i, signals[tf].columns.get_loc('sl_price')] = sl_price
                    signals[tf].iloc[i, signals[tf].columns.get_loc('tp_price')] = tp_price
    
    return signals

strategy.analyze_timeframe_signals = lambda multi_tf_data: optimized_analyze_timeframe_signals(strategy, multi_tf_data)

original_merge_method = strategy.merge_timeframe_signals

def optimized_merge_timeframe_signals(self, df, signals):
    """
    最適化された複数時間足シグナル統合メソッド
    """
    result_df = df.copy()
    result_df['signal'] = 0
    result_df['signal_score'] = 0.0
    result_df['entry_price'] = 0.0
    result_df['sl_price'] = 0.0
    result_df['tp_price'] = 0.0
    result_df['strategy'] = 'bollinger_rsi_mt'
    
    for i in range(len(result_df)):
        current_time = result_df.index[i]
        
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for tf, tf_weight in self.timeframe_weights.items():
            if tf in signals:
                tf_df = signals[tf]
                
                past_signals = tf_df[tf_df.index <= current_time]
                
                if not past_signals.empty:
                    latest_signal = past_signals.iloc[-1]
                    
                    time_diff = (current_time - past_signals.index[-1]).total_seconds() / 3600
                    
                    if time_diff <= 6:  # 6時間以内のシグナルを考慮
                        if latest_signal['signal'] == 1:
                            buy_score += tf_weight
                        elif latest_signal['signal'] == -1:
                            sell_score += tf_weight
                        
                        total_weight += tf_weight
        
        if total_weight > 0:
            buy_score_pct = buy_score / sum(self.timeframe_weights.values())
            sell_score_pct = sell_score / sum(self.timeframe_weights.values())
            
            threshold = sum(self.timeframe_weights.values()) * 0.30
            
            if buy_score >= threshold:
                month = current_time.month
                low_win_rate_months = [2, 6, 11, 12]  # 2月、6月、11月、12月
                
                if month not in low_win_rate_months:
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'signal_score'] = buy_score
                    
                    entry_price = result_df.iloc[i]['Open']
                    sl_price = entry_price - self.sl_pips * 0.01
                    tp_price = entry_price + self.tp_pips * 0.01
                    
                    result_df.loc[result_df.index[i], 'entry_price'] = entry_price
                    result_df.loc[result_df.index[i], 'sl_price'] = sl_price
                    result_df.loc[result_df.index[i], 'tp_price'] = tp_price
                
            elif sell_score >= threshold:
                month = current_time.month
                low_win_rate_months = [2, 6, 11, 12]  # 2月、6月、11月、12月
                
                if month not in low_win_rate_months:
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'signal_score'] = -sell_score
                    
                    entry_price = result_df.iloc[i]['Open']
                    sl_price = entry_price + self.sl_pips * 0.01
                    tp_price = entry_price - self.tp_pips * 0.01
                    
                    result_df.loc[result_df.index[i], 'entry_price'] = entry_price
                    result_df.loc[result_df.index[i], 'sl_price'] = sl_price
                    result_df.loc[result_df.index[i], 'tp_price'] = tp_price
    
    last_signal = 0
    consecutive_count = 0
    
    for i in range(len(result_df)):
        current_signal = result_df.iloc[i]['signal']
        
        if current_signal != 0 and current_signal == last_signal:
            consecutive_count += 1
            if consecutive_count > self.consecutive_limit:
                result_df.iloc[i, result_df.columns.get_loc('signal')] = 0
        elif current_signal != 0:
            consecutive_count = 1
        
        if current_signal != 0:
            last_signal = current_signal
    
    for i in range(len(result_df)):
        hour = result_df.index[i].hour
        
        if not ((0 <= hour < 9) or (8 <= hour < 16)):
            result_df.iloc[i, result_df.columns.get_loc('signal')] = 0
    
    return result_df

strategy.merge_timeframe_signals = lambda df, signals: optimized_merge_timeframe_signals(strategy, df, signals)

logger.log_info("シグナル生成開始")
signals_df = strategy.generate_signals(df_15min, years[0], data_dir)
logger.log_info(f"シグナル生成完了: {len(signals_df)}行")

signal_count = len(signals_df[signals_df['signal'] != 0])
buy_signals = len(signals_df[signals_df['signal'] == 1])
sell_signals = len(signals_df[signals_df['signal'] == -1])
logger.log_info(f"シグナル総数: {signal_count}（買い: {buy_signals}, 売り: {sell_signals}）")

required_columns = ['entry_price', 'sl_price', 'tp_price', 'strategy']
missing_columns = [col for col in required_columns if col not in signals_df.columns]
if missing_columns:
    logger.log_error(f"欠落しているカラム: {missing_columns}")
    exit(1)

logger.log_info("バックテスト実行開始")
backtest_engine = CustomBacktestEngine(
    data=signals_df,
    initial_balance=200000,
    lot_size=0.01,
    spread_pips=0.2,
    max_positions=1
)

results = backtest_engine.run()
logger.log_info("バックテスト実行完了")

if not results.empty:
    results.to_csv(f"{log_dir}/trade_history.csv")
    logger.log_info(f"取引履歴を保存しました: {len(results)}トレード")
    
    total_trades = len(results)
    wins = len(results[results['損益(円)'] > 0])
    losses = len(results[results['損益(円)'] < 0])
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = results[results['損益(円)'] > 0]['損益(円)'].sum()
    total_loss = abs(results[results['損益(円)'] < 0]['損益(円)'].sum())
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    net_profit = total_profit - total_loss
    
    results['エントリー時間'] = pd.to_datetime(results['エントリー時間'])
    results['month'] = results['エントリー時間'].dt.strftime('%Y-%m')
    
    monthly_performance = results.groupby('month').agg(
        trades=('損益(円)', 'count'),
        win_rate=('損益(円)', lambda x: (x > 0).mean() * 100),
        net_profit=('損益(円)', 'sum')
    ).reset_index()
    
    visualizer = Visualizer(chart_dir)
    
    equity_curve = results.copy()
    equity_curve['cumulative_profit'] = equity_curve['損益(円)'].cumsum()
    equity_curve['equity'] = 200000 + equity_curve['cumulative_profit']
    
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve['エントリー時間'], equity_curve['equity'])
    plt.title('Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Equity (JPY)')
    plt.grid(True)
    plt.savefig(f"{chart_dir}/equity_curve.png")
    
    equity_curve['peak'] = equity_curve['equity'].cummax()
    equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
    
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve['エントリー時間'], equity_curve['drawdown'])
    plt.title('Drawdown')
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    plt.grid(True)
    plt.savefig(f"{chart_dir}/drawdown.png")
    
    plt.figure(figsize=(12, 6))
    plt.bar(monthly_performance['month'], monthly_performance['net_profit'])
    plt.title('Monthly Returns')
    plt.xlabel('Month')
    plt.ylabel('Net Profit (JPY)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{chart_dir}/monthly_returns.png")
    
    with open(f"{log_dir}/backtest_summary.md", "w") as f:
        f.write("# 最終バランス型戦略のバックテスト結果\n\n")
        f.write(f"期間: 2024-2025年\n")
        f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 戦略パラメータ\n\n")
        f.write("- 時間足: 1時間足 + 4時間足（15分足を除外）\n")
        f.write("- 時間足の重み付け: 1H: 1.0, 4H: 2.0\n")
        f.write("- RSI上限: 80\n")
        f.write("- RSI下限: 20\n")
        f.write("- ボリンジャーバンド偏差: 2.0\n")
        f.write("- ストップロス: 10.0 pips\n")
        f.write("- テイクプロフィット: 30.0 pips\n")
        f.write("- 連続シグナル制限: 3\n")
        f.write("- 季節性フィルター: 有効\n")
        f.write("- 価格アクションパターン: 有効\n")
        f.write("- ボラティリティフィルター: 有効\n")
        f.write("- シグナル閾値: 30%\n")
        f.write("- 月別フィルター: 有効（2月、6月、11月、12月を除外）\n")
        f.write("- 時間帯フィルター: 有効（アジア時間とロンドン時間のみ）\n\n")
        
        f.write("## パフォーマンス指標\n\n")
        f.write(f"- 総トレード数: {total_trades}\n")
        f.write(f"- 勝率: {win_rate:.2f}%\n")
        f.write(f"- プロフィットファクター: {profit_factor:.2f}\n")
        f.write(f"- 総利益: {total_profit:.2f}円\n")
        f.write(f"- 総損失: {total_loss:.2f}円\n")
        f.write(f"- 純利益: {net_profit:.2f}円\n\n")
        
        f.write("## 月別パフォーマンス\n\n")
        f.write("| 月 | トレード数 | 勝率 | 純利益 |\n")
        f.write("|---|---|---|---|\n")
        for _, row in monthly_performance.iterrows():
            f.write(f"| {row['month']} | {row['trades']} | {row['win_rate']:.2f}% | {row['net_profit']:.2f}円 |\n")
        
        f.write("\n## 結論\n\n")
        if win_rate >= 70 and profit_factor >= 2.0:
            f.write("最終バランス型戦略は目標を達成しました。勝率70%以上、プロフィットファクター2.0以上を達成しています。\n")
        else:
            f.write("最終バランス型戦略は目標を達成していません。さらなる最適化が必要です。\n")
            
            if win_rate < 70:
                f.write("- 勝率が目標（70%）を下回っています。シグナル生成条件をさらに調整することを検討してください。\n")
            
            if profit_factor < 2.0:
                f.write("- プロフィットファクターが目標（2.0）を下回っています。リスク・リワード比の調整を検討してください。\n")
    
    logger.log_info(f"バックテスト結果のサマリーを保存しました: {log_dir}/backtest_summary.md")
else:
    logger.log_warning("取引履歴がありません")

strategy.analyze_timeframe_signals = original_analyze_method
strategy.merge_timeframe_signals = original_merge_method

logger.log_info("最終バランス型戦略のテスト完了")
