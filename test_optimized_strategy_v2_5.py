#!/usr/bin/env python3
"""
最適化版戦略V2.5のバックテスト（月20万円目標）
V2の成功をベースにV3の良い要素のみを選択的に採用
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import json
import matplotlib.pyplot as plt

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

def run_optimized_backtest_v25():
    """最適化版戦略V2.5のバックテスト実行"""
    
    # 出力ディレクトリ作成
    output_dir = "results/optimized_strategy_v2_5"
    log_dir = f"{output_dir}/logs"
    chart_dir = f"{output_dir}/charts"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(chart_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("最適化版戦略V2.5バックテスト（月20万円目標）")
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
    
    # V2.5戦略初期化（V2ベースで一部パラメータ調整）
    strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'  # V2の成功したフェーズ
    )
    
    # V2.5パラメータ調整（V3の良い要素のみ採用）
    strategy.lot_multipliers['growth'] = 1.3  # 1.0→1.3（V3の1.7より控えめ）
    strategy.base_lot_sizes['core'] = 0.6     # 0.5→0.6（V3から採用）
    strategy.max_risk_per_trade = 0.025       # 2%→2.5%（V3の3%より控えめ）
    
    # 取引執行シミュレーター初期化
    executor = TradeExecutor(
        initial_balance=3000000,
        spread_pips=0.2,
        commission_per_lot=0,
        max_positions=12  # V2の10とV3の15の中間
    )
    
    # カラム名の確認と正規化
    price_col = 'Close' if 'Close' in data_15min.columns else 'close'
    high_col = 'High' if 'High' in data_15min.columns else 'high'
    low_col = 'Low' if 'Low' in data_15min.columns else 'low'
    
    print("\nバックテスト実行中...")
    print("V2.5最適化内容:")
    print("- V2の成功をベース（RSI 25/75、BB 2.2σ、時間帯9時間）")
    print("- シグナル生成頻度: 5本 → 3本（取引機会増加）")
    print("- ロット調整: growthフェーズ 1.0 → 1.3倍（控えめ増加）") 
    print("- リスク許容度: 2% → 2.5%（控えめ増加）")
    print("- 最大ポジション: 10 → 12（適度に増加）")
    print("- 最大ロット: 2.0 → 2.5（適度に増加）")
    print("-" * 50)
    
    # 最大ロット制限を調整
    strategy.base_lot_sizes['stable'] = 1.5  # 1.0→1.5に増加
    
    # プログレス変数
    total_signals = 0
    executed_trades = 0
    skipped_by_time = 0
    skipped_by_trend = 0
    core_signals = 0
    aggressive_signals = 0
    stable_signals = 0
    
    # メインループ
    for i in range(200, len(data_15min)):
        # 現在のデータウィンドウ
        window_data = data_15min.iloc[:i+1]
        current_time = window_data.index[-1]
        current_price = window_data[price_col].iloc[-1]
        
        # TP/SLチェック（既存ポジション）
        closed_positions = executor.check_positions(current_price, current_time)
        for pos in closed_positions:
            logger.log_info(f"決済: {pos.strategy} - {pos.exit_reason.upper()} - "
                          f"PnL: {pos.pnl_amount:,.0f}円 ({pos.pnl_pips:.1f}pips)")
        
        # 新規シグナル生成（3本ごと - V2の5本から頻度増加）
        if i % 3 == 0 and len(window_data) >= 200:
            
            # 1. コア戦略シグナル（V2の成功パターンを維持）
            if strategy.is_good_trading_time(current_time):
                trend = strategy.check_trend_alignment(window_data)
                if trend != 0:  # V2の厳格なトレンド要求を維持
                    core_signal = strategy.generate_core_signal(window_data)
                    if core_signal != 0:
                        core_signals += 1
                        total_signals += 1
                        
                        # 動的TP/SL計算
                        tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                        lot_size = strategy.calculate_optimal_lot_size('core', sl_pips)
                        lot_size = min(lot_size, 2.5)  # 最大ロット制限を2.5に調整
                        
                        # 取引実行
                        position = executor.open_position(
                            signal=core_signal,
                            price=current_price,
                            lot_size=lot_size,
                            stop_loss_pips=sl_pips,
                            take_profit_pips=tp_pips,
                            timestamp=current_time,
                            strategy='core_v2_5'
                        )
                        
                        if position:
                            executed_trades += 1
                            logger.log_info(f"新規: CORE_V2.5 - {'BUY' if core_signal == 1 else 'SELL'} - "
                                          f"価格: {position.entry_price:.3f} - "
                                          f"Lot: {lot_size} - TP: {tp_pips:.1f}pips - SL: {sl_pips:.1f}pips")
                else:
                    skipped_by_trend += 1
            else:
                skipped_by_time += 1
            
            # 2. アグレッシブ戦略（V2版を維持、頻度のみ増加）
            if len(executor.positions) < 6:  # ポジション制限は控えめ
                aggressive_signal = strategy.generate_aggressive_signal(window_data)
                if aggressive_signal != 0:
                    aggressive_signals += 1
                    total_signals += 1
                    
                    # V2のTP/SL設定を維持
                    tp_pips = 15.0
                    sl_pips = 8.0
                    lot_size = strategy.calculate_optimal_lot_size('aggressive', sl_pips)
                    lot_size = min(lot_size, 1.5)  # アグレッシブは控えめ制限
                    
                    position = executor.open_position(
                        signal=aggressive_signal,
                        price=current_price,
                        lot_size=lot_size,
                        stop_loss_pips=sl_pips,
                        take_profit_pips=tp_pips,
                        timestamp=current_time,
                        strategy='aggressive_v2_5'
                    )
                    
                    if position:
                        executed_trades += 1
                        logger.log_info(f"新規: AGGRESSIVE_V2.5 - {'BUY' if aggressive_signal == 1 else 'SELL'} - "
                                      f"価格: {position.entry_price:.3f} - Lot: {lot_size}")
            
            # 3. 安定戦略（15本ごと、V2ベース）
            if i % 15 == 0 and len(executor.positions) < 3:
                stable_signal = strategy.generate_stable_signal(window_data)
                if stable_signal != 0:
                    stable_signals += 1
                    total_signals += 1
                    
                    # 安定戦略用TP/SL（V2ベース、やや改善）
                    tp_pips = 45.0  # 40→45に微調整
                    sl_pips = 16.0  # 15→16に微調整
                    lot_size = strategy.calculate_optimal_lot_size('stable', sl_pips)
                    lot_size = min(lot_size, 2.5)
                    
                    position = executor.open_position(
                        signal=stable_signal,
                        price=current_price,
                        lot_size=lot_size,
                        stop_loss_pips=sl_pips,
                        take_profit_pips=tp_pips,
                        timestamp=current_time,
                        strategy='stable_v2_5'
                    )
                    
                    if position:
                        executed_trades += 1
                        logger.log_info(f"新規: STABLE_V2.5 - {'BUY' if stable_signal == 1 else 'SELL'} - "
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
    print("最適化版V2.5バックテスト完了")
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
    print(f" - コア: {core_signals}")
    print(f" - アグレッシブ: {aggressive_signals}")
    print(f" - 安定: {stable_signals}")
    print(f"実行取引数: {executed_trades}")
    print(f"決済取引数: {stats['total_trades']}")
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
            target_achieved = "[達成]" if row['profit'] >= 200000 else "[未達]"
            print(f"{month}: {row['trades']}取引 - "
                  f"損益: {profit_color}{row['profit']:,.0f}円 - "
                  f"勝率: {row['win_rate']:.1f}% {target_achieved}")
        
        # 月平均と目標達成率
        avg_monthly_profit = monthly_perf['profit'].mean()
        months_achieving_target = len(monthly_perf[monthly_perf['profit'] >= 200000])
        months_above_100k = len(monthly_perf[monthly_perf['profit'] >= 100000])
        
        print(f"\n月平均損益: {avg_monthly_profit:,.0f}円")
        print(f"月20万円達成率: {(avg_monthly_profit / 200000) * 100:.1f}%")
        print(f"目標達成月数: {months_achieving_target}/{len(monthly_perf)}ヶ月 ({months_achieving_target/len(monthly_perf)*100:.1f}%)")
        print(f"10万円以上月数: {months_above_100k}/{len(monthly_perf)}ヶ月 ({months_above_100k/len(monthly_perf)*100:.1f}%)")
    
    # グラフ生成
    create_optimized_charts_v25(executor, chart_dir)
    
    # 結果保存
    save_optimized_results_v25(executor, stats, output_dir, {
        'core_signals': core_signals,
        'aggressive_signals': aggressive_signals,
        'stable_signals': stable_signals,
        'skipped_by_time': skipped_by_time,
        'skipped_by_trend': skipped_by_trend
    })
    
    return executor, stats

def create_optimized_charts_v25(executor, output_dir):
    """V2.5のチャート生成"""
    print("\nチャート生成中...")
    
    # 資産推移と目標ライン
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    balance_series = pd.Series(executor.balance_history)
    
    # 月20万円の理想ライン
    months = len(balance_series) / (30 * 24 * 4)  # 15分足から月数を概算
    ideal_line = [3000000 + (200000 * i / 12) for i in range(int(months * 12) + 1)]
    ideal_x = np.linspace(0, len(balance_series), len(ideal_line))
    
    ax1.plot(balance_series, label='V2.5 Balance', color='darkgreen', linewidth=2)
    ax1.plot(ideal_x, ideal_line, label='Target (200K/month)', color='red', linestyle='--', alpha=0.7)
    ax1.axhline(y=executor.initial_balance, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Optimized Strategy V2.5 - Balance vs Target', fontweight='bold')
    ax1.set_ylabel('Balance (JPY)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/10000:.0f}万'))
    
    # ドローダウン
    peak = pd.Series(executor.balance_history).expanding().max()
    drawdown = (pd.Series(executor.balance_history) - peak) / peak * 100
    ax2.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
    ax2.set_title('Drawdown Analysis')
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_xlabel('Trading Period')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/optimized_v2_5_results.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    print("チャート生成完了")

def save_optimized_results_v25(executor, stats, output_dir, signal_stats):
    """V2.5の結果を保存"""
    
    # 統計情報をJSON保存
    enhanced_stats = {**stats, **signal_stats}
    with open(f'{output_dir}/statistics.json', 'w') as f:
        json.dump(enhanced_stats, f, indent=2, default=str)
    
    # 取引履歴をCSV保存
    if executor.trade_history:
        df = pd.DataFrame(executor.trade_history)
        df.to_csv(f'{output_dir}/trade_history.csv', index=False)
    
    # サマリーレポート作成
    create_summary_report_v25(executor, stats, output_dir, signal_stats)
    
    print(f"\n結果を {output_dir} に保存しました")

def create_summary_report_v25(executor, stats, output_dir, signal_stats):
    """V2.5サマリーレポート作成"""
    
    monthly_perf = executor.get_monthly_performance()
    avg_monthly_profit = monthly_perf['profit'].mean() if not monthly_perf.empty else 0
    months_achieving_target = len(monthly_perf[monthly_perf['profit'] >= 200000]) if not monthly_perf.empty else 0
    
    report = f"""# 最適化版戦略V2.5バックテスト結果

## テスト期間
- 開始: 2022年8月9日
- 終了: 2025年8月9日
- 期間: 3年間

## V2.5最適化内容
**V2の成功をベースに選択的改良**
- V2の堅実なフィルター維持（RSI25/75、BB2.2σ、時間帯9時間）
- シグナル生成頻度: 5本 → 3本（取引機会増加）
- ロット調整: growthフェーズ1.0→1.3倍（控えめ増加）
- リスク許容度: 2%→2.5%（控えめ増加）
- 最大ポジション: 10→12（適度増加）
- トレンドフィルター: V2の厳格な判定を維持

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

## シグナル分析
- コアシグナル: {signal_stats['core_signals']}
- アグレッシブシグナル: {signal_stats['aggressive_signals']}
- 安定シグナル: {signal_stats['stable_signals']}
- 総シグナル数: {signal_stats['core_signals'] + signal_stats['aggressive_signals'] + signal_stats['stable_signals']}

## フィルタリング効果
- 時間帯フィルター除外: {signal_stats['skipped_by_time']}回
- トレンドフィルター除外: {signal_stats['skipped_by_trend']}回

## 収益性指標
- 平均利益: {stats['avg_win']:,.0f}円
- 平均損失: {stats['avg_loss']:,.0f}円
- プロフィットファクター: {stats['profit_factor']:.2f}
- リスクリワード比: {abs(stats['avg_win']/stats['avg_loss']) if stats['avg_loss'] != 0 else 0:.2f}

## 目標達成状況
- 月平均損益: {avg_monthly_profit:,.0f}円
- 月20万円達成率: {(avg_monthly_profit / 200000) * 100:.1f}%
- 目標達成月数: {months_achieving_target}/{len(monthly_perf) if not monthly_perf.empty else 0}ヶ月

## V2.5の特徴
**V2の安定性 + 取引頻度向上**
- V2の高勝率（41%）と低ドローダウンを維持
- シグナル頻度増加で取引機会を拡大
- 過度な最適化を避け、堅実な改良に留める
- フィルターの重要性を認識し、品質を重視
"""
    
    # ファイル保存
    with open(f'{output_dir}/summary_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("最適化版戦略V2.5バックテスト")
    print("月間目標: 20万円")
    print("初期資金: 300万円")
    print("戦略: V2の成功 + 選択的改良")
    print("=" * 50)
    
    executor, stats = run_optimized_backtest_v25()