import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class TrendFollowingStrategy:
    """
    トレンド追従戦略
    
    ADXでトレンドを確認し、移動平均線のクロスでエントリーする
    
    特徴：
    - ADXによる強いトレンドの確認（ADX > 25）
    - 短期/長期移動平均線のクロスでエントリー
    - ATRベースの動的な損切り/利確幅
    - トレイリングストップの導入
    """
    
    def __init__(self, short_ma: int = 5, long_ma: int = 20, min_adx: float = 25.0, atr_multiplier: float = 2.0, use_higher_timeframe: bool = True):
        """
        初期化
        
        Parameters
        ----------
        short_ma : int, default 5
            短期移動平均線の期間
        long_ma : int, default 20
            長期移動平均線の期間
        min_adx : float, default 25.0
            最小ADX値（これより低い場合はエントリーしない）
        atr_multiplier : float, default 2.0
            ATRの乗数（動的なストップロス/テイクプロフィットの計算に使用）
        use_higher_timeframe : bool, default True
            1時間足での確認を使用するかどうか
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.min_adx = min_adx
        self.atr_multiplier = atr_multiplier
        self.use_higher_timeframe = use_higher_timeframe
        self.name = "トレンド追従"
    
    def generate_signals(self, df: pd.DataFrame, hourly_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            15分足のOHLCデータ
        hourly_df : pd.DataFrame, default None
            1時間足のOHLCデータ（複数時間足分析用）
               
        Returns
        -------
        pd.DataFrame
            トレードシグナルが追加されたDataFrame
        """
        df = df.copy()
        
        df[f'ma_{self.short_ma}'] = df['Close'].rolling(window=self.short_ma).mean()
        df[f'ma_{self.long_ma}'] = df['Close'].rolling(window=self.long_ma).mean()
        
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        df['trailing_stop'] = True  # トレイリングストップを常に有効
        df['strategy'] = None
        
        df['ma_cross'] = 0
        
        for i in range(1, len(df)):
            prev_row = df.iloc[i-1]
            curr_row = df.iloc[i]
            
            if prev_row[f'ma_{self.short_ma}'] <= prev_row[f'ma_{self.long_ma}'] and \
               curr_row[f'ma_{self.short_ma}'] > curr_row[f'ma_{self.long_ma}']:
                df.loc[df.index[i], 'ma_cross'] = 1
            
            elif prev_row[f'ma_{self.short_ma}'] >= prev_row[f'ma_{self.long_ma}'] and \
                 curr_row[f'ma_{self.short_ma}'] < curr_row[f'ma_{self.long_ma}']:
                df.loc[df.index[i], 'ma_cross'] = -1
        
        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            
            if 'adx' not in curr_row or curr_row['adx'] < self.min_adx:
                continue
            
            trend_up = curr_row['adx_pos'] > curr_row['adx_neg']
            
            higher_tf_trend_up = None  # 初期値：未確認
            
            if self.use_higher_timeframe and hourly_df is not None:
                current_time = df.index[i]
                closest_hourly_idx = hourly_df.index.get_indexer([current_time], method='pad')[0]
                
                if closest_hourly_idx >= 0:
                    higher_tf_row = hourly_df.iloc[closest_hourly_idx]
                    if 'adx_pos' in higher_tf_row and 'adx_neg' in higher_tf_row:
                        higher_tf_trend_up = higher_tf_row['adx_pos'] > higher_tf_row['adx_neg']
            
            near_resistance = np.nan
            near_support = np.nan
            
            if 'nearest_resistance' in curr_row:
                near_resistance = curr_row['nearest_resistance']
            if 'nearest_support' in curr_row:
                near_support = curr_row['nearest_support']
            
            if trend_up and curr_row['ma_cross'] == 1 and (higher_tf_trend_up is None or higher_tf_trend_up):
                signal_strength = 1.0
                if not np.isnan(near_support) and abs(curr_row['Close'] - near_support) < 10 * 0.01:  # 10pips以内
                    signal_strength = 1.5  # シグナル強度を上げる
                
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01 * signal_strength
                    tp_pips_dynamic = self.atr_multiplier * 2.0 * curr_row['atr'] / 0.01 * signal_strength
                    
                    adjusted_tp = curr_row['Close'] + tp_pips_dynamic * 0.01
                    if not np.isnan(near_resistance) and near_resistance > curr_row['Close'] and near_resistance < adjusted_tp:
                        adjusted_tp = near_resistance
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = adjusted_tp
            
            elif not trend_up and curr_row['ma_cross'] == -1 and (higher_tf_trend_up is None or not higher_tf_trend_up):
                signal_strength = 1.0
                if not np.isnan(near_resistance) and abs(curr_row['Close'] - near_resistance) < 10 * 0.01:  # 10pips以内
                    signal_strength = 1.5  # シグナル強度を上げる
                
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01 * signal_strength
                    tp_pips_dynamic = self.atr_multiplier * 2.0 * curr_row['atr'] / 0.01 * signal_strength
                    
                    adjusted_tp = curr_row['Close'] - tp_pips_dynamic * 0.01
                    if not np.isnan(near_support) and near_support < curr_row['Close'] and near_support > adjusted_tp:
                        adjusted_tp = near_support
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = adjusted_tp
        
        columns_to_drop = ['ma_cross']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(col, axis=1)
        
        return df
