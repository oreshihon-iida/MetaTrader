import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy

class LongTermBollingerRsiStrategy(BollingerRsiEnhancedMTStrategy):
    """
    1時間足と4時間足を組み合わせた長期ボリンジャーバンド＋RSI戦略
    
    少ない取引で大きな利益を得ることを目的とした戦略
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
            'bb_dev': 2.0,          # 標準偏差を大きくしてバンド幅を広める
            'rsi_window': 14,
            'rsi_upper': 80,        # RSIの閾値を厳格化して高品質シグナルに限定
            'rsi_lower': 20,        # RSIの閾値を厳格化して高品質シグナルに限定
            'sl_pips': 10.0,        # 損切り幅を大きくする
            'tp_pips': 25.0,        # 利確幅も大きくする
            'atr_window': 14,
            'atr_sl_multiplier': 1.5,  # ATRベースの損切り乗数を大きくする
            'atr_tp_multiplier': 3.0,  # ATRベースの利確乗数を大きくする
            'use_adaptive_params': True,
            'trend_filter': True,   # トレンドフィルターを有効化して高品質シグナルに限定
            'vol_filter': True,     # ボラティリティフィルターを有効化
            'time_filter': True,    # 時間フィルターを有効化
            'use_multi_timeframe': True,
            'timeframe_weights': {'1H': 1.0, '4H': 3.0},  # 4時間足の重みを大きくする
            'use_seasonal_filter': True,
            'use_price_action': True,
            'consecutive_limit': 5   # 連続シグナル制限を大きくする
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "長期ボリンジャーバンド＋RSI戦略（1時間足+4時間足）"
