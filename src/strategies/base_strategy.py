import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

class BaseStrategy:
    """
    取引戦略の基底クラス
    
    全ての戦略クラスはこのクラスを継承する
    """
    
    def __init__(self):
        """
        初期化
        """
        self.name = "BaseStrategy"
        self.description = "基本戦略"
        
        self.sl_pips = 10.0  # ストップロス（pips）
        self.tp_pips = 20.0  # テイクプロフィット（pips）
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        取引シグナルを生成する
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        pd.DataFrame
            シグナルが付与されたデータフレーム
        """
        data['signal'] = 0
        return data
    
    def calculate_position_size(self, signal: float, equity: float) -> float:
        """
        ポジションサイズを計算する
        
        Parameters
        ----------
        signal : float
            トレードシグナル（1.0=買い、-1.0=売り、0.0=シグナルなし）
        equity : float
            口座残高
            
        Returns
        -------
        float
            ポジションサイズ（ロット単位）
        """
        if signal == 0:
            return 0.0
            
        risk_percent = 0.01
        risk_amount = equity * risk_percent
        
        pip_value = 10.0
        position_size = risk_amount / (self.sl_pips * pip_value)
        
        return position_size
    
    def calculate_stop_loss(self, price: float, signal: float) -> float:
        """
        ストップロス価格を計算する
        
        Parameters
        ----------
        price : float
            現在価格
        signal : float
            トレードシグナル（1.0=買い、-1.0=売り）
            
        Returns
        -------
        float
            ストップロス価格
        """
        if signal > 0:
            return price - self.sl_pips / 100
        elif signal < 0:
            return price + self.sl_pips / 100
        else:
            return 0.0
    
    def calculate_take_profit(self, price: float, signal: float) -> float:
        """
        テイクプロフィット価格を計算する
        
        Parameters
        ----------
        price : float
            現在価格
        signal : float
            トレードシグナル（1.0=買い、-1.0=売り）
            
        Returns
        -------
        float
            テイクプロフィット価格
        """
        if signal > 0:
            return price + self.tp_pips / 100
        elif signal < 0:
            return price - self.tp_pips / 100
        else:
            return 0.0
