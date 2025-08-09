#!/usr/bin/env python3
"""
月利益50万円を目指す高利益目標戦略のテスト
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.profit_target_strategy import ProfitTargetStrategy
from src.data.data_processor_enhanced import DataProcessor
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger

def run_profit_target_backtest():
    """
    高利益目標戦略のバックテストを実行
    """
    # ログディレクトリを作成
    log_dir = "results/profit_target_strategy/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("高利益目標戦略バックテスト開始")
    logger.log_info("目標: 月間50万円 / 年間600万円")
    logger.log_info("=" * 50)
    
    # データの読み込み（2024-2025年）
    processor = DataProcessor(None)
    data_15min = pd.DataFrame()
    data_5min = pd.DataFrame()
    data_1h = pd.DataFrame()
    data_daily = pd.DataFrame()
    
    # 15分足データの読み込み
    for year in [2024, 2025]:
        year_data = processor.load_processed_data('15min', year)
        if not year_data.empty:
            data_15min = pd.concat([data_15min, year_data]) if not data_15min.empty else year_data
    
    if data_15min.empty:
        logger.log_error("データが見つかりません")
        return [], {}
    
    # カラム名を確認してログに記録
    logger.log_info(f"データカラム: {data_15min.columns.tolist()}")
    logger.log_info(f"データサイズ: {len(data_15min)} 行")
    
    # 5分足データの生成（15分足から）- カラム名を修正
    if 'Close' in data_15min.columns:
        # カラム名が大文字の場合
        data_5min = data_15min.resample('5min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
    else:
        # カラム名が小文字の場合
        data_5min = data_15min.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    # 1時間足データの生成
    if 'Close' in data_15min.columns:
        data_1h = data_15min.resample('1h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # 日足データの生成
        data_daily = data_15min.resample('1D').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
    else:
        data_1h = data_15min.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # 日足データの生成
        data_daily = data_15min.resample('1D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    logger.log_info(f"データ読み込み完了:")
    logger.log_info(f"  5分足: {len(data_5min)} 本")
    logger.log_info(f"  15分足: {len(data_15min)} 本")
    logger.log_info(f"  1時間足: {len(data_1h)} 本")
    logger.log_info(f"  日足: {len(data_daily)} 本")
    
    # 戦略の初期化（300万円ベース）
    strategy = ProfitTargetStrategy(
        initial_balance=3000000,  # 300万円
        monthly_profit_target=500000,
        max_risk_per_trade=0.015,  # 1.5%
        max_daily_loss=0.05,  # 5%
        max_drawdown=0.20,
        scaling_phase='initial'  # 初期段階から開始
    )
    
    # バックテストエンジンの初期化
    engine = CustomBacktestEngine(
        data=data_15min,
        initial_balance=3000000,  # 300万円
        spread_pips=0.2
    )
    
    # 各戦略のシグナル生成とトレード実行
    trades = []
    
    # データをチャンクで処理（メモリ効率のため）
    chunk_size = 1000
    for i in range(0, len(data_15min), chunk_size):
        chunk_15min = data_15min.iloc[max(0, i-200):i+chunk_size]
        chunk_5min = data_5min.loc[chunk_15min.index[0]:chunk_15min.index[-1]]
        chunk_1h = data_1h.loc[chunk_15min.index[0]:chunk_15min.index[-1]]
        chunk_daily = data_daily.loc[chunk_15min.index[0]:chunk_15min.index[-1]]
        
        if len(chunk_15min) < 50:
            continue
        
        # コア戦略のシグナル（15分足）
        for j in range(50, len(chunk_15min)):
            window_data = chunk_15min.iloc[:j+1]
            
            # リスクチェック
            if not strategy.check_risk_limits():
                strategy.reset_daily_metrics()
                continue
            
            # コア戦略
            core_signal = strategy.generate_core_signal(window_data)
            if core_signal != 0:
                trade = strategy.execute_trade(core_signal, 'core', window_data)
                if trade:
                    trades.append(trade)
                    logger.log_info(f"コア戦略トレード: {trade['timestamp']} - {'買い' if trade['signal'] == 1 else '売り'}")
        
        # アグレッシブ戦略のシグナル（5分足）
        if len(chunk_5min) >= 20:
            for j in range(20, len(chunk_5min), 3):  # 3本ごとにチェック（頻度調整）
                window_data = chunk_5min.iloc[:j+1]
                
                aggressive_signal = strategy.generate_aggressive_signal(window_data)
                if aggressive_signal != 0:
                    trade = strategy.execute_trade(aggressive_signal, 'aggressive', window_data)
                    if trade:
                        trades.append(trade)
                        logger.log_info(f"アグレッシブ戦略トレード: {trade['timestamp']} - {'買い' if trade['signal'] == 1 else '売り'}")
        
        # 安定戦略のシグナル（日足）
        if len(chunk_daily) >= 200 and i % 10000 == 0:  # 低頻度でチェック
            stable_signal = strategy.generate_stable_signal(chunk_daily)
            if stable_signal != 0:
                trade = strategy.execute_trade(stable_signal, 'stable', chunk_15min.iloc[-1:])
                if trade:
                    trades.append(trade)
                    logger.log_info(f"安定戦略トレード: {trade['timestamp']} - {'買い' if trade['signal'] == 1 else '売り'}")
    
    # 結果の集計
    logger.log_info("=" * 50)
    logger.log_info("バックテスト結果")
    logger.log_info("=" * 50)
    
    total_trades = len(trades)
    logger.log_info(f"総トレード数: {total_trades}")
    
    if total_trades > 0:
        # 戦略別の集計
        core_trades = [t for t in trades if t['strategy'] == 'core']
        aggressive_trades = [t for t in trades if t['strategy'] == 'aggressive']
        stable_trades = [t for t in trades if t['strategy'] == 'stable']
        
        logger.log_info(f"\n戦略別トレード数:")
        logger.log_info(f"  コア戦略: {len(core_trades)}")
        logger.log_info(f"  アグレッシブ戦略: {len(aggressive_trades)}")
        logger.log_info(f"  安定戦略: {len(stable_trades)}")
        
        # ロットサイズ分析
        avg_lot_size = np.mean([t['lot_size'] for t in trades])
        logger.log_info(f"\n平均ロットサイズ: {avg_lot_size:.2f}")
        
        # 推定月間取引数（2024-2025の期間から推定）
        days_in_backtest = (data_15min.index[-1] - data_15min.index[0]).days
        monthly_trades = total_trades * 30 / days_in_backtest
        logger.log_info(f"推定月間取引数: {monthly_trades:.0f}")
        
        # 目標達成の見込み計算
        # 仮定: 勝率60%、平均利益10pips、平均損失5pips
        win_rate = 0.60  # 仮定値
        avg_win_pips = 10
        avg_loss_pips = 5
        
        expected_monthly_pips = monthly_trades * (win_rate * avg_win_pips - (1 - win_rate) * avg_loss_pips)
        pip_value_per_lot = 1000  # 円/pip（1ロットあたり）
        expected_monthly_profit = expected_monthly_pips * avg_lot_size * pip_value_per_lot
        
        logger.log_info(f"\n推定月間獲得pips: {expected_monthly_pips:.0f}")
        logger.log_info(f"推定月間利益: {expected_monthly_profit:,.0f}円")
        logger.log_info(f"目標達成率: {(expected_monthly_profit / 500000) * 100:.1f}%")
        
        # フェーズ別の推奨事項
        logger.log_info("\n=" * 50)
        logger.log_info("段階的実装の推奨事項")
        logger.log_info("=" * 50)
        
        logger.log_info("\n【初期段階】（1-3ヶ月）")
        logger.log_info("  - ロットサイズ: 基本の50%（0.15-0.25ロット）")
        logger.log_info("  - 月間目標: 25万円")
        logger.log_info("  - 重点: リスク管理とシステムの安定性")
        
        logger.log_info("\n【成長段階】（4-6ヶ月）")
        logger.log_info("  - ロットサイズ: 基本の75%（0.23-0.38ロット）")
        logger.log_info("  - 月間目標: 37.5万円")
        logger.log_info("  - 重点: パラメータ最適化と勝率向上")
        
        logger.log_info("\n【安定段階】（7ヶ月以降）")
        logger.log_info("  - ロットサイズ: 基本の100%（0.3-0.5ロット）")
        logger.log_info("  - 月間目標: 50万円")
        logger.log_info("  - 重点: 一貫性のある収益と規模拡大")
        
    # パフォーマンスサマリー
    summary = strategy.get_performance_summary()
    logger.log_info("\n=" * 50)
    logger.log_info("パフォーマンスサマリー")
    logger.log_info("=" * 50)
    logger.log_info(f"現在の残高: {summary['current_balance']:,.0f}円")
    logger.log_info(f"総損益: {summary['total_pnl']:,.0f}円")
    logger.log_info(f"スケーリングフェーズ: {summary['scaling_phase']}")
    
    return trades, summary

if __name__ == "__main__":
    trades, summary = run_profit_target_backtest()
    
    # 結果をファイルに保存
    import json
    
    output_dir = "results/profit_target_strategy"
    os.makedirs(output_dir, exist_ok=True)
    
    # サマリーを保存
    with open(os.path.join(output_dir, "backtest_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    # トレード履歴を保存
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv(os.path.join(output_dir, "trade_history.csv"), index=False)
    
    print("\n結果を results/profit_target_strategy に保存しました")