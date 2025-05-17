import pandas as pd
import numpy as np

class SupportResistanceStrategy:
    """
    サポート/レジスタンスレベルに基づく取引戦略（改良版）
    """
    
    def __init__(self, sl_pips=10.0, tp_pips=20.0, bounce_threshold=0.0003, breakout_threshold=0.0005, 
                 rsi_lower=40, rsi_upper=60, min_level_strength=2, max_signals_per_day=3):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 10.0
            損切り幅（pips）
        tp_pips : float, default 20.0
            利確幅（pips）
        bounce_threshold : float, default 0.0003
            バウンス判定の閾値
        breakout_threshold : float, default 0.0005
            ブレイクアウト判定の閾値
        rsi_lower : int, default 40
            RSI下限閾値
        rsi_upper : int, default 60
            RSI上限閾値
        min_level_strength : int, default 2
            最小レベル強度（タッチ回数）
        max_signals_per_day : int, default 3
            1日あたりの最大シグナル数
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.bounce_threshold = bounce_threshold
        self.breakout_threshold = breakout_threshold
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.min_level_strength = min_level_strength
        self.max_signals_per_day = max_signals_per_day
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
        result_df['rsi_slope'] = self._calculate_slope(result_df['rsi'], 5)
        
        result_df['ma20'] = result_df['Close'].rolling(window=20).mean()
        result_df['trend'] = self._calculate_slope(result_df['ma20'], 10)
        
        daily_signal_count = {}
        
        for i in range(5, len(result_df)):
            current_row = result_df.iloc[i]
            prev_row = result_df.iloc[i-1]
            price = current_row['Close']
            
            if isinstance(result_df.index[i], pd.Timestamp):
                current_date = result_df.index[i].date()
            else:
                current_date = pd.to_datetime(result_df.index[i]).date()
            
            if current_date not in daily_signal_count:
                daily_signal_count[current_date] = 0
            
            if daily_signal_count[current_date] >= self.max_signals_per_day:
                continue
            
            support_strength = self._calculate_level_strength(result_df, i, 'support')
            resistance_strength = self._calculate_level_strength(result_df, i, 'resistance')
            
            if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']) and current_row['trend'] > 0:
                support_level = current_row['support_level_1']
                
                price_near_support = (prev_row['Low'] - support_level) / support_level < self.bounce_threshold
                rsi_condition = current_row['rsi'] < self.rsi_lower and current_row['rsi_slope'] > 0
                
                if price_near_support and rsi_condition and support_strength >= self.min_level_strength:
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBounce"
                    daily_signal_count[current_date] += 1
            
            if 'resistance_level_1' in current_row and not pd.isna(current_row['resistance_level_1']) and current_row['trend'] < 0:
                resistance_level = current_row['resistance_level_1']
                
                price_near_resistance = (resistance_level - prev_row['High']) / resistance_level < self.bounce_threshold
                rsi_condition = current_row['rsi'] > self.rsi_upper and current_row['rsi_slope'] < 0
                
                if price_near_resistance and rsi_condition and resistance_strength >= self.min_level_strength:
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                    result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBounce"
                    daily_signal_count[current_date] += 1
            
            if 'support_level_1' in prev_row and not pd.isna(prev_row['support_level_1']) and current_row['trend'] < 0:
                support_level = prev_row['support_level_1']
                
                breakout_condition = price < support_level and (support_level - price) / support_level > self.breakout_threshold
                volume_condition = True  # ボリューム条件（データがあれば追加）
                
                if breakout_condition and volume_condition and support_strength >= self.min_level_strength:
                    h1_confirmation = True
                    if 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']):
                        h1_support = current_row['h1_support_level_1']
                        h1_confirmation = price < h1_support
                    
                    if h1_confirmation:
                        result_df.loc[result_df.index[i], 'signal'] = -1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                        result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBreak"
                        daily_signal_count[current_date] += 1
            
            if 'resistance_level_1' in prev_row and not pd.isna(prev_row['resistance_level_1']) and current_row['trend'] > 0:
                resistance_level = prev_row['resistance_level_1']
                
                breakout_condition = price > resistance_level and (price - resistance_level) / resistance_level > self.breakout_threshold
                volume_condition = True  # ボリューム条件（データがあれば追加）
                
                if breakout_condition and volume_condition and resistance_strength >= self.min_level_strength:
                    h1_confirmation = True
                    if 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']):
                        h1_resistance = current_row['h1_resistance_level_1']
                        h1_confirmation = price > h1_resistance
                    
                    if h1_confirmation:
                        result_df.loc[result_df.index[i], 'signal'] = 1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                        result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBreak"
                        daily_signal_count[current_date] += 1
            
            if 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']) and current_row['trend'] > 0:
                h1_support = current_row['h1_support_level_1']
                
                price_near_support = (prev_row['Low'] - h1_support) / h1_support < self.bounce_threshold
                rsi_condition = current_row['rsi'] < self.rsi_lower and current_row['rsi_slope'] > 0
                
                if price_near_support and rsi_condition:
                    m15_confirmation = True
                    if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']):
                        m15_support = current_row['support_level_1']
                        m15_confirmation = abs(h1_support - m15_support) / h1_support < 0.001
                    
                    if m15_confirmation:
                        result_df.loc[result_df.index[i], 'signal'] = 1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
                        result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_SupportBounce"
                        daily_signal_count[current_date] += 1
            
            if 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']) and current_row['trend'] < 0:
                h1_resistance = current_row['h1_resistance_level_1']
                
                price_near_resistance = (h1_resistance - prev_row['High']) / h1_resistance < self.bounce_threshold
                rsi_condition = current_row['rsi'] > self.rsi_upper and current_row['rsi_slope'] < 0
                
                if price_near_resistance and rsi_condition:
                    m15_confirmation = True
                    if 'resistance_level_1' in current_row and not pd.isna(current_row['resistance_level_1']):
                        m15_resistance = current_row['resistance_level_1']
                        m15_confirmation = abs(h1_resistance - m15_resistance) / h1_resistance < 0.001
                    
                    if m15_confirmation:
                        result_df.loc[result_df.index[i], 'signal'] = -1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price + self.sl_pips * 0.01
                        result_df.loc[result_df.index[i], 'tp_price'] = price - self.tp_pips * 0.01
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_ResistanceBounce"
                        daily_signal_count[current_date] += 1
        
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
    
    def _calculate_slope(self, series, window=5):
        """
        系列の傾きを計算する
        
        Parameters
        ----------
        series : pd.Series
            対象の系列
        window : int, default 5
            傾きを計算する期間
            
        Returns
        -------
        pd.Series
            傾き
        """
        slope = series.diff(window)
        return slope
    
    def _calculate_level_strength(self, df, index, level_type):
        """
        サポート/レジスタンスレベルの強度を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            データフレーム
        index : int
            現在の行インデックス
        level_type : str
            'support' または 'resistance'
            
        Returns
        -------
        int
            レベルの強度
        """
        current_row = df.iloc[index]
        level_col = f"{level_type}_level_1"
        
        if level_col not in current_row or pd.isna(current_row[level_col]):
            return 0
        
        current_level = current_row[level_col]
        
        start_idx = max(0, index - 20)
        end_idx = index
        
        touch_count = 0
        for i in range(start_idx, end_idx):
            row = df.iloc[i]
            
            if level_type == 'support':
                if 'Low' in row and abs(row['Low'] - current_level) / current_level < 0.0005:
                    touch_count += 1
            else:
                if 'High' in row and abs(row['High'] - current_level) / current_level < 0.0005:
                    touch_count += 1
        
        return touch_count
