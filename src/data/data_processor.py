import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Optional, List, Tuple
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
    
    def resample(self, timeframe: str = '15min') -> pd.DataFrame:
        """
        指定された時間足にリサンプリングする
        
        Parameters
        ----------
        timeframe : str, default '15min'
            リサンプリングする時間足（pandas resampleの形式）
            例: '15min'=15分, '1H'=1時間
        
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
        
        if isinstance(df_jst.index, pd.DatetimeIndex):
            df_jst['date'] = df_jst.index.strftime('%Y-%m-%d')
        else:
            df_jst['date'] = pd.to_datetime(df_jst.index).strftime('%Y-%m-%d')
        
        tokyo_session = df_jst.between_time('09:00', '15:00')
        
        daily_highs = tokyo_session.groupby('date')['High'].max()
        daily_lows = tokyo_session.groupby('date')['Low'].min()
        
        if isinstance(df.index, pd.DatetimeIndex):
            df['date'] = df.index.strftime('%Y-%m-%d')
        else:
            df['date'] = pd.to_datetime(df.index).strftime('%Y-%m-%d')
        
        df = df.merge(
            pd.DataFrame({'tokyo_high': daily_highs, 'tokyo_low': daily_lows}),
            left_on='date',
            right_index=True,
            how='left'
        )
        
        for group_name, group_data in df.groupby('date'):
            mask = group_data.index
            df.loc[mask, ['tokyo_high', 'tokyo_low']] = group_data[['tokyo_high', 'tokyo_low']].ffill()
        
        df = df.drop('date', axis=1)
        
        return df
