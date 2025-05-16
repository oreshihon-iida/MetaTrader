import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional

class BollingerRsiStrategy:
    """
    ボリンジャーバンド＋RSI逆張り戦略
    
    価格がボリンジャーバンドの上下限に達し、かつRSIが過買い/過売りの状態でエントリーする
    
    改善ポイント：
    - 市場環境フィルター（レンジ相場のみで取引）
    - 時間帯フィルター（ボラティリティが低い時間帯のみ）
    - ATRベースの動的な損切り/利確幅
    - RSIのダイバージェンスをエントリーの追加条件に
    - トレイリングストップの導入
    """
    
    def __init__(self, sl_pips: float = 7.0, tp_pips: float = 10.0, atr_multiplier: float = 1.2, max_adx: float = 20.0):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 7.0
            固定ストップロス（pips）
        tp_pips : float, default 10.0
            固定テイクプロフィット（pips）
        atr_multiplier : float, default 1.2
            ATRの乗数（動的なストップロス/テイクプロフィットの計算に使用）
        max_adx : float, default 20.0
            最大ADX値（これより高い場合はエントリーしない）
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.atr_multiplier = atr_multiplier
        self.max_adx = max_adx
        self.name = "ボリンジャーバンド＋RSI逆張り"
    
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
        
        df['rsi_divergence'] = 0
        
        df['price_higher_high'] = False
        df['price_lower_low'] = False
        df['rsi_higher_high'] = False
        df['rsi_lower_low'] = False
        
        window_size = 5
        for i in range(window_size, len(df) - window_size):
            price_left = df['Close'].iloc[i-window_size:i].max()
            price_right = df['Close'].iloc[i:i+window_size].max()
            rsi_left = df['rsi'].iloc[i-window_size:i].max()
            rsi_right = df['rsi'].iloc[i:i+window_size].max()
            
            if price_right > price_left and rsi_right < rsi_left:
                df.loc[df.index[i], 'rsi_divergence'] = -1
                
            price_left = df['Close'].iloc[i-window_size:i].min()
            price_right = df['Close'].iloc[i:i+window_size].min()
            rsi_left = df['rsi'].iloc[i-window_size:i].min()
            rsi_right = df['rsi'].iloc[i:i+window_size].min()
            
            if price_right < price_left and rsi_right > rsi_left:
                df.loc[df.index[i], 'rsi_divergence'] = 1
        
        jst_hours = (df.index.hour + 9) % 24
        
        df['valid_time'] = (jst_hours >= 9) & (jst_hours < 15)
        
        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            
            if not curr_row['valid_time']:
                continue
                
            if 'adx' in curr_row and curr_row['adx'] > self.max_adx:
                continue
            
            upper_band_touch = curr_row['Close'] >= curr_row['bb_upper']
            rsi_overbought = curr_row['rsi'] >= 70
            bearish_divergence = curr_row['rsi_divergence'] == -1
            
            if upper_band_touch and rsi_overbought and bearish_divergence:
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
                    
            lower_band_touch = curr_row['Close'] <= curr_row['bb_lower']
            rsi_oversold = curr_row['rsi'] <= 30
            bullish_divergence = curr_row['rsi_divergence'] == 1
            
            if lower_band_touch and rsi_oversold and bullish_divergence:
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'entry_price'] = curr_row['Close']
                df.loc[df.index[i], 'strategy'] = self.name
                
                if 'atr' in curr_row:
                    sl_pips_dynamic = self.atr_multiplier * curr_row['atr'] / 0.01
                    tp_pips_dynamic = self.atr_multiplier * 1.5 * curr_row['atr'] / 0.01
                    
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - sl_pips_dynamic * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + tp_pips_dynamic * 0.01
                    df.loc[df.index[i], 'trailing_stop'] = True
                else:
                    df.loc[df.index[i], 'sl_price'] = curr_row['Close'] - self.sl_pips * 0.01
                    df.loc[df.index[i], 'tp_price'] = curr_row['Close'] + self.tp_pips * 0.01
        
        columns_to_drop = ['price_higher_high', 'price_lower_low', 'rsi_higher_high', 'rsi_lower_low', 'rsi_divergence', 'valid_time']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(col, axis=1)
        
        return df
