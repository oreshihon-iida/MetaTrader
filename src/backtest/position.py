import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

class PositionStatus(Enum):
    OPEN = "オープン"
    CLOSED_TAKE_PROFIT = "利確"
    CLOSED_STOP_LOSS = "損切り"
    CLOSED_MANUAL = "手動決済"

class Position:
    """
    トレードポジションを表すクラス
    """
    
    def __init__(self, entry_time: pd.Timestamp, direction: int, entry_price: float, 
                 sl_price: float, tp_price: float, strategy: str, lot_size: float = 0.01):
        """
        初期化
        
        Parameters
        ----------
        entry_time : pd.Timestamp
            エントリー時間
        direction : int
            取引方向（1=買い, -1=売り）
        entry_price : float
            エントリー価格
        sl_price : float
            損切り価格
        tp_price : float
            利確価格
        strategy : str
            使用した戦略の名前
        lot_size : float, default 0.01
            取引サイズ（ロット）
        """
        self.entry_time = entry_time
        self.direction = direction
        self.entry_price = entry_price
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.strategy = strategy
        self.lot_size = lot_size
        
        self.exit_time = None
        self.exit_price = None
        self.status = PositionStatus.OPEN
        self.profit_pips = None
        self.profit_jpy = None
    
    def close_position(self, exit_time: pd.Timestamp, exit_price: float, status: PositionStatus):
        """
        ポジションを決済する
        
        Parameters
        ----------
        exit_time : pd.Timestamp
            決済時間
        exit_price : float
            決済価格
        status : PositionStatus
            決済理由
        """
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = status
        
        self.profit_pips = (exit_price - self.entry_price) * self.direction * 100
        
        pip_value = 0.01 * 1000 * self.lot_size
        self.profit_jpy = self.profit_pips * pip_value
    
    def to_dict(self) -> Dict:
        """
        ポジション情報を辞書形式で返す
        
        Returns
        -------
        Dict
            ポジション情報の辞書
        """
        direction_str = "買い" if self.direction == 1 else "売り"
        return {
            'エントリー時間': self.entry_time,
            '決済時間': self.exit_time,
            '取引方向': direction_str,
            'エントリー価格': self.entry_price,
            '決済価格': self.exit_price,
            '損益(pips)': self.profit_pips,
            '損益(円)': self.profit_jpy,
            '決済理由': self.status.value if self.status else None,
            '戦略': self.strategy,
            'ロットサイズ': self.lot_size
        }
