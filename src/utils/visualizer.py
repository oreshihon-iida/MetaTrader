import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional, Tuple

class Visualizer:
    """
    データの可視化を行うクラス
    
    特徴:
    - エクイティカーブの描画
    - ドローダウンの描画
    - 月別リターンの描画
    - トレード結果の可視化
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        """
        初期化
        
        Parameters
        ----------
        figsize : Tuple[int, int]
            図のサイズ
        dpi : int
            解像度
        """
        self.figsize = figsize
        self.dpi = dpi
        
        plt.style.use('ggplot')
    
    def plot_equity_curve(self, equity_df: pd.DataFrame, title: str = 'Equity Curve', output_dir: str = 'results/charts'):
        """
        エクイティカーブを描画
        
        Parameters
        ----------
        equity_df : pd.DataFrame
            エクイティデータを含むデータフレーム
        title : str
            グラフのタイトル
        output_dir : str
            出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        
        plt.figure(figsize=self.figsize, dpi=self.dpi)
        
        if 'equity' in equity_df.columns:
            plt.plot(equity_df.index, equity_df['equity'], label='Equity', color='blue', linewidth=2)
        elif 'portfolio_equity' in equity_df.columns:
            plt.plot(equity_df.index, equity_df['portfolio_equity'], label='Portfolio Equity', color='blue', linewidth=2)
        else:
            column = equity_df.columns[0]
            plt.plot(equity_df.index, equity_df[column], label=column, color='blue', linewidth=2)
        
        if 'equity' in equity_df.columns:
            initial_equity = equity_df['equity'].iloc[0]
            plt.axhline(y=initial_equity, color='gray', linestyle='--', label=f'Initial: {initial_equity:,.0f}')
        
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.legend()
        plt.grid(True)
        
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{title.replace(' ', '_')}.png")
        plt.close()
    
    def plot_drawdown(self, equity_df: pd.DataFrame, title: str = 'Drawdown', output_dir: str = 'results/charts'):
        """
        ドローダウンを描画
        
        Parameters
        ----------
        equity_df : pd.DataFrame
            エクイティデータを含むデータフレーム
        title : str
            グラフのタイトル
        output_dir : str
            出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        
        plt.figure(figsize=self.figsize, dpi=self.dpi)
        
        if 'drawdown_pct' in equity_df.columns:
            plt.plot(equity_df.index, equity_df['drawdown_pct'], label='Drawdown %', color='red', linewidth=2)
        else:
            if 'equity' in equity_df.columns:
                equity = equity_df['equity']
            elif 'portfolio_equity' in equity_df.columns:
                equity = equity_df['portfolio_equity']
            else:
                equity = equity_df[equity_df.columns[0]]
                
            equity_max = equity.cummax()
            
            drawdown_pct = (equity_max - equity) / equity_max * 100
            
            plt.plot(equity_df.index, drawdown_pct, label='Drawdown %', color='red', linewidth=2)
        
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.legend()
        plt.grid(True)
        
        plt.gca().invert_yaxis()
        
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{title.replace(' ', '_')}.png")
        plt.close()
    
    def plot_monthly_returns(self, months: List[str], returns: List[float], title: str = 'Monthly Returns', output_dir: str = 'results/charts'):
        """
        月別リターンを棒グラフで描画
        
        Parameters
        ----------
        months : List[str]
            月のリスト
        returns : List[float]
            リターンのリスト
        title : str
            グラフのタイトル
        output_dir : str
            出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        
        plt.figure(figsize=self.figsize, dpi=self.dpi)
        
        colors = ['green' if r >= 0 else 'red' for r in returns]
        
        plt.bar(months, returns, color=colors)
        
        plt.title(title)
        plt.xlabel('Month')
        plt.ylabel('Return')
        plt.grid(True, axis='y')
        
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{title.replace(' ', '_')}.png")
        plt.close()
    
    def plot_trade_results(self, trades: pd.DataFrame, title: str = 'Trade Results', output_dir: str = 'results/charts'):
        """
        トレード結果を散布図で描画
        
        Parameters
        ----------
        trades : pd.DataFrame
            トレード結果を含むデータフレーム
        title : str
            グラフのタイトル
        output_dir : str
            出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        
        plt.figure(figsize=self.figsize, dpi=self.dpi)
        
        winning_trades = trades[trades['profit'] > 0]
        losing_trades = trades[trades['profit'] <= 0]
        
        if not winning_trades.empty:
            plt.scatter(winning_trades.index, winning_trades['profit'], color='green', label='Win', alpha=0.7)
        if not losing_trades.empty:
            plt.scatter(losing_trades.index, losing_trades['profit'], color='red', label='Loss', alpha=0.7)
        
        plt.title(title)
        plt.xlabel('Trade #')
        plt.ylabel('Profit/Loss')
        plt.axhline(y=0, color='gray', linestyle='--')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{title.replace(' ', '_')}.png")
        plt.close()
    
    def plot_win_rate_by_hour(self, trades: pd.DataFrame, title: str = 'Win Rate by Hour', output_dir: str = 'results/charts'):
        """
        時間帯別の勝率を棒グラフで描画
        
        Parameters
        ----------
        trades : pd.DataFrame
            トレード結果を含むデータフレーム
        title : str
            グラフのタイトル
        output_dir : str
            出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        
        if 'entry_time' not in trades.columns:
            return
        
        trades['hour'] = trades['entry_time'].dt.hour
        hourly_stats = trades.groupby('hour').agg({
            'profit': ['count', lambda x: (x > 0).mean() * 100]
        })
        
        hourly_stats.columns = ['count', 'win_rate']
        
        plt.figure(figsize=self.figsize, dpi=self.dpi)
        
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        ax1.bar(hourly_stats.index, hourly_stats['count'], color='blue', alpha=0.3, label='Trade Count')
        ax2.plot(hourly_stats.index, hourly_stats['win_rate'], color='green', marker='o', label='Win Rate %')
        
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Trade Count')
        ax2.set_ylabel('Win Rate %')
        
        plt.title(title)
        plt.grid(True)
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.xticks(range(0, 24))
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{title.replace(' ', '_')}.png")
        plt.close()
