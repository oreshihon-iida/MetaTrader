import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional, Tuple

class ReportGenerator:
    """
    レポート生成クラス
    """
    
    def __init__(self, output_dir: str):
        """
        初期化
        
        Parameters
        ----------
        output_dir : str
            レポートを保存するディレクトリ
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def calculate_performance_metrics(self, trade_history: pd.DataFrame, equity_curve: pd.DataFrame) -> Dict:
        """
        パフォーマンス指標を計算する
        
        Parameters
        ----------
        trade_history : pd.DataFrame
            トレード履歴のDataFrame
        equity_curve : pd.DataFrame
            資産推移のDataFrame
            
        Returns
        -------
        Dict
            パフォーマンス指標の辞書
        """
        if trade_history is None or trade_history.empty or '損益(円)' not in trade_history.columns:
            return {
                '総トレード数': 0,
                '勝ちトレード数': 0,
                '負けトレード数': 0,
                '勝率 (%)': 0,
                '総利益 (円)': 0,
                '平均利益 (円/トレード)': 0,
                '平均勝ちトレード (円)': 0,
                '平均負けトレード (円)': 0,
                'プロフィットファクター': 0,
                '最大ドローダウン (%)': 0 if equity_curve is None or equity_curve.empty else abs(equity_curve['drawdown'].min() if 'drawdown' in equity_curve.columns else 0),
                '月別勝率 (%)': 0,
                '戦略別勝率': {},
                '戦略別統計': {},
                '決済理由別統計': {}
            }
        
        total_trades = len(trade_history)
        winning_trades = len(trade_history[trade_history['損益(円)'] > 0])
        losing_trades = len(trade_history[trade_history['損益(円)'] <= 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = trade_history['損益(円)'].sum()
        avg_profit = trade_history['損益(円)'].mean()
        avg_win = trade_history[trade_history['損益(円)'] > 0]['損益(円)'].mean() if winning_trades > 0 else 0
        avg_loss = trade_history[trade_history['損益(円)'] <= 0]['損益(円)'].mean() if losing_trades > 0 else 0
        profit_factor = abs(trade_history[trade_history['損益(円)'] > 0]['損益(円)'].sum() / trade_history[trade_history['損益(円)'] < 0]['損益(円)'].sum()) if trade_history[trade_history['損益(円)'] < 0]['損益(円)'].sum() != 0 else float('inf')
        
        # equity_curveがNoneでないことを確認
        max_drawdown = 0
        if equity_curve is not None and not equity_curve.empty:
            equity_curve['peak'] = equity_curve['equity'].cummax()
            equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
            max_drawdown = abs(equity_curve['drawdown'].min())
        
        monthly_win_rate = 0
        if not trade_history.empty:
            if isinstance(trade_history.index, pd.DatetimeIndex):
                trade_history['月'] = trade_history.index.to_period('M')
                monthly_returns = trade_history.groupby('月')['損益(円)'].sum()
                profitable_months = len(monthly_returns[monthly_returns > 0])
                total_months = len(monthly_returns)
                monthly_win_rate = profitable_months / total_months * 100 if total_months > 0 else 0
            elif 'エントリー時間' in trade_history.columns:
                trade_history = trade_history.set_index('エントリー時間')
                trade_history['月'] = trade_history.index.to_period('M')
                monthly_returns = trade_history.groupby('月')['損益(円)'].sum()
                profitable_months = len(monthly_returns[monthly_returns > 0])
                total_months = len(monthly_returns)
                monthly_win_rate = profitable_months / total_months * 100 if total_months > 0 else 0
        
        strategy_stats = {}
        strategy_win_rates = {}
        if '戦略' in trade_history.columns:
            strategy_stats = trade_history.groupby('戦略').agg({
                '損益(円)': ['sum', 'mean', 'count'],
                '損益(pips)': ['sum', 'mean']
            })
            
            for strategy in trade_history['戦略'].unique():
                strategy_trades = trade_history[trade_history['戦略'] == strategy]
                strategy_wins = len(strategy_trades[strategy_trades['損益(円)'] > 0])
                strategy_total = len(strategy_trades)
                strategy_win_rates[strategy] = strategy_wins / strategy_total * 100 if strategy_total > 0 else 0
        
        exit_reason_stats = {}
        if '決済理由' in trade_history.columns:
            exit_reason_stats = trade_history.groupby('決済理由').agg({
                '損益(円)': ['sum', 'mean', 'count'],
                '損益(pips)': ['sum', 'mean']
            })
        
        metrics = {
            '総トレード数': total_trades,
            '勝ちトレード数': winning_trades,
            '負けトレード数': losing_trades,
            '勝率 (%)': win_rate,
            '総利益 (円)': total_profit,
            '平均利益 (円/トレード)': avg_profit,
            '平均勝ちトレード (円)': avg_win,
            '平均負けトレード (円)': avg_loss,
            'プロフィットファクター': profit_factor,
            '最大ドローダウン (%)': max_drawdown,
            '月別勝率 (%)': monthly_win_rate,
            '戦略別勝率': strategy_win_rates,
            '戦略別統計': strategy_stats.to_dict(),
            '決済理由別統計': exit_reason_stats.to_dict()
        }
        
        return metrics
    
    def generate_summary_report(self, metrics: Dict, trade_history: pd.DataFrame, equity_curve: pd.DataFrame) -> str:
        """
        サマリーレポートを生成する
        
        Parameters
        ----------
        metrics : Dict
            パフォーマンス指標の辞書
        trade_history : pd.DataFrame
            トレード履歴のDataFrame
        equity_curve : pd.DataFrame
            資産推移のDataFrame
            
        Returns
        -------
        str
            レポートのファイルパス
        """
        report_path = os.path.join(self.output_dir, 'backtest_summary.md')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# FXトレードシステム バックテスト結果\n\n")
            
            f.write("## 基本情報\n\n")
            
            # equity_curveが空でないことを確認
            if equity_curve is not None and not equity_curve.empty:
                f.write(f"- バックテスト期間: {equity_curve.index[0].strftime('%Y-%m-%d')} から {equity_curve.index[-1].strftime('%Y-%m-%d')}\n")
                f.write(f"- 初期資金: {equity_curve['balance'].iloc[0]:,.0f}円\n")
                f.write(f"- 最終資金: {equity_curve['balance'].iloc[-1]:,.0f}円\n")
                f.write(f"- 総利益: {metrics['総利益 (円)']:,.0f}円\n")
                f.write(f"- リターン: {(equity_curve['balance'].iloc[-1] / equity_curve['balance'].iloc[0] - 1) * 100:.2f}%\n\n")
            else:
                f.write("- バックテスト期間: データなし\n")
                f.write("- 初期資金: データなし\n")
                f.write("- 最終資金: データなし\n")
                f.write("- 総利益: 0円\n")
                f.write("- リターン: 0%\n\n")
            
            f.write("## パフォーマンス指標\n\n")
            f.write(f"- 総トレード数: {metrics['総トレード数']}\n")
            f.write(f"- 勝ちトレード数: {metrics['勝ちトレード数']}\n")
            f.write(f"- 負けトレード数: {metrics['負けトレード数']}\n")
            f.write(f"- 勝率: {metrics['勝率 (%)']:.2f}%\n")
            f.write(f"- 平均利益: {metrics['平均利益 (円/トレード)']:,.0f}円/トレード\n")
            f.write(f"- 平均勝ちトレード: {metrics['平均勝ちトレード (円)']:,.0f}円\n")
            f.write(f"- 平均負けトレード: {metrics['平均負けトレード (円)']:,.0f}円\n")
            f.write(f"- プロフィットファクター: {metrics['プロフィットファクター']:.2f}\n")
            f.write(f"- 最大ドローダウン: {metrics['最大ドローダウン (%)']:.2f}%\n")
            f.write(f"- 月別勝率: {metrics['月別勝率 (%)']:.2f}%\n\n")
            
            f.write("## 戦略別パフォーマンス\n\n")
            
            if '戦略別勝率' in metrics and metrics['戦略別勝率'] and '戦略別統計' in metrics and metrics['戦略別統計']:
                f.write("| 戦略 | トレード数 | 勝率 (%) | 総利益 (円) | 平均利益 (円/トレード) | プロフィットファクター |\n")
                f.write("|------|------------|----------|------------|------------------------|------------------------|\n")
                
                for strategy, win_rate in metrics['戦略別勝率'].items():
                    if ('損益(円)', 'count') in metrics['戦略別統計'] and strategy in metrics['戦略別統計'][('損益(円)', 'count')]:
                        strategy_trades = metrics['戦略別統計'][('損益(円)', 'count')][strategy]
                        strategy_total_profit = metrics['戦略別統計'][('損益(円)', 'sum')][strategy]
                        strategy_avg_profit = metrics['戦略別統計'][('損益(円)', 'mean')][strategy]
                        
                        strategy_df = trade_history[trade_history['戦略'] == strategy]
                        winning_trades = strategy_df[strategy_df['損益(円)'] > 0]['損益(円)'].sum()
                        losing_trades = abs(strategy_df[strategy_df['損益(円)'] < 0]['損益(円)'].sum())
                        profit_factor = winning_trades / losing_trades if losing_trades > 0 else float('inf')
                        
                        f.write(f"| {strategy} | {strategy_trades} | {win_rate:.2f} | {strategy_total_profit:,.0f} | {strategy_avg_profit:,.0f} | {profit_factor:.2f} |\n")
            else:
                f.write("データなし\n")
            
            f.write("\n")
            
            f.write("## 決済理由別パフォーマンス\n\n")
            
            if '決済理由別統計' in metrics and metrics['決済理由別統計'] and ('損益(円)', 'count') in metrics['決済理由別統計']:
                f.write("| 決済理由 | トレード数 | 総利益 (円) | 平均利益 (円/トレード) |\n")
                f.write("|----------|------------|------------|------------------------|\n")
                
                for reason in metrics['決済理由別統計'][('損益(円)', 'count')].keys():
                    reason_trades = metrics['決済理由別統計'][('損益(円)', 'count')][reason]
                    reason_total_profit = metrics['決済理由別統計'][('損益(円)', 'sum')][reason]
                    reason_avg_profit = metrics['決済理由別統計'][('損益(円)', 'mean')][reason]
                    
                    f.write(f"| {reason} | {reason_trades} | {reason_total_profit:,.0f} | {reason_avg_profit:,.0f} |\n")
            else:
                f.write("データなし\n")
            
            f.write("\n")
            
            f.write("## 月別パフォーマンス\n\n")
            
            if trade_history is not None and not trade_history.empty and '損益(円)' in trade_history.columns and '損益(pips)' in trade_history.columns:
                if isinstance(trade_history.index, pd.DatetimeIndex):
                    trade_history['月'] = trade_history.index.to_period('M')
                    monthly_stats = trade_history.groupby('月').agg({
                        '損益(円)': ['sum', 'count'],
                        '損益(pips)': 'sum'
                    })
                    
                    f.write("| 月 | トレード数 | 総利益 (円) | 総利益 (pips) |\n")
                    f.write("|------|------------|------------|---------------|\n")
                    
                    for month, row in monthly_stats.iterrows():
                        month_str = month.strftime('%Y-%m')
                        trades = row[('損益(円)', 'count')]
                        profit_jpy = row[('損益(円)', 'sum')]
                        profit_pips = row[('損益(pips)', 'sum')]
                        
                        f.write(f"| {month_str} | {trades} | {profit_jpy:,.0f} | {profit_pips:.1f} |\n")
                elif 'エントリー時間' in trade_history.columns:
                    temp_df = trade_history.copy()
                    temp_df = temp_df.set_index('エントリー時間')
                    temp_df['月'] = temp_df.index.to_period('M')
                    monthly_stats = temp_df.groupby('月').agg({
                        '損益(円)': ['sum', 'count'],
                        '損益(pips)': 'sum'
                    })
                    
                    f.write("| 月 | トレード数 | 総利益 (円) | 総利益 (pips) |\n")
                    f.write("|------|------------|------------|---------------|\n")
                    
                    for month, row in monthly_stats.iterrows():
                        month_str = month.strftime('%Y-%m')
                        trades = row[('損益(円)', 'count')]
                        profit_jpy = row[('損益(円)', 'sum')]
                        profit_pips = row[('損益(pips)', 'sum')]
                        
                        f.write(f"| {month_str} | {trades} | {profit_jpy:,.0f} | {profit_pips:.1f} |\n")
                else:
                    f.write("データなし（インデックスが日付型ではありません）\n")
            else:
                f.write("データなし\n")
            
            f.write("\n")
            
            f.write("## グラフ\n\n")
            f.write("- [資産推移](../charts/equity_curve.png)\n")
            f.write("- [ドローダウン](../charts/drawdown.png)\n")
            f.write("- [月別リターン](../charts/monthly_returns.png)\n")
            f.write("- [戦略比較](../charts/strategy_comparison.png)\n")
        
        return report_path
