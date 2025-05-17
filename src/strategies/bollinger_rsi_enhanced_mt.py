import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .bollinger_rsi_enhanced import BollingerRsiEnhancedStrategy

class BollingerRsiEnhancedMTStrategy(BollingerRsiEnhancedStrategy):
    """
    複数時間足分析を組み込んだ拡張版ボリンジャーバンド＋RSI逆張り戦略
    
    従来のボリンジャーバンド＋RSI拡張戦略をベースに、以下の機能を追加：
    - 複数時間足（15分足、1時間足、4時間足）からのシグナル確認
    - 2020年データに特化したパラメータ最適化
    - 時間足ごとのシグナル重みづけ
    """
    
    def __init__(self, 
                bb_window: int = 20,
                bb_dev: float = 2.0, 
                rsi_window: int = 14,
                rsi_upper: int = 70,
                rsi_lower: int = 30,
                sl_pips: float = 7.0, 
                tp_pips: float = 10.0,
                atr_window: int = 14,
                atr_sl_multiplier: float = 1.5,
                atr_tp_multiplier: float = 2.0,
                use_adaptive_params: bool = True,
                trend_filter: bool = True,
                vol_filter: bool = True,
                time_filter: bool = True,
                use_multi_timeframe: bool = True,
                timeframe_weights: Optional[Dict[str, float]] = None,
                use_seasonal_filter: bool = True,
                use_price_action: bool = True):
        """
        初期化
        
        Parameters
        ----------
        bb_window : int, default 20
            ボリンジャーバンドの期間
        bb_dev : float, default 2.0
            ボリンジャーバンドの標準偏差の倍率
        rsi_window : int, default 14
            RSIの期間
        rsi_upper : int, default 70
            RSIの上限値（売りシグナル）
        rsi_lower : int, default 30
            RSIの下限値（買いシグナル）
        sl_pips : float, default 7.0
            固定損切り幅（pips）
        tp_pips : float, default 10.0
            固定利確幅（pips）
        atr_window : int, default 14
            ATR（Average True Range）の期間
        atr_sl_multiplier : float, default 1.5
            ATRベースの損切り幅の乗数
        atr_tp_multiplier : float, default 2.0
            ATRベースの利確幅の乗数
        use_adaptive_params : bool, default True
            適応型パラメータを使用するかどうか
        trend_filter : bool, default True
            トレンドフィルターを使用するかどうか
        vol_filter : bool, default True
            ボラティリティフィルターを使用するかどうか
        time_filter : bool, default True
            時間帯フィルターを使用するかどうか
        use_multi_timeframe : bool, default True
            複数時間足分析を使用するかどうか
        timeframe_weights : Dict[str, float], optional
            各時間足の重みづけ（例: {'15min': 1.0, '1H': 2.0, '4H': 3.0}）
        use_seasonal_filter : bool, default True
            季節性分析に基づくフィルターを使用するかどうか
        use_price_action : bool, default True
            価格アクションパターンを使用するかどうか
        """
        super().__init__(
            bb_window=bb_window,
            bb_dev=bb_dev,
            rsi_window=rsi_window,
            rsi_upper=rsi_upper,
            rsi_lower=rsi_lower,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            atr_window=atr_window,
            atr_sl_multiplier=atr_sl_multiplier,
            atr_tp_multiplier=atr_tp_multiplier,
            use_adaptive_params=use_adaptive_params,
            trend_filter=trend_filter,
            vol_filter=vol_filter,
            time_filter=time_filter
        )
        
        self.use_multi_timeframe = use_multi_timeframe
        self.timeframe_weights = timeframe_weights if timeframe_weights else {
            '15min': 1.0,
            '1H': 2.0,
            '4H': 3.0
        }
        self.name = "複数時間足拡張版ボリンジャーバンド＋RSI逆張り"
        self.use_seasonal_filter = use_seasonal_filter
        self.use_price_action = use_price_action
        
    def load_multi_timeframe_data(self, year: int, processed_dir: str = 'data/processed') -> Dict[str, pd.DataFrame]:
        """
        複数時間足のデータを読み込む
        
        Parameters
        ----------
        year : int
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム
        """
        data_processor = DataProcessor(pd.DataFrame())
        timeframes = list(self.timeframe_weights.keys())
        
        multi_tf_data = {}
        for tf in timeframes:
            df = data_processor.load_processed_data(tf, year, processed_dir)
            if not df.empty:
                multi_tf_data[tf] = df
        
        return multi_tf_data
        
    def analyze_timeframe_signals(self, multi_tf_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        各時間足のデータに対してシグナルを生成する
        
        Parameters
        ----------
        multi_tf_data : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            シグナルが追加された時間足ごとのデータフレーム
        """
        signals = {}
        for tf, df in multi_tf_data.items():
            # 各時間足のデータに対して技術的指標を計算
            df_with_indicators = self._calculate_technical_indicators(df.copy())
            signals[tf] = super().generate_signals(df_with_indicators)
        
        return signals
        
    def merge_timeframe_signals(self, primary_df: pd.DataFrame, signals: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        複数時間足のシグナルを統合する
        
        Parameters
        ----------
        primary_df : pd.DataFrame
            主要時間足（通常は15分足）のデータフレーム
        signals : Dict[str, pd.DataFrame]
            各時間足のシグナル付きデータフレーム
            
        Returns
        -------
        pd.DataFrame
            統合されたシグナル付きデータフレーム
        """
        result_df = self._calculate_technical_indicators(primary_df.copy())
        
        resampled_signals = {}
        for tf, df in signals.items():
            if tf == '15min':
                resampled_signals[tf] = df['signal']
            else:
                resampled = df['signal'].reindex(result_df.index, method='ffill')
                resampled_signals[tf] = resampled
        
        result_df['signal_score'] = 0.0
        result_df['signal'] = 0
        
        for tf, signal_series in resampled_signals.items():
            weight = self.timeframe_weights[tf]
            result_df['signal_score'] += signal_series * weight
        
        threshold = sum(self.timeframe_weights.values()) * 0.6  # 60%以上の重みでシグナル発生
        
        result_df.loc[result_df['signal_score'] >= threshold, 'signal'] = 1
        result_df.loc[result_df['signal_score'] <= -threshold, 'signal'] = -1
        
        for i in range(1, len(result_df)):
            if result_df.iloc[i]['signal'] != 0:
                result_df.loc[result_df.index[i], 'entry_price'] = result_df.iloc[i]['Open']
                
                sl_price, tp_price = self._calculate_adaptive_sl_tp(
                    result_df, i, result_df.iloc[i]['signal']
                )
                
                result_df.loc[result_df.index[i], 'sl_price'] = sl_price
                result_df.loc[result_df.index[i], 'tp_price'] = tp_price
                result_df.loc[result_df.index[i], 'strategy'] = self.name
        
        return result_df
        
    def _apply_seasonal_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        季節性分析に基づくフィルターを適用する
        
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
        if not self.use_seasonal_filter:
            return True
            
        current_time = df.index[i]
        
        weekday = current_time.weekday()
        
        month = current_time.month
        
        if weekday == 0:  # 月曜
            if current_time.hour < 10:
                return False
        elif weekday == 4:  # 金曜
            if current_time.hour >= 18:
                return False
        
        if month == 1:
            if current_time.day < 10:
                return False
        elif month == 12:
            if current_time.day > 20:
                return False
        
        return True
    
    def _check_price_action_patterns(self, df: pd.DataFrame, i: int) -> bool:
        """
        価格アクションパターンをチェックする
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            確認されたパターンがある場合はTrue、ない場合はFalse
        """
        if not self.use_price_action or i < 3:
            return True
            
        current = df.iloc[i]
        prev1 = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        prev3 = df.iloc[i-3]
        
        signal_direction = 0
        if current['Close'] >= current['bb_upper'] and current['rsi'] >= self.rsi_upper:
            signal_direction = -1  # 売りシグナル
        elif current['Close'] <= current['bb_lower'] and current['rsi'] <= self.rsi_lower:
            signal_direction = 1   # 買いシグナル
            
        if signal_direction == 0:
            return False
            
        def is_pin_bar(candle, direction):
            body_size = abs(candle['Close'] - candle['Open'])
            total_size = candle['High'] - candle['Low']
            
            if total_size == 0:
                return False
                
            if candle['Close'] >= candle['Open']:  # 陽線
                upper_wick = candle['High'] - candle['Close']
                lower_wick = candle['Open'] - candle['Low']
            else:  # 陰線
                upper_wick = candle['High'] - candle['Open']
                lower_wick = candle['Close'] - candle['Low']
            
            if direction == 1:  # 買いシグナル用の下ヒゲピンバー
                return (lower_wick > 2 * body_size and lower_wick > upper_wick * 2 and 
                        body_size / total_size < 0.3)
            else:  # 売りシグナル用の上ヒゲピンバー
                return (upper_wick > 2 * body_size and upper_wick > lower_wick * 2 and 
                        body_size / total_size < 0.3)
        
        def is_engulfing(curr, prev, direction):
            if direction == 1:  # 買いシグナル用の陽線エンゲルフィング
                return (curr['Open'] < prev['Close'] and curr['Close'] > prev['Open'] and 
                        curr['Close'] > curr['Open'] and prev['Close'] < prev['Open'])
            else:  # 売りシグナル用の陰線エンゲルフィング
                return (curr['Open'] > prev['Close'] and curr['Close'] < prev['Open'] and 
                        curr['Close'] < curr['Open'] and prev['Close'] > prev['Open'])
        
        pin_bar_signal = is_pin_bar(prev1, signal_direction)
        engulfing_signal = is_engulfing(prev1, prev2, signal_direction)
        
        return pin_bar_signal or engulfing_signal
    
    def _calculate_adaptive_sl_tp(self, df: pd.DataFrame, i: int, signal: int) -> Tuple[float, float]:
        """
        適応型の損切り・利確レベルを計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        signal : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        Tuple[float, float]
            (損切りレベル, 利確レベル)
        """
        current = df.iloc[i]
        
        if self.use_adaptive_params:
            atr_value = current['atr']
            
            recent_atr_avg = df['atr'].iloc[max(0, i-20):i+1].mean()
            atr_ratio = atr_value / recent_atr_avg if recent_atr_avg > 0 else 1.0
            
            time_multiplier = 1.0
            hour = df.index[i].hour
            
            if 0 <= hour < 6:
                time_multiplier = 0.8
            elif 7 <= hour < 15:
                time_multiplier = 1.2
            
            rsi_multiplier = 1.0
            if current['rsi'] < 20 or current['rsi'] > 80:
                rsi_multiplier = 1.3
            
            sl_multiplier = self.atr_sl_multiplier * atr_ratio * time_multiplier
            tp_multiplier = self.atr_tp_multiplier * atr_ratio * time_multiplier * rsi_multiplier
            
            sl_distance = atr_value * sl_multiplier
            tp_distance = atr_value * tp_multiplier
        else:
            sl_distance = self.sl_pips * 0.01
            tp_distance = self.tp_pips * 0.01
        
        entry_price = current['Open']
        
        if signal == 1:  # 買いシグナル
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
        else:  # 売りシグナル
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance
        
        return sl_price, tp_price
    
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
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
        
        if self.use_seasonal_filter and not self._apply_seasonal_filter(df, i):
            return False
            
        # 価格アクションパターンを確認
        if self.use_price_action and not self._check_price_action_patterns(df, i):
            return False
        
        return True
    
    def generate_signals(self, df: pd.DataFrame, year: int = 2020, 
                       processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        複数時間足分析を用いてトレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            主要時間足（15分足）のデータ
        year : int, default 2020
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        # 複数時間足分析を使用しない場合は親クラスの処理を使用
        if not self.use_multi_timeframe:
            return super().generate_signals(df)
        
        available_timeframes = {}
        data_processor = DataProcessor(pd.DataFrame())
        
        for tf in self.timeframe_weights.keys():
            try:
                tf_data = data_processor.load_processed_data(tf, year, processed_dir)
                if not tf_data.empty:
                    available_timeframes[tf] = self.timeframe_weights[tf]
            except Exception:
                continue
        
        if not available_timeframes or '15min' not in available_timeframes:
            return super().generate_signals(df)
        
        temp_weights = self.timeframe_weights.copy()
        self.timeframe_weights = available_timeframes
        
        multi_tf_data = self.load_multi_timeframe_data(year, processed_dir)
        
        if len(multi_tf_data) < 2 or '15min' not in multi_tf_data:
            self.timeframe_weights = temp_weights  # 元の重みに戻す
            return super().generate_signals(df)
        
        signals = self.analyze_timeframe_signals(multi_tf_data)
        
        # 複数時間足のシグナルを統合
        result_df = self.merge_timeframe_signals(df, signals)
        
        self.timeframe_weights = temp_weights
        
        return result_df
