import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class Visualizer:
    """
    バックテスト結果の可視化クラス
    """
    
    def __init__(self, output_dir: str = 'results/charts'):
        """
        初期化
        
        Parameters
        ----------
        output_dir : str, default 'results/charts'
            チャート出力ディレクトリ
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_equity_curve(self, results: pd.DataFrame, initial_balance: float = 200000, 
                          filename: str = 'equity_curve.png') -> None:
        """
        損益曲線をプロットする
        
        Parameters
        ----------
        results : pd.DataFrame
            バックテスト結果
        initial_balance : float, default 200000
            初期資金
        filename : str, default 'equity_curve.png'
            出力ファイル名
        """
        if results.empty:
            return
            
        results = results.copy()
        results['entry_time'] = pd.to_datetime(results['エントリー時間']) if 'エントリー時間' in results.columns else pd.to_datetime(results['entry_time'])
        results['cumulative_profit'] = results['profit_jpy'].cumsum()
        results['equity'] = initial_balance + results['cumulative_profit']
        
        plt.figure(figsize=(12, 6))
        plt.plot(results['entry_time'], results['equity'])
        plt.title('Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity (JPY)')
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def plot_drawdown(self, results: pd.DataFrame, initial_balance: float = 200000,
                      filename: str = 'drawdown.png') -> None:
        """
        ドローダウンをプロットする
        
        Parameters
        ----------
        results : pd.DataFrame
            バックテスト結果
        initial_balance : float, default 200000
            初期資金
        filename : str, default 'drawdown.png'
            出力ファイル名
        """
        if results.empty:
            return
            
        results = results.copy()
        results['entry_time'] = pd.to_datetime(results['エントリー時間']) if 'エントリー時間' in results.columns else pd.to_datetime(results['entry_time'])
        results['cumulative_profit'] = results['profit_jpy'].cumsum()
        results['equity'] = initial_balance + results['cumulative_profit']
        results['peak'] = results['equity'].cummax()
        results['drawdown'] = (results['equity'] - results['peak']) / results['peak'] * 100
        
        plt.figure(figsize=(12, 6))
        plt.plot(results['entry_time'], results['drawdown'])
        plt.title('Drawdown')
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def plot_monthly_returns(self, results: pd.DataFrame, filename: str = 'monthly_returns.png') -> None:
        """
        月別リターンをプロットする
        
        Parameters
        ----------
        results : pd.DataFrame
            バックテスト結果
        filename : str, default 'monthly_returns.png'
            出力ファイル名
        """
        if results.empty:
            return
            
        results = results.copy()
        results['entry_time'] = pd.to_datetime(results['エントリー時間']) if 'エントリー時間' in results.columns else pd.to_datetime(results['entry_time'])
        results['month'] = results['entry_time'].dt.strftime('%Y-%m')
        
        monthly_performance = results.groupby('month').agg(
            net_profit=('profit_jpy', 'sum')
        ).reset_index()
        
        plt.figure(figsize=(12, 6))
        plt.bar(monthly_performance['month'], monthly_performance['net_profit'])
        plt.title('Monthly Returns')
        plt.xlabel('Month')
        plt.ylabel('Net Profit (JPY)')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def plot_win_loss_distribution(self, results: pd.DataFrame, filename: str = 'win_loss_distribution.png') -> None:
        """
        勝ち負けの分布をプロットする
        
        Parameters
        ----------
        results : pd.DataFrame
            バックテスト結果
        filename : str, default 'win_loss_distribution.png'
            出力ファイル名
        """
        if results.empty:
            return
            
        wins = results[results['profit_jpy'] > 0]['profit_jpy']
        losses = results[results['profit_jpy'] < 0]['profit_jpy']
        
        plt.figure(figsize=(12, 6))
        
        if not wins.empty:
            plt.hist(wins, bins=20, alpha=0.5, color='green', label='Wins')
        
        if not losses.empty:
            plt.hist(losses, bins=20, alpha=0.5, color='red', label='Losses')
        
        plt.title('Win/Loss Distribution')
        plt.xlabel('Profit/Loss (JPY)')
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def plot_strategy_comparison(self, results_dict: Dict[str, pd.DataFrame], 
                                initial_balance: float = 200000,
                                filename: str = 'strategy_comparison.png') -> None:
        """
        複数戦略の損益曲線を比較する
        
        Parameters
        ----------
        results_dict : Dict[str, pd.DataFrame]
            戦略名とバックテスト結果のディクショナリ
        initial_balance : float, default 200000
            初期資金
        filename : str, default 'strategy_comparison.png'
            出力ファイル名
        """
        plt.figure(figsize=(12, 6))
        
        for strategy_name, results in results_dict.items():
            if results.empty:
                continue
                
            results = results.copy()
            results['entry_time'] = pd.to_datetime(results['エントリー時間']) if 'エントリー時間' in results.columns else pd.to_datetime(results['entry_time'])
            results = results.sort_values('entry_time')
            results['cumulative_profit'] = results['profit_jpy'].cumsum()
            results['equity'] = initial_balance + results['cumulative_profit']
            
            plt.plot(results['entry_time'], results['equity'], label=strategy_name)
        
        plt.title('Strategy Comparison')
        plt.xlabel('Date')
        plt.ylabel('Equity (JPY)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def create_performance_summary(self, results: pd.DataFrame, initial_balance: float = 200000) -> Dict:
        """
        パフォーマンスサマリーを作成する
        
        Parameters
        ----------
        results : pd.DataFrame
            バックテスト結果
        initial_balance : float, default 200000
            初期資金
            
        Returns
        -------
        Dict
            パフォーマンス指標のディクショナリ
        """
        if results.empty:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'net_profit': 0.0,
                'max_drawdown': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'max_win': 0.0,
                'max_loss': 0.0
            }
            
        total_trades = len(results)
        wins = len(results[results['profit_jpy'] > 0])
        losses = len(results[results['profit_jpy'] < 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = results[results['profit_jpy'] > 0]['profit_jpy'].sum()
        total_loss = abs(results[results['profit_jpy'] < 0]['profit_jpy'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        net_profit = total_profit - total_loss
        
        results = results.copy()
        results['cumulative_profit'] = results['profit_jpy'].cumsum()
        results['equity'] = initial_balance + results['cumulative_profit']
        results['peak'] = results['equity'].cummax()
        results['drawdown'] = (results['equity'] - results['peak']) / results['peak'] * 100
        max_drawdown = abs(results['drawdown'].min())
        
        avg_win = results[results['profit_jpy'] > 0]['profit_jpy'].mean() if wins > 0 else 0
        avg_loss = results[results['profit_jpy'] < 0]['profit_jpy'].mean() if losses > 0 else 0
        max_win = results['profit_jpy'].max() if not results.empty else 0
        max_loss = results['profit_jpy'].min() if not results.empty else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_profit': net_profit,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss
        }
