import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class RangeTradingStrategy:
    """
    レンジ取引戦略
    
    ADXでレンジ相場を確認し、ボリンジャーバンドとストキャスティクスを組み合わせてエントリーする
    
    特徴：
    - ADXによるレンジ相場の確認（ADX < 20）
    - ボリンジャーバンドの上下限でのエントリー
    - ストキャスティクスによる確認
    - ATRベースの動的な損切り/利確幅
    """
    
    def __init__(self, max_adx: float = 20.0, stoch_k: int = 14, stoch_d: int = 3, atr_multiplier: float = 1.0):
        """
        初期化
        
        Parameters
        ----------
        max_adx : float, default 20.0
            最大ADX値（これより高い場合はエントリーしない）
        stoch_k : int, default 14
            ストキャスティクスのK期間
        stoch_d : int, default 3
            ストキャスティクスのD期間
        atr_multiplier : float, default 1.0
            ATRの乗数（動的なストップロス/テイクプロフィットの計算に使用）
        """
        self.max_adx = max_adx
        self.stoch_k = stoch_k
        self.stoch_d = stoch_d
        self.atr_multiplier = atr_multiplier
        self.name = "レンジ取引"
    
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
        
        df['stoch_k'] = 100 * (df['Close'] - df['Low'].rolling(window=self.stoch_k).min()) / \
                        (df['High'].rolling(window=self.stoch_k).max() - df['Low'].rolling(window=self.stoch_k).min())
        df['stoch_d'] = df['stoch_k'].rolling(window=self.stoch_d).mean()
        
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        df['trailing_stop'] = False
        df['strategy'] = None
        
        for i in range(self.stoch_k + self.stoch_d, len(df)):
            curr_row = df.iloc[i]
            
            if 'adx' in curr_row and curr_row['adx'] > self.max_adx:
                continue
            
            if curr_row['Close'] <= curr_row['bb_lower'] and curr_row['stoch_k'] <= 20 and curr_row['stoch_d'] <= 20:
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                    tp_pips_dynamic = self.atr_multiplier * 1.5 * curr_row['atr'] / 0.01
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + tp_pips_dynamic * 0.01
                else:
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - 7.0 * 0.01  # デフォルト7pips
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + 10.0 * 0.01  # デフォルト10pips
            
            elif curr_row['Close'] >= curr_row['bb_upper'] and curr_row['stoch_k'] >= 80 and curr_row['stoch_d'] >= 80:
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                    tp_pips_dynamic = self.atr_multiplier * 1.5 * curr_row['atr'] / 0.01
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] - tp_pips_dynamic * 0.01
                else:
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + 7.0 * 0.01  # デフォルト7pips
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] - 10.0 * 0.01  # デフォルト10pips
        
        columns_to_drop = ['stoch_k', 'stoch_d']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(col, axis=1)
        
        return df
