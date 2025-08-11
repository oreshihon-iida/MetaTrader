#!/usr/bin/env python3
"""
Enhanced Trinity ML 段階1改善版 3年間フルテスト
2022-2024年の全期間データで正確な月別結果を出力
"""

import pandas as pd
import sys
import os
from datetime import datetime
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.enhanced_trinity_ml_stage1 import EnhancedTrinityMLStage1
from src.backtest.trade_executor import TradeExecutor

def main():
    print('=== Enhanced Trinity ML 段階1改善版 3年間フルテスト ===')
    print('期間: 2022-2024年（3年間完全データ）')
    print('目標: 月5万円達成への最終調整')
    print()

    # 3年間データ読み込み
    data_files = []
    for year in [2022, 2023, 2024]:
        file_path = f'data/processed/15min/{year}/USDJPY_15min_{year}.csv'
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
            data_files.append(df)
            print(f'{year}年データ読み込み: {len(df):,}レコード')
        else:
            print(f'{year}年データが見つかりません: {file_path}')

    if not data_files:
        print('データファイルが見つかりません')
        return

    data = pd.concat(data_files)
    print(f'\n総データ: {len(data):,}レコード')
    print(f'期間: {data.index.min()} - {data.index.max()}')
    print()
    
    # 段階1改善版戦略初期化
    print('Enhanced Trinity ML 段階1改善版戦略初期化中...')
    strategy = EnhancedTrinityMLStage1(
        base_confidence_threshold=0.10,  # 0.15から緩和
        prediction_horizon=4,
        max_cores=24,
        sentiment_weight=0.25,           # 0.20から強化
        sentiment_hours_back=12,
        training_size=1500,
        processing_interval=4
    )
    
    # TradeExecutor初期化（レバレッジ1倍、追証絶対なし）
    executor = TradeExecutor(
        initial_balance=3000000,    # 300万円
        margin_rate=1.0,           # レバレッジ1倍（100%証拠金率）
        max_positions=15           # システム最大15ポジション（動的調整）
    )
    print(f'初期資本: {executor.initial_balance:,}円')
    print(f'レバレッジ: 1倍（追証リスク: ゼロ）')
    print(f'証拠金使用率: 80%')
    print()
    
    # シグナル生成
    print('シグナル生成開始...')
    signals = strategy.generate_signals(data)
    
    signal_count = (signals['Signal'] != 0).sum()
    print(f'生成シグナル数: {signal_count}')
    print()
    
    # 月別統計用データ構造
    monthly_stats = defaultdict(lambda: {
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'pnl': 0.0,
        'win_pips': 0.0,
        'loss_pips': 0.0
    })
    
    # 取引実行
    print('3年間フルバックテスト実行中...')
    total_trades = 0
    signal_points = signals[signals['Signal'] != 0]
    
    for idx, row in signal_points.iterrows():
        if idx not in data.index:
            continue
            
        current_price = data.loc[idx, 'Close']
        signal = int(row['Signal'])
        tp_pips = row.get('TP_pips', 15)  # 改善版
        sl_pips = row.get('SL_pips', 8)   # 改善版
        
        if pd.isna(tp_pips):
            tp_pips = 15
        if pd.isna(sl_pips):
            sl_pips = 8
        
        # ポジション管理
        executor.check_positions(current_price, idx)
        
        # 動的最大ポジション制御（価格連動）
        current_positions = len([p for p in executor.positions.values() if p.status.value == 'open'])
        max_positions_now = executor.calculate_max_positions(0.01, current_price)
        if current_positions >= max_positions_now:
            continue
            
        # ポジションサイズ計算（実際の価格使用）
        max_lot_size = executor.calculate_max_lot_size(current_price)
        if max_lot_size <= 0:
            continue
            
        lot_size = min(0.01, max_lot_size)  # 0.01ロット（300万円・レバレッジ1倍に適正化）
        
        # 取引実行
        position = executor.open_position(
            signal=signal,
            price=current_price,
            lot_size=lot_size,
            stop_loss_pips=sl_pips,
            take_profit_pips=tp_pips,
            timestamp=idx,
            strategy='Enhanced_Trinity_Stage1_Improved'
        )
        
        if position:
            total_trades += 1
        
        executor.update_equity(current_price)
    
    # 最終決済
    final_price = data['Close'].iloc[-1]
    final_timestamp = data.index[-1]
    
    open_positions = [p for p in executor.positions.values() if p.status.value == 'open']
    for position in open_positions:
        position.close(final_price, final_timestamp, 'final_close')
        executor.balance += position.pnl_amount
    
    # 月別統計の集計
    for position in executor.closed_positions:
        if position.exit_time:
            year_month = position.exit_time.strftime('%Y-%m')
            monthly_stats[year_month]['trades'] += 1
            
            if position.pnl_amount > 0:
                monthly_stats[year_month]['wins'] += 1
                monthly_stats[year_month]['win_pips'] += position.pnl_pips
            else:
                monthly_stats[year_month]['losses'] += 1
                monthly_stats[year_month]['loss_pips'] += abs(position.pnl_pips)
                
            monthly_stats[year_month]['pnl'] += position.pnl_amount
    
    # 結果表示
    print('\n' + '=' * 100)
    print('Enhanced Trinity ML 段階1改善版 - 3年間フル月別パフォーマンス')
    print('=' * 100)
    print()
    
    print(f"{'年月':<8} {'取引数':<6} {'勝数':<6} {'負数':<6} {'勝率%':<8} {'PF':<8} {'損益額':<12} {'備考'}")
    print('-' * 100)
    
    # 年月順にソートして表示
    total_pnl = 0
    total_trades_all = 0
    total_wins_all = 0
    total_losses_all = 0
    months_with_trades = 0
    
    # 全期間のすべての月を網羅
    start_date = data.index.min()
    end_date = data.index.max()
    
    # 月別データを年月順で生成
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        year_month = current_date.strftime('%Y-%m')
        
        if year_month in monthly_stats:
            stats = monthly_stats[year_month]
            trades = stats['trades']
            wins = stats['wins']
            losses = stats['losses']
            pnl = stats['pnl']
            
            win_rate = (wins / trades * 100) if trades > 0 else 0
            
            # プロフィットファクター計算
            total_win_pips = stats['win_pips']
            total_loss_pips = stats['loss_pips']
            pf = (total_win_pips / total_loss_pips) if total_loss_pips > 0 else 999.0 if total_win_pips > 0 else 0.0
            
            remark = ""
            if trades == 0:
                remark = "取引なし"
            elif win_rate >= 60:
                remark = "高勝率"
            elif pnl >= 50000:
                remark = "目標達成"
            elif pnl < -100000:
                remark = "大損失月"
            
            print(f"{year_month:<8} {trades:<6} {wins:<6} {losses:<6} {win_rate:<8.1f} {pf:<8.2f} {pnl:<12,.0f} {remark}")
            
            total_pnl += pnl
            total_trades_all += trades
            total_wins_all += wins
            total_losses_all += losses
            months_with_trades += 1
        else:
            # 取引がなかった月
            print(f"{year_month:<8} {'0':<6} {'0':<6} {'0':<6} {'0.0':<8} {'0.00':<8} {'0':<12} 取引なし")
        
        # 次の月へ
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    print('-' * 100)
    
    # 総計表示
    overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0
    monthly_avg = total_pnl / months_with_trades if months_with_trades > 0 else 0
    
    # 36ヶ月での平均も計算
    total_months = 36  # 3年間
    monthly_avg_36months = total_pnl / total_months
    
    print(f"{'合計':<8} {total_trades_all:<6} {total_wins_all:<6} {total_losses_all:<6} {overall_win_rate:<8.1f} {'-':<8} {total_pnl:<12,.0f}")
    print()
    
    print(f'3年間フル統計:')
    print(f'  総取引数: {total_trades_all}')
    print(f'  総勝率: {overall_win_rate:.1f}%')
    print(f'  総損益: {total_pnl:,.0f}円')
    print(f'  取引があった月数: {months_with_trades}')
    print(f'  月平均損益（取引月のみ）: {monthly_avg:,.0f}円')
    print(f'  月平均損益（全36ヶ月）: {monthly_avg_36months:,.0f}円')
    
    # 最終評価
    print(f'\n最終評価:')
    target = 50000
    achievement_rate = (monthly_avg_36months / target) * 100
    
    print(f'目標月次利益: {target:,}円')
    print(f'実際月次利益: {monthly_avg_36months:,.0f}円')
    print(f'達成率: {achievement_rate:.1f}%')
    
    if achievement_rate >= 100:
        print('SUCCESS: 段階1改善版で月5万円目標達成！')
        print('段階2（月8万円目標）への準備完了です。')
    elif achievement_rate >= 80:
        print('ALMOST: 目標にあと少し。微調整で達成可能です。')
    elif achievement_rate >= 50:
        print('PROGRESS: 大幅改善達成。さらなる調整で目標達成可能。')
    else:
        print('INSUFFICIENT: さらなる改善が必要です。')
    
    # ファイルに詳細結果保存
    result_file = f'stage1_improved_3year_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write('Enhanced Trinity ML 段階1改善版 3年間フルテスト結果\n')
        f.write(f'実行日時: {datetime.now()}\n')
        f.write(f'期間: {data.index.min()} - {data.index.max()}\n')
        f.write(f'総データ数: {len(data):,}レコード\n\n')
        
        f.write('月別詳細結果:\n')
        f.write(f"{'年月':<8} {'取引数':<6} {'勝数':<6} {'負数':<6} {'勝率%':<8} {'PF':<8} {'損益額':<12} {'備考'}\n")
        f.write('-' * 100 + '\n')
        
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            year_month = current_date.strftime('%Y-%m')
            if year_month in monthly_stats:
                stats = monthly_stats[year_month]
                trades = stats['trades']
                wins = stats['wins']
                losses = stats['losses']
                pnl = stats['pnl']
                win_rate = (wins / trades * 100) if trades > 0 else 0
                total_win_pips = stats['win_pips']
                total_loss_pips = stats['loss_pips']
                pf = (total_win_pips / total_loss_pips) if total_loss_pips > 0 else 999.0 if total_win_pips > 0 else 0.0
                remark = ""
                if trades == 0:
                    remark = "取引なし"
                elif win_rate >= 60:
                    remark = "高勝率"
                elif pnl >= 50000:
                    remark = "目標達成"
                elif pnl < -100000:
                    remark = "大損失月"
                f.write(f"{year_month:<8} {trades:<6} {wins:<6} {losses:<6} {win_rate:<8.1f} {pf:<8.2f} {pnl:<12,.0f} {remark}\n")
            else:
                f.write(f"{year_month:<8} {'0':<6} {'0':<6} {'0':<6} {'0.0':<8} {'0.00':<8} {'0':<12} 取引なし\n")
            
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        f.write(f'\n総計: 総取引数{total_trades_all}, 勝率{overall_win_rate:.1f}%, 総損益{total_pnl:,.0f}円\n')
        f.write(f'月平均損益（全36ヶ月）: {monthly_avg_36months:,.0f}円\n')
        f.write(f'目標達成率: {achievement_rate:.1f}%\n')
    
    print(f'\n詳細結果ファイル保存: {result_file}')
    print(f'レバレッジ1倍（追証絶対なし）設定での3年間実績確認完了')

if __name__ == "__main__":
    main()