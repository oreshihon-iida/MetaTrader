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
            'sl_pips': 3.0,         # フェーズ2の2.5からフェーズ1の3.0に戻す
            'tp_pips': 7.5,         # フェーズ2の8.0からフェーズ1の7.5に戻す
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,  # フェーズ2の0.7からフェーズ1の0.8に戻す
            'atr_tp_multiplier': 2.0,  # フェーズ2の2.2からフェーズ1の2.0に戻す
            'use_adaptive_params': True,
            'trend_filter': False,
            'vol_filter': True,     # ボラティリティフィルターを有効化して高ボラティリティ時のみ取引
            'time_filter': True,
            'day_filter': True,     # 曜日フィルターを有効化
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
            'use_seasonal_filter': False,
            'use_price_action': False,
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        self.day_filter = kwargs.pop('day_filter', True)
        
        super().__init__(**kwargs)
        self.name = "改良版短期ボリンジャーバンド＋RSI戦略"
        
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        
        self.adaptive_rsi_upper = self.rsi_upper
        self.adaptive_rsi_lower = self.rsi_lower
        
    def _calculate_trend_strength(self, df: pd.DataFrame, i: int) -> float:
        """
        トレンド強度を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        float
            トレンド強度（-1.0〜1.0）
            正の値は上昇トレンド、負の値は下降トレンド、0に近い値はレンジ相場を示す
        """
        if i < 20:
            return 0.0
            
        short_ma = df['Close'].iloc[i-10:i].mean()
        long_ma = df['Close'].iloc[i-20:i].mean()
        
        price_direction = 1 if short_ma > long_ma else -1
        
        rsi_direction = 1 if df['rsi'].iloc[i] > 50 else -1
        
        trend_strength = price_direction * (abs(short_ma - long_ma) / long_ma) * 10
        
        if price_direction == rsi_direction:
            trend_strength *= 1.2
            
        return max(min(trend_strength, 1.0), -1.0)
        
    def _apply_filters(self, df: pd.DataFrame, i: int, signal: int = 0) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        改良版では時間フィルターと曜日フィルターを強化し、高勝率の時間帯と曜日に限定
        また、市場環境に応じてRSI閾値を動的に調整
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        signal : int, default 0
            シグナル（1: 買い、-1: 売り、0: シグナルなし）
            
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
            if not ((0 <= hour < 3) or (8 <= hour < 11) or (13 <= hour < 16)):
                return False
        
        if self.day_filter and hasattr(df.index[i], 'weekday'):
            weekday = df.index[i].weekday()
            if weekday in [0, 4]:
                rsi = df['rsi'].iloc[i]
                if signal > 0 and rsi > self.rsi_upper * 0.9:  # 買いシグナルの場合
                    return False
                if signal < 0 and rsi < self.rsi_lower * 1.1:  # 売りシグナルの場合
                    return False
        
        if self.use_adaptive_params:
            trend_strength = self._calculate_trend_strength(df, i)
            volatility = df['atr'].iloc[i] / df['atr'].rolling(window=20).mean().iloc[i] if i >= 20 else 1.0
            
            if volatility > 1.5:  # 高ボラティリティ
                self.adaptive_rsi_upper = 70
                self.adaptive_rsi_lower = 30
            elif abs(trend_strength) > 0.7:  # トレンド相場
                self.adaptive_rsi_upper = 55
                self.adaptive_rsi_lower = 45
            else:  # レンジ相場
                self.adaptive_rsi_upper = 65
                self.adaptive_rsi_lower = 35
                
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
