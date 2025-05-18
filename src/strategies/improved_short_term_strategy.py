import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy

class ImprovedShortTermStrategy(ShortTermBollingerRsiStrategy):
    """
    改良版短期ボリンジャーバンド＋RSI戦略
    
    プロフィットファクターを向上させるための改良を加えた短期戦略
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            ShortTermBollingerRsiStrategyに渡すパラメータ
        """
        default_params = {
            'bb_window': 20,
            'bb_dev': 1.8,          # 標準偏差を1.6から1.8に調整してノイズを減少
            'rsi_window': 14,
            'rsi_upper': 60,        # RSI閾値を55から60に調整して高品質シグナルに限定
            'rsi_lower': 40,        # RSI閾値を45から40に調整して高品質シグナルに限定
            'sl_pips': 3.0,         # 損切り幅は維持
            'tp_pips': 7.5,         # 利確幅を6.0から7.5に拡大してリスク・リワード比を改善
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,
            'atr_tp_multiplier': 2.0,  # ATRベースの利確乗数を1.6から2.0に拡大
            'use_adaptive_params': True,
            'trend_filter': False,
            'vol_filter': True,     # ボラティリティフィルターを有効化して高ボラティリティ時のみ取引
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
        self.name = "改良版短期ボリンジャーバンド＋RSI戦略"
        
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        改良版では時間フィルターを強化し、高勝率の時間帯に限定
        
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
        if not super()._apply_filters(df, i):
            return False
            
        if self.vol_filter:
            atr = df['atr'].iloc[i]
            avg_atr = df['atr'].rolling(window=20).mean().iloc[i]
            
            if atr < avg_atr * 0.7:
                return False
                
            if atr > avg_atr * 2.0:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 2) or (8 <= hour < 10) or (13 <= hour < 15)):
                return False
                
        return True
        
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        連続損失後はポジションサイズを削減
        
        Parameters
        ----------
        signal : int
            シグナル（1: 買い、-1: 売り、0: シグナルなし）
        equity : float, default 10000.0
            現在の資金
            
        Returns
        -------
        float
            ポジションサイズ（ロット）
        """
        if signal == 0:
            return 0.0
            
        base_size = 0.01
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return base_size * 0.5
            
        return base_size
        
    def update_consecutive_losses(self, is_win: bool) -> None:
        """
        連続損失カウンターを更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        """
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
