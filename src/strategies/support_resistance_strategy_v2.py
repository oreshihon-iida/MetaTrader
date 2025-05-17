import pandas as pd
import numpy as np

class SupportResistanceStrategyV2:
    """
    サポート/レジスタンスレベルに基づく取引戦略（改良版2）
    """
    
    def __init__(self, sl_pips=10.0, tp_pips=25.0, bounce_threshold=0.0004, breakout_threshold=0.0006, 
                 rsi_lower=45, rsi_upper=55, min_level_strength=3, max_signals_per_day=2,
                 time_decay_factor=0.9, price_action_confirmation=True, multi_timeframe_confirmation=True):
        """
        初期化
        
        Parameters
        ----------
        sl_pips : float, default 10.0
            損切り幅（pips）
        tp_pips : float, default 25.0
            利確幅（pips）
        bounce_threshold : float, default 0.0004
            バウンス判定の閾値
        breakout_threshold : float, default 0.0006
            ブレイクアウト判定の閾値
        rsi_lower : int, default 45
            RSI下限閾値
        rsi_upper : int, default 55
            RSI上限閾値
        min_level_strength : int, default 3
            最小レベル強度（タッチ回数）
        max_signals_per_day : int, default 2
            1日あたりの最大シグナル数
        time_decay_factor : float, default 0.9
            時間減衰係数（古いタッチの重みを減らす）
        price_action_confirmation : bool, default True
            価格アクションによる確認を行うかどうか
        multi_timeframe_confirmation : bool, default True
            複数時間足の確認を行うかどうか
        """
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.bounce_threshold = bounce_threshold
        self.breakout_threshold = breakout_threshold
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.min_level_strength = min_level_strength
        self.max_signals_per_day = max_signals_per_day
        self.time_decay_factor = time_decay_factor
        self.price_action_confirmation = price_action_confirmation
        self.multi_timeframe_confirmation = multi_timeframe_confirmation
        self.strategy_name = "Support/Resistance_V2"
    
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
        result_df['ma50'] = result_df['Close'].rolling(window=50).mean()
        result_df['ma100'] = result_df['Close'].rolling(window=100).mean()
        
        result_df['trend'] = self._calculate_slope(result_df['ma20'], 10)
        result_df['trend_strength'] = self._calculate_trend_strength(result_df)
        
        result_df['atr'] = self._calculate_atr(result_df, 14)
        
        daily_signal_count = {}
        
        if self.price_action_confirmation:
            result_df = self._detect_price_action_patterns(result_df)
        
        for i in range(100, len(result_df)):  # 十分な履歴データを確保するため100から開始
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
            
            support_strength = self._calculate_level_strength_with_decay(result_df, i, 'support')
            resistance_strength = self._calculate_level_strength_with_decay(result_df, i, 'resistance')
            
            volatility_factor = current_row['atr'] / result_df['atr'].rolling(window=50).mean().iloc[i]
            adaptive_bounce_threshold = self.bounce_threshold * max(0.8, min(1.2, volatility_factor))
            adaptive_breakout_threshold = self.breakout_threshold * max(0.8, min(1.2, volatility_factor))
            
            if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']) and current_row['trend_strength'] > 0.5:
                support_level = current_row['support_level_1']
                
                price_near_support = (prev_row['Low'] - support_level) / support_level < adaptive_bounce_threshold
                rsi_condition = current_row['rsi'] < self.rsi_lower and current_row['rsi_slope'] > 0
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bullish_pattern', False)
                
                multi_tf_confirmation = True
                if self.multi_timeframe_confirmation and 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']):
                    h1_support = current_row['h1_support_level_1']
                    multi_tf_confirmation = abs(support_level - h1_support) / support_level < 0.002
                
                if (price_near_support and rsi_condition and support_strength >= self.min_level_strength 
                        and price_action_confirmation and multi_tf_confirmation):
                    risk = self.sl_pips * 0.01
                    reward = self.tp_pips * 0.01
                    
                    adjusted_sl = risk * (1 - (support_strength - self.min_level_strength) * 0.1)
                    adjusted_tp = reward * (1 + (support_strength - self.min_level_strength) * 0.1)
                    
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - adjusted_sl
                    result_df.loc[result_df.index[i], 'tp_price'] = price + adjusted_tp
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBounce"
                    daily_signal_count[current_date] += 1
            
            if 'resistance_level_1' in current_row and not pd.isna(current_row['resistance_level_1']) and current_row['trend_strength'] < -0.5:
                resistance_level = current_row['resistance_level_1']
                
                price_near_resistance = (resistance_level - prev_row['High']) / resistance_level < adaptive_bounce_threshold
                rsi_condition = current_row['rsi'] > self.rsi_upper and current_row['rsi_slope'] < 0
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bearish_pattern', False)
                
                multi_tf_confirmation = True
                if self.multi_timeframe_confirmation and 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']):
                    h1_resistance = current_row['h1_resistance_level_1']
                    multi_tf_confirmation = abs(resistance_level - h1_resistance) / resistance_level < 0.002
                
                if (price_near_resistance and rsi_condition and resistance_strength >= self.min_level_strength 
                        and price_action_confirmation and multi_tf_confirmation):
                    risk = self.sl_pips * 0.01
                    reward = self.tp_pips * 0.01
                    
                    adjusted_sl = risk * (1 - (resistance_strength - self.min_level_strength) * 0.1)
                    adjusted_tp = reward * (1 + (resistance_strength - self.min_level_strength) * 0.1)
                    
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + adjusted_sl
                    result_df.loc[result_df.index[i], 'tp_price'] = price - adjusted_tp
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBounce"
                    daily_signal_count[current_date] += 1
            
            if 'support_level_1' in prev_row and not pd.isna(prev_row['support_level_1']) and current_row['trend_strength'] < -0.7:
                support_level = prev_row['support_level_1']
                
                breakout_condition = price < support_level and (support_level - price) / support_level > adaptive_breakout_threshold
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bearish_pattern', False)
                
                multi_tf_confirmation = True
                if self.multi_timeframe_confirmation:
                    if 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']):
                        h1_support = current_row['h1_support_level_1']
                        multi_tf_confirmation = price < h1_support
                
                if (breakout_condition and support_strength >= self.min_level_strength 
                        and price_action_confirmation and multi_tf_confirmation):
                    risk = self.sl_pips * 0.01
                    reward = self.tp_pips * 0.01
                    
                    adjusted_sl = risk * (1 - (support_strength - self.min_level_strength) * 0.1)
                    adjusted_tp = reward * (1 + (support_strength - self.min_level_strength) * 0.1)
                    
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price + adjusted_sl
                    result_df.loc[result_df.index[i], 'tp_price'] = price - adjusted_tp
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBreak"
                    daily_signal_count[current_date] += 1
            
            if 'resistance_level_1' in prev_row and not pd.isna(prev_row['resistance_level_1']) and current_row['trend_strength'] > 0.7:
                resistance_level = prev_row['resistance_level_1']
                
                breakout_condition = price > resistance_level and (price - resistance_level) / resistance_level > adaptive_breakout_threshold
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bullish_pattern', False)
                
                multi_tf_confirmation = True
                if self.multi_timeframe_confirmation:
                    if 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']):
                        h1_resistance = current_row['h1_resistance_level_1']
                        multi_tf_confirmation = price > h1_resistance
                
                if (breakout_condition and resistance_strength >= self.min_level_strength 
                        and price_action_confirmation and multi_tf_confirmation):
                    risk = self.sl_pips * 0.01
                    reward = self.tp_pips * 0.01
                    
                    adjusted_sl = risk * (1 - (resistance_strength - self.min_level_strength) * 0.1)
                    adjusted_tp = reward * (1 + (resistance_strength - self.min_level_strength) * 0.1)
                    
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'entry_price'] = price
                    result_df.loc[result_df.index[i], 'sl_price'] = price - adjusted_sl
                    result_df.loc[result_df.index[i], 'tp_price'] = price + adjusted_tp
                    result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_ResistanceBreak"
                    daily_signal_count[current_date] += 1
            
            if 'h1_support_level_1' in current_row and not pd.isna(current_row['h1_support_level_1']) and current_row['trend_strength'] > 0.6:
                h1_support = current_row['h1_support_level_1']
                
                price_near_support = (prev_row['Low'] - h1_support) / h1_support < adaptive_bounce_threshold
                rsi_condition = current_row['rsi'] < self.rsi_lower and current_row['rsi_slope'] > 0
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bullish_pattern', False)
                
                if price_near_support and rsi_condition and price_action_confirmation:
                    m15_confirmation = True
                    if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']):
                        m15_support = current_row['support_level_1']
                        m15_confirmation = abs(h1_support - m15_support) / h1_support < 0.002
                    
                    if m15_confirmation:
                        risk = self.sl_pips * 0.01
                        reward = self.tp_pips * 0.01
                        
                        adjusted_sl = risk * 0.8
                        adjusted_tp = reward * 1.2
                        
                        result_df.loc[result_df.index[i], 'signal'] = 1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price - adjusted_sl
                        result_df.loc[result_df.index[i], 'tp_price'] = price + adjusted_tp
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_SupportBounce"
                        daily_signal_count[current_date] += 1
            
            if 'h1_resistance_level_1' in current_row and not pd.isna(current_row['h1_resistance_level_1']) and current_row['trend_strength'] < -0.6:
                h1_resistance = current_row['h1_resistance_level_1']
                
                price_near_resistance = (h1_resistance - prev_row['High']) / h1_resistance < adaptive_bounce_threshold
                rsi_condition = current_row['rsi'] > self.rsi_upper and current_row['rsi_slope'] < 0
                
                price_action_confirmation = True
                if self.price_action_confirmation:
                    price_action_confirmation = current_row.get('bearish_pattern', False)
                
                if price_near_resistance and rsi_condition and price_action_confirmation:
                    m15_confirmation = True
                    if 'resistance_level_1' in current_row and not pd.isna(current_row['resistance_level_1']):
                        m15_resistance = current_row['resistance_level_1']
                        m15_confirmation = abs(h1_resistance - m15_resistance) / h1_resistance < 0.002
                    
                    if m15_confirmation:
                        risk = self.sl_pips * 0.01
                        reward = self.tp_pips * 0.01
                        
                        adjusted_sl = risk * 0.8
                        adjusted_tp = reward * 1.2
                        
                        result_df.loc[result_df.index[i], 'signal'] = -1
                        result_df.loc[result_df.index[i], 'entry_price'] = price
                        result_df.loc[result_df.index[i], 'sl_price'] = price + adjusted_sl
                        result_df.loc[result_df.index[i], 'tp_price'] = price - adjusted_tp
                        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_H1_ResistanceBounce"
                        daily_signal_count[current_date] += 1
        
        return result_df
    
    def _calculate_level_strength_with_decay(self, df, index, level_type):
        """
        サポート/レジスタンスレベルの強度を計算する（時間減衰を考慮）
        
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
        float
            レベルの強度
        """
        current_row = df.iloc[index]
        level_col = f"{level_type}_level_1"
        
        if level_col not in current_row or pd.isna(current_row[level_col]):
            return 0
        
        current_level = current_row[level_col]
        
        start_idx = max(0, index - 50)
        end_idx = index
        
        strength = 0
        for i in range(start_idx, end_idx):
            row = df.iloc[i]
            
            time_decay = self.time_decay_factor ** (end_idx - i)
            
            if level_type == 'support':
                if 'Low' in row and abs(row['Low'] - current_level) / current_level < 0.0005:
                    if abs(row['Close'] - current_level) / current_level < 0.001:
                        strength += 1.5 * time_decay
                    else:
                        strength += 1.0 * time_decay
            else:
                if 'High' in row and abs(row['High'] - current_level) / current_level < 0.0005:
                    if abs(row['Close'] - current_level) / current_level < 0.001:
                        strength += 1.5 * time_decay
                    else:
                        strength += 1.0 * time_decay
        
        return strength
        
    def _calculate_trend_strength(self, df):
        """
        トレンドの強度を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            データフレーム
            
        Returns
        -------
        pd.Series
            トレンド強度（-1.0〜1.0）
        """
        ma_alignment = np.zeros(len(df))
        
        for i in range(100, len(df)):
            ma20 = df['ma20'].iloc[i]
            ma50 = df['ma50'].iloc[i]
            ma100 = df['ma100'].iloc[i]
            
            if ma20 > ma50 > ma100:
                ma_alignment[i] = 1.0
            elif ma20 < ma50 < ma100:
                ma_alignment[i] = -1.0
            elif ma20 > ma50:
                ma_alignment[i] = 0.5
            elif ma20 < ma50:
                ma_alignment[i] = -0.5
            
            trend_slope = df['trend'].iloc[i]
            if trend_slope > 0 and ma_alignment[i] > 0:
                ma_alignment[i] = min(1.0, ma_alignment[i] + 0.2)
            elif trend_slope < 0 and ma_alignment[i] < 0:
                ma_alignment[i] = max(-1.0, ma_alignment[i] - 0.2)
        
        return pd.Series(ma_alignment, index=df.index)
    
    def _calculate_atr(self, df, window=14):
        """
        ATR（Average True Range）を計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            データフレーム
        window : int, default 14
            ATRの計算期間
            
        Returns
        -------
        pd.Series
            ATR値
        """
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()
        
        return atr
    
    def _detect_price_action_patterns(self, df):
        """
        価格アクションパターンを検出する
        
        Parameters
        ----------
        df : pd.DataFrame
            データフレーム
            
        Returns
        -------
        pd.DataFrame
            価格アクションパターンを追加したデータフレーム
        """
        result_df = df.copy()
        
        result_df['bullish_pattern'] = False
        result_df['bearish_pattern'] = False
        
        for i in range(1, len(result_df)):
            current = result_df.iloc[i]
            prev = result_df.iloc[i-1]
            
            current_body = abs(current['Open'] - current['Close'])
            prev_body = abs(prev['Open'] - prev['Close'])
            
            if current['Close'] > current['Open']:  # 陽線
                current_upper_wick = current['High'] - current['Close']
                current_lower_wick = current['Open'] - current['Low']
            else:  # 陰線
                current_upper_wick = current['High'] - current['Open']
                current_lower_wick = current['Close'] - current['Low']
            
            if prev['Close'] > prev['Open']:  # 陽線
                prev_upper_wick = prev['High'] - prev['Close']
                prev_lower_wick = prev['Open'] - prev['Low']
            else:  # 陰線
                prev_upper_wick = prev['High'] - prev['Open']
                prev_lower_wick = prev['Close'] - prev['Low']
            
            if current_lower_wick > current_body * 3 and current_lower_wick > current_upper_wick * 2:
                result_df.loc[result_df.index[i], 'bullish_pattern'] = True
            
            if current_upper_wick > current_body * 3 and current_upper_wick > current_lower_wick * 2:
                result_df.loc[result_df.index[i], 'bearish_pattern'] = True
            
            if (current['Close'] > current['Open'] and  # 現在が陽線
                prev['Close'] < prev['Open'] and  # 前が陰線
                current['Close'] > prev['Open'] and  # 終値が前の始値より高い
                current['Open'] < prev['Close']):  # 始値が前の終値より低い
                result_df.loc[result_df.index[i], 'bullish_pattern'] = True
            
            if (current['Close'] < current['Open'] and  # 現在が陰線
                prev['Close'] > prev['Open'] and  # 前が陽線
                current['Close'] < prev['Open'] and  # 終値が前の始値より低い
                current['Open'] > prev['Close']):  # 始値が前の終値より高い
                result_df.loc[result_df.index[i], 'bearish_pattern'] = True
        
        return result_df
    
    def _calculate_slope(self, series, window=5):
        """
        系列の傾きを計算する
        
        Parameters
        ----------
        series : pd.Series
            傾きを計算する系列
        window : int, default 5
            傾きの計算期間
            
        Returns
        -------
        pd.Series
            傾き
        """
        slopes = np.zeros(len(series))
        
        for i in range(window, len(series)):
            y = series.iloc[i-window:i].values
            x = np.arange(window)
            
            slope, _ = np.polyfit(x, y, 1)
            slopes[i] = slope
        
        return pd.Series(slopes, index=series.index)
    
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
