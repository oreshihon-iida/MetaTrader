import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional

class BollingerRsiStrategy:
    """
    ボリンジャーバンド＋RSI逆張り戦略
    
    ボリンジャーバンド2σ（±2σ）到達 ＆ RSIが70超（売り）or 30未満（買い）の両方成立で逆張りエントリー
    損切り幅（SL）：7pips
    利確幅（TP）：10pips
    """
    
    def __init__(self, sl_pips: float = 7.0, tp_pips: float = 10.0):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 7.0
            損切り幅（pips）
        tp_pips : float, default 10.0
            利確幅（pips）
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.name = "ボリンジャーバンド＋RSI逆張り"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ（15分足）。bb_upper, bb_lower, rsiカラムが必要。
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        if 'signal' not in df.columns:
            df['signal'] = 0
            df['entry_price'] = np.nan
            df['sl_price'] = np.nan
            df['tp_price'] = np.nan
            df['strategy'] = None
        
        df['prev_close'] = df['Close'].shift(1)
        
        for i in range(1, len(df)):
            if df['signal'].iloc[i-1] != 0:
                continue
            
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            if (previous['Close'] >= previous['bb_upper'] and 
                previous['rsi'] >= 70):
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'entry_price'] = current['Open']
                df.loc[df.index[i], 'sl_price'] = current['Open'] + self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = current['Open'] - self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = self.name
            
            elif (previous['Close'] <= previous['bb_lower'] and 
                  previous['rsi'] <= 30):
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = current['Open']
                df.loc[df.index[i], 'sl_price'] = current['Open'] - self.sl_pips * 0.01
                df.loc[df.index[i], 'tp_price'] = current['Open'] + self.tp_pips * 0.01
                df.loc[df.index[i], 'strategy'] = self.name
        
        df = df.drop('prev_close', axis=1)
        
        return df
