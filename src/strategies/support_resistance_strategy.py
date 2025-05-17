import pandas as pd
import numpy as np

class SupportResistanceStrategy:
    """
    サポート/レジスタンスレベルに基づく取引戦略
    """
    
    def __init__(self, sl_pips=10.0, tp_pips=15.0, bounce_threshold=0.0002, breakout_threshold=0.0003):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 10.0
            損切り幅（pips）
        tp_pips : float, default 15.0
            利確幅（pips）
        bounce_threshold : float, default 0.0002
            バウンス判定の閾値
        breakout_threshold : float, default 0.0003
            ブレイクアウト判定の閾値
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.bounce_threshold = bounce_threshold
        self.breakout_threshold = breakout_threshold
        self.strategy_name = "Support/Resistance"
    
    def generate_signals(self, df):
        """
        トレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ（15分足）。support_level_*およびresistance_level_*カラムが必要。
            
        Returns
        -------
        pd.DataFrame
            シグナルを追加したデータフレーム
        """
        result_df = df.copy()
        
        result_df['signal'] = 0
        result_df['entry_price'] = np.nan
        result_df['sl_price'] = np.nan
        result_df['tp_price'] = np.nan
        result_df['strategy'] = ''
        
        result_df['rsi'] = self._calculate_rsi(result_df['Close'], 14)
        
        for i in range(1, len(result_df)):
            current_row = result_df.iloc[i]
            prev_row = result_df.iloc[i-1]
            price = current_row['Close']
            
            if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']):
                support_level = current_row['support_level_1']
                
                if (prev_row['Low'] - support_level) / support_level < self.bounce_threshold and current_row['rsi'] < 30:
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBounce"
            
            if 'resistance_level_1' in current_row and not pd.isna(current_row['resistance_level_1']):
                resistance_level = current_row['resistance_level_1']
                
                if (resistance_level - prev_row['High']) / resistance_level < self.bounce_threshold and current_row['rsi'] > 70:
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBounce"
            
            if 'support_level_1' in prev_row and not pd.isna(prev_row['support_level_1']):
                support_level = prev_row['support_level_1']
                
                if (price < support_level and (support_level - price) / support_level > self.breakout_threshold):
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBreak"
            
            if 'resistance_level_1' in prev_row and not pd.isna(prev_row['resistance_level_1']):
                resistance_level = prev_row['resistance_level_1']
                
                if (price > resistance_level and (price - resistance_level) / resistance_level > self.breakout_threshold):
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBreak"
            
            if 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']):
                h1_support = current_row['h1_support_level_1']
                
                if (prev_row['Low'] - h1_support) / h1_support < self.bounce_threshold and current_row['rsi'] < 30:
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_SupportBounce"
            
            if 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']):
                h1_resistance = current_row['h1_resistance_level_1']
                
                if (h1_resistance - prev_row['High']) / h1_resistance < self.bounce_threshold and current_row['rsi'] > 70:
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_ResistanceBounce"
        
        return result_df
    
    def _calculate_rsi(self, prices, window=14):
        """
        RSI（相対力指数）を計算する
        
        Parameters
        ----------
        prices : pd.Series
            価格系列
        window : int, default 14
            RSIの計算期間
            
        Returns
        -------
        pd.Series
            RSI値
        """
        delta = prices.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
