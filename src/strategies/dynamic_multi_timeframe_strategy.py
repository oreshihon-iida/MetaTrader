import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .improved_short_term_strategy import ImprovedShortTermStrategy

class DynamicMultiTimeframeStrategy(ImprovedShortTermStrategy):
    """
    動的パラメータ調整と強化された複数時間足分析を行う戦略
    
    市場環境に応じてパラメータを動的に調整し、複数時間足のデータを統合的に分析する
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            ImprovedShortTermStrategyに渡すパラメータ
        """
        self.market_regime_detection = kwargs.pop('market_regime_detection', True)
        self.dynamic_timeframe_weights = kwargs.pop('dynamic_timeframe_weights', True)
        self.volatility_based_params = kwargs.pop('volatility_based_params', True)
        
        default_params = {
            'bb_window': 20,
            'bb_dev': 1.3,    # 1.4から1.3に調整してさらにバンドに触れる頻度を増加
            'rsi_window': 14,
            'rsi_upper': 50,  # 51から50に調整してさらに取引機会を増加
            'rsi_lower': 50,  # 49から50に調整してさらに取引機会を増加
            'sl_pips': 2.5,
            'tp_pips': 12.5,
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,
            'atr_tp_multiplier': 2.0,
            'use_adaptive_params': True,
            'trend_filter': False,  # トレンドフィルターを無効化して取引機会を増加
            'vol_filter': False,    # ボラティリティフィルターを無効化して取引機会を増加
            'time_filter': True,
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0},  # 一時的に15分足のみに簡略化
            'use_seasonal_filter': False,  # 季節性フィルターを無効化して取引機会を増加
            'use_price_action': False,     # 価格アクションフィルターを無効化して取引機会を増加
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "動的複数時間足戦略"
        
        self.current_regime = 'unknown'  # 'trend', 'range', 'volatile'
        
        self.time_based_params = {
            'tokyo': {'rsi_upper': 58, 'rsi_lower': 42, 'bb_dev': 1.7},     # 東京時間は60/40→58/42に調整
            'london': {'rsi_upper': 53, 'rsi_lower': 47, 'bb_dev': 1.5},    # ロンドン時間は55/45→53/47に調整
            'ny': {'rsi_upper': 56, 'rsi_lower': 44, 'bb_dev': 1.6},        # NY時間は58/42→56/44に調整
            'overlap': {'rsi_upper': 51, 'rsi_lower': 49, 'bb_dev': 1.4},   # オーバーラップ時間は53/47→51/49に調整
        }
        
    def generate_signals(self, data: pd.DataFrame, year: int, data_dir: str) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        複数時間足データを読み込み、市場環境に応じてパラメータを調整し、シグナルを生成する
        
        Parameters
        ----------
        data : pd.DataFrame
            処理対象のデータ
        year : int
            対象年
        data_dir : str
            データディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルを含むデータフレーム
        """
        timeframes = list(self.timeframe_weights.keys())
        multi_tf_data = {}
        
        for tf in timeframes:
            if tf != data.index.freq:  # 現在のデータと異なる時間足のみ読み込む
                tf_dir = f"{data_dir}/{tf}/{year}"
                tf_file = f"{tf_dir}/USDJPY_{tf}_{year}.csv"
                
                try:
                    tf_data = pd.read_csv(tf_file, index_col=0, parse_dates=True)
                    multi_tf_data[tf] = tf_data
                except FileNotFoundError:
                    print(f"Warning: {tf_file} not found. Skipping this timeframe.")
        
        df = data.copy()
        
        df = self._calculate_technical_indicators(df)
        
        if self.market_regime_detection:
            df = self._detect_market_regime(df)
        
        df = self._adjust_params_by_time(df)
        
        if self.volatility_based_params:
            df = self._adjust_params_by_volatility(df)
        
        if self.dynamic_timeframe_weights and multi_tf_data:
            self._adjust_timeframe_weights(df, multi_tf_data)
        
        df['signal'] = 0
        
        for i in range(1, len(df)):
            consecutive_signals = 0
            for j in range(1, min(self.consecutive_limit + 1, i + 1)):
                if df['signal'].iloc[i-j] != 0:
                    consecutive_signals += 1
            
            if consecutive_signals >= self.consecutive_limit:
                continue
            
            if self.time_filter:
                hour = df.index[i].hour
                if not ((0 <= hour < 3) or (5 <= hour < 7) or (8 <= hour < 11) or (13 <= hour < 16) or (17 <= hour < 20)):
                    continue
                    
            if not self._apply_filters(df, i):
                continue
            
            rsi_upper_adjusted = self.rsi_upper
            rsi_lower_adjusted = self.rsi_lower
            bb_multiplier = 1.0
            
            if 'regime' in df.columns:
                current_regime = df['regime'].iloc[i]
                if current_regime == 'trend':
                    rsi_upper_adjusted = self.rsi_upper + 2
                    rsi_lower_adjusted = self.rsi_lower - 2
                    bb_multiplier = 0.98
                elif current_regime == 'range':
                    rsi_upper_adjusted = self.rsi_upper - 3
                    rsi_lower_adjusted = self.rsi_lower + 3
                    bb_multiplier = 1.05
                elif current_regime == 'volatile':
                    rsi_upper_adjusted = self.rsi_upper - 5
                    rsi_lower_adjusted = self.rsi_lower + 5
                    bb_multiplier = 1.1
            
            if (df['Close'].iloc[i] <= df['bb_lower'].iloc[i] * bb_multiplier and 
                df['rsi'].iloc[i] <= rsi_lower_adjusted):
                
                if self.use_price_action and not self._check_price_action_patterns(df, i):
                    continue
                
                if self.use_multi_timeframe and multi_tf_data:
                    if not self._check_multi_timeframe(df, i, multi_tf_data, 1):
                        continue
                
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] - self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] + self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = self.name
            
            elif (df['Close'].iloc[i] >= df['bb_upper'].iloc[i] * (2 - bb_multiplier) and 
                  df['rsi'].iloc[i] >= rsi_upper_adjusted):
                
                if self.use_price_action and not self._check_price_action_patterns(df, i):
                    continue
                
                if self.use_multi_timeframe and multi_tf_data:
                    if not self._check_multi_timeframe(df, i, multi_tf_data, -1):
                        continue
                
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] + self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] - self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = self.name
        
        return df
    
    def _detect_market_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        市場レジームを検出する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.DataFrame
            市場レジーム情報を含むデータフレーム
        """
        df['plus_dm'] = df['High'].diff().clip(lower=0)
        df['minus_dm'] = (-df['Low'].diff()).clip(lower=0)
        
        condition = df['High'].shift(1) - df['Low'].shift(1) > df['plus_dm'] + df['minus_dm']
        df.loc[condition, ['plus_dm', 'minus_dm']] = 0
        
        window = 14
        df['tr'] = df[['High', 'Close']].max(axis=1) - df[['Low', 'Close']].min(axis=1)
        df['atr14'] = df['tr'].rolling(window=window).mean()
        
        df['plus_di14'] = 100 * (df['plus_dm'].rolling(window=window).mean() / df['atr14'])
        df['minus_di14'] = 100 * (df['minus_dm'].rolling(window=window).mean() / df['atr14'])
        
        df['dx'] = 100 * abs(df['plus_di14'] - df['minus_di14']) / (df['plus_di14'] + df['minus_di14'])
        df['adx'] = df['dx'].rolling(window=window).mean()
        
        df['atr_ratio'] = df['atr14'] / df['atr14'].rolling(window=50).mean()
        
        df['regime'] = 'unknown'
        
        df.loc[df['adx'] > 25, 'regime'] = 'trend'
        
        df.loc[(df['adx'] < 20) & (df['atr_ratio'] < 1.1), 'regime'] = 'range'
        
        df.loc[df['atr_ratio'] > 1.3, 'regime'] = 'volatile'
        
        if len(df) > 0:
            self.current_regime = df['regime'].iloc[-1]
        
        return df
    
    def _adjust_params_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        時間帯に基づいてパラメータを調整する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.DataFrame
            調整後のデータフレーム
        """
        df['session'] = 'other'
        
        df.loc[(df.index.hour >= 0) & (df.index.hour < 6), 'session'] = 'tokyo'
        
        df.loc[(df.index.hour >= 8) & (df.index.hour < 16), 'session'] = 'london'
        
        df.loc[(df.index.hour >= 13) & (df.index.hour < 21), 'session'] = 'ny'
        
        df.loc[(df.index.hour >= 13) & (df.index.hour < 16), 'session'] = 'overlap'
        
        df['rsi_upper_adjusted'] = df['session'].map(
            lambda x: self.time_based_params.get(x, {'rsi_upper': self.rsi_upper})['rsi_upper']
        )
        
        df['rsi_lower_adjusted'] = df['session'].map(
            lambda x: self.time_based_params.get(x, {'rsi_lower': self.rsi_lower})['rsi_lower']
        )
        
        df['bb_dev_adjusted'] = df['session'].map(
            lambda x: self.time_based_params.get(x, {'bb_dev': self.bb_dev})['bb_dev']
        )
        
        return df
    
    def _adjust_params_by_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ボラティリティに基づいてパラメータを調整する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.DataFrame
            調整後のデータフレーム
        """
        if 'atr_ratio' not in df.columns:
            df['atr'] = df['Close'].rolling(window=self.atr_window).mean()
            df['atr_ratio'] = df['atr'] / df['atr'].rolling(window=50).mean()
        
        df['rsi_upper_vol_adjusted'] = df['rsi_upper_adjusted'].copy()
        df['rsi_lower_vol_adjusted'] = df['rsi_lower_adjusted'].copy()
        
        high_vol_mask = df['atr_ratio'] > 1.2
        df.loc[high_vol_mask, 'rsi_upper_vol_adjusted'] = df.loc[high_vol_mask, 'rsi_upper_adjusted'] + 5
        df.loc[high_vol_mask, 'rsi_lower_vol_adjusted'] = df.loc[high_vol_mask, 'rsi_lower_adjusted'] - 5
        
        low_vol_mask = df['atr_ratio'] < 0.8
        df.loc[low_vol_mask, 'rsi_upper_vol_adjusted'] = df.loc[low_vol_mask, 'rsi_upper_adjusted'] - 3
        df.loc[low_vol_mask, 'rsi_lower_vol_adjusted'] = df.loc[low_vol_mask, 'rsi_lower_adjusted'] + 3
        
        self.rsi_upper = df['rsi_upper_vol_adjusted'].iloc[-1] if len(df) > 0 else self.rsi_upper
        self.rsi_lower = df['rsi_lower_vol_adjusted'].iloc[-1] if len(df) > 0 else self.rsi_lower
        
        return df
    
    def _adjust_timeframe_weights(self, df: pd.DataFrame, multi_tf_data: Dict[str, pd.DataFrame]) -> None:
        """
        市場環境に基づいて時間足の重み付けを調整する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        multi_tf_data : Dict[str, pd.DataFrame]
            複数時間足のデータ
        """
        if 'regime' not in df.columns or len(df) == 0:
            return
        
        current_regime = df['regime'].iloc[-1]
        
        if current_regime == 'trend':
            self.timeframe_weights = {
                '5min': 1.0,
                '15min': 2.0,
                '30min': 3.0
            }
        elif current_regime == 'range':
            self.timeframe_weights = {
                '5min': 3.0,
                '15min': 1.5,
                '30min': 0.5
            }
        elif current_regime == 'volatile':
            self.timeframe_weights = {
                '5min': 1.5,
                '15min': 3.0,
                '30min': 1.5
            }
        else:
            self.timeframe_weights = {
                '5min': 2.0,
                '15min': 1.0,
                '30min': 0.5
            }
    
    def _check_multi_timeframe(self, df: pd.DataFrame, i: int, multi_tf_data: Dict[str, pd.DataFrame], direction: int) -> bool:
        """
        複数時間足のデータを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        multi_tf_data : Dict[str, pd.DataFrame]
            複数時間足のデータ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        bool
            複数時間足の確認がOKの場合はTrue、そうでない場合はFalse
        """
        current_time = df.index[i]
        confirmation_count = 0
        total_weight = 0
        
        for tf, tf_data in multi_tf_data.items():
            weight = self.timeframe_weights.get(tf, 1.0)
            total_weight += weight
            
            tf_idx = tf_data.index.get_indexer([current_time], method='pad')[0]
            
            if tf_idx < 0 or tf_idx >= len(tf_data):
                continue
                
            tf_row = tf_data.iloc[tf_idx]
            
            if direction == 1:
                if (tf_row['Close'] <= tf_row['bb_lower'] * 1.03 and tf_row['rsi'] <= self.rsi_lower + 2):
                    confirmation_count += weight
            else:
                if (tf_row['Close'] >= tf_row['bb_upper'] * 0.97 and tf_row['rsi'] >= self.rsi_upper - 2):
                    confirmation_count += weight
        
        confirmation_threshold = total_weight * 0.4  # 40%以上の時間足で確認が必要（50%から引き下げ）
        
        return confirmation_count >= confirmation_threshold
    
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        市場レジームに基づいてポジションサイズを調整
        
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
            
        base_size = super().calculate_position_size(signal, equity)
        
        if self.current_regime == 'trend':
            return base_size
        elif self.current_regime == 'range':
            return base_size * 0.8
        elif self.current_regime == 'volatile':
            return base_size * 0.7
        else:
            return base_size
