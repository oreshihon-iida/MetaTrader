#!/usr/bin/env python3
"""
取引執行シミュレーション付きバックテスト（3年間）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.profit_target_strategy import ProfitTargetStrategy
from src.backtest.trade_executor import TradeExecutor
from src.data.data_processor_enhanced import DataProcessor
from src.utils.logger import Logger

def load_multi_year_data(start_year, end_year, timeframe='15min'):
    """複数年のデータを読み込み"""
    processor = DataProcessor(None)
    all_data = pd.DataFrame()
    
    for year in range(start_year, end_year + 1):
        year_data = processor.load_processed_data(timeframe, year)
        if not year_data.empty:
            print(f"  {year}年: {len(year_data)} 行")
            all_data = pd.concat([all_data, year_data]) if not all_data.empty else year_data
    
    return all_data

def run_backtest_with_execution():
    """取引執行シミュレーション付きバックテスト"""
    
    # 出力ディレクトリ作成
    output_dir = "results/with_execution"
    log_dir = f"{output_dir}/logs"
    chart_dir = f"{output_dir}/charts"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(chart_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("取引執行シミュレーション付きバックテスト")
    logger.log_info("期間: 2022年8月 - 2025年8月（3年間）")
    logger.log_info("=" * 50)
    
    # データ読み込み
    print("\nデータ読み込み中...")
    data_15min = load_multi_year_data(2022, 2025, '15min')
    
    if data_15min.empty:
        logger.log_error("データが見つかりません")
        return None
    
    # 期間フィルタリング
    start_date = pd.Timestamp('2022-08-09')
    end_date = pd.Timestamp('2025-08-09')
    data_15min = data_15min[start_date:end_date]
    
    logger.log_info(f"データサイズ: {len(data_15min)} 行")
    
    # 戦略初期化
    strategy = ProfitTargetStrategy(
        initial_balance=3000000,
        monthly_profit_target=500000,
        scaling_phase='initial'
    )
    
    # 取引執行シミュレーター初期化
    executor = TradeExecutor(
        initial_balance=3000000,
        spread_pips=0.2,
        commission_per_lot=0,
        max_positions=8
    )
    
    # カラム名の確認と正規化
    price_col = 'Close' if 'Close' in data_15min.columns else 'close'
    high_col = 'High' if 'High' in data_15min.columns else 'high'
    low_col = 'Low' if 'Low' in data_15min.columns else 'low'
    
    print("\nバックテスト実行中...")
    
    # プログレス変数
    total_signals = 0
    executed_trades = 0
    
    # メインループ
    for i in range(50, len(data_15min)):
        # 現在のデータウィンドウ
        window_data = data_15min.iloc[:i+1]
        current_time = window_data.index[-1]
        current_price = window_data[price_col].iloc[-1]
        
        # TP/SLチェック（既存ポジション）
        closed_positions = executor.check_positions(current_price, current_time)
        for pos in closed_positions:
            logger.log_info(f"決済: {pos.strategy} - {pos.exit_reason.upper()} - "
                          f"PnL: {pos.pnl_amount:,.0f}円 ({pos.pnl_pips:.1f}pips)")
        
        # 新規シグナル生成（5本ごと）
        if i % 5 == 0 and len(window_data) >= 50:
            # コア戦略シグナル
            signal = strategy.generate_core_signal(window_data)
            
            if signal != 0:
                total_signals += 1
                
                # 取引実行
                position = executor.open_position(
                    signal=signal,
                    price=current_price,
                    lot_size=0.2,  # 初期段階: 0.5 * 0.4 = 0.2ロット
                    stop_loss_pips=10,
                    take_profit_pips=30,
                    timestamp=current_time,
                    strategy='core'
                )
                
                if position:
                    executed_trades += 1
                    logger.log_info(f"新規: CORE - {'BUY' if signal == 1 else 'SELL'} - "
                                  f"価格: {position.entry_price:.3f}")
        
        # 資産額更新
        executor.update_equity(current_price)
        
        # 進捗表示
        if i % 5000 == 0 and i > 0:
            progress = (i / len(data_15min)) * 100
            stats = executor.get_statistics()
            print(f"  進捗: {progress:.1f}% - "
                  f"取引: {stats['total_trades']} - "
                  f"勝率: {stats['win_rate']:.1f}% - "
                  f"残高: {stats['final_balance']:,.0f}円")
    
    # 最終統計
    print("\n" + "=" * 50)
    print("バックテスト完了")
    print("=" * 50)
    
    stats = executor.get_statistics()
    
    # 結果表示
    print(f"\n【基本統計】")
    print(f"初期資金: {stats['initial_balance']:,.0f}円")
    print(f"最終資金: {stats['final_balance']:,.0f}円")
    print(f"総損益: {stats['total_pnl']:,.0f}円 ({stats['total_return']:.2f}%)")
    print(f"ピーク資金: {stats['peak_balance']:,.0f}円")
    
    print(f"\n【取引統計】")
    print(f"シグナル数: {total_signals}")
    print(f"実行取引数: {executed_trades}")
    print(f"決済取引数: {stats['total_trades']}")
    print(f"勝ちトレード: {stats['winning_trades']}")
    print(f"負けトレード: {stats['losing_trades']}")
    print(f"勝率: {stats['win_rate']:.2f}%")
    
    print(f"\n【収益性指標】")
    print(f"平均利益: {stats['avg_win']:,.0f}円")
    print(f"平均損失: {stats['avg_loss']:,.0f}円")
    print(f"プロフィットファクター: {stats['profit_factor']:.2f}")
    print(f"最大ドローダウン: {stats['max_drawdown']:.2f}%")
    
    print(f"\n【連続記録】")
    print(f"最大連続勝利: {stats['max_consecutive_wins']}")
    print(f"最大連続敗北: {stats['max_consecutive_losses']}")
    
    # 月別パフォーマンス
    monthly_perf = executor.get_monthly_performance()
    if not monthly_perf.empty:
        print(f"\n【月別パフォーマンス（直近10ヶ月）】")
        for month, row in monthly_perf.tail(10).iterrows():
            print(f"{month}: {row['trades']}取引 - "
                  f"損益: {row['profit']:,.0f}円 - "
                  f"勝率: {row['win_rate']:.1f}%")
        
        # 月平均
        avg_monthly_profit = monthly_perf['profit'].mean()
        print(f"\n月平均損益: {avg_monthly_profit:,.0f}円")
        print(f"月目標達成率: {(avg_monthly_profit / 500000) * 100:.1f}%")
    
    # グラフ生成
    create_charts(executor, chart_dir)
    
    # 結果保存
    save_results(executor, stats, output_dir)
    
    return executor, stats

def create_charts(executor, output_dir):
    """チャート生成"""
    print("\nチャート生成中...")
    
    # 1. 資産推移グラフ
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 残高推移
    balance_series = pd.Series(executor.balance_history)
    ax1.plot(balance_series, label='残高', color='blue', linewidth=1.5)
    ax1.axhline(y=executor.initial_balance, color='gray', linestyle='--', alpha=0.5, label='初期資金')
    ax1.set_title('資産推移')
    ax1.set_ylabel('残高（円）')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/10000:.0f}万'))
    
    # ドローダウン
    peak = pd.Series(executor.balance_history).expanding().max()
    drawdown = (pd.Series(executor.balance_history) - peak) / peak * 100
    ax2.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
    ax2.set_title('ドローダウン')
    ax2.set_ylabel('ドローダウン（%）')
    ax2.set_xlabel('取引期間')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/equity_curve.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    # 2. 月別損益グラフ
    monthly_perf = executor.get_monthly_performance()
    if not monthly_perf.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = ['green' if x > 0 else 'red' for x in monthly_perf['profit']]
        bars = ax.bar(range(len(monthly_perf)), monthly_perf['profit'], color=colors, alpha=0.7)
        
        # 目標ライン
        ax.axhline(y=500000, color='blue', linestyle='--', alpha=0.5, label='月目標(50万円)')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        ax.set_title('月別損益')
        ax.set_ylabel('損益（円）')
        ax.set_xlabel('月')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/10000:.0f}万'))
        
        # X軸ラベル（3ヶ月ごと）
        months = [str(m) for m in monthly_perf.index]
        ax.set_xticks(range(0, len(months), 3))
        ax.set_xticklabels(months[::3], rotation=45)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/monthly_returns.png', dpi=100, bbox_inches='tight')
        plt.close()
    
    print("チャート生成完了")

def save_results(executor, stats, output_dir):
    """結果を保存"""
    
    # 統計情報をJSON保存
    with open(f'{output_dir}/statistics.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    # 取引履歴をCSV保存
    if executor.trade_history:
        df = pd.DataFrame(executor.trade_history)
        df.to_csv(f'{output_dir}/trade_history.csv', index=False)
    
    # サマリーレポート作成
    create_summary_report(executor, stats, output_dir)
    
    print(f"\n結果を {output_dir} に保存しました")

def create_summary_report(executor, stats, output_dir):
    """サマリーレポート作成"""
    
    monthly_perf = executor.get_monthly_performance()
    
    report = f"""# 取引執行シミュレーション付きバックテスト結果

## テスト期間
- 開始: 2022年8月9日
- 終了: 2025年8月9日
- 期間: 3年間

## 資金状況
- 初期資金: {stats['initial_balance']:,.0f}円
- 最終資金: {stats['final_balance']:,.0f}円
- 総損益: {stats['total_pnl']:,.0f}円
- リターン: {stats['total_return']:.2f}%
- 最大ドローダウン: {stats['max_drawdown']:.2f}%

## 取引統計
- 総取引数: {stats['total_trades']}
- 勝ちトレード: {stats['winning_trades']}
- 負けトレード: {stats['losing_trades']}
- 勝率: {stats['win_rate']:.2f}%

## 収益性指標
- 平均利益: {stats['avg_win']:,.0f}円
- 平均損失: {stats['avg_loss']:,.0f}円
- プロフィットファクター: {stats['profit_factor']:.2f}
- リスクリワード比: {abs(stats['avg_win']/stats['avg_loss']) if stats['avg_loss'] != 0 else 0:.2f}

## 月別パフォーマンス
"""
    
    if not monthly_perf.empty:
        report += f"""
- 月平均損益: {monthly_perf['profit'].mean():,.0f}円
- 月目標達成率: {(monthly_perf['profit'].mean() / 500000) * 100:.1f}%
- プラス月: {len(monthly_perf[monthly_perf['profit'] > 0])}ヶ月
- マイナス月: {len(monthly_perf[monthly_perf['profit'] < 0])}ヶ月
"""
    
    # ファイル保存
    with open(f'{output_dir}/summary_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("取引執行シミュレーション付きバックテスト")
    print("期間: 2022年8月 - 2025年8月")
    print("初期資金: 300万円")
    print("=" * 50)
    
    executor, stats = run_backtest_with_execution()