import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor import DataProcessor

class BollingerRsiEnhancedStrategy:
    """
    拡張版ボリンジャーバンド＋RSI逆張り戦略
    
    従来のボリンジャーバンド＋RSI戦略をベースに、以下の機能を追加：
    - パラメータの最適化機能
    - 適応型パラメータ（ボラティリティに基づく調整）
    - 追加のフィルタリング条件
    - 強化されたエントリー/イグジット条件
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
                time_filter: bool = True):
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
        """
        self.bb_window = bb_window
        self.bb_dev = bb_dev
        self.rsi_window = rsi_window
        self.rsi_upper = rsi_upper
        self.rsi_lower = rsi_lower
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.atr_window = atr_window
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp_multiplier = atr_tp_multiplier
        self.use_adaptive_params = use_adaptive_params
        self.trend_filter = trend_filter
        self.vol_filter = vol_filter
        self.time_filter = time_filter
        self.name = "拡張版ボリンジャーバンド＋RSI逆張り"
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        必要なテクニカル指標を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
            
        Returns
        -------
        pd.DataFrame
            テクニカル指標が追加されたDataFrame
        """
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns or 'rsi' not in df.columns:
            temp_processor = DataProcessor(pd.DataFrame())
            df = temp_processor.add_technical_indicators(df)
        
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=self.atr_window).mean()
        
        df['sma_short'] = df['Close'].rolling(window=10).mean()
        df['sma_medium'] = df['Close'].rolling(window=20).mean()
        df['sma_long'] = df['Close'].rolling(window=50).mean()
        
        df['trend'] = 0
        df.loc[(df['sma_short'] > df['sma_medium']) & (df['sma_medium'] > df['sma_long']), 'trend'] = 1  # 上昇トレンド
        df.loc[(df['sma_short'] < df['sma_medium']) & (df['sma_medium'] < df['sma_long']), 'trend'] = -1  # 下降トレンド
        
        return df
    
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
        current = df.iloc[i]
        
        if i > 0 and df['signal'].iloc[i-1] != 0:
            return False
        
        if self.trend_filter:
            if current['Close'] >= current['bb_upper'] and current['trend'] == 1:
                return False  # 上昇トレンド中の売りシグナルを無効化
            if current['Close'] <= current['bb_lower'] and current['trend'] == -1:
                return False  # 下降トレンド中の買いシグナルを無効化
        
        if self.vol_filter:
            avg_atr = df['atr'].iloc[max(0, i-20):i+1].mean()
            if current['atr'] > avg_atr * 2:
                return False
        
        if self.time_filter:
            hour = df.index[i].hour
            if not ((0 <= hour < 6) or (7 <= hour < 15)):
                return False
        
        return True
    
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
            sl_distance = current['atr'] * self.atr_sl_multiplier
            tp_distance = current['atr'] * self.atr_tp_multiplier
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
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ（15分足）
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        df = df.copy()
        
        df = self._calculate_technical_indicators(df)
        
        if 'signal' not in df.columns:
            df['signal'] = 0
            df['entry_price'] = np.nan
            df['sl_price'] = np.nan
            df['tp_price'] = np.nan
            df['strategy'] = None
        
        df['prev_close'] = df['Close'].shift(1)
        
        for i in range(1, len(df)):
            if not self._apply_filters(df, i):
                continue
            
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            if (previous['Close'] >= previous['bb_upper'] and 
                previous['rsi'] >= self.rsi_upper):
                
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = current['Open']
                
                sl_price, tp_price = self._calculate_adaptive_sl_tp(df, i, -1)
                
                df.loc[df.index[i], 'sl_price'] = sl_price
                df.loc[df.index[i], 'tp_price'] = tp_price
                df.loc[df.index[i], 'strategy'] = self.name
            
            elif (previous['Close'] <= previous['bb_lower'] and 
                  previous['rsi'] <= self.rsi_lower):
                
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = current['Open']
                
                sl_price, tp_price = self._calculate_adaptive_sl_tp(df, i, 1)
                
                df.loc[df.index[i], 'sl_price'] = sl_price
                df.loc[df.index[i], 'tp_price'] = tp_price
                df.loc[df.index[i], 'strategy'] = self.name
        
        df = df.drop(['prev_close', 'tr'], axis=1, errors='ignore')
        
        return df
