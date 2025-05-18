import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .improved_short_term_strategy import ImprovedShortTermStrategy

class BalancedShortTermStrategy(ImprovedShortTermStrategy):
    """
    バランス型短期ボリンジャーバンド＋RSI戦略
    
    取引頻度とプロフィットファクターのバランスを取った短期戦略
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            ImprovedShortTermStrategyに渡すパラメータ
        """
        default_params = {
            'bb_window': 20,
            'bb_dev': 1.5,          # 標準偏差を1.6から1.5に調整して取引頻度を適度に向上
            'rsi_window': 14,
            'rsi_upper': 57,        # RSI閾値を55から57に緩和して取引頻度を適度に向上
            'rsi_lower': 43,        # RSI閾値を45から43に緩和して取引頻度を適度に向上
            'sl_pips': 3.0,         # 損切り幅は維持
            'tp_pips': 7.5,         # 利確幅は維持
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,
            'atr_tp_multiplier': 2.0,
            'use_adaptive_params': True,
            'trend_filter': False,
            'vol_filter': True,     # ボラティリティフィルターは維持
            'time_filter': True,
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
            'use_seasonal_filter': False,
            'use_price_action': False,
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "バランス型短期ボリンジャーバンド＋RSI戦略"
        
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        バランス型では時間フィルターを若干緩和
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            シグナルを生成する場合はTrue、そうでない場合はFalse
        """
        if i < 1:
            return False
            
        consecutive_signals = 0
        for j in range(1, min(self.consecutive_limit + 1, i + 1)):
            if df['signal'].iloc[i-j] != 0:
                consecutive_signals += 1
        
        if consecutive_signals >= self.consecutive_limit:
            return False
            
        if self.vol_filter:
            atr = df['atr'].iloc[i]
            atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.7
            if atr < atr_threshold:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 3) or (8 <= hour < 11) or (13 <= hour < 16)):
                return False
                
        return True
