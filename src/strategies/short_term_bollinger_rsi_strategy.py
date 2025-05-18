import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy

class ShortTermBollingerRsiStrategy(BollingerRsiEnhancedMTStrategy):
    """
    1分足と15分足を組み合わせた超短期ボリンジャーバンド＋RSI戦略
    
    頻繁な取引機会を生成し、小さな利益を積み重ねることを目的とした戦略
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            BollingerRsiEnhancedMTStrategyに渡すパラメータ
        """
        default_params = {
            'bb_window': 20,
            'bb_dev': 1.4,          # 標準偏差を小さくしてバンド幅を狭める
            'rsi_window': 14,
            'rsi_upper': 65,        # RSIの閾値を緩和して売りシグナルを増やす
            'rsi_lower': 35,        # RSIの閾値を緩和して買いシグナルを増やす
            'sl_pips': 3.0,         # 損切り幅を小さくする
            'tp_pips': 6.0,         # 利確幅も小さくする
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,  # ATRベースの損切り乗数を小さくする
            'atr_tp_multiplier': 1.6,  # ATRベースの利確乗数を小さくする
            'use_adaptive_params': True,
            'trend_filter': False,  # トレンドフィルターを無効化して取引頻度を上げる
            'vol_filter': False,    # ボラティリティフィルターを無効化
            'time_filter': True,    # 時間フィルターは有効化（効果的な時間帯に限定）
            'use_multi_timeframe': True,
            'timeframe_weights': {'1min': 3.0, '15min': 1.0},  # 1分足の重みを大きくする
            'use_seasonal_filter': False,
            'use_price_action': False,
            'consecutive_limit': 2   # 連続シグナル制限を小さくして取引頻度を上げる
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "超短期ボリンジャーバンド＋RSI戦略（1分足+15分足）"
    
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
            時間足をキー、データフレームを値とする辞書
        """
        multi_tf_data = {}
        data_processor = DataProcessor(pd.DataFrame())
        
        for tf in self.timeframe_weights.keys():
            try:
                tf_data = data_processor.load_processed_data(tf, year, processed_dir)
                if not tf_data.empty:
                    multi_tf_data[tf] = tf_data
            except Exception as e:
                print(f"Error loading {tf} data: {e}")
                continue
        
        return multi_tf_data
    
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        超短期戦略では一部のフィルターを緩和して取引頻度を上げる
        
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
        if i < 1:
            return False
            
        consecutive_signals = 0
        for j in range(1, min(self.consecutive_limit + 1, i + 1)):
            if df['signal'].iloc[i-j] != 0:
                consecutive_signals += 1
        
        if consecutive_signals >= self.consecutive_limit:
            return False
            
        if self.use_seasonal_filter and not self._apply_seasonal_filter(df, i):
            return False
            
        if self.use_price_action and not self._check_price_action_patterns(df, i):
            return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 6) or (8 <= hour < 16) or (13 <= hour < 22)):
                return False
        
        return True
