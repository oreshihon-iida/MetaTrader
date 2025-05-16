import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator

class DataProcessor:
    """
    FXデータを処理するクラス
    1分足から15分足へのリサンプリング、テクニカル指標の計算など
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初期化
        
        Parameters
        ----------
        data : pd.DataFrame
            処理対象のデータ（1分足）
        """
        self.data = data
    
    def resample(self, timeframe: str = '15T') -> pd.DataFrame:
        """
        指定された時間足にリサンプリングする
        
        Parameters
        ----------
        timeframe : str, default '15T'
            リサンプリングする時間足（pandas resampleの形式）
            例: '15T'=15分, '1H'=1時間
        
        Returns
        -------
        pd.DataFrame
            リサンプリングされたデータ
        """
        resampled = self.data.resample(timeframe).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return resampled
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を追加する
        
        Parameters
        ----------
        df : pd.DataFrame
            テクニカル指標を追加するDataFrame
            
        Returns
        -------
        pd.DataFrame
            テクニカル指標が追加されたDataFrame
        """
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        
        rsi = RSIIndicator(close=df['Close'], window=14)
        df['rsi'] = rsi.rsi()
        
        return df
    
    def get_tokyo_session_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        東京時間のレンジ（高値・安値）を追加する
        
        Parameters
        ----------
        df : pd.DataFrame
            東京時間のレンジを追加するDataFrame
            
        Returns
        -------
        pd.DataFrame
            東京時間のレンジが追加されたDataFrame
        """
        df_jst = df.copy()
        df_jst.index = df_jst.index + pd.Timedelta(hours=9)
        
        df_jst['date'] = df_jst.index.date
        
        tokyo_session = df_jst.between_time('09:00', '15:00')
        
        daily_highs = tokyo_session.groupby('date')['High'].max()
        daily_lows = tokyo_session.groupby('date')['Low'].min()
        
        df['date'] = df.index.date
        df = df.merge(
            pd.DataFrame({'tokyo_high': daily_highs, 'tokyo_low': daily_lows}),
            left_on='date',
            right_index=True,
            how='left'
        )
        
        df[['tokyo_high', 'tokyo_low']] = df.groupby('date')[['tokyo_high', 'tokyo_low']].fillna(method='ffill')
        
        df = df.drop('date', axis=1)
        
        return df
