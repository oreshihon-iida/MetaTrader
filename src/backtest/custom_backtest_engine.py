import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import datetime
from .backtest_engine import BacktestEngine
from .position import Position, PositionStatus
from src.utils.logger import Logger

class CustomBacktestEngine(BacktestEngine):
    """
    カスタムバックテストエンジン
    既存のシグナルを使用し、新たにシグナルを生成しない
    """
    
    def __init__(self, data, initial_balance=2000000, max_positions=5, spread_pips=0.2):
        super().__init__(data, initial_balance, max_positions, spread_pips)
        log_dir = "logs"
        import os
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)

    def run(self, strategies=None) -> Dict[str, Any]:
        """
        バックテストを実行する（シグナル生成をスキップ）

        Parameters
        ----------
        strategies : list, default None
            無視されます。互換性のために残しています。

        Returns
        -------
        Dict[str, Any]
            バックテスト結果（トレード履歴、エクイティカーブ、月別パフォーマンス）
        """
        for i in range(len(self.data)):
            current_time = self.data.index[i]
            current_bar = self.data.iloc[i]

            self._check_positions_for_exit(current_time, current_bar)

            if current_bar['signal'] != 0:
                self.logger.log_info(f"シグナル検出: {current_time}, 値: {current_bar['signal']}, 必要なカラム: entry_price={current_bar.get('entry_price', 'なし')}, sl_price={current_bar.get('sl_price', 'なし')}, tp_price={current_bar.get('tp_price', 'なし')}, strategy={current_bar.get('strategy', 'なし')}")
                if len(self.open_positions) < self.max_positions:
                    self._open_new_position(current_time, current_bar)
                else:
                    self.ignored_signals += 1
                    self.logger.log_info(f"ポジション上限到達のためシグナル無視: {current_time}")

            self._record_equity(current_time)

        if self.closed_positions:
            trades_df = pd.DataFrame([pos.to_dict() for pos in self.closed_positions])
        else:
            trades_df = pd.DataFrame(columns=['entry_time', 'exit_time', 'direction', 
                                              'entry_price', 'exit_price', 'sl_price', 'tp_price',
                                              'profit_pips', 'profit_jpy', 'status', 'strategy'])
        
        equity_curve = pd.DataFrame(self.equity_curve)
        equity_curve.set_index('time', inplace=True)
        
        monthly_performance = {}
        if not trades_df.empty and 'entry_time' in trades_df.columns:
            trades_df['month'] = trades_df['entry_time'].dt.strftime('%Y-%m')
            monthly_groups = trades_df.groupby('month')
            
            for month, group in monthly_groups:
                monthly_performance[month] = {
                    'trades': len(group),
                    'wins': len(group[group['profit_jpy'] > 0]),
                    'losses': len(group[group['profit_jpy'] <= 0]),
                    'profit': group['profit_jpy'].sum(),
                    'win_rate': len(group[group['profit_jpy'] > 0]) / len(group) * 100 if len(group) > 0 else 0
                }
        
        return {
            'trades': trades_df,
            'equity_curve': equity_curve,
            'monthly_performance': monthly_performance,
            'ignored_signals': self.ignored_signals
        }
