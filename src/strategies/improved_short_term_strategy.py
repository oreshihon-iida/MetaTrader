import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy

class ImprovedShortTermStrategy(ShortTermBollingerRsiStrategy):
    """
    改良版短期ボリンジャーバンド＋RSI戦略
    
    プロフィットファクターを向上させるための改良を加えた短期戦略
    フェーズ4: 価格アクションパターンの導入による勝率向上
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
            'bb_window': 20,
            'bb_dev': 1.6,          # 標準偏差を1.4から1.6に調整してノイズを減少
            'rsi_window': 14,
            'rsi_upper': 55,        # RSI閾値を60から55に調整して高品質シグナルに限定
            'rsi_lower': 45,        # RSI閾値を40から45に調整して高品質シグナルに限定
            'sl_pips': 2.5,         # 損切り幅を縮小（3.0→2.5）
            'tp_pips': 12.5,        # 利確幅を大幅に拡大してリスク・リワード比を1:5に改善
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,
            'atr_tp_multiplier': 2.0,  # ATRベースの利確乗数を1.6から2.0に拡大
            'use_adaptive_params': True,
            'trend_filter': False,
            'vol_filter': True,     # ボラティリティフィルターを有効化して高ボラティリティ時のみ取引
            'time_filter': True,
            'use_multi_timeframe': True,
            'timeframe_weights': {'5min': 2.0, '15min': 1.0},  # 5分足と15分足を使用
            'use_seasonal_filter': False,
            'use_price_action': True,  # フェーズ4: 価格アクションパターンを有効化
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "改良版短期ボリンジャーバンド＋RSI戦略"
        
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.consecutive_wins = 0
        self.max_consecutive_wins = 5
        self.total_trades = 0
        self.winning_trades = 0
        self.win_rate = 0.0
        
    def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        改良版では時間フィルターを強化し、高勝率の時間帯に限定
        
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
            
        if self.vol_filter:
            atr = df['atr'].iloc[i]
            atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.8
            if atr < atr_threshold:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 2) or (8 <= hour < 10) or (13 <= hour < 15)):
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
            return True  # 価格アクションパターンを使用しない場合は常にTrue
            
        current = df.iloc[i]
        prev1 = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        
        signal_direction = 0
        if 'signal' in df.columns and i < len(df):
            signal_direction = df['signal'].iloc[i]
        
        if signal_direction == 0:
            if current['Close'] >= current['bb_upper'] * 0.95 and current['rsi'] >= self.rsi_upper * 0.9:
                signal_direction = -1  # 売りシグナル
            elif current['Close'] <= current['bb_lower'] * 1.05 and current['rsi'] <= self.rsi_lower * 1.1:
                signal_direction = 1   # 買いシグナル
            
        if signal_direction == 0:
            return False
            
        pin_bar_signal = self._is_pin_bar(prev1, signal_direction)
        
        engulfing_signal = self._is_engulfing(prev1, prev2, signal_direction)
        
        trend_signal = self._check_trend(df.iloc[max(0, i-3):i+1], signal_direction)
        
        bollinger_signal = self._check_bollinger_position(df.iloc[i-1:i+1], signal_direction)
        
        rsi_signal = self._check_rsi_extreme(df.iloc[i-1:i+1], signal_direction)
        
        pattern_count = sum([pin_bar_signal, engulfing_signal, trend_signal, bollinger_signal, rsi_signal])
        
        return pattern_count >= 2
    
    def _is_pin_bar(self, candle, direction):
        """
        ピンバーパターンを検出する
        
        Parameters
        ----------
        candle : pd.Series
            ローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        bool
            ピンバーパターンが検出された場合はTrue、そうでない場合はFalse
        """
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
            return (lower_wick > 1.5 * body_size and lower_wick > upper_wick * 1.5)
        else:  # 売りシグナル用の上ヒゲピンバー
            return (upper_wick > 1.5 * body_size and upper_wick > lower_wick * 1.5)
    
    def _is_engulfing(self, curr, prev, direction):
        """
        エンゲルフィングパターンを検出する
        
        Parameters
        ----------
        curr : pd.Series
            現在のローソク足データ
        prev : pd.Series
            前のローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        bool
            エンゲルフィングパターンが検出された場合はTrue、そうでない場合はFalse
        """
        if direction == 1:  # 買いシグナル用の陽線エンゲルフィング
            return (curr['Close'] > curr['Open'] and  # 陽線
                    prev['Close'] < prev['Open'])     # 前日が陰線
        else:  # 売りシグナル用の陰線エンゲルフィング
            return (curr['Close'] < curr['Open'] and  # 陰線
                    prev['Close'] > prev['Open'])     # 前日が陽線
    
    def _check_trend(self, bars, direction, min_bars=3):
        """
        トレンドを確認する
        
        Parameters
        ----------
        bars : pd.DataFrame
            ローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
        min_bars : int, default 3
            確認する最小バー数
            
        Returns
        -------
        bool
            トレンドが確認された場合はTrue、そうでない場合はFalse
        """
        if len(bars) < min_bars:
            return False
            
        if direction == 1:  # 買いシグナル用の上昇トレンド確認
            return bars.iloc[-1]['Close'] > bars.iloc[-2]['Close']
        else:  # 売りシグナル用の下降トレンド確認
            return bars.iloc[-1]['Close'] < bars.iloc[-2]['Close']
    
    def _check_bollinger_position(self, bars, direction):
        """
        ボリンジャーバンドの位置関係を確認する
        
        Parameters
        ----------
        bars : pd.DataFrame
            ローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        bool
            ボリンジャーバンドの位置関係が確認された場合はTrue、そうでない場合はFalse
        """
        if direction == 1:  # 買いシグナル
            return bars.iloc[-1]['Close'] < bars.iloc[-1]['bb_lower'] * 1.02
        else:  # 売りシグナル
            return bars.iloc[-1]['Close'] > bars.iloc[-1]['bb_upper'] * 0.98
    
    def _check_rsi_extreme(self, bars, direction):
        """
        RSIの極値を確認する
        
        Parameters
        ----------
        bars : pd.DataFrame
            ローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        bool
            RSIの極値が確認された場合はTrue、そうでない場合はFalse
        """
        if direction == 1:  # 買いシグナル
            return bars.iloc[-1]['rsi'] < 30
        else:  # 売りシグナル
            return bars.iloc[-1]['rsi'] > 70
        
    def calculate_position_size(self, signal: int, equity: float = 10000.0) -> float:
        """
        ポジションサイズを計算する
        
        連続損失後はポジションサイズを削減
        連続勝利後はポジションサイズを増加
        
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
            return base_size * 0.5
        
        if self.consecutive_wins >= 2:
            bonus_factor = 1.0 + (self.consecutive_wins * 0.2)
            max_factor = 5.0  # 最大5倍まで（0.05ロット）
            
            if self.win_rate >= 0.5:  # 勝率50%以上の場合のみ最大倍率を適用
                return base_size * min(max_factor, bonus_factor)
            else:
                return base_size * min(2.0, bonus_factor)  # 勝率低い場合は最大2倍まで
        
        return base_size
        
    def update_consecutive_stats(self, is_win: bool) -> None:
        """
        連続勝敗カウンターを更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        """
        self.total_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
            self.consecutive_wins += 1
            self.winning_trades += 1
            
            if self.consecutive_wins > self.max_consecutive_wins:
                self.max_consecutive_wins = self.consecutive_wins
        else:
            self.consecutive_wins = 0
            self.consecutive_losses += 1
            
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
    
    def update_consecutive_losses(self, is_win: bool) -> None:
        """
        連続損失カウンターを更新する（後方互換性のため）
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        """
        self.update_consecutive_stats(is_win)
