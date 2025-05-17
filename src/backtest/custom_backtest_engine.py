import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import datetime
from .backtest_engine import BacktestEngine
from .position import Position, PositionStatus

class CustomBacktestEngine(BacktestEngine):
    """
    カスタムバックテストエンジン
    既存のシグナルを使用し、新たにシグナルを生成しない
    """

    def run(self, strategies=None) -> pd.DataFrame:
        """
        バックテストを実行する（シグナル生成をスキップ）

        Parameters
        ----------
        strategies : list, default None
            無視されます。互換性のために残しています。

        Returns
        -------
        pd.DataFrame
            トレード履歴
        """
        for i in range(len(self.data)):
            current_time = self.data.index[i]
            current_bar = self.data.iloc[i]

            self._check_positions_for_exit(current_time, current_bar)

            if current_bar['signal'] != 0 and len(self.open_positions) < self.max_positions:
                self._open_new_position(current_time, current_bar)

            self._record_equity(current_time)

        if self.closed_positions:
            history_df = pd.DataFrame([pos.to_dict() for pos in self.closed_positions])
        else:
            history_df = pd.DataFrame(columns=['entry_time', 'exit_time', 'direction', 
                                              'entry_price', 'exit_price', 'sl_price', 'tp_price',
                                              'profit_pips', 'profit_jpy', 'status', 'strategy'])
        return history_df
