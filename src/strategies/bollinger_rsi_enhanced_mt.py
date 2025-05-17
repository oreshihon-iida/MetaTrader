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
                timeframe_weights: Dict[str, float] = None):
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
        if not self.use_multi_timeframe:
            return super().generate_signals(df)
        
        multi_tf_data = self.load_multi_timeframe_data(year, processed_dir)
        
        if len(multi_tf_data) < 2 or '15min' not in multi_tf_data:
            return super().generate_signals(df)
        
        signals = self.analyze_timeframe_signals(multi_tf_data)
        
        result_df = self.merge_timeframe_signals(df, signals)
        
        return result_df
