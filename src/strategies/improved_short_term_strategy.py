import pandas as pd
import numpy as np
import datetime
from typing import Dict, Tuple, List, Optional, Set
from ..data.data_processor_enhanced import DataProcessor
from .short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy

class ImprovedShortTermStrategy(ShortTermBollingerRsiStrategy):
    """
    改良版短期ボリンジャーバンド＋RSI戦略
    
    プロフィットファクターを向上させるための改良を加えた短期戦略
    フェーズ5: パターン検出精度向上と市場環境適応型パターン適用
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
            'bb_dev': 1.8,          # 標準偏差を1.6から1.8に調整してノイズを減少
            'rsi_window': 14,
            'rsi_upper': 60,        # RSI閾値を55から60に調整して高品質シグナルに限定
            'rsi_lower': 40,        # RSI閾値を45から40に調整して高品質シグナルに限定
            'sl_pips': 3.0,         # フェーズ2の2.5からフェーズ1の3.0に戻す
            'tp_pips': 7.5,         # フェーズ2の8.0からフェーズ1の7.5に戻す
            'atr_window': 14,
            'atr_sl_multiplier': 0.8,  # フェーズ2の0.7からフェーズ1の0.8に戻す
            'atr_tp_multiplier': 2.0,  # フェーズ2の2.2からフェーズ1の2.0に戻す
            'use_adaptive_params': True,
            'trend_filter': False,
            'vol_filter': True,     # ボラティリティフィルターを有効化して高ボラティリティ時のみ取引
            'time_filter': True,
            'day_filter': True,     # 曜日フィルターを有効化
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
            'use_seasonal_filter': False,
            'use_price_action': True,  # フェーズ4: 価格アクションパターンを有効化
            'use_enhanced_patterns': True,  # フェーズ5: 強化版パターン検出を有効化
            'use_market_env_patterns': True,  # フェーズ5: 市場環境別パターン適用を有効化
            'use_composite_patterns': True,  # フェーズ5: 複合パターン検出を有効化
            'use_year_specific_filters': True,  # フェーズ5: 年別フィルターを有効化
            'consecutive_limit': 2
        }
        
        for key, value in default_params.items():
            if key not in kwargs:
                kwargs[key] = value
        
        self.day_filter = kwargs.pop('day_filter', True)
        self.use_enhanced_patterns = kwargs.pop('use_enhanced_patterns', True)
        self.use_market_env_patterns = kwargs.pop('use_market_env_patterns', True)
        self.use_composite_patterns = kwargs.pop('use_composite_patterns', True)
        self.use_year_specific_filters = kwargs.pop('use_year_specific_filters', True)
        
        super().__init__(**kwargs)
        self.name = "改良版短期ボリンジャーバンド＋RSI戦略"
        
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.consecutive_wins = 0
        self.max_consecutive_wins = 5
        self.total_trades = 0
        self.winning_trades = 0
        self.win_rate = 0.0
        
        self.adaptive_rsi_upper = self.rsi_upper
        self.adaptive_rsi_lower = self.rsi_lower
        
        self.pattern_stats = {
            'pin_bar': {'count': 0, 'wins': 0},
            'engulfing': {'count': 0, 'wins': 0},
            'trend_confirmation': {'count': 0, 'wins': 0},
            'bollinger_position': {'count': 0, 'wins': 0},
            'rsi_extreme': {'count': 0, 'wins': 0},
            'composite': {'count': 0, 'wins': 0}
        }
        
        self.active_trade_patterns = {}
        
    def _calculate_trend_strength(self, df: pd.DataFrame, i: int) -> float:
        """
        トレンド強度を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        float
            トレンド強度（-1.0〜1.0）
            正の値は上昇トレンド、負の値は下降トレンド、0に近い値はレンジ相場を示す
        """
        if i < 20:
            return 0.0
            
        short_ma = df['Close'].iloc[i-10:i].mean()
        long_ma = df['Close'].iloc[i-20:i].mean()
        
        price_direction = 1 if short_ma > long_ma else -1
        
        rsi_direction = 1 if df['rsi'].iloc[i] > 50 else -1
        
        trend_strength = price_direction * (abs(short_ma - long_ma) / long_ma) * 10
        
        if price_direction == rsi_direction:
            trend_strength *= 1.2
            
        return max(min(trend_strength, 1.0), -1.0)
        
    def _apply_filters(self, df: pd.DataFrame, i: int, signal: int = 0) -> bool:
        """
        各種フィルターを適用し、シグナルを生成するかどうかを判断する
        
        改良版では時間フィルターと曜日フィルターを強化し、高勝率の時間帯と曜日に限定
        また、市場環境に応じてRSI閾値を動的に調整
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        signal : int, default 0
            シグナル（1: 買い、-1: 売り、0: シグナルなし）
            
        Returns
        -------
        bool
            シグナルを生成する場合はTrue、そうでない場合はFalse
        """
        if not super()._apply_filters(df, i):
            return False
            
        if self.vol_filter:
            atr = df['atr'].iloc[i]
            avg_atr = df['atr'].rolling(window=20).mean().iloc[i]
            
            if atr < avg_atr * 0.7:
                return False
                
            if atr > avg_atr * 2.0:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 3) or (8 <= hour < 11) or (13 <= hour < 16)):
                return False
        
        if self.day_filter and hasattr(df.index[i], 'weekday'):
            weekday = df.index[i].weekday()
            if weekday in [0, 4]:
                rsi = df['rsi'].iloc[i]
                if signal > 0 and rsi > self.rsi_upper * 0.9:  # 買いシグナルの場合
                    return False
                if signal < 0 and rsi < self.rsi_lower * 1.1:  # 売りシグナルの場合
                    return False
        
        if self.use_adaptive_params:
            trend_strength = self._calculate_trend_strength(df, i)
            volatility = df['atr'].iloc[i] / df['atr'].rolling(window=20).mean().iloc[i] if i >= 20 else 1.0
            
            if volatility > 1.5:  # 高ボラティリティ
                self.adaptive_rsi_upper = 70
                self.adaptive_rsi_lower = 30
            elif abs(trend_strength) > 0.7:  # トレンド相場
                self.adaptive_rsi_upper = 55
                self.adaptive_rsi_lower = 45
            else:  # レンジ相場
                self.adaptive_rsi_upper = 65
                self.adaptive_rsi_lower = 35
                
        return True
    
    def determine_market_environment(self, df: pd.DataFrame, i: int) -> str:
        """
        市場環境を判定する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        str
            市場環境（'trend', 'range', 'high_volatility'）
        """
        if i < 20:
            return 'range'  # デフォルト
            
        trend_strength = abs(self._calculate_trend_strength(df, i))
        volatility = df['atr'].iloc[i] / df['atr'].rolling(window=20).mean().iloc[i] if i >= 20 else 1.0
        
        if volatility > 1.5:
            return 'high_volatility'
        elif trend_strength > 0.7:
            return 'trend'
        else:
            return 'range'
    
    def calculate_pattern_weight(self, df: pd.DataFrame, i: int, pattern_type: str) -> float:
        """
        市場環境に応じたパターンの重み付けを計算
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        pattern_type : str
            パターンタイプ
            
        Returns
        -------
        float
            パターンの重み
        """
        if not self.use_market_env_patterns:
            return 1.0
            
        market_env = self.determine_market_environment(df, i)
        
        weights = {
            'trend': {
                'pin_bar': 1.2,
                'engulfing': 1.5,
                'trend_confirmation': 1.4,
                'bollinger_position': 1.1,
                'rsi_extreme': 1.1
            },
            'range': {
                'pin_bar': 1.7,
                'engulfing': 1.1,
                'trend_confirmation': 0.9,
                'bollinger_position': 1.4,
                'rsi_extreme': 1.1
            },
            'high_volatility': {
                'pin_bar': 1.1,
                'engulfing': 1.1,
                'trend_confirmation': 0.9,
                'bollinger_position': 0.9,
                'rsi_extreme': 1.6
            }
        }
        
        return weights[market_env][pattern_type]
    
    def detect_composite_patterns(self, df: pd.DataFrame, i: int, direction: int) -> Tuple[float, Set[str]]:
        """
        複合パターンを検出し、シグナル強度を計算
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
            
        Returns
        -------
        Tuple[float, Set[str]]
            シグナル強度（0.0〜1.0）と検出されたパターンタイプのセット
        """
        if not self.use_composite_patterns or i < 3:
            return 0.0, set()
            
        current = df.iloc[i]
        prev1 = df.iloc[i-1]
        prev_candles = df.iloc[max(0, i-10):i]
        
        patterns = {
            'pin_bar': self._is_pin_bar(prev1, direction, prev_candles),
            'engulfing': self._is_engulfing(prev1, prev_candles.iloc[-1] if len(prev_candles) > 0 else None, direction),
            'trend_confirmation': self._check_trend(df.iloc[max(0, i-3):i+1], direction),
            'bollinger_position': self._check_bollinger_position(df.iloc[i-1:i+1], direction),
            'rsi_extreme': self._check_rsi_extreme(df.iloc[i-1:i+1], direction)
        }
        
        detected_patterns = sum(1 for p in patterns.values() if p)
        detected_pattern_types = set()
        
        weighted_sum = 0
        for pattern_type, detected in patterns.items():
            if detected:
                weight = self.calculate_pattern_weight(df, i, pattern_type)
                weighted_sum += weight
                self.pattern_stats[pattern_type]['count'] += 1
                detected_pattern_types.add(pattern_type)
        
        if detected_patterns > 0:
            strength = weighted_sum / (detected_patterns * 1.3)  # 1.3は最大の重み（緩和）
            if strength > 0.6:  # 強い複合パターン（閾値緩和）
                self.pattern_stats['composite']['count'] += 1
                detected_pattern_types.add('composite')
            return strength, detected_pattern_types
        else:
            return 0.0, set()
    
    def apply_year_specific_filters(self, df: pd.DataFrame, i: int, year: int) -> bool:
        """
        年別の特別フィルター
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        year : int
            年
            
        Returns
        -------
        bool
            フィルターを通過する場合はTrue、そうでない場合はFalse
        """
        if not self.use_year_specific_filters:
            return True
            
        if year == 2024:
            if df['atr'].iloc[i] > df['atr'].iloc[i-20:i].mean() * 1.8:
                return False
                
            if hasattr(df.index[i], 'date'):
                date = df.index[i].date()
                important_dates_2024 = [
                    datetime.date(2024, 1, 10),  # 米CPI発表日
                    datetime.date(2024, 1, 31),  # FOMC発表日
                    datetime.date(2024, 2, 2),   # 米雇用統計発表日
                    datetime.date(2024, 3, 20),  # FOMC発表日
                    datetime.date(2024, 4, 5),   # 米雇用統計発表日
                ]
                if date in important_dates_2024:
                    return False
        
        return True
    
    def _check_price_action_patterns(self, df: pd.DataFrame, i: int) -> Tuple[bool, Set[str]]:
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
        Tuple[bool, Set[str]]
            確認されたパターンがある場合はTrue、ない場合はFalseと検出されたパターンタイプのセット
        """
        if not self.use_price_action or i < 3:
            return True, set()  # 価格アクションパターンを使用しない場合は常にTrue
            
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
            return False, set()
        
        if hasattr(df.index[i], 'year'):
            year = df.index[i].year
            if not self.apply_year_specific_filters(df, i, year):
                return False, set()
        
        # 前のローソク足データを取得
        prev_candles = df.iloc[max(0, i-10):i]
        
        detected_patterns = set()
        
        pin_bar_signal = self._is_pin_bar(prev1, signal_direction, prev_candles)
        if pin_bar_signal:
            detected_patterns.add('pin_bar')
            
        engulfing_signal = self._is_engulfing(prev1, prev2, signal_direction)
        if engulfing_signal:
            detected_patterns.add('engulfing')
            
        trend_signal = self._check_trend(df.iloc[max(0, i-3):i+1], signal_direction)
        if trend_signal:
            detected_patterns.add('trend_confirmation')
            
        bollinger_signal = self._check_bollinger_position(df.iloc[i-1:i+1], signal_direction)
        if bollinger_signal:
            detected_patterns.add('bollinger_position')
            
        rsi_signal = self._check_rsi_extreme(df.iloc[i-1:i+1], signal_direction)
        if rsi_signal:
            detected_patterns.add('rsi_extreme')
        
        composite_strength, composite_patterns = self.detect_composite_patterns(df, i, signal_direction)
        detected_patterns.update(composite_patterns)
        
        if self.use_market_env_patterns:
            pin_bar_weight = self.calculate_pattern_weight(df, i, 'pin_bar')
            engulfing_weight = self.calculate_pattern_weight(df, i, 'engulfing')
            trend_weight = self.calculate_pattern_weight(df, i, 'trend_confirmation')
            bollinger_weight = self.calculate_pattern_weight(df, i, 'bollinger_position')
            rsi_weight = self.calculate_pattern_weight(df, i, 'rsi_extreme')
            
            weighted_count = (
                pin_bar_signal * pin_bar_weight +
                engulfing_signal * engulfing_weight +
                trend_signal * trend_weight +
                bollinger_signal * bollinger_weight +
                rsi_signal * rsi_weight
            )
            
            if composite_strength > 0.6:
                weighted_count += 1.0
                
            return weighted_count >= 1.8, detected_patterns
        else:
            pattern_count = sum([pin_bar_signal, engulfing_signal, trend_signal, bollinger_signal, rsi_signal])
            return pattern_count >= 2, detected_patterns
    
    def _is_pin_bar(self, candle, direction, prev_candles=None):
        """
        改良版ピンバーパターン検出
        
        Parameters
        ----------
        candle : pd.Series
            ローソク足データ
        direction : int
            シグナルの方向（1: 買い、-1: 売り）
        prev_candles : pd.DataFrame, optional
            前のローソク足データ（トレンド転換確認用）
            
        Returns
        -------
        bool
            ピンバーパターンが検出された場合はTrue、そうでない場合はFalse
        """
        body_size = abs(candle['Close'] - candle['Open'])
        total_size = candle['High'] - candle['Low']
        
        if total_size == 0:
            return False
            
        body_ratio = body_size / total_size
        
        if candle['Close'] >= candle['Open']:  # 陽線
            upper_wick = candle['High'] - candle['Close']
            lower_wick = candle['Open'] - candle['Low']
        else:  # 陰線
            upper_wick = candle['High'] - candle['Open']
            lower_wick = candle['Close'] - candle['Low']
        
        if direction == 1:  # 買いシグナル用の下ヒゲピンバー
            lower_wick_ratio = lower_wick / total_size
            basic_pin_bar = (body_ratio < 0.3 and lower_wick_ratio > 0.6)
        else:  # 売りシグナル用の上ヒゲピンバー
            upper_wick_ratio = upper_wick / total_size
            basic_pin_bar = (body_ratio < 0.3 and upper_wick_ratio > 0.6)
        
        if not basic_pin_bar:
            return False
            
        trend_reversal = False
        if prev_candles is not None and len(prev_candles) >= 2:
            prev1 = prev_candles.iloc[-1]
            prev2 = prev_candles.iloc[-2] if len(prev_candles) >= 2 else None
            
            if direction == 1 and prev2 is not None:  # 買いシグナル（下降トレンドからの転換）
                trend_reversal = prev1['Close'] < prev1['Open'] and prev2['Close'] < prev2['Open']
            elif direction == -1 and prev2 is not None:  # 売りシグナル（上昇トレンドからの転換）
                trend_reversal = prev1['Close'] > prev1['Open'] and prev2['Close'] > prev2['Open']
        
        support_resistance = False
        if prev_candles is not None and len(prev_candles) >= 10:
            if direction == 1:  # 買いシグナル（サポートレベルでの反発）
                recent_lows = [prev_candles.iloc[j]['Low'] for j in range(len(prev_candles))]
                support_level = min(recent_lows)
                support_resistance = abs(candle['Low'] - support_level) / support_level < 0.003
            else:  # 売りシグナル（レジスタンスレベルでの反発）
                recent_highs = [prev_candles.iloc[j]['High'] for j in range(len(prev_candles))]
                resistance_level = max(recent_highs)
                support_resistance = abs(candle['High'] - resistance_level) / resistance_level < 0.003
        
        if self.use_enhanced_patterns:
            return basic_pin_bar and (trend_reversal or support_resistance)
        else:
            return basic_pin_bar
    
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
        
    def calculate_position_size(self, signal: int, equity: float = 10000.0, composite_strength: float = 0.0) -> float:
        """
        ポジションサイズを計算する
        
        連続損失後はポジションサイズを削減
        連続勝利後はポジションサイズを増加
        複合パターン強度に応じて調整
        
        Parameters
        ----------
        signal : int
            シグナル（1: 買い、-1: 売り、0: シグナルなし）
        equity : float, default 10000.0
            現在の資金
        composite_strength : float, default 0.0
            複合パターン強度（0.0〜1.0）
            
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
        
        if self.consecutive_wins >= 3:
            if self.win_rate >= 0.8:  # 勝率80%以上の場合のみ
                return min(base_size * 1.5, 0.02)  # 最大0.02ロット
        
        if composite_strength > 0.8:
            return min(base_size * 1.2, 0.015)  # 強いシグナルでは1.2倍（最大0.015ロット）
        elif composite_strength > 0.6:
            return min(base_size * 1.1, 0.012)  # 中程度のシグナルでは1.1倍（最大0.012ロット）
        
        return base_size
        
    def update_consecutive_stats(self, is_win: bool, pattern_types: Optional[Set[str]] = None) -> None:
        """
        連続勝敗カウンターとパターン統計を更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        pattern_types : Optional[Set[str]], default None
            検出されたパターンタイプのセット
        """
        self.total_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
            self.consecutive_wins += 1
            self.winning_trades += 1
            
            if self.consecutive_wins > self.max_consecutive_wins:
                self.max_consecutive_wins = self.consecutive_wins
                
            if pattern_types:
                for pattern_type in pattern_types:
                    if pattern_type in self.pattern_stats:
                        self.pattern_stats[pattern_type]['wins'] += 1
        else:
            self.consecutive_wins = 0
            self.consecutive_losses += 1
            
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
    
    def update_consecutive_losses(self, is_win: bool, pattern_types: Optional[Set[str]] = None) -> None:
        """
        連続損失カウンターを更新する（後方互換性のため）
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        pattern_types : Optional[Set[str]], default None
            検出されたパターンタイプのセット
        """
        self.update_consecutive_stats(is_win, pattern_types)
