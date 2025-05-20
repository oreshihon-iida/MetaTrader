import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from src.utils.logger import Logger
from src.data.data_processor_enhanced import DataProcessor

class MultiTimeframeDataManager:
    """
    複数時間足のデータを管理するクラス
    
    特徴:
    - 日足/週足/月足データの効率的な処理
    - 時間足間の同期処理
    - 増分計算による最適化
    """
    
    def __init__(self, base_timeframe: str = "1D"):
        """
        初期化
        
        Parameters
        ----------
        base_timeframe : str
            基準となる時間足
        """
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        self.base_timeframe = base_timeframe
        self.data_processor = DataProcessor(pd.DataFrame())
        
        self.data_cache = {}
        
        self.last_updates = {}
        
        self.timeframe_hierarchy = {
            "1min": 0,
            "5min": 1,
            "15min": 2,
            "30min": 3,
            "1H": 4,
            "4H": 5,
            "1D": 6,
            "1W": 7,
            "1M": 8
        }
    
    def load_data(self, timeframes: List[str], years: List[int]) -> Dict[str, pd.DataFrame]:
        """
        複数の時間足のデータを読み込む
        
        Parameters
        ----------
        timeframes : List[str]
            読み込む時間足のリスト
        years : List[int]
            読み込む年のリスト
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
        """
        result = {}
        
        for timeframe in timeframes:
            timeframe_data = []
            
            for year in years:
                df = self.data_processor.load_processed_data(timeframe, year)
                if not df.empty:
                    timeframe_data.append(df)
                    self.logger.log_info(f"{timeframe}データ読み込み成功: {year}年, {len(df)}行")
                else:
                    self.logger.log_warning(f"{timeframe}データが見つかりません: {year}年")
            
            if timeframe_data:
                combined_df = pd.concat(timeframe_data)
                combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
                combined_df = combined_df.sort_index()
                
                result[timeframe] = combined_df
                self.data_cache[timeframe] = combined_df
                self.last_updates[timeframe] = datetime.now()
            else:
                self.logger.log_error(f"{timeframe}データが読み込めませんでした")
        
        return result
    
    def synchronize_timeframes(self, data_dict: Dict[str, pd.DataFrame], base_timeframe: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        異なる時間足のデータを同期する
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
        base_timeframe : Optional[str]
            基準となる時間足（指定がなければself.base_timeframeを使用）
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            同期されたデータフレーム辞書
        """
        if not base_timeframe:
            base_timeframe = self.base_timeframe
            
        if base_timeframe not in data_dict:
            self.logger.log_error(f"基準時間足 {base_timeframe} のデータがありません")
            return data_dict
            
        base_df = data_dict[base_timeframe]
        result = {base_timeframe: base_df}
        
        for timeframe, df in data_dict.items():
            if self.timeframe_hierarchy[timeframe] < self.timeframe_hierarchy[base_timeframe]:
                resampled_df = self._resample_to_base(df, base_df.index, timeframe, base_timeframe)
                result[timeframe] = resampled_df
            
            elif self.timeframe_hierarchy[timeframe] > self.timeframe_hierarchy[base_timeframe]:
                downsampled_df = self._downsample_to_base(df, base_df.index, timeframe, base_timeframe)
                result[timeframe] = downsampled_df
        
        return result
    
    def _resample_to_base(self, df: pd.DataFrame, base_index: pd.DatetimeIndex, timeframe: str, base_timeframe: str) -> pd.DataFrame:
        """
        短い時間足のデータを基準時間足に集約する
        
        Parameters
        ----------
        df : pd.DataFrame
            集約するデータフレーム
        base_index : pd.DatetimeIndex
            基準時間足のインデックス
        timeframe : str
            集約する時間足
        base_timeframe : str
            基準時間足
            
        Returns
        -------
        pd.DataFrame
            集約されたデータフレーム
        """
        result = pd.DataFrame(index=base_index)
        
        column_mapping = {}
        for col in df.columns:
            column_mapping[col.lower()] = col
            
        agg_dict = {}
        
        if 'open' in column_mapping:
            agg_dict[column_mapping['open']] = 'first'
        elif 'Open' in df.columns:
            agg_dict['Open'] = 'first'
            
        if 'high' in column_mapping:
            agg_dict[column_mapping['high']] = 'max'
        elif 'High' in df.columns:
            agg_dict['High'] = 'max'
            
        if 'low' in column_mapping:
            agg_dict[column_mapping['low']] = 'min'
        elif 'Low' in df.columns:
            agg_dict['Low'] = 'min'
            
        if 'close' in column_mapping:
            agg_dict[column_mapping['close']] = 'last'
        elif 'Close' in df.columns:
            agg_dict['Close'] = 'last'
            
        if 'volume' in column_mapping:
            agg_dict[column_mapping['volume']] = 'sum'
        elif 'Volume' in df.columns:
            agg_dict['Volume'] = 'sum'
            
        for col in df.columns:
            if col not in agg_dict:
                agg_dict[col] = 'last'
        
        if base_timeframe == "1D":
            freq = 'D'
        elif base_timeframe == "1W":
            freq = 'W-FRI'
        elif base_timeframe == "1M":
            freq = 'M'
        else:
            freq_map = {"1H": "1H", "4H": "4H"}
            freq = freq_map.get(base_timeframe, "1D")
        
        resampled = df.resample(freq).agg(agg_dict)
        
        common_index = base_index.intersection(resampled.index)
        result = pd.DataFrame(index=base_index, columns=resampled.columns)
        result.loc[common_index] = resampled.loc[common_index]
        
        return result
    
    def _downsample_to_base(self, df: pd.DataFrame, base_index: pd.DatetimeIndex, timeframe: str, base_timeframe: str) -> pd.DataFrame:
        """
        長い時間足のデータを基準時間足にダウンサンプルする
        
        Parameters
        ----------
        df : pd.DataFrame
            ダウンサンプルするデータフレーム
        base_index : pd.DatetimeIndex
            基準時間足のインデックス
        timeframe : str
            ダウンサンプルする時間足
        base_timeframe : str
            基準時間足
            
        Returns
        -------
        pd.DataFrame
            ダウンサンプルされたデータフレーム
        """
        result = pd.DataFrame(index=base_index, columns=df.columns)
        
        if isinstance(df.index, pd.DatetimeIndex):
            if timeframe == "1W" and base_timeframe == "1D":
                for week_start, row in df.iterrows():
                    week_end = week_start + timedelta(days=6)
                    week_dates = pd.date_range(week_start, week_end, freq='D')
                    
                    common_dates = base_index.intersection(week_dates)
                    
                    for date in common_dates:
                        result.loc[date] = row
            
            elif timeframe == "1M" and base_timeframe in ["1D", "1W"]:
                for month_start, row in df.iterrows():
                    next_month = month_start + pd.offsets.MonthEnd(1)
                    month_dates = pd.date_range(month_start, next_month, freq='D')
                    
                    common_dates = base_index.intersection(month_dates)
                    
                    for date in common_dates:
                        result.loc[date] = row
            
            else:
                for date in base_index:
                    mask = df.index <= date
                    if mask.any():
                        closest_idx = df.index[mask][-1]
                        result.loc[date] = df.loc[closest_idx]
        
        return result
    
    def calculate_indicators(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        各時間足のテクニカル指標を計算する
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            指標が計算されたデータフレーム辞書
        """
        result = {}
        
        for timeframe, df in data_dict.items():
            if df.empty:
                result[timeframe] = df
                continue
                
            processed_df = df.copy()
            
            column_mapping = {}
            for col in processed_df.columns:
                column_mapping[col.lower()] = col
            
            close_col = None
            high_col = None
            low_col = None
            
            if 'close' in column_mapping:
                close_col = column_mapping['close']
            elif 'Close' in processed_df.columns:
                close_col = 'Close'
                
            if 'high' in column_mapping:
                high_col = column_mapping['high']
            elif 'High' in processed_df.columns:
                high_col = 'High'
                
            if 'low' in column_mapping:
                low_col = column_mapping['low']
            elif 'Low' in processed_df.columns:
                low_col = 'Low'
            
            if close_col is not None:
                processed_df['bb_middle'] = processed_df[close_col].rolling(window=20).mean()
                rolling_std = processed_df[close_col].rolling(window=20).std()
                processed_df['bb_upper'] = processed_df['bb_middle'] + 2 * rolling_std
                processed_df['bb_lower'] = processed_df['bb_middle'] - 2 * rolling_std
                
                delta = processed_df[close_col].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                processed_df['rsi'] = 100 - (100 / (1 + rs))
                
                processed_df['sma_50'] = processed_df[close_col].rolling(window=50).mean()
                processed_df['sma_200'] = processed_df[close_col].rolling(window=200).mean()
            
            if high_col is not None and low_col is not None and close_col is not None:
                processed_df['tr1'] = abs(processed_df[high_col] - processed_df[low_col])
                processed_df['tr2'] = abs(processed_df[high_col] - processed_df[close_col].shift(1))
                processed_df['tr3'] = abs(processed_df[low_col] - processed_df[close_col].shift(1))
            processed_df['tr'] = processed_df[['tr1', 'tr2', 'tr3']].max(axis=1)
            processed_df['atr'] = processed_df['tr'].rolling(window=14).mean()
            
            processed_df['plus_dm'] = processed_df['High'].diff()
            processed_df['minus_dm'] = processed_df['Low'].shift(1) - processed_df['Low']
            processed_df['plus_dm'] = processed_df['plus_dm'].where(
                (processed_df['plus_dm'] > 0) & (processed_df['plus_dm'] > processed_df['minus_dm']), 0)
            processed_df['minus_dm'] = processed_df['minus_dm'].where(
                (processed_df['minus_dm'] > 0) & (processed_df['minus_dm'] > processed_df['plus_dm']), 0)
            processed_df['plus_di'] = 100 * (processed_df['plus_dm'].rolling(window=14).mean() / processed_df['atr'])
            processed_df['minus_di'] = 100 * (processed_df['minus_dm'].rolling(window=14).mean() / processed_df['atr'])
            
            processed_df['dx'] = 100 * abs(processed_df['plus_di'] - processed_df['minus_di']) / (processed_df['plus_di'] + processed_df['minus_di'])
            processed_df['adx'] = processed_df['dx'].rolling(window=14).mean()
            
            processed_df.drop(['tr1', 'tr2', 'tr3', 'tr', 'plus_dm', 'minus_dm', 'dx'], axis=1, inplace=True, errors='ignore')
            
            result[timeframe] = processed_df
        
        return result
    
    def detect_market_regime(self, data_dict: Dict[str, pd.DataFrame], base_timeframe: Optional[str] = None) -> Tuple[str, float]:
        """
        市場レジームを検出する
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
        base_timeframe : Optional[str]
            基準となる時間足（指定がなければself.base_timeframeを使用）
            
        Returns
        -------
        Tuple[str, float]
            市場レジーム（"trend", "range", "volatile", "normal"）とその強度
        """
        if not base_timeframe:
            base_timeframe = self.base_timeframe
            
        if base_timeframe not in data_dict:
            self.logger.log_error(f"基準時間足 {base_timeframe} のデータがありません")
            return "normal", 0.0
            
        df = data_dict[base_timeframe]
        
        if df.empty or 'adx' not in df.columns or 'atr' not in df.columns:
            return "normal", 0.0
            
        latest = df.iloc[-1]
        
        adx = latest['adx']
        
        atr = latest['atr']
        atr_percentile = df['atr'].rank(pct=True).iloc[-1]
        
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            bb_width = (latest['bb_upper'] - latest['bb_lower']) / latest['bb_middle']
            bb_width_percentile = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']).rank(pct=True).iloc[-1]
        else:
            bb_width = 0
            bb_width_percentile = 0
            
        trend_score = min(1.0, (adx - 20) / 30) if adx > 20 else 0  # ADX 20-50を0-1にスケール
        volatility_score = min(1.0, (atr_percentile - 0.7) / 0.3) if atr_percentile > 0.7 else 0  # 0.7-1.0を0-1にスケール
        range_score = min(1.0, (0.4 - bb_width_percentile) / 0.4) if bb_width_percentile < 0.4 else 0  # 0-0.4を1-0にスケール
        
        if trend_score > volatility_score and trend_score > range_score and trend_score > 0.3:
            regime = "trend"
            strength = trend_score
        elif volatility_score > trend_score and volatility_score > range_score and volatility_score > 0.3:
            regime = "volatile"
            strength = volatility_score
        elif range_score > trend_score and range_score > volatility_score and range_score > 0.3:
            regime = "range"
            strength = range_score
        else:
            regime = "normal"
            strength = 0.5
            
        return regime, strength
