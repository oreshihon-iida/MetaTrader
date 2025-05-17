import pandas as pd
import numpy as np
from typing import Dict, Optional
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class TrendStrengthIndex:
    """
    トレンド強度指標（Trend Strength Index）
    
    ボリンジャーバンドとRSIに加えて、複数の移動平均線を組み合わせたトレンド強度指標
    """
    
    def __init__(self, price_data: pd.DataFrame, window_short: int = 20, window_med: int = 50, window_long: int = 200):
        """
        初期化
        
        Parameters
        ----------
        price_data : pd.DataFrame
            価格データ（OHLC形式）
        window_short : int, default 20
            短期移動平均線の期間
        window_med : int, default 50
            中期移動平均線の期間
        window_long : int, default 200
            長期移動平均線の期間
        """
        self.data = price_data
        self.window_short = window_short
        self.window_med = window_med
        self.window_long = window_long
    
    def calculate(self) -> pd.Series:
        """
        トレンド強度指標を計算する
        
        Returns
        -------
        pd.Series
            トレンド強度指標（-1.0〜1.0の範囲、正の値は上昇トレンド、負の値は下降トレンド）
        """
        ma_short = self.data['Close'].rolling(self.window_short).mean()
        ma_med = self.data['Close'].rolling(self.window_med).mean()
        ma_long = self.data['Close'].rolling(self.window_long).mean()
        
        trend_strength = pd.Series(0, index=self.data.index)
        
        uptrend = (ma_short > ma_med) & (ma_med > ma_long) & (self.data['Close'] > ma_short)
        downtrend = (ma_short < ma_med) & (ma_med < ma_long) & (self.data['Close'] < ma_short)
        
        rsi = RSIIndicator(close=self.data['Close'], window=14).rsi()
        
        trend_strength[uptrend] = 1
        
        trend_strength[downtrend] = -1
        
        trend_strength[(uptrend) & (rsi > 50)] += 0.5
        trend_strength[(downtrend) & (rsi < 50)] -= 0.5
        
        trend_strength = trend_strength / 1.5
        
        return trend_strength


class VolatilityAdjustedOscillator:
    """
    ボラティリティ調整型オシレーター（Volatility-Adjusted Oscillator）
    
    ボラティリティに応じてRSIの感度を調整する新しいオシレーター
    """
    
    def __init__(self, price_data: pd.DataFrame, rsi_window: int = 14, vol_window: int = 20):
        """
        初期化
        
        Parameters
        ----------
        price_data : pd.DataFrame
            価格データ（OHLC形式）
        rsi_window : int, default 14
            RSIの期間
        vol_window : int, default 20
            ボラティリティ（ATR）の期間
        """
        self.data = price_data
        self.rsi_window = rsi_window
        self.vol_window = vol_window
    
    def calculate(self) -> tuple:
        """
        ボラティリティ調整型オシレーターを計算する
        
        Returns
        -------
        tuple
            (ボラティリティ調整型オシレーター値, 調整後の上限閾値, 調整後の下限閾値)
        """
        rsi = RSIIndicator(close=self.data['Close'], window=self.rsi_window).rsi()
        
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.rolling(self.vol_window).mean()
        
        avg_atr = atr.rolling(100).mean()
        
        vol_ratio = atr / avg_atr
        vol_ratio = vol_ratio.fillna(1.0)
        
        adjusted_upper = 50 + (25 * vol_ratio).clip(20, 30)
        adjusted_lower = 50 - (25 * vol_ratio).clip(20, 30)
        
        vao = pd.Series(0, index=self.data.index)
        
        vao[rsi > adjusted_upper] = 1
        
        vao[rsi < adjusted_lower] = -1
        
        mid_zone = (rsi >= adjusted_lower) & (rsi <= adjusted_upper)
        vao[mid_zone] = (rsi[mid_zone] - 50) / (adjusted_upper.mean() - 50)
        
        return vao, adjusted_upper, adjusted_lower


class MultiTimeframeConfirmationIndex:
    """
    マルチタイムフレーム確認指標（Multi-Timeframe Confirmation Index）
    
    複数の時間足からの確認を行い、偽シグナルを減らす指標
    """
    
    def __init__(self, tf_data_dict: Dict[str, pd.DataFrame], indicator_func):
        """
        初期化
        
        Parameters
        ----------
        tf_data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム（例: {'15min': df_15min, '1H': df_1h, '4H': df_4h}）
        indicator_func : function
            指標計算関数（データフレームを受け取り、指標値のSeriesを返す関数）
        """
        self.tf_data = tf_data_dict
        self.indicator_func = indicator_func
        
    def calculate(self, base_tf: str = '15min', weights: Optional[Dict[str, float]] = None) -> pd.Series:
        """
        マルチタイムフレーム確認指標を計算する
        
        Parameters
        ----------
        base_tf : str, default '15min'
            ベースとなる時間足
        weights : Dict[str, float], optional
            各時間足の重み（例: {'15min': 1.0, '1H': 2.0, '4H': 3.0}）
            
        Returns
        -------
        pd.Series
            マルチタイムフレーム確認指標値
        """
        if weights is None:
            weights = {
                '15min': 1.0,
                '1H': 2.0,
                '4H': 3.0
            }
        
        tf_indicators = {}
        for tf, df in self.tf_data.items():
            tf_indicators[tf] = self.indicator_func(df)
        
        base_index = self.tf_data[base_tf].index
        
        confirmation_index = pd.Series(0.0, index=base_index)
        
        total_weight = sum(weights.values())
        
        for tf, indicator in tf_indicators.items():
            if tf == base_tf:
                resampled_indicator = indicator
            else:
                resampled_indicator = indicator.reindex(base_index, method='ffill')
            
            confirmation_index += (resampled_indicator * weights[tf]) / total_weight
        
        return confirmation_index
