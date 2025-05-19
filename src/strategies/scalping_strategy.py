import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy

class ScalpingStrategy(ShortTermBollingerRsiStrategy):
    """
    1分足に特化したスキャルピング戦略
    
    非常に短期間の小さな価格変動を捉え、小さな利益を素早く確定することを目的とした戦略
    """
    
    def __init__(self, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        **kwargs
            ShortTermBollingerRsiStrategyに渡すパラメータ
        """
        default_params = {
            'bb_window': 10,           # ボリンジャーバンド期間を短く設定
            'bb_dev': 1.2,             # 標準偏差を小さく設定して感度を上げる
            'rsi_window': 7,           # RSI期間を短く設定
            'rsi_upper': 70,           # 過買い閾値
            'rsi_lower': 30,           # 過売り閾値
            'sl_pips': 1.5,            # 非常に小さなストップロス
            'tp_pips': 3.0,            # 小さな利確目標（リスク・リワード比 1:2）
            'atr_window': 7,           # ATR期間を短く設定
            'atr_sl_multiplier': 0.5,  # ATRの0.5倍で損切り
            'atr_tp_multiplier': 1.0,  # ATRの1倍で利確
            'use_adaptive_params': True,
            'trend_filter': False,     # トレンドフィルターは使用しない（短期の動きに集中）
            'vol_filter': True,        # ボラティリティフィルターは使用（最小限のボラティリティが必要）
            'time_filter': True,       # 時間フィルターは使用（効果的な時間帯に限定）
            'use_multi_timeframe': True,
            'timeframe_weights': {'1min': 3.0},  # 1分足のみを使用
            'use_seasonal_filter': False,
            'use_price_action': False,
            'consecutive_limit': 1     # 連続シグナル制限を最小にして取引頻度を上げる
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "スキャルピング戦略（1分足）"
        
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.win_rate = 0.0
        
        self.active_hours = [0, 1, 2, 8, 9, 10, 13, 14, 15, 20, 21, 22]
    
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        スキャルピング戦略では取引頻度を上げるために一部フィルターを緩和
        
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
        
        if self.time_filter:
            hour = df.index[i].hour
            if hour not in self.active_hours:
                return False
        
        if self.vol_filter:
            if 'atr' not in df.columns:
                df['atr'] = df['Close'].rolling(window=self.atr_window).mean()
            
            atr = df['atr'].iloc[i]
            atr_threshold = df['atr'].rolling(window=10).mean().iloc[i] * 0.8
            if atr < atr_threshold:
                return False
        
        return True
    
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        連続勝利時に積極的にポジションサイズを増加
        
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
        
        if self.consecutive_losses >= 3:
            return base_size * 0.5  # 連続損失時は50%に削減
        
        if self.consecutive_wins >= 1:
            bonus_factor = 1.0 + (self.consecutive_wins * 0.2)
            max_factor = 2.0  # 最大2倍まで（0.02ロット）
            
            if self.win_rate >= 0.5:  # 勝率50%以上なら最大倍率を上げる
                max_factor = 5.0  # 最大5倍まで（0.05ロット）
            
            return base_size * min(max_factor, bonus_factor)
        
        return base_size
    
    def update_consecutive_stats(self, is_win: bool, pattern_types: Optional[List[str]] = None) -> None:
        """
        連続勝敗カウンターを更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        pattern_types : Optional[List[str]], default None
            検出されたパターンタイプのリスト
        """
        self.total_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
            self.consecutive_wins += 1
            self.winning_trades += 1
        else:
            self.consecutive_wins = 0
            self.consecutive_losses += 1
        
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
