import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .improved_short_term_strategy import ImprovedShortTermStrategy

class BalancedOptimizedStrategy(ImprovedShortTermStrategy):
    """
    バランス最適化版短期ボリンジャーバンド＋RSI戦略
    
    プロフィットファクター1.5を目標としたバランス最適化版短期戦略
    ImprovedShortTermStrategyをベースに、バランスの取れたパラメータ設定と
    効果的なフィルターを適用した戦略
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            ImprovedShortTermStrategyに渡すパラメータ
        """
        default_params = {
            'bb_window': 20,
            'bb_dev': 1.7,          # ボリンジャーバンド幅を適度に広げる（1.6→1.7）
            'rsi_window': 14,
            'rsi_upper': 65,        # RSI閾値を調整（55→65）- 強い過買い状態でのみ売り
            'rsi_lower': 35,        # RSI閾値を調整（45→35）- 強い過売り状態でのみ買い
            'sl_pips': 3.0,         # 損切り幅は維持
            'tp_pips': 10.5,        # 利確幅を拡大（7.5→10.5）してリスク・リワード比を1:3.5に改善
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,  # ATRベースの損切り乗数は維持
            'atr_tp_multiplier': 2.8,  # ATRベースの利確乗数を拡大（2.0→2.8）
            'use_adaptive_params': True,
            'trend_filter': True,   # トレンドフィルターを有効化
            'vol_filter': True,     # ボラティリティフィルターを維持
            'time_filter': True,    # 時間フィルターを維持
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
            'use_seasonal_filter': False,  # 季節性フィルターは無効化（シンプルに）
            'use_price_action': False,     # 価格アクションパターンは無効化（シンプルに）
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "バランス最適化版短期ボリンジャーバンド＋RSI戦略"
        
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.max_consecutive_losses = 3
        
        self.high_win_rate_hours = [0, 1, 2, 8, 9, 10, 13, 14, 15]
        
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        バランス最適化版では効果的なフィルターのみを適用
        
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
            
        if self.vol_filter:
            if 'atr' not in df.columns:
                df['atr'] = self._calculate_atr(df)
                
            atr = df['atr'].iloc[i]
            atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.8
            if atr < atr_threshold:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if hour not in self.high_win_rate_hours:
                return False
                
        if self.trend_filter:
            if 'ma5' not in df.columns:
                df['ma5'] = df['Close'].rolling(window=5).mean()
            if 'ma20' not in df.columns:
                df['ma20'] = df['Close'].rolling(window=20).mean()
                
            ma5 = df['ma5'].iloc[i]
            ma20 = df['ma20'].iloc[i]
            
            signal = df['signal'].iloc[i]
            
            if signal > 0 and ma5 <= ma20:
                return False
                
            if signal < 0 and ma5 >= ma20:
                return False
                
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            price = df['Close'].iloc[i]
            bb_upper = df['bb_upper'].iloc[i]
            bb_lower = df['bb_lower'].iloc[i]
            bb_middle = df['bb_middle'].iloc[i]
            
            if df['signal'].iloc[i] > 0:
                if price > bb_lower + (bb_middle - bb_lower) * 0.3:
                    return False
                    
            if df['signal'].iloc[i] < 0:
                if price < bb_upper - (bb_upper - bb_middle) * 0.3:
                    return False
                    
        return True
        
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        ATR（Average True Range）を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.Series
            ATRの値
        """
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1).fillna(df['Close'].iloc[0])
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_window).mean()
        
        return atr
        
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        連続損失後はポジションサイズを削減し、連続利益後は徐々に回復
        
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
            
        base_size = 0.01
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return base_size * 0.5  # 連続損失時は50%に削減
        elif self.consecutive_losses > 0:
            reduction_factor = 1.0 - (self.consecutive_losses * 0.15)
            return base_size * max(0.5, reduction_factor)
        elif self.consecutive_wins > 0:
            bonus_factor = 1.0 + (self.consecutive_wins * 0.1)
            return base_size * min(1.5, bonus_factor)
            
        return base_size
        
    def update_consecutive_counters(self, is_win: bool) -> None:
        """
        連続勝敗カウンターを更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        """
        if is_win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            
    def generate_signals(self, df: pd.DataFrame, year: int, processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        トレーディングシグナルを生成する
        
        バランス最適化版では移動平均線を追加
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        year : int
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルを含むデータフレーム
        """
        if 'ma5' not in df.columns:
            df['ma5'] = df['Close'].rolling(window=5).mean()
        if 'ma20' not in df.columns:
            df['ma20'] = df['Close'].rolling(window=20).mean()
            
        return super().generate_signals(df, year, processed_dir)
