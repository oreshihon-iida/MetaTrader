"""
基本戦略クラス
すべての取引戦略の基底クラスとして機能
"""
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

class BaseStrategy:
    """
    すべての取引戦略の基底クラス
    
    このクラスは基本的なインターフェースを定義し、
    すべての具体的な戦略クラスはこのクラスを継承する必要があります。
    """
    
    def __init__(self):
        """
        基本的な初期化
        """
        pass
    
    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
            
        Returns
        -------
        pd.DataFrame
            シグナルが付与されたデータフレーム
        """
        raise NotImplementedError("このメソッドは子クラスでオーバーライドする必要があります")
    
    def calculate_position_size(self, signal: float, equity: float) -> float:
        """
        ポジションサイズを計算する
        
        Parameters
        ----------
        signal : float
            トレードシグナル
        equity : float
            口座残高
            
        Returns
        -------
        float
            ポジションサイズ
        """
        return 0.01 * equity
