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
                                      cluster_distance: float = 0.0005,
                                      max_level_count: int = 3,
                                      vol_lookback: int = 50,
                                      adaptive_params: bool = True) -> pd.DataFrame:
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
        max_level_count : int, default 3
            抽出するサポート/レジスタンスレベルの最大数
        vol_lookback : int, default 50
            ボラティリティ計算のための過去データ数
        adaptive_params : bool, default True
            市場ボラティリティに基づいてパラメータを調整するかどうか
            
        Returns
        -------
        pd.DataFrame
            サポート・レジスタンスレベルが追加されたデータフレーム
        """
        result_df = df.copy()
        
        if adaptive_params:
            high = result_df['High']
            low = result_df['Low']
            close = result_df['Close'].shift(1).fillna(result_df['Close'].iloc[0])
            
            high_minus_low = high - low
            high_minus_close = (high - close).abs()
            low_minus_close = (low - close).abs()
            
            true_range = pd.concat([high_minus_low, high_minus_close, low_minus_close], axis=1).max(axis=1)
            atr = true_range.rolling(vol_lookback).mean()
            
            atr_mean = atr.mean()
            if atr_mean > 0:
                atr_ratio = atr / atr_mean
                atr_ratio = atr_ratio.fillna(1.0)
            else:
                atr_ratio = pd.Series(1.0, index=atr.index)
                
            dynamic_swing_threshold = pd.Series(swing_threshold, index=result_df.index)
            dynamic_cluster_distance = pd.Series(cluster_distance, index=result_df.index)
            
            mask = atr_ratio > 0
            dynamic_swing_threshold = dynamic_swing_threshold.mask(mask, swing_threshold * atr_ratio)
            dynamic_cluster_distance = dynamic_cluster_distance.mask(mask, cluster_distance * atr_ratio)
            
            dynamic_swing_threshold = dynamic_swing_threshold.values
            dynamic_cluster_distance = dynamic_cluster_distance.values
        else:
            dynamic_swing_threshold = np.full(len(result_df), swing_threshold)
            dynamic_cluster_distance = np.full(len(result_df), cluster_distance)
        
        swing_highs = []
        swing_lows = []
        
        prices = result_df['Close'].values
        dates = result_df.index
        
        for i in range(window_size, len(prices) - window_size):
            current_swing_threshold = dynamic_swing_threshold[i]
            
            is_swing_high = True
            for j in range(1, window_size + 1):
                if prices[i] < prices[i - j] or prices[i] < prices[i + j]:
                    is_swing_high = False
                    break
                    
            if is_swing_high and (len(swing_highs) == 0 or prices[i] - prices[swing_highs[-1]] > current_swing_threshold):
                swing_highs.append(i)
            
            is_swing_low = True
            for j in range(1, window_size + 1):
                if prices[i] > prices[i - j] or prices[i] > prices[i + j]:
                    is_swing_low = False
                    break
                    
            if is_swing_low and (len(swing_lows) == 0 or prices[swing_lows[-1]] - prices[i] > current_swing_threshold):
                swing_lows.append(i)
        
        resistance_levels = self._improved_cluster_levels(prices, swing_highs, dynamic_cluster_distance[len(dynamic_cluster_distance)//2])
        support_levels = self._improved_cluster_levels(prices, swing_lows, dynamic_cluster_distance[len(dynamic_cluster_distance)//2])
        
        last_price = prices[-1]
        
        valid_support = [level for level in support_levels if level < last_price]
        valid_support.sort(key=lambda x: last_price - x)
        valid_support = valid_support[:max_level_count]
        
        valid_resistance = [level for level in resistance_levels if level > last_price]
        valid_resistance.sort(key=lambda x: x - last_price)
        valid_resistance = valid_resistance[:max_level_count]
        
        for i, level in enumerate(valid_support):
            result_df[f'support_level_{i+1}'] = level
            
        for i, level in enumerate(valid_resistance):
            result_df[f'resistance_level_{i+1}'] = level
        
        return result_df
        
    def _improved_cluster_levels(self, prices: Any, points: List[int], cluster_distance: float) -> List[float]:
        """
        価格レベルをクラスタリングする（改良版）
        
        Parameters
        ----------
        prices : np.ndarray
            価格配列
        points : list
            クラスタリング対象のインデックス
        cluster_distance : float
            クラスタリングの距離閾値
            
        Returns
        -------
        list
            クラスタリングされた価格レベル
        """
        if len(points) == 0:
            return []
        
        price_points = [prices[i] for i in points]
        
        strength = {}
        for p in price_points:
            for p2 in price_points:
                if abs(p - p2) < cluster_distance:
                    strength[p] = strength.get(p, 0) + 1
        
        clusters = []
        visited = set()
        
        for p in sorted(price_points, key=lambda x: strength.get(x, 0), reverse=True):
            if p in visited:
                continue
                
            cluster = []
            self._expand_cluster(p, price_points, cluster, visited, cluster_distance)
            
            if cluster:
                weighted_sum = sum(p * strength.get(p, 1) for p in cluster)
                total_weight = sum(strength.get(p, 1) for p in cluster)
                cluster_avg = weighted_sum / total_weight if total_weight > 0 else 0
                clusters.append(cluster_avg)
        
        return clusters
        
    def _expand_cluster(self, point: float, points: List[float], cluster: List[float], visited: set, cluster_distance: float):
        """
        クラスタを拡張する（DBSCAN風）
        
        Parameters
        ----------
        point : float
            拡張の起点となる価格ポイント
        points : list
            全ての価格ポイント
        cluster : list
            現在のクラスタ
        visited : set
            訪問済みのポイント
        cluster_distance : float
            クラスタリングの距離閾値
        """
        cluster.append(point)
        visited.add(point)
        
        for p in points:
            if p not in visited and abs(point - p) < cluster_distance:
                self._expand_cluster(p, points, cluster, visited, cluster_distance)
                
    def _cluster_levels(self, points: Any, distance_threshold: float) -> List[float]:
        """
        価格レベルをクラスタリングする（旧バージョン）
        
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
        
    def merge_multi_timeframe_levels(self, df_15min: pd.DataFrame, df_1h: pd.DataFrame, max_levels: int = 3) -> pd.DataFrame:
        """
        複数時間足のサポート/レジスタンスレベルを統合する
        
        Parameters
        ----------
        df_15min : pd.DataFrame
            15分足のデータフレーム（サポート/レジスタンスレベル付き）
        df_1h : pd.DataFrame
            1時間足のデータフレーム（サポート/レジスタンスレベル付き）
        max_levels : int, default 3
            各カテゴリで保持するレベルの最大数
            
        Returns
        -------
        pd.DataFrame
            統合されたレベルを持つ15分足のデータフレーム
        """
        result_df = df_15min.copy()
        
        hour_support_levels = {}
        hour_resistance_levels = {}
        
        for i in range(1, max_levels + 1):
            if f'support_level_{i}' in df_1h.columns:
                hour_support_levels[i] = df_1h[f'support_level_{i}'].resample('15T').ffill()
            
            if f'resistance_level_{i}' in df_1h.columns:
                hour_resistance_levels[i] = df_1h[f'resistance_level_{i}'].resample('15T').ffill()
        
        for i in range(1, max_levels + 1):
            if i in hour_support_levels:
                result_df[f'h1_support_level_{i}'] = hour_support_levels[i]
            
            if i in hour_resistance_levels:
                result_df[f'h1_resistance_level_{i}'] = hour_resistance_levels[i]
        
        return result_df
