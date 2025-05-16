import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional

class TokyoLondonStrategy:
    """
    東京レンジ・ロンドンブレイクアウト戦略
    
    東京時間のレンジを計算し、ロンドン時間にブレイクアウトしたらエントリーする
    
    改善ポイント：
    - ADXによる市場環境フィルター（トレンド相場のみで取引）
    - 時間帯フィルター（ニューヨーク時間のボラティリティが高い時間を除外）
    - ATRベースの動的な損切り/利確幅
    - 偽ブレイクアウト対策（一定以上の値動きがあった場合のみエントリー）
    """
    
    def __init__(self, sl_pips: float = 10.0, tp_pips: float = 15.0, atr_multiplier: float = 1.5, min_adx: float = 25.0):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 10.0
            固定ストップロス（pips）
        tp_pips : float, default 15.0
            固定テイクプロフィット（pips）
        atr_multiplier : float, default 1.5
            ATRの乗数（動的なストップロス/テイクプロフィットの計算に使用）
        min_adx : float, default 25.0
            最小ADX値（これより低い場合はエントリーしない）
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.atr_multiplier = atr_multiplier
        self.min_adx = min_adx
        self.name = "東京レンジ・ロンドンブレイクアウト"
    
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
        
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        df['trailing_stop'] = False  # トレイリングストップフラグ
        df['strategy'] = None
        
        jst_hours = (df.index.hour + 9) % 24
        
        df['valid_time'] = ~((jst_hours >= 21) & (jst_hours < 24))
        
        for i in range(1, len(df)):
            prev_row = df.iloc[i-1]
            curr_row = df.iloc[i]
            
            if not curr_row['valid_time']:
                continue
                
            if 'adx' in curr_row and curr_row['adx'] < self.min_adx:
                continue
            
            jst_hour = (df.index[i].hour + 9) % 24
            
            if jst_hour >= 16:
                tokyo_high = curr_row['tokyo_high']
                tokyo_low = curr_row['tokyo_low']
                
                if curr_row['Close'] > tokyo_high and (curr_row['Close'] - tokyo_high) > 0.5 * curr_row['atr']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                    df.loc[df.index[i], 'strategy'] = self.name
                    
                    if 'atr' in curr_row:
                        sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01  # 0.01 = 1pip（USD/JPY）
                        tp_pips_dynamic = self.atr_multiplier * 1.5 * curr_row['atr'] / 0.01
                        
                        df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - sl_pips_dynamic * 0.01
                        df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + tp_pips_dynamic * 0.01
                        df.loc[df.index[i], 'trailing_stop'] = True
                    else:
                        df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - self.sl_pips * 0.01
                        df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + self.tp_pips * 0.01
                
                elif curr_row['Close'] < tokyo_low and (tokyo_low - curr_row['Close']) > 0.5 * curr_row['atr']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                    df.loc[df.index[i], 'strategy'] = self.name
                    
                    if 'atr' in curr_row:
                        sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                        tp_pips_dynamic = self.atr_multiplier * 1.5 * curr_row['atr'] / 0.01
                        
                        df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + sl_pips_dynamic * 0.01
                        df.loc[df.index[i], 'tp_price'] = curr_row['Close'] - tp_pips_dynamic * 0.01
                        df.loc[df.index[i], 'trailing_stop'] = True
                    else:
                        df.loc[df.index[i], 'sl_price'] = curr_row['Close'] + self.sl_pips * 0.01
                        df.loc[df.index[i], 'tp_price'] = curr_row['Close'] - self.tp_pips * 0.01
        
        if 'valid_time' in df.columns:
            df = df.drop('valid_time', axis=1)
        
        return df
