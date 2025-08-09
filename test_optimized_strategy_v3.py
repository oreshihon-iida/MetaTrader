#!/usr/bin/env python3
"""
最適化版戦略V3のバックテスト（月20万円目標）
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

from src.strategies.profit_target_strategy_v3 import ProfitTargetStrategyV3
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

def run_optimized_backtest():
    """最適化版戦略V3のバックテスト実行"""
    
    # 出力ディレクトリ作成
    output_dir = "results/optimized_strategy_v3"
    log_dir = f"{output_dir}/logs"
    chart_dir = f"{output_dir}/charts"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(chart_dir, exist_ok=True)
    
    logger = Logger(log_dir)
    logger.log_info("=" * 50)
    logger.log_info("最適化版戦略V3バックテスト（月20万円目標）")
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
    
    # 最適化版戦略V3初期化
    strategy = ProfitTargetStrategyV3(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='stable'  # stableフェーズ（ロット1.7倍）でテスト
    )
    
    # 取引執行シミュレーター初期化
    executor = TradeExecutor(
        initial_balance=3000000,
        spread_pips=0.2,
        commission_per_lot=0,
        max_positions=15  # ポジション数をさらに増加
    )
    
    # カラム名の確認と正規化
    price_col = 'Close' if 'Close' in data_15min.columns else 'close'
    high_col = 'High' if 'High' in data_15min.columns else 'high'
    low_col = 'Low' if 'Low' in data_15min.columns else 'low'
    
    print("\nバックテスト実行中...")
    print("最適化内容（V2 → V3）:")
    print("- RSI閾値: 25/75 → 30/70（緩和）")
    print("- BB幅: 2.2σ → 2.0σ（緩和）")
    print("- 時間帯: 9時間 → 12時間（拡大）")
    print("- トレンド: EMA20/50/200 → EMA20/50（緩和）")
    print("- レンジ相場でも取引可能に変更")
    print("- ロットサイズ: stableフェーズ（1.7倍）")
    print("- リスク許容度: 2% → 3%")
    print("- 最大ロット: 2.0 → 3.0")
    print("-" * 50)
    
    # プログレス変数
    total_signals = 0
    executed_trades = 0
    core_signals = 0
    aggressive_signals = 0
    stable_signals = 0
    
    # メインループ
    for i in range(50, len(data_15min)):  # 200→50に緩和
        # 現在のデータウィンドウ
        window_data = data_15min.iloc[:i+1]
        current_time = window_data.index[-1]
        current_price = window_data[price_col].iloc[-1]
        
        # TP/SLチェック（既存ポジション）
        closed_positions = executor.check_positions(current_price, current_time)
        for pos in closed_positions:
            logger.log_info(f"決済: {pos.strategy} - {pos.exit_reason.upper()} - "
                          f"PnL: {pos.pnl_amount:,.0f}円 ({pos.pnl_pips:.1f}pips)")
        
        # 新規シグナル生成（5本ごと、処理軽量化）
        if i % 5 == 0 and len(window_data) >= 50:
            
            # 1. コア戦略シグナル
            core_signal = strategy.generate_core_signal(window_data)
            if core_signal != 0:
                core_signals += 1
                total_signals += 1
                
                # 動的TP/SL計算
                tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                lot_size = strategy.calculate_optimal_lot_size('core', sl_pips)
                
                # 取引実行
                position = executor.open_position(
                    signal=core_signal,
                    price=current_price,
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips,
                    timestamp=current_time,
                    strategy='core_v3'
                )
                
                if position:
                    executed_trades += 1
                    logger.log_info(f"新規: CORE_V3 - {'BUY' if core_signal == 1 else 'SELL'} - "
                                  f"価格: {position.entry_price:.3f} - "
                                  f"Lot: {lot_size} - TP: {tp_pips:.1f}pips - SL: {sl_pips:.1f}pips")
            
            # 2. アグレッシブ戦略（強化版）
            if len(executor.positions) < 8:
                aggressive_signal = strategy.generate_enhanced_aggressive_signal(window_data)
                if aggressive_signal != 0:
                    aggressive_signals += 1
                    total_signals += 1
                    
                    # アグレッシブ用TP/SL（最適化）
                    tp_pips = 18.0  # 15→18に増加
                    sl_pips = 7.0   # 8→7に削減
                    lot_size = strategy.calculate_optimal_lot_size('aggressive', sl_pips)
                    
                    position = executor.open_position(
                        signal=aggressive_signal,
                        price=current_price,
                        lot_size=lot_size,
                        stop_loss_pips=sl_pips,
                        take_profit_pips=tp_pips,
                        timestamp=current_time,
                        strategy='aggressive_v3'
                    )
                    
                    if position:
                        executed_trades += 1
                        logger.log_info(f"新規: AGGRESSIVE_V3 - {'BUY' if aggressive_signal == 1 else 'SELL'} - "
                                      f"価格: {position.entry_price:.3f} - Lot: {lot_size}")
            
            # 3. 安定戦略（最適化版、20本ごと、軽量化）
            if i % 20 == 0 and len(executor.positions) < 5:
                stable_signal = strategy.generate_stable_signal(window_data)
                if stable_signal != 0:
                    stable_signals += 1
                    total_signals += 1
                    
                    # 安定戦略用TP/SL（長期保有）
                    tp_pips = 40.0
                    sl_pips = 15.0
                    lot_size = strategy.calculate_optimal_lot_size('stable', sl_pips)
                    
                    position = executor.open_position(
                        signal=stable_signal,
                        price=current_price,
                        lot_size=lot_size,
                        stop_loss_pips=sl_pips,
                        take_profit_pips=tp_pips,
                        timestamp=current_time,
                        strategy='stable_v3'
                    )
                    
                    if position:
                        executed_trades += 1
                        logger.log_info(f"新規: STABLE_V3 - {'BUY' if stable_signal == 1 else 'SELL'} - "
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
    print("最適化版V3バックテスト完了")
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
    create_optimized_charts(executor, chart_dir)
    
    # 結果保存
    save_optimized_results(executor, stats, output_dir, {
        'core_signals': core_signals,
        'aggressive_signals': aggressive_signals,
        'stable_signals': stable_signals
    })
    
    return executor, stats

def create_optimized_charts(executor, output_dir):
    """最適化版のチャート生成"""
    print("\nチャート生成中...")
    
    # 資産推移と目標ライン
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    balance_series = pd.Series(executor.balance_history)
    
    # 月20万円の理想ライン（より細かく）
    months = len(balance_series) / (30 * 24 * 4)  # 15分足から月数を概算
    ideal_line = [3000000 + (200000 * i / 12) for i in range(int(months * 12) + 1)]
    ideal_x = np.linspace(0, len(balance_series), len(ideal_line))
    
    ax1.plot(balance_series, label='V3 Optimized Balance', color='green', linewidth=2)
    ax1.plot(ideal_x, ideal_line, label='Target (200K/month)', color='red', linestyle='--', alpha=0.7)
    ax1.axhline(y=executor.initial_balance, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Optimized Strategy V3 - Balance vs Target', fontweight='bold')
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
    plt.savefig(f'{output_dir}/optimized_v3_results.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    print("チャート生成完了")

def save_optimized_results(executor, stats, output_dir, signal_stats):
    """最適化版の結果を保存"""
    
    # 統計情報をJSON保存
    enhanced_stats = {**stats, **signal_stats}
    with open(f'{output_dir}/statistics.json', 'w') as f:
        json.dump(enhanced_stats, f, indent=2, default=str)
    
    # 取引履歴をCSV保存
    if executor.trade_history:
        df = pd.DataFrame(executor.trade_history)
        df.to_csv(f'{output_dir}/trade_history.csv', index=False)
    
    # サマリーレポート作成
    create_optimized_summary_report(executor, stats, output_dir, signal_stats)
    
    print(f"\n結果を {output_dir} に保存しました")

def create_optimized_summary_report(executor, stats, output_dir, signal_stats):
    """最適化版サマリーレポート作成"""
    
    monthly_perf = executor.get_monthly_performance()
    avg_monthly_profit = monthly_perf['profit'].mean() if not monthly_perf.empty else 0
    months_achieving_target = len(monthly_perf[monthly_perf['profit'] >= 200000]) if not monthly_perf.empty else 0
    
    report = f"""# 最適化版戦略V3バックテスト結果

## テスト期間
- 開始: 2022年8月9日
- 終了: 2025年8月9日
- 期間: 3年間

## V3最適化内容
- RSI閾値: 30/70（V2から緩和）
- ボリンジャーバンド: 2.0σ（V2から緩和）
- 時間帯フィルター: 12時間（V2の9時間から拡大）
- トレンドフィルター: EMA20/50のみ（EMA200除外）
- レンジ相場でも取引可能
- ロットサイズ: stableフェーズ（1.7倍）
- リスク許容度: 3%（2%から増加）
- 最大ロット: 3.0（2.0から増加）

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
- 総シグナル数: {sum(signal_stats.values())}

## 収益性指標
- 平均利益: {stats['avg_win']:,.0f}円
- 平均損失: {stats['avg_loss']:,.0f}円
- プロフィットファクター: {stats['profit_factor']:.2f}
- リスクリワード比: {abs(stats['avg_win']/stats['avg_loss']) if stats['avg_loss'] != 0 else 0:.2f}

## 目標達成状況
- 月平均損益: {avg_monthly_profit:,.0f}円
- 月20万円達成率: {(avg_monthly_profit / 200000) * 100:.1f}%
- 目標達成月数: {months_achieving_target}/{len(monthly_perf) if not monthly_perf.empty else 0}ヶ月
"""
    
    # ファイル保存
    with open(f'{output_dir}/summary_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("最適化版戦略V3バックテスト")
    print("月間目標: 20万円")
    print("初期資金: 300万円")
    print("最適化: フィルター緩和 + ロット増加")
    print("=" * 50)
    
    executor, stats = run_optimized_backtest()