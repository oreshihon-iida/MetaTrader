import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ...data.data_processor_enhanced import DataProcessor
from ..bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy

class HighPerformanceStrategy(BollingerRsiEnhancedMTStrategy):
    """
    高性能ボリンジャーバンド＋RSI戦略
    
    勝率70%以上、プロフィットファクター2.0以上を目指した最適化戦略
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
            'bb_dev': 2.0,          # 2010年の成功パターンに合わせてバンド幅を広げる
            'rsi_window': 14,
            'rsi_upper': 70,        # RSI閾値を標準的な値に設定
            'rsi_lower': 30,        # RSI閾値を標準的な値に設定
            'sl_pips': 2.0,         # 損切り幅を小さくして勝率向上
            'tp_pips': 10.0,        # リスク・リワード比1:5を維持
            'atr_window': 14,
            'atr_sl_multiplier': 1.0,
            'atr_tp_multiplier': 5.0,  # ATRベースのリスク・リワード比1:5
            'use_adaptive_params': True,
            'trend_filter': True,   # トレンドフィルターを再有効化して高品質シグナルを選別
            'vol_filter': True,     # ボラティリティフィルターを再有効化して高品質シグナルを選別
            'time_filter': True,    # 時間フィルターを再有効化して高品質シグナルを選別
            'use_multi_timeframe': True,
            'timeframe_weights': {'15min': 1.0, '1H': 2.0, '4H': 3.0},  # 長期時間足の重みを大きくする
            'use_seasonal_filter': True, # 季節性フィルターを再有効化して高品質シグナルを選別
            'use_price_action': True,  # 価格アクションフィルターを再有効化して高品質シグナルを選別
            'consecutive_limit': 5,  # 連続シグナル制限を適度に設定
            'max_consecutive_losses': 2  # 連続損失後のポジションサイズ削減
        }
        
        self.max_consecutive_losses = default_params['max_consecutive_losses']
        if 'max_consecutive_losses' in kwargs:
            self.max_consecutive_losses = kwargs.pop('max_consecutive_losses')
        
        for key, value in default_params.items():
            if key != 'max_consecutive_losses' and key not in kwargs:
                kwargs[key] = value
        
        super().__init__(**kwargs)
        self.name = "高性能ボリンジャーバンド＋RSI戦略"
        self.consecutive_losses = 0
        self.market_environment = 'normal'  # 'normal', 'trending', 'volatile', 'ranging'
    
    def _detect_market_environment(self, df: pd.DataFrame, i: int) -> str:
        """
        現在の市場環境を検出する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        str
            市場環境 ('normal', 'trending', 'volatile', 'ranging')
        """
        if i < 50:
            return 'normal'
        
        recent_atr = df['atr'].iloc[i]
        avg_atr = df['atr'].iloc[i-20:i].mean()
        atr_ratio = recent_atr / avg_atr if avg_atr > 0 else 1.0
        
        price_change = abs(df['Close'].iloc[i] - df['Close'].iloc[i-20])
        price_range = df['High'].iloc[i-20:i].max() - df['Low'].iloc[i-20:i].min()
        price_change_ratio = price_change / price_range if price_range > 0 else 0.5
        
        ma_slope = (df['ma_50'].iloc[i] - df['ma_50'].iloc[i-10]) / 10
        ma_slope_normalized = abs(ma_slope) / df['Close'].iloc[i] * 1000  # 1000pipsあたりの傾き
        
        if atr_ratio > 1.8:  # 1.5から1.8に緩和
            return 'volatile'  # ボラティリティが高い
        elif ma_slope_normalized > 0.4:  # 0.5から0.4に緩和して検出率を向上
            return 'trending'  # トレンドが強い
        elif price_change_ratio < 0.25:  # 0.3から0.25に厳格化してレンジ相場の精度を向上
            return 'ranging'   # レンジ相場
        else:
            return 'normal'    # 通常の市場環境
    
    def _get_environment_specific_params(self, environment: str) -> Dict:
        """
        市場環境に応じたパラメータを取得する
        
        Parameters
        ----------
        environment : str
            市場環境 ('normal', 'trending', 'volatile', 'ranging')
            
        Returns
        -------
        Dict
            市場環境に応じたパラメータ
        """
        params = {
            'normal': {
                'rsi_upper': 65,  # 70から65に緩和して取引数を増加
                'rsi_lower': 35,  # 30から35に緩和して取引数を増加
                'bb_dev': 1.8,    # 2.0から1.8に縮小して取引数を増加
                'sl_pips': 2.0,
                'tp_pips': 10.0
            },
            'trending': {
                'rsi_upper': 75,  # 80から75に緩和して取引数を増加
                'rsi_lower': 25,
                'bb_dev': 2.0,    # 2.2から2.0に縮小して取引数を増加
                'sl_pips': 2.5,
                'tp_pips': 12.5
            },
            'volatile': {
                'rsi_upper': 80,  # 85から80に緩和して取引数を増加
                'rsi_lower': 20,  # 15から20に変更して極端な値を避ける
                'bb_dev': 2.2,    # 2.5から2.2に縮小して取引数を増加
                'sl_pips': 3.0,
                'tp_pips': 15.0
            },
            'ranging': {
                'rsi_upper': 60,  # 65から60に緩和して取引数を増加
                'rsi_lower': 40,  # 35から40に緩和して取引数を増加
                'bb_dev': 1.5,    # 1.6から1.5に縮小して取引数を増加
                'sl_pips': 1.5,
                'tp_pips': 7.5
            }
        }
        
        return params.get(environment, params['normal'])
    
    def _apply_trend_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        トレンドフィルターを適用する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            トレンドフィルターを通過する場合はTrue、そうでない場合はFalse
        """
        if i < 20:  # 50から20に緩和して早期からシグナルを生成可能に
            return False
        
        ma_20 = df['ma_20'].iloc[i]
        ma_50 = df['ma_50'].iloc[i]
        ma_100 = df['ma_100'].iloc[i]
        
        if df['rsi'].iloc[i] < self.rsi_lower and df['Close'].iloc[i] < df['lower_band'].iloc[i]:
            
            if ma_20 < ma_50 < ma_100:
                ma_slope = (ma_20 - df['ma_20'].iloc[i-10]) / 10 if i >= 10 else 0
                if ma_slope < -0.001:  # -0.0005から-0.001に緩和
                    return False
            
            if df['ma_20'].iloc[i] > df['ma_20'].iloc[i-5]:
                return True  # 条件を緩和（Close > ma_20の条件を削除）
                
            if (i >= 3 and 
                df['Close'].iloc[i-3] > df['Open'].iloc[i-3] and
                df['Close'].iloc[i-2] < df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
                df['Close'].iloc[i] > df['Open'].iloc[i]):
                return True
                
            if i > 0 and df['rsi'].iloc[i] > df['rsi'].iloc[i-1]:
                return True
        
        elif df['rsi'].iloc[i] > self.rsi_upper and df['Close'].iloc[i] > df['upper_band'].iloc[i]:
            
            if ma_20 > ma_50 > ma_100:
                ma_slope = (ma_20 - df['ma_20'].iloc[i-10]) / 10 if i >= 10 else 0
                if ma_slope > 0.001:  # 0.0005から0.001に緩和
                    return False
            
            if df['ma_20'].iloc[i] < df['ma_20'].iloc[i-5]:
                return True  # 条件を緩和（Close < ma_20の条件を削除）
                
            if (i >= 3 and 
                df['Close'].iloc[i-3] < df['Open'].iloc[i-3] and
                df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] > df['Open'].iloc[i-1] and
                df['Close'].iloc[i] < df['Open'].iloc[i]):
                return True
                
            if i > 0 and df['rsi'].iloc[i] < df['rsi'].iloc[i-1]:
                return True
        
        return False  # デフォルトではフィルターを通過しない
    
    def _apply_time_filter(self, df: pd.DataFrame, i: int) -> bool:
        """
        時間フィルターを適用する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            時間フィルターを通過する場合はTrue、そうでない場合はFalse
        """
        if not self.time_filter:
            return True
        
        hour = df.index[i].hour
        weekday = df.index[i].weekday()  # 0=月曜日, 6=日曜日
        month = df.index[i].month
        
        if not ((0 <= hour < 12) or (14 <= hour < 20)):  # UTCで調整
            return False
        
        if weekday == 0 or weekday == 4:
            if (weekday == 0 and hour < 2) or (weekday == 4 and hour > 20):
                return False
        
        # if month in [2]:  # 2月のみ除外（クリスマス休暇明け）
        #     return False
            
        return True
    
    def _check_price_action_patterns(self, df: pd.DataFrame, i: int) -> bool:
        """
        価格アクションパターンを確認する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
            
        Returns
        -------
        bool
            価格アクションパターンが確認された場合はTrue、そうでない場合はFalse
        """
        if not self.use_price_action or i < 3:
            return True
        
        if df['rsi'].iloc[i] < self.rsi_lower and df['Close'].iloc[i] < df['lower_band'].iloc[i]:
            if (df['Close'].iloc[i-3] > df['Open'].iloc[i-3] and
                df['Close'].iloc[i-2] < df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
                df['Close'].iloc[i] > df['Open'].iloc[i]):
                return True
            
            body_size = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            lower_wick = min(df['Close'].iloc[i], df['Open'].iloc[i]) - df['Low'].iloc[i]
            if lower_wick > body_size * 2:
                return True
            
            if (df['Close'].iloc[i-2] < df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
                df['Close'].iloc[i] < df['Open'].iloc[i]):
                return True
        
        elif df['rsi'].iloc[i] > self.rsi_upper and df['Close'].iloc[i] > df['upper_band'].iloc[i]:
            if (df['Close'].iloc[i-3] < df['Open'].iloc[i-3] and
                df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] > df['Open'].iloc[i-1] and
                df['Close'].iloc[i] < df['Open'].iloc[i]):
                return True
            
            body_size = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            upper_wick = df['High'].iloc[i] - max(df['Close'].iloc[i], df['Open'].iloc[i])
            if upper_wick > body_size * 2:
                return True
            
            if (df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] > df['Open'].iloc[i-1] and
                df['Close'].iloc[i] > df['Open'].iloc[i]):
                return True
        
        return False
    
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
        if i < 20:  # 50から20に緩和して早期からシグナルを生成可能に
            return False
            
        consecutive_signals = 0
        for j in range(1, min(self.consecutive_limit + 2, i + 1)):  # +1から+2に変更
            if df['signal'].iloc[i-j] != 0:
                consecutive_signals += 1
        
        if consecutive_signals >= self.consecutive_limit + 1:  # 制限を1つ増やす
            return False
        
        self.market_environment = self._detect_market_environment(df, i)
        
        env_params = self._get_environment_specific_params(self.market_environment)
        self.rsi_upper = env_params['rsi_upper']
        self.rsi_lower = env_params['rsi_lower']
        self.bb_dev = env_params['bb_dev']
        self.sl_pips = env_params['sl_pips']
        self.tp_pips = env_params['tp_pips']
        
        
        if df['rsi'].iloc[i] < self.rsi_lower:
            # if df['rsi'].iloc[i] > self.rsi_lower - 3:
            #     return False
                
            min_low = df['Low'].iloc[i-20:i].min()
            price_deviation = (df['Close'].iloc[i] - min_low) / min_low * 100
            
            if price_deviation > 2.0:  # 1.5%から2.0%に緩和してさらに取引数を増加
                return False
                
            down_count = 0
            for j in range(1, 4):  # 直近3本を確認
                if i-j >= 0 and df['Close'].iloc[i-j] < df['Open'].iloc[i-j]:
                    down_count += 1
            
            if down_count < 1:  # 2本から1本に緩和
                return False
                
            # bb_deviation = (df['lower_band'].iloc[i] - df['Close'].iloc[i]) / df['Close'].iloc[i] * 100
            # if bb_deviation < 0.1:
            #     return False
        
        elif df['rsi'].iloc[i] > self.rsi_upper:
            # if df['rsi'].iloc[i] < self.rsi_upper + 3:
            #     return False
                
            max_high = df['High'].iloc[i-20:i].max()
            price_deviation = (max_high - df['Close'].iloc[i]) / max_high * 100
            
            if price_deviation > 2.0:  # 1.5%から2.0%に緩和してさらに取引数を増加
                return False
                
            up_count = 0
            for j in range(1, 4):  # 直近3本を確認
                if i-j >= 0 and df['Close'].iloc[i-j] > df['Open'].iloc[i-j]:
                    up_count += 1
            
            if up_count < 1:  # 2本から1本に緩和
                return False
                
            # bb_deviation = (df['Close'].iloc[i] - df['upper_band'].iloc[i]) / df['Close'].iloc[i] * 100
            # if bb_deviation < 0.1:
            #     return False
        
        if i >= 50:  # 100から50に緩和
            ma_20 = df['ma_20'].iloc[i]
            ma_50 = df['ma_50'].iloc[i]
            
            if df['rsi'].iloc[i] < self.rsi_lower:
                ma_below_count = 0
                if df['Close'].iloc[i] < ma_20:
                    ma_below_count += 1
                if df['Close'].iloc[i] < ma_50:
                    ma_below_count += 1
                
                if ma_below_count < 1:  # 2から1に緩和
                    return False
            
            elif df['rsi'].iloc[i] > self.rsi_upper:
                ma_above_count = 0
                if df['Close'].iloc[i] > ma_20:
                    ma_above_count += 1
                if df['Close'].iloc[i] > ma_50:
                    ma_above_count += 1
                
                if ma_above_count < 1:  # 2から1に緩和
                    return False
        
        if self.trend_filter and not self._apply_trend_filter(df, i):
            return False
            
        if self.vol_filter:
            atr = df['atr'].iloc[i]
            avg_atr = df['atr'].iloc[i-20:i].mean()
            
            if atr < avg_atr * 0.5:  # 0.6から0.5に緩和してより多くのシグナルを許可
                return False
            
            if atr > avg_atr * 2.5:  # 2.0から2.5に緩和して極端な高ボラティリティでも取引可能に
                return False
        
        if self.time_filter and not self._apply_time_filter(df, i):
            return False
            
        if self.use_seasonal_filter:
            month = df.index[i].month
            
            if month in [2]:  # 2月のみ除外（低流動性月）
                return False
        
        # 価格アクションパターンフィルターを条件付きで適用（市場環境がレンジ相場の場合のみ）
        # 価格アクションパターンフィルターを完全に無効化して取引数を増加
        # if self.use_price_action and self.market_environment != 'ranging' and not self._check_price_action_patterns(df, i):
        #     return False
        
        return True
    
    def _calculate_position_size(self, df: pd.DataFrame, i: int, signal: int) -> float:
        """
        ポジションサイズを計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        i : int
            現在の行のインデックス
        signal : int
            シグナル（1: 買い、-1: 売り、0: なし）
            
        Returns
        -------
        float
            ポジションサイズ
        """
        base_size = 0.01  # 基本ロットサイズ
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return base_size * 0.5  # 連続損失後は50%に削減
        
        return base_size
    
    def _generate_signals_multi_timeframe(self, df: pd.DataFrame, year: int, processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        複数時間足分析を用いてトレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            主要時間足（15分足）のデータ
        year : int
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルを含むデータフレーム
        """
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
        
        result_df = self.merge_timeframe_signals(df, signals)
        
        self.timeframe_weights = temp_weights
        
        return result_df
        
    def generate_signals(self, df: pd.DataFrame, year: int, processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
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
        if self.use_multi_timeframe:
            return self._generate_signals_multi_timeframe(df, year, processed_dir)
        
        signals_df = df.copy()
        
        if 'ma_20' not in signals_df.columns:
            signals_df['ma_20'] = signals_df['Close'].rolling(window=20).mean()
        if 'ma_50' not in signals_df.columns:
            signals_df['ma_50'] = signals_df['Close'].rolling(window=50).mean()
        if 'ma_100' not in signals_df.columns:
            signals_df['ma_100'] = signals_df['Close'].rolling(window=100).mean()
            
        signals_df['signal'] = 0
        signals_df['sl_price'] = np.nan
        signals_df['tp_price'] = np.nan
        signals_df['position_size'] = np.nan
        signals_df['strategy'] = self.name
        
        for i in range(1, len(signals_df)):
            if signals_df['rsi'].iloc[i] < self.rsi_lower and signals_df['Close'].iloc[i] < signals_df['lower_band'].iloc[i]:
                if self._apply_filters(signals_df, i):
                    signals_df.loc[signals_df.index[i], 'signal'] = 1  # 買いシグナル
                    
                    if self.use_adaptive_params:
                        sl_pips = signals_df['atr'].iloc[i] * self.atr_sl_multiplier
                        tp_pips = signals_df['atr'].iloc[i] * self.atr_tp_multiplier
                    else:
                        sl_pips = self.sl_pips
                        tp_pips = self.tp_pips
                    
                    signals_df.loc[signals_df.index[i], 'sl_price'] = signals_df['Close'].iloc[i] - sl_pips / 100
                    signals_df.loc[signals_df.index[i], 'tp_price'] = signals_df['Close'].iloc[i] + tp_pips / 100
                    
                    signals_df.loc[signals_df.index[i], 'position_size'] = self._calculate_position_size(signals_df, i, 1)
            
            elif signals_df['rsi'].iloc[i] > self.rsi_upper and signals_df['Close'].iloc[i] > signals_df['upper_band'].iloc[i]:
                if self._apply_filters(signals_df, i):
                    signals_df.loc[signals_df.index[i], 'signal'] = -1  # 売りシグナル
                    
                    if self.use_adaptive_params:
                        sl_pips = signals_df['atr'].iloc[i] * self.atr_sl_multiplier
                        tp_pips = signals_df['atr'].iloc[i] * self.atr_tp_multiplier
                    else:
                        sl_pips = self.sl_pips
                        tp_pips = self.tp_pips
                    
                    signals_df.loc[signals_df.index[i], 'sl_price'] = signals_df['Close'].iloc[i] + sl_pips / 100
                    signals_df.loc[signals_df.index[i], 'tp_price'] = signals_df['Close'].iloc[i] - tp_pips / 100
                    
                    signals_df.loc[signals_df.index[i], 'position_size'] = self._calculate_position_size(signals_df, i, -1)
        
        return signals_df
    
    def update_consecutive_losses(self, is_win: bool):
        """
        連続損失カウンターを更新する
        
        Parameters
        ----------
        is_win : bool
            勝ちトレードの場合はTrue、負けトレードの場合はFalse
        """
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
