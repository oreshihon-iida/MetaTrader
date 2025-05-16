import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from typing import Dict, List, Optional, Tuple

class ChartGenerator:
    """
    チャート生成クラス
    """
    
    def __init__(self, chart_dir: str):
        """
        初期化
        
        Parameters
        ----------
        chart_dir : str
            チャートを保存するディレクトリ
        """
        self.chart_dir = chart_dir
        os.makedirs(chart_dir, exist_ok=True)
        
        plt.style.use('ggplot')
    
    def plot_equity_curve(self, equity_df: pd.DataFrame, save: bool = True) -> plt.Figure:
        """
        資産推移グラフを生成する
        
        Parameters
        ----------
        equity_df : pd.DataFrame
            資産推移のDataFrame
        save : bool, default True
            グラフを保存するかどうか
            
        Returns
        -------
        plt.Figure
            生成されたグラフ
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(equity_df.index, equity_df['equity'], label='総資産', color='blue')
        ax.plot(equity_df.index, equity_df['balance'], label='残高', color='green', linestyle='--')
        
        ax.set_title('資産推移', fontsize=15)
        ax.set_xlabel('日付', fontsize=12)
        ax.set_ylabel('金額（円）', fontsize=12)
        ax.legend()
        ax.grid(True)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        fig.autofmt_xdate()
        
        if save:
            plt.tight_layout()
            plt.savefig(os.path.join(self.chart_dir, 'equity_curve.png'), dpi=300)
        
        return fig
    
    def plot_monthly_returns(self, trade_history: pd.DataFrame, save: bool = True) -> plt.Figure:
        """
        月別リターングラフを生成する
        
        Parameters
        ----------
        trade_history : pd.DataFrame
            トレード履歴のDataFrame
        save : bool, default True
            グラフを保存するかどうか
            
        Returns
        -------
        plt.Figure
            生成されたグラフ
        """
        if trade_history.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_title('月別損益（データなし）', fontsize=15)
            ax.set_xlabel('月', fontsize=12)
            ax.set_ylabel('損益（円）', fontsize=12)
            ax.grid(True, axis='y')
            
            if save:
                plt.tight_layout()
                plt.savefig(os.path.join(self.chart_dir, 'monthly_returns.png'), dpi=300)
            
            return fig
        
        if not isinstance(trade_history.index, pd.DatetimeIndex):
            if 'エントリー時間' in trade_history.columns:
                trade_history = trade_history.set_index('エントリー時間')
            else:
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.set_title('月別損益（日付データなし）', fontsize=15)
                ax.set_xlabel('月', fontsize=12)
                ax.set_ylabel('損益（円）', fontsize=12)
                ax.grid(True, axis='y')
                
                if save:
                    plt.tight_layout()
                    plt.savefig(os.path.join(self.chart_dir, 'monthly_returns.png'), dpi=300)
                
                return fig
        
        trade_history['月'] = trade_history.index.to_period('M')
        monthly_returns = trade_history.groupby('月')['損益(円)'].sum()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.bar(monthly_returns.index.astype(str), monthly_returns.values)
        
        for i, bar in enumerate(bars):
            if monthly_returns.values[i] >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        ax.set_title('月別損益', fontsize=15)
        ax.set_xlabel('月', fontsize=12)
        ax.set_ylabel('損益（円）', fontsize=12)
        ax.grid(True, axis='y')
        
        plt.xticks(rotation=90)
        
        if save:
            plt.tight_layout()
            plt.savefig(os.path.join(self.chart_dir, 'monthly_returns.png'), dpi=300)
        
        return fig
    
    def plot_drawdown(self, equity_df: pd.DataFrame, save: bool = True) -> plt.Figure:
        """
        ドローダウングラフを生成する
        
        Parameters
        ----------
        equity_df : pd.DataFrame
            資産推移のDataFrame
        save : bool, default True
            グラフを保存するかどうか
            
        Returns
        -------
        plt.Figure
            生成されたグラフ
        """
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.fill_between(equity_df.index, equity_df['drawdown'], 0, color='red', alpha=0.3)
        ax.plot(equity_df.index, equity_df['drawdown'], color='red', linewidth=1)
        
        ax.set_title('ドローダウン', fontsize=15)
        ax.set_xlabel('日付', fontsize=12)
        ax.set_ylabel('ドローダウン（%）', fontsize=12)
        ax.grid(True)
        
        ax.invert_yaxis()
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        fig.autofmt_xdate()
        
        if save:
            plt.tight_layout()
            plt.savefig(os.path.join(self.chart_dir, 'drawdown.png'), dpi=300)
        
        return fig
    
    def plot_strategy_comparison(self, trade_history: pd.DataFrame, save: bool = True) -> plt.Figure:
        """
        戦略比較グラフを生成する
        
        Parameters
        ----------
        trade_history : pd.DataFrame
            トレード履歴のDataFrame
        save : bool, default True
            グラフを保存するかどうか
            
        Returns
        -------
        plt.Figure
            生成されたグラフ
        """
        if trade_history.empty:
            fig, ax = plt.subplots(figsize=(15, 10))
            ax.set_title('戦略比較（データなし）', fontsize=15)
            ax.grid(True, axis='y')
            
            if save:
                plt.tight_layout()
                plt.savefig(os.path.join(self.chart_dir, 'strategy_comparison.png'), dpi=300)
            
            return fig
        
        required_columns = ['戦略', '損益(円)', '損益(pips)']
        for col in required_columns:
            if col not in trade_history.columns:
                if col == '戦略' and '戦略' not in trade_history.columns and 'strategy' in trade_history.columns:
                    trade_history['戦略'] = trade_history['strategy']
                elif col == '損益(円)' and '損益(円)' not in trade_history.columns and 'profit_jpy' in trade_history.columns:
                    trade_history['損益(円)'] = trade_history['profit_jpy']
                elif col == '損益(pips)' and '損益(pips)' not in trade_history.columns and 'profit_pips' in trade_history.columns:
                    trade_history['損益(pips)'] = trade_history['profit_pips']
                else:
                    fig, ax = plt.subplots(figsize=(15, 10))
                    ax.set_title(f'戦略比較（{col}列がありません）', fontsize=15)
                    ax.grid(True, axis='y')
                    
                    if save:
                        plt.tight_layout()
                        plt.savefig(os.path.join(self.chart_dir, 'strategy_comparison.png'), dpi=300)
                    
                    return fig
        
        strategy_stats = trade_history.groupby('戦略').agg({
            '損益(円)': ['sum', 'mean', 'count'],
            '損益(pips)': ['sum', 'mean']
        })
        
        strategy_stats['勝率'] = trade_history[trade_history['損益(円)'] > 0].groupby('戦略').size() / strategy_stats[('損益(円)', 'count')] * 100
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        axes[0, 0].bar(strategy_stats.index, strategy_stats[('損益(円)', 'sum')])
        axes[0, 0].set_title('戦略別総利益（円）')
        axes[0, 0].grid(True, axis='y')
        
        axes[0, 1].bar(strategy_stats.index, strategy_stats[('損益(円)', 'mean')])
        axes[0, 1].set_title('戦略別平均利益（円/トレード）')
        axes[0, 1].grid(True, axis='y')
        
        axes[1, 0].bar(strategy_stats.index, strategy_stats[('損益(円)', 'count')])
        axes[1, 0].set_title('戦略別トレード回数')
        axes[1, 0].grid(True, axis='y')
        
        axes[1, 1].bar(strategy_stats.index, strategy_stats['勝率'])
        axes[1, 1].set_title('戦略別勝率（%）')
        axes[1, 1].grid(True, axis='y')
        
        if save:
            plt.tight_layout()
            plt.savefig(os.path.join(self.chart_dir, 'strategy_comparison.png'), dpi=300)
        
        return fig
