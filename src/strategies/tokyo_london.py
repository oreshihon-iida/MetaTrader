import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional

class TokyoLondonStrategy:
    """
    東京レンジ・ロンドンブレイクアウト戦略
    
    9:00～15:00（東京時間）の高値・安値をレンジとして記録
    16:00以降、高値・安値のどちらかを明確にブレイクしたら、その方向にエントリー
    損切り幅（SL）：10pips
    利確幅（TP）：15pips
    """
    
    def __init__(self, sl_pips: float = 10.0, tp_pips: float = 15.0):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 10.0
            損切り幅（pips）
        tp_pips : float, default 15.0
            利確幅（pips）
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.name = "東京レンジ・ロンドンブレイクアウト"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ（15分足）。tokyo_high, tokyo_lowカラムが必要。
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        df['hour_jst'] = (df.index + pd.Timedelta(hours=9)).hour
        
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        df['strategy'] = None
        
        df['prev_close'] = df['Close'].shift(1)
        
        london_session = df[df['hour_jst'] >= 16].copy()
        
        for i in range(1, len(london_session)):
            idx = london_session.index[i]
            prev_idx = london_session.index[i-1]
            
            if df.loc[prev_idx, 'signal'] != 0:
                continue
            
            current = london_session.iloc[i]
            previous = london_session.iloc[i-1]
            
            if (previous['Close'] > current['tokyo_high'] and 
                current['prev_close'] <= current['tokyo_high']):
                df.loc[idx, 'signal'] = 1
                df.loc[idx, 'entry_price'] = current['Close']
                df.loc[idx, 'sl_price'] = current['Close'] - self.sl_pips * 0.01
                df.loc[idx, 'tp_price'] = current['Close'] + self.tp_pips * 0.01
                df.loc[idx, 'strategy'] = self.name
            
            elif (previous['Close'] < current['tokyo_low'] and 
                  current['prev_close'] >= current['tokyo_low']):
                df.loc[idx, 'signal'] = -1
                df.loc[idx, 'entry_price'] = current['Close']
                df.loc[idx, 'sl_price'] = current['Close'] + self.sl_pips * 0.01
                df.loc[idx, 'tp_price'] = current['Close'] - self.tp_pips * 0.01
                df.loc[idx, 'strategy'] = self.name
        
        df = df.drop(['hour_jst', 'prev_close'], axis=1)
        
        return df
