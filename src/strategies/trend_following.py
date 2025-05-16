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
    
    def __init__(self, short_ma: int = 5, long_ma: int = 20, min_adx: float = 25.0, atr_multiplier: float = 2.0):
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
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.min_adx = min_adx
        self.atr_multiplier = atr_multiplier
        self.name = "トレンド追従"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            15分足のOHLCデータ
               
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
            
            if trend_up and curr_row['ma_cross'] == 1:
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                    tp_pips_dynamic = self.atr_multiplier * 2.0 * curr_row['atr'] / 0.01
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + tp_pips_dynamic * 0.01
            
            elif not trend_up and curr_row['ma_cross'] == -1:
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                    tp_pips_dynamic = self.atr_multiplier * 2.0 * curr_row['atr'] / 0.01
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] - tp_pips_dynamic * 0.01
        
        columns_to_drop = ['ma_cross']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(col, axis=1)
        
        return df
