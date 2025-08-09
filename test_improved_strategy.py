#!/usr/bin/env python3
"""
改良版戦略のバックテスト（月20万円目標）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 日本語フォント設定
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2
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

def run_improved_backtest():
    """改良版戦略のバックテスト実行"""
    
    # 出力ディレクトリ作成
    output_dir = "results/improved_strategy"
    log_dir = f"{output_dir}/logs"
    chart_dir = f"{output_dir}/charts"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(chart_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("改良版戦略バックテスト（月20万円目標）")
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
    
    # 改良版戦略初期化
    strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,  # 月20万円目標
        scaling_phase='growth'  # growthフェーズ（ロット1.0倍）でテスト
    )
    
    # 取引執行シミュレーター初期化
    executor = TradeExecutor(
        initial_balance=3000000,
        spread_pips=0.2,
        commission_per_lot=0,
        max_positions=10  # 最大ポジション数を増加
    )
    
    # カラム名の確認と正規化
    price_col = 'Close' if 'Close' in data_15min.columns else 'close'
    high_col = 'High' if 'High' in data_15min.columns else 'high'
    low_col = 'Low' if 'Low' in data_15min.columns else 'low'
    
    print("\nバックテスト実行中...")
    print("改良内容:")
    print("- RSI閾値: 25/75（より強いシグナル）")
    print("- BB幅: 2.2σ（偽シグナル削減）")
    print("- 時間帯フィルター: 東京/ロンドン/NY時間")
    print("- トレンドフィルター: EMA20/50/200")
    print("- 動的TP/SL: ATRベース")
    print("-" * 50)
    
    # プログレス変数
    total_signals = 0
    executed_trades = 0
    skipped_by_time = 0
    skipped_by_trend = 0
    
    # メインループ
    for i in range(200, len(data_15min)):  # 200本必要（EMA200のため）
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
        if i % 5 == 0 and len(window_data) >= 200:
            # 時間帯チェック
            if not strategy.is_good_trading_time(current_time):
                skipped_by_time += 1
                continue
            
            # トレンドチェック
            trend = strategy.check_trend_alignment(window_data)
            if trend == 0:
                skipped_by_trend += 1
                continue
            
            # コア戦略シグナル
            signal = strategy.generate_core_signal(window_data)
            
            if signal != 0:
                total_signals += 1
                
                # 動的TP/SL計算
                tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                
                # ロットサイズ計算
                lot_size = strategy.calculate_optimal_lot_size('core', sl_pips)
                
                # 取引実行
                position = executor.open_position(
                    signal=signal,
                    price=current_price,
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips,
                    timestamp=current_time,
                    strategy='core_v2'
                )
                
                if position:
                    executed_trades += 1
                    logger.log_info(f"新規: CORE_V2 - {'BUY' if signal == 1 else 'SELL'} - "
                                  f"価格: {position.entry_price:.3f} - "
                                  f"Lot: {lot_size} - TP: {tp_pips:.1f}pips - SL: {sl_pips:.1f}pips")
            
            # アグレッシブ戦略も追加（取引数増加のため）
            if len(executor.positions) < 5:  # ポジション数制限
                aggressive_signal = strategy.generate_aggressive_signal(window_data)
                if aggressive_signal != 0:
                    total_signals += 1
                    
                    # アグレッシブ用の短めTP/SL
                    tp_pips = 15.0
                    sl_pips = 8.0
                    lot_size = strategy.calculate_optimal_lot_size('aggressive', sl_pips)
                    
                    position = executor.open_position(
                        signal=aggressive_signal,
                        price=current_price,
                        lot_size=lot_size,
                        stop_loss_pips=sl_pips,
                        take_profit_pips=tp_pips,
                        timestamp=current_time,
                        strategy='aggressive_v2'
                    )
                    
                    if position:
                        executed_trades += 1
                        logger.log_info(f"新規: AGGRESSIVE_V2 - {'BUY' if aggressive_signal == 1 else 'SELL'} - "
                                      f"価格: {position.entry_price:.3f} - Lot: {lot_size}")
        
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
    print(f"最大ドローダウン: {stats['max_drawdown']:.2f}%")
    
    print(f"\n【取引統計】")
    print(f"シグナル数: {total_signals}")
    print(f"実行取引数: {executed_trades}")
    print(f"決済取引数: {stats['total_trades']}")
    print(f"勝ちトレード: {stats['winning_trades']}")
    print(f"負けトレード: {stats['losing_trades']}")
    print(f"勝率: {stats['win_rate']:.2f}%")
    
    print(f"\n【フィルタリング統計】")
    print(f"時間帯フィルター除外: {skipped_by_time}回")
    print(f"トレンドフィルター除外: {skipped_by_trend}回")
    
    print(f"\n【収益性指標】")
    print(f"平均利益: {stats['avg_win']:,.0f}円")
    print(f"平均損失: {stats['avg_loss']:,.0f}円")
    print(f"リスクリワード比: {abs(stats['avg_win']/stats['avg_loss']) if stats['avg_loss'] != 0 else 0:.2f}")
    print(f"プロフィットファクター: {stats['profit_factor']:.2f}")
    
    # 月別パフォーマンス
    monthly_perf = executor.get_monthly_performance()
    if not monthly_perf.empty:
        print(f"\n【月別パフォーマンス（直近10ヶ月）】")
        for month, row in monthly_perf.tail(10).iterrows():
            profit_color = "+" if row['profit'] > 0 else ""
            target_achieved = "[OK]" if row['profit'] >= 200000 else "[NG]"
            print(f"{month}: {row['trades']}取引 - "
                  f"損益: {profit_color}{row['profit']:,.0f}円 - "
                  f"勝率: {row['win_rate']:.1f}% {target_achieved}")
        
        # 月平均と目標達成率
        avg_monthly_profit = monthly_perf['profit'].mean()
        months_achieving_target = len(monthly_perf[monthly_perf['profit'] >= 200000])
        print(f"\n月平均損益: {avg_monthly_profit:,.0f}円")
        print(f"月20万円達成率: {(avg_monthly_profit / 200000) * 100:.1f}%")
        print(f"目標達成月数: {months_achieving_target}/{len(monthly_perf)}ヶ月")
    
    # グラフ生成
    create_improved_charts(executor, chart_dir)
    
    # 結果保存
    save_improved_results(executor, stats, output_dir)
    
    return executor, stats

def create_improved_charts(executor, output_dir):
    """改良版のチャート生成"""
    print("\nチャート生成中...")
    
    # 1. 資産推移と目標ライン
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    balance_series = pd.Series(executor.balance_history)
    months = len(balance_series) / (20 * 24 * 2)  # 15分足から月数を概算
    
    # 月20万円の理想ライン
    ideal_line = [3000000 + (200000 * i) for i in range(int(months) + 1)]
    ideal_x = np.linspace(0, len(balance_series), len(ideal_line))
    
    ax1.plot(balance_series, label='Actual Balance', color='blue', linewidth=1.5)
    ax1.plot(ideal_x, ideal_line, label='Target (200K/month)', color='green', linestyle='--', alpha=0.7)
    ax1.axhline(y=executor.initial_balance, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Balance Progress vs Target')
    ax1.set_ylabel('Balance (JPY)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/10000:.0f}'))
    
    # ドローダウン
    peak = pd.Series(executor.balance_history).expanding().max()
    drawdown = (pd.Series(executor.balance_history) - peak) / peak * 100
    ax2.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
    ax2.set_title('Drawdown')
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_xlabel('Trading Period')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/improved_equity_curve.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    print("チャート生成完了")

def save_improved_results(executor, stats, output_dir):
    """改良版の結果を保存"""
    
    # 統計情報をJSON保存
    with open(f'{output_dir}/statistics.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    # 取引履歴をCSV保存
    if executor.trade_history:
        df = pd.DataFrame(executor.trade_history)
        df.to_csv(f'{output_dir}/trade_history.csv', index=False)
    
    # サマリーレポート作成
    create_improved_summary_report(executor, stats, output_dir)
    
    print(f"\n結果を {output_dir} に保存しました")

def create_improved_summary_report(executor, stats, output_dir):
    """改良版サマリーレポート作成"""
    
    monthly_perf = executor.get_monthly_performance()
    avg_monthly_profit = monthly_perf['profit'].mean() if not monthly_perf.empty else 0
    
    report = f"""# 改良版戦略バックテスト結果

## テスト期間
- 開始: 2022年8月9日
- 終了: 2025年8月9日
- 期間: 3年間

## 改良内容
- RSI閾値: 25/75（強化）
- ボリンジャーバンド: 2.2σ
- 時間帯フィルター: 東京/ロンドン/NY時間
- トレンドフィルター: EMA20/50/200
- 動的TP/SL: ATRベース

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

## 目標達成状況
- 月平均損益: {avg_monthly_profit:,.0f}円
- 月20万円達成率: {(avg_monthly_profit / 200000) * 100:.1f}%
"""
    
    # ファイル保存
    with open(f'{output_dir}/summary_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("改良版戦略バックテスト")
    print("月間目標: 20万円")
    print("初期資金: 300万円")
    print("=" * 50)
    
    executor, stats = run_improved_backtest()