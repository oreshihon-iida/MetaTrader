import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import datetime
from .backtest_engine import BacktestEngine
from .position import Position, PositionStatus

class CustomBacktestEngine(BacktestEngine):
    """
    カスタムバックテストエンジン
    既存のシグナルを使用し、新たにシグナルを生成しない
    """

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

            if current_bar['signal'] != 0 and len(self.open_positions) < self.max_positions:
                self._open_new_position(current_time, current_bar)

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
