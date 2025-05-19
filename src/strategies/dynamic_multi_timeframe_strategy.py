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
        self.confirmation_threshold = kwargs.pop('confirmation_threshold', 0.4)  # 確認閾値（デフォルト0.4）
        self.expand_time_filter = kwargs.pop('expand_time_filter', False)  # 時間フィルターの拡大（デフォルトFalse）
        self.disable_time_filter = kwargs.pop('disable_time_filter', False)  # 時間フィルターの無効化（デフォルトFalse）
        self.disable_multi_timeframe = kwargs.pop('disable_multi_timeframe', False)  # 複数時間足確認の無効化（デフォルトFalse）
        self.use_price_only_signals = kwargs.pop('use_price_only_signals', False)  # 価格のみに基づくシグナル生成（デフォルトFalse）
        self.use_moving_average = kwargs.pop('use_moving_average', False)  # 移動平均を使用（デフォルトFalse）
        self.ma_fast_period = kwargs.pop('ma_fast_period', 5)  # 短期移動平均期間
        self.ma_slow_period = kwargs.pop('ma_slow_period', 20)  # 長期移動平均期間
        self.use_adx_filter = kwargs.pop('use_adx_filter', False)  # ADXフィルターを使用（デフォルトFalse）
        self.adx_threshold = kwargs.pop('adx_threshold', 25)  # ADX閾値（デフォルト25）
        self.use_pattern_filter = kwargs.pop('use_pattern_filter', False)  # パターンフィルターを使用（デフォルトFalse）
        self.use_quality_filter = kwargs.pop('use_quality_filter', False)  # 品質フィルターを使用（デフォルトFalse）
        self.quality_threshold = kwargs.pop('quality_threshold', 0.7)  # 品質閾値（デフォルト0.7）
        
        self.consecutive_wins = 0
        self.max_consecutive_wins = 5
        self.total_trades = 0
        self.winning_trades = 0
        self.win_rate = 0.0
        
        default_params = {
            'bb_window': 20,
            'bb_dev': 0.8,    # 1.0から0.8に縮小してさらにバンドに触れる頻度を大幅増加
            'rsi_window': 7,  # 14から7に短縮して反応速度を上げる
            'rsi_upper': 50,  # 中立値を維持
            'rsi_lower': 50,  # 中立値を維持
            'sl_pips': 2.5,
            'tp_pips': 12.5,
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,
            'atr_tp_multiplier': 2.0,
            'use_adaptive_params': True,
            'trend_filter': False,  # トレンドフィルターを無効化
            'vol_filter': False,    # ボラティリティフィルターを無効化
            'time_filter': False,   # 時間フィルターをデフォルトで無効化
            'use_multi_timeframe': False,  # 複数時間足確認をデフォルトで無効化
            'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
            'use_seasonal_filter': False,  # 季節性フィルターを無効化
            'use_price_action': False,     # 価格アクションフィルターを無効化
            'consecutive_limit': 1  # 連続シグナル制限を1に緩和
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
        
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.DataFrame
            テクニカル指標を含むデータフレーム
        """
        df = super()._calculate_technical_indicators(df)
        
        if self.use_moving_average:
            df['ma_fast'] = df['Close'].rolling(window=self.ma_fast_period).mean()
            df['ma_slow'] = df['Close'].rolling(window=self.ma_slow_period).mean()
            df['ma_cross'] = 0
            
            for i in range(1, len(df)):
                if pd.notna(df['ma_fast'].iloc[i-1]) and pd.notna(df['ma_slow'].iloc[i-1]) and pd.notna(df['ma_fast'].iloc[i]) and pd.notna(df['ma_slow'].iloc[i]):
                    if df['ma_fast'].iloc[i-1] < df['ma_slow'].iloc[i-1] and df['ma_fast'].iloc[i] >= df['ma_slow'].iloc[i]:
                        df.loc[df.index[i], 'ma_cross'] = 1  # ゴールデンクロス（買い）
                    elif df['ma_fast'].iloc[i-1] > df['ma_slow'].iloc[i-1] and df['ma_fast'].iloc[i] <= df['ma_slow'].iloc[i]:
                        df.loc[df.index[i], 'ma_cross'] = -1  # デッドクロス（売り）
        
        return df
        
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
            
            if self.time_filter and not self.disable_time_filter:
                hour = df.index[i].hour
                if self.expand_time_filter:
                    if not ((0 <= hour < 3) or (4 <= hour < 21)):
                        continue
                else:
                    if not ((0 <= hour < 3) or (5 <= hour < 7) or (8 <= hour < 11) or (13 <= hour < 16) or (17 <= hour < 20)):
                        continue
                    
            if not self._apply_filters(df, i):
                continue
            
            if self.use_price_only_signals:
                if i >= 3:  # 少なくとも3つの過去の価格ポイントが必要
                    if (df['Close'].iloc[i-3] < df['Close'].iloc[i-2] < df['Close'].iloc[i-1] < df['Close'].iloc[i]):
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                        df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] + self.sl_pips * 0.01
                        df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] - self.tp_pips * 0.01
                        df.loc[df.index[i], 'strategy'] = f"{self.name} (価格のみ)"
                    elif (df['Close'].iloc[i-3] > df['Close'].iloc[i-2] > df['Close'].iloc[i-1] > df['Close'].iloc[i]):
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                        df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] - self.sl_pips * 0.01
                        df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] + self.tp_pips * 0.01
                        df.loc[df.index[i], 'strategy'] = f"{self.name} (価格のみ)"
                continue  # 価格のみのシグナル生成を使用する場合は、他のシグナル生成ロジックをスキップ
            
            if self.use_moving_average and 'ma_cross' in df.columns:
                if df['ma_cross'].iloc[i] == 1:  # ゴールデンクロス（買い）
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                    df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] - self.sl_pips * 0.01
                    df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] + self.tp_pips * 0.01
                    df.loc[df.index[i], 'strategy'] = f"{self.name} (MA)"
                    continue  # 移動平均シグナルが生成された場合は、他のシグナル生成ロジックをスキップ
                elif df['ma_cross'].iloc[i] == -1:  # デッドクロス（売り）
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                    df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] + self.sl_pips * 0.01
                    df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] - self.tp_pips * 0.01
                    df.loc[df.index[i], 'strategy'] = f"{self.name} (MA)"
                    continue  # 移動平均シグナルが生成された場合は、他のシグナル生成ロジックをスキップ
            
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
            
            if (df['Close'].iloc[i] <= df['bb_lower'].iloc[i] * 1.2 and 
                df['rsi'].iloc[i] <= 60):  # RSI条件も大幅に緩和
                
                if self.use_price_action and not self._check_price_action_patterns(df, i):
                    continue
                
                if self.use_multi_timeframe and multi_tf_data and not self.disable_multi_timeframe:
                    if not self._check_multi_timeframe(df, i, multi_tf_data, 1):
                        continue
                
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] - self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] + self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = f"{self.name} (BB+RSI)"
            
            elif (df['Close'].iloc[i] >= df['bb_upper'].iloc[i] * 0.8 and 
                  df['rsi'].iloc[i] >= 40):  # RSI条件も大幅に緩和
                
                if self.use_price_action and not self._check_price_action_patterns(df, i):
                    continue
                
                if self.use_multi_timeframe and multi_tf_data and not self.disable_multi_timeframe:
                    if not self._check_multi_timeframe(df, i, multi_tf_data, -1):
                        continue
                
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = df['Close'].iloc[i]
                df.loc[df.index[i], 'sl_price'] = df['Close'].iloc[i] + self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = df['Close'].iloc[i] - self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = f"{self.name} (BB+RSI)"
        
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
                if (tf_row['Close'] <= tf_row['bb_lower'] * 1.10 and tf_row['rsi'] <= self.rsi_lower + 10):  # 1.05→1.10、+5→+10
                    confirmation_count += weight
            else:
                if (tf_row['Close'] >= tf_row['bb_upper'] * 0.90 and tf_row['rsi'] >= self.rsi_upper - 10):  # 0.95→0.90、-5→-10
                    confirmation_count += weight
        
        confirmation_threshold = total_weight * self.confirmation_threshold  # 設定された確認閾値を使用
        
        return confirmation_count >= confirmation_threshold
    
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            フィルターをパスした場合はTrue、そうでない場合はFalse
        """
        if self.trend_filter:
            if not self._check_trend_filter(df, i):
                return False
        
        if self.vol_filter:
            if not self._check_volatility_filter(df, i):
                return False
        
        if self.use_adx_filter and 'adx' in df.columns:
            if not self._check_adx_filter(df, i):
                return False
        
        if self.use_pattern_filter:
            if not self._check_pattern_filter(df, i):
                return False
        
        if self.use_quality_filter:
            if not self._check_quality_filter(df, i):
                return False
        
        return True
    
    def _check_adx_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        ADXフィルターを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            ADXフィルターをパスした場合はTrue、そうでない場合はFalse
        """
        if 'adx' not in df.columns:
            return True
            
        adx = df['adx'].iloc[i]
        
        if adx > self.adx_threshold:
            return True
            
        return False
    
    def _check_pattern_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        パターンフィルターを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            パターンフィルターをパスした場合はTrue、そうでない場合はFalse
        """
        if i < 5:  # 少なくとも5つの過去の価格ポイントが必要
            return False
            
        if self._is_pin_bar(df, i):
            return True
            
        if self._is_engulfing(df, i):
            return True
            
        return False
    
    def _is_pin_bar(self, df: pd.DataFrame, i: int) -> bool:
        """
        ピンバーパターンを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            ピンバーパターンの場合はTrue、そうでない場合はFalse
        """
        body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
        total_range = df['High'].iloc[i] - df['Low'].iloc[i]
        
        if total_range == 0:
            return False
            
        body_ratio = body / total_range
        
        if body_ratio <= 0.3:
            if df['Close'].iloc[i] > df['Open'].iloc[i] and (df['Close'].iloc[i] - df['Low'].iloc[i]) / total_range > 0.6:
                return True
                
            if df['Close'].iloc[i] < df['Open'].iloc[i] and (df['High'].iloc[i] - df['Close'].iloc[i]) / total_range > 0.6:
                return True
                
        return False
    
    def _is_engulfing(self, df: pd.DataFrame, i: int) -> bool:
        """
        エンゲルフィングパターンを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            エンゲルフィングパターンの場合はTrue、そうでない場合はFalse
        """
        if i < 1:
            return False
            
        if (df['Close'].iloc[i] > df['Open'].iloc[i] and  # 現在の足が陽線
            df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and  # 前の足が陰線
            df['Close'].iloc[i] > df['Open'].iloc[i-1] and  # 現在の終値が前の始値より高い
            df['Open'].iloc[i] < df['Close'].iloc[i-1]):  # 現在の始値が前の終値より低い
            return True
            
        if (df['Close'].iloc[i] < df['Open'].iloc[i] and  # 現在の足が陰線
            df['Close'].iloc[i-1] > df['Open'].iloc[i-1] and  # 前の足が陽線
            df['Close'].iloc[i] < df['Open'].iloc[i-1] and  # 現在の終値が前の始値より低い
            df['Open'].iloc[i] > df['Close'].iloc[i-1]):  # 現在の始値が前の終値より高い
            return True
            
        return False
    
    def _check_quality_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        品質フィルターを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            品質フィルターをパスした場合はTrue、そうでない場合はFalse
        """
        quality_score = 0.0
        total_factors = 0
        
        # 市場レジームに基づいて品質閾値を動的に調整
        current_regime = 'unknown'
        if 'regime' in df.columns and i < len(df):
            current_regime = df['regime'].iloc[i]
            
        regime_thresholds = {
            'trend': 0.5,     # トレンド市場では中程度の閾値
            'range': 0.7,     # レンジ市場では高い閾値
            'volatile': 0.4,  # ボラティリティ市場では低い閾値
            'unknown': self.quality_threshold  # 不明な場合はデフォルト閾値
        }
        
        if 'rsi' in df.columns:
            total_factors += 1
            rsi = df['rsi'].iloc[i]
            
            if current_regime == 'trend':
                if rsi <= 20 or rsi >= 80:
                    quality_score += 1.0
                elif rsi <= 30 or rsi >= 70:
                    quality_score += 0.7
                elif rsi <= 40 or rsi >= 60:
                    quality_score += 0.3
            elif current_regime == 'range':
                if (rsi <= 30 and rsi >= 20) or (rsi >= 70 and rsi <= 80):
                    quality_score += 1.0
                elif (rsi <= 35 and rsi >= 25) or (rsi >= 65 and rsi <= 75):
                    quality_score += 0.7
                elif (rsi <= 40 and rsi >= 30) or (rsi >= 60 and rsi <= 70):
                    quality_score += 0.4
            else:
                if rsi <= 30 or rsi >= 70:
                    quality_score += 1.0
                elif rsi <= 35 or rsi >= 65:
                    quality_score += 0.7
                elif rsi <= 40 or rsi >= 60:
                    quality_score += 0.4
        
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            total_factors += 1
            close = df['Close'].iloc[i]
            bb_upper = df['bb_upper'].iloc[i]
            bb_lower = df['bb_lower'].iloc[i]
            
            if current_regime == 'trend':
                if close >= bb_upper * 1.05 or close <= bb_lower * 0.95:
                    quality_score += 1.0
                elif close >= bb_upper * 1.02 or close <= bb_lower * 0.98:
                    quality_score += 0.7
                elif close >= bb_upper or close <= bb_lower:
                    quality_score += 0.4
            elif current_regime == 'range':
                if close >= bb_upper * 0.98 or close <= bb_lower * 1.02:
                    quality_score += 1.0
                elif close >= bb_upper * 0.95 or close <= bb_lower * 1.05:
                    quality_score += 0.7
                elif close >= bb_upper * 0.9 or close <= bb_lower * 1.1:
                    quality_score += 0.4
            else:
                if close >= bb_upper * 1.05 or close <= bb_lower * 0.95:
                    quality_score += 1.0
                elif close >= bb_upper * 1.02 or close <= bb_lower * 0.98:
                    quality_score += 0.7
                elif close >= bb_upper or close <= bb_lower:
                    quality_score += 0.4
        
        if 'adx' in df.columns:
            total_factors += 1
            adx = df['adx'].iloc[i]
            
            if current_regime == 'trend':
                if adx >= 35:
                    quality_score += 1.0
                elif adx >= 25:
                    quality_score += 0.7
                elif adx >= 20:
                    quality_score += 0.4
            elif current_regime == 'range':
                if adx <= 15:
                    quality_score += 1.0
                elif adx <= 20:
                    quality_score += 0.7
                elif adx <= 25:
                    quality_score += 0.4
            else:
                if adx >= 40:
                    quality_score += 1.0
                elif adx >= 30:
                    quality_score += 0.7
                elif adx >= 20:
                    quality_score += 0.4
        
        if self._is_pin_bar(df, i) or self._is_engulfing(df, i):
            total_factors += 1
            quality_score += 1.0
        
        final_score = quality_score / total_factors if total_factors > 0 else 0
        
        # 市場レジームに基づいて閾値を調整
        adjusted_threshold = regime_thresholds.get(current_regime, self.quality_threshold)
        
        return final_score >= adjusted_threshold
    
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        市場レジームと連続勝利数に基づいてポジションサイズを調整
        
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
        
        consecutive_wins_multiplier = 1.0
        # ImprovedShortTermStrategyクラスから継承した属性を使用
        if hasattr(self, 'consecutive_wins') and hasattr(self, 'win_rate'):
            if self.consecutive_wins >= 2:
                consecutive_wins_multiplier = min(1.0 + (self.consecutive_wins * 0.25), 3.0)
                
                if self.win_rate >= 0.4:
                    consecutive_wins_multiplier = min(1.0 + (self.consecutive_wins * 0.3), 4.0)
                elif self.win_rate >= 0.3:
                    consecutive_wins_multiplier = min(1.0 + (self.consecutive_wins * 0.25), 3.0)
                else:
                    consecutive_wins_multiplier = min(1.0 + (self.consecutive_wins * 0.2), 2.5)
        
        regime_multiplier = 1.0
        if self.current_regime == 'trend':
            regime_multiplier = 1.1  # トレンド市場ではやや大きめ
        elif self.current_regime == 'range':
            regime_multiplier = 0.8  # レンジ市場では小さめ
        elif self.current_regime == 'volatile':
            regime_multiplier = 0.7  # ボラティリティ市場では最小
        
        final_size = base_size * consecutive_wins_multiplier * regime_multiplier
        
        max_position_size = equity * 0.05 / 10000.0  # 最大5%リスク
        
        return min(final_size, max_position_size)
