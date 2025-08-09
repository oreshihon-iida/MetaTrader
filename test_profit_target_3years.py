#!/usr/bin/env python3
"""
過去3年間（2022年8月〜2025年8月）の高利益目標戦略バックテスト
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import json

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.profit_target_strategy import ProfitTargetStrategy
from src.data.data_processor_enhanced import DataProcessor
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger

def load_multi_year_data(start_year, end_year, timeframe='15min'):
    """
    複数年のデータを読み込み
    """
    processor = DataProcessor(None)
    all_data = pd.DataFrame()
    
    for year in range(start_year, end_year + 1):
        year_data = processor.load_processed_data(timeframe, year)
        if not year_data.empty:
            print(f"  {year}年: {len(year_data)} 行")
            all_data = pd.concat([all_data, year_data]) if not all_data.empty else year_data
        else:
            print(f"  {year}年: データなし")
    
    return all_data

def run_3year_backtest():
    """
    3年間のバックテストを実行
    """
    # ログディレクトリを作成
    log_dir = "results/profit_target_3years/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("3年間バックテスト開始")
    logger.log_info("期間: 2022年8月9日 - 2025年8月9日")
    logger.log_info("=" * 50)
    
    # データの読み込み（2022-2025年）
    print("\nデータ読み込み中...")
    
    # 15分足データ
    data_15min = load_multi_year_data(2022, 2025, '15min')
    
    if data_15min.empty:
        logger.log_error("データが見つかりません")
        return [], {}
    
    # 期間でフィルタリング（2022年8月9日〜2025年8月9日）
    start_date = pd.Timestamp('2022-08-09')
    end_date = pd.Timestamp('2025-08-09')
    data_15min = data_15min[start_date:end_date]
    
    logger.log_info(f"データサイズ: {len(data_15min)} 行")
    logger.log_info(f"期間: {data_15min.index[0]} 〜 {data_15min.index[-1]}")
    
    # 他の時間足データを生成
    print("時間足データ生成中...")
    
    # カラム名を確認
    if 'Close' in data_15min.columns:
        # 5分足
        data_5min = data_15min.resample('5min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
        # 1時間足
        data_1h = data_15min.resample('1h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
        # 日足
        data_daily = data_15min.resample('1D').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
    else:
        # 5分足
        data_5min = data_15min.resample('5min').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()
        # 1時間足
        data_1h = data_15min.resample('1h').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()
        # 日足
        data_daily = data_15min.resample('1D').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()
    
    logger.log_info(f"データ生成完了:")
    logger.log_info(f"  5分足: {len(data_5min)} 本")
    logger.log_info(f"  15分足: {len(data_15min)} 本")
    logger.log_info(f"  1時間足: {len(data_1h)} 本")
    logger.log_info(f"  日足: {len(data_daily)} 本")
    
    # 戦略の初期化（300万円ベース）
    strategy = ProfitTargetStrategy(
        initial_balance=3000000,
        monthly_profit_target=500000,
        max_risk_per_trade=0.015,
        max_daily_loss=0.05,
        max_drawdown=0.20,
        scaling_phase='initial'
    )
    
    # バックテストエンジンの初期化
    engine = CustomBacktestEngine(
        data=data_15min,
        initial_balance=3000000,
        spread_pips=0.2
    )
    
    # シグナル生成とトレード記録
    trades = []
    monthly_stats = {}
    
    print("\nバックテスト実行中...")
    
    # 月別統計の初期化
    current_month = None
    month_trades = []
    month_pnl = 0
    
    # データをチャンクで処理
    chunk_size = 1000
    for i in range(0, len(data_15min), chunk_size):
        chunk_15min = data_15min.iloc[max(0, i-200):i+chunk_size]
        
        if len(chunk_15min) < 50:
            continue
        
        # 現在の月を確認
        chunk_month = pd.Timestamp(chunk_15min.index[-1]).strftime('%Y-%m')
        if current_month != chunk_month:
            # 前月の統計を保存
            if current_month and month_trades:
                monthly_stats[current_month] = {
                    'trades': len(month_trades),
                    'pnl': month_pnl,
                    'phase': strategy.scaling_phase
                }
            
            # 新しい月の初期化
            current_month = chunk_month
            month_trades = []
            month_pnl = 0
            strategy.reset_monthly_metrics()
        
        # 対応する時間枠のデータを取得
        chunk_5min = data_5min.loc[chunk_15min.index[0]:chunk_15min.index[-1]]
        chunk_1h = data_1h.loc[chunk_15min.index[0]:chunk_15min.index[-1]]
        chunk_daily = data_daily.loc[:chunk_15min.index[-1]]
        
        # コア戦略のシグナル（15分足）
        for j in range(50, len(chunk_15min), 5):  # 5本ごとにチェック
            window_data = chunk_15min.iloc[:j+1]
            
            if not strategy.check_risk_limits():
                strategy.reset_daily_metrics()
                continue
            
            core_signal = strategy.generate_core_signal(window_data)
            if core_signal != 0:
                trade = strategy.execute_trade(core_signal, 'core', window_data)
                if trade:
                    trades.append(trade)
                    month_trades.append(trade)
        
        # アグレッシブ戦略（5分足）- 処理頻度を下げる
        if len(chunk_5min) >= 20 and i % 5000 == 0:
            for j in range(20, min(len(chunk_5min), 100), 10):
                window_data = chunk_5min.iloc[:j+1]
                
                aggressive_signal = strategy.generate_aggressive_signal(window_data)
                if aggressive_signal != 0:
                    trade = strategy.execute_trade(aggressive_signal, 'aggressive', window_data)
                    if trade:
                        trades.append(trade)
                        month_trades.append(trade)
        
        # 安定戦略（日足）- 低頻度
        if len(chunk_daily) >= 200 and i % 20000 == 0:
            stable_signal = strategy.generate_stable_signal(chunk_daily)
            if stable_signal != 0:
                trade = strategy.execute_trade(stable_signal, 'stable', chunk_15min.iloc[-1:])
                if trade:
                    trades.append(trade)
                    month_trades.append(trade)
        
        # 進捗表示
        if i % 10000 == 0 and i > 0:
            progress = (i / len(data_15min)) * 100
            print(f"  進捗: {progress:.1f}% - {len(trades)} トレード生成")
    
    # 最後の月の統計を保存
    if current_month and month_trades:
        monthly_stats[current_month] = {
            'trades': len(month_trades),
            'pnl': month_pnl,
            'phase': strategy.scaling_phase
        }
    
    # 結果の集計
    logger.log_info("=" * 50)
    logger.log_info("バックテスト結果")
    logger.log_info("=" * 50)
    
    total_trades = len(trades)
    logger.log_info(f"総トレード数: {total_trades}")
    
    # 戦略別の集計
    if total_trades > 0:
        core_trades = [t for t in trades if t['strategy'] == 'core']
        aggressive_trades = [t for t in trades if t['strategy'] == 'aggressive']
        stable_trades = [t for t in trades if t['strategy'] == 'stable']
        
        logger.log_info(f"\n戦略別トレード数:")
        logger.log_info(f"  コア戦略: {len(core_trades)}")
        logger.log_info(f"  アグレッシブ戦略: {len(aggressive_trades)}")
        logger.log_info(f"  安定戦略: {len(stable_trades)}")
        
        # 月平均
        total_months = len(monthly_stats)
        if total_months > 0:
            avg_trades_per_month = total_trades / total_months
            logger.log_info(f"\n月平均トレード数: {avg_trades_per_month:.1f}")
        
        # ロットサイズ分析
        avg_lot_size = np.mean([t['lot_size'] for t in trades])
        logger.log_info(f"平均ロットサイズ: {avg_lot_size:.2f}")
    
    # パフォーマンスサマリー
    summary = strategy.get_performance_summary()
    summary['period'] = {
        'start': str(start_date),
        'end': str(end_date),
        'months': len(monthly_stats)
    }
    summary['monthly_stats'] = monthly_stats
    
    return trades, summary

def save_results(trades, summary):
    """
    結果を保存
    """
    output_dir = "results/profit_target_3years"
    os.makedirs(output_dir, exist_ok=True)
    
    # サマリーを保存
    with open(os.path.join(output_dir, "backtest_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    # トレード履歴を保存
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv(os.path.join(output_dir, "trade_history.csv"), index=False)
    
    print(f"\n結果を {output_dir} に保存しました")
    
    # 月別統計を表示
    if 'monthly_stats' in summary:
        print("\n月別トレード数:")
        for month, stats in sorted(summary['monthly_stats'].items())[:10]:
            print(f"  {month}: {stats['trades']} トレード")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("3年間バックテスト")
    print("期間: 2022年8月9日 - 2025年8月9日")
    print("初期資金: 300万円")
    print("目標: 月50万円")
    print("=" * 50)
    
    trades, summary = run_3year_backtest()
    save_results(trades, summary)
    
    print("\n" + "=" * 50)
    print("バックテスト完了")
    print("=" * 50)