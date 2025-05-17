import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy.typing as npt
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
        
    def detect_support_resistance_levels(self, df: pd.DataFrame, 
                                      window_size: int = 10, 
                                      swing_threshold: float = 0.0003,
                                      cluster_distance: float = 0.0005) -> pd.DataFrame:
        """
        サポート・レジスタンスレベルを検出する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータフレーム
        window_size : int, default 10
            スイングポイント検出のためのウィンドウサイズ
        swing_threshold : float, default 0.0003
            スイングポイントとみなす最小価格変動
        cluster_distance : float, default 0.0005
            クラスタリングの距離閾値
            
        Returns
        -------
        pd.DataFrame
            サポート・レジスタンスレベルが追加されたデータフレーム
        """
        result_df = df.copy()
        
        result_df['swing_high'] = False
        result_df['swing_low'] = False
        
        for i in range(window_size, len(result_df) - window_size):
            prev_window = result_df.iloc[i-window_size:i]
            next_window = result_df.iloc[i+1:i+window_size+1]
            current = result_df.iloc[i]
            
            if (current['High'] > prev_window['High'].max() and 
                current['High'] > next_window['High'].max() and
                current['High'] - max(prev_window['High'].max(), next_window['High'].max()) > swing_threshold):
                result_df.at[result_df.index[i], 'swing_high'] = True
            
            if (current['Low'] < prev_window['Low'].min() and 
                current['Low'] < next_window['Low'].min() and
                min(prev_window['Low'].min(), next_window['Low'].min()) - current['Low'] > swing_threshold):
                result_df.at[result_df.index[i], 'swing_low'] = True
        
        swing_highs = result_df.loc[result_df['swing_high'], 'High'].values
        swing_lows = result_df.loc[result_df['swing_low'], 'Low'].values
        
        support_levels = self._cluster_levels(swing_lows, cluster_distance)
        resistance_levels = self._cluster_levels(swing_highs, cluster_distance)
        
        recent_support = sorted(support_levels, key=lambda x: abs(x - result_df['Close'].iloc[-1]))[:3]
        recent_resistance = sorted(resistance_levels, key=lambda x: abs(x - result_df['Close'].iloc[-1]))[:3]
        
        result_df['support_level_1'] = recent_support[0] if recent_support else None
        result_df['support_level_2'] = recent_support[1] if len(recent_support) > 1 else None
        result_df['support_level_3'] = recent_support[2] if len(recent_support) > 2 else None
        
        result_df['resistance_level_1'] = recent_resistance[0] if recent_resistance else None
        result_df['resistance_level_2'] = recent_resistance[1] if len(recent_resistance) > 1 else None
        result_df['resistance_level_3'] = recent_resistance[2] if len(recent_resistance) > 2 else None
        
        return result_df
        
    def _cluster_levels(self, points: Any, distance_threshold: float) -> List[float]:
        """
        価格レベルをクラスタリングする
        
        Parameters
        ----------
        points : np.ndarray
            クラスタリング対象の価格点
        distance_threshold : float
            クラスタリングの距離閾値
            
        Returns
        -------
        List[float]
            クラスタリングされた価格レベル
        """
        if len(points) == 0:
            return []
            
        sorted_points = np.sort(points)
        clusters = []
        current_cluster = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i] - current_cluster[-1] < distance_threshold:
                current_cluster.append(sorted_points[i])
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [sorted_points[i]]
        
        if current_cluster:
            clusters.append(np.mean(current_cluster))
            
        return clusters
        
    def save_processed_data(self, df: pd.DataFrame, timeframe: str, 
                          processed_dir: str = 'data/processed') -> str:
        """
        処理済みデータをCSVファイルとして保存する
        
        Parameters
        ----------
        df : pd.DataFrame
            保存するデータフレーム
        timeframe : str
            時間足（例: '15min', '1H'）
        processed_dir : str, default 'data/processed'
            データ保存先のディレクトリ
            
        Returns
        -------
        str
            保存したファイルのパス
        """
        timeframe_dir = os.path.join(processed_dir, timeframe)
        os.makedirs(timeframe_dir, exist_ok=True)
        
        if isinstance(df.index, pd.DatetimeIndex):
            years = df.index.year.unique()
        else:
            years = pd.to_datetime(df.index).year.unique()
        
        saved_files = []
        for year in years:
            if isinstance(df.index, pd.DatetimeIndex):
                year_data = df[df.index.year == year]
            else:
                year_data = df[pd.to_datetime(df.index).year == year]
                
            if not year_data.empty:
                year_dir = os.path.join(timeframe_dir, str(year))
                os.makedirs(year_dir, exist_ok=True)
                file_path = os.path.join(year_dir, f'USDJPY_{timeframe}_{year}.csv')
                year_data.to_csv(file_path)
                saved_files.append(file_path)
                
        return ','.join(saved_files)
        
    def load_processed_data(self, timeframe: str, year: Optional[int] = None, 
                          processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        処理済みデータをCSVファイルから読み込む
        
        Parameters
        ----------
        timeframe : str
            時間足（例: '15min', '1H'）
        year : int, optional
            読み込む年。指定しない場合は全年のデータを読み込む
        processed_dir : str, default 'data/processed'
            データが保存されているディレクトリ
            
        Returns
        -------
        pd.DataFrame
            読み込んだデータフレーム。データが見つからない場合は空のDataFrame
        """
        timeframe_dir = os.path.join(processed_dir, timeframe)
        
        if not os.path.exists(timeframe_dir):
            return pd.DataFrame()
            
        if year is not None:
            year_dir = os.path.join(timeframe_dir, str(year))
            if not os.path.exists(year_dir):
                return pd.DataFrame()
                
            file_path = os.path.join(year_dir, f'USDJPY_{timeframe}_{year}.csv')
            if not os.path.exists(file_path):
                return pd.DataFrame()
                
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        
        dfs = []
        years = [d for d in os.listdir(timeframe_dir) if os.path.isdir(os.path.join(timeframe_dir, d))]
        
        for y in sorted(years):
            year_dir = os.path.join(timeframe_dir, y)
            files = [f for f in os.listdir(year_dir) if f.endswith('.csv')]
            
            for file in files:
                file_path = os.path.join(year_dir, file)
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                dfs.append(df)
                
        if not dfs:
            return pd.DataFrame()
            
        return pd.concat(dfs).sort_index()
