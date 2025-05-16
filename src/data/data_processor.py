import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import ADXIndicator

class DataProcessor:
    """
    FXデータを処理するクラス
    1分足から15分足へのリサンプリング、テクニカル指標の計算など
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初期化
        
        Parameters
        ----------
        data : pd.DataFrame
            処理対象のデータ（1分足）
        """
        self.data = data
    
    def resample(self, timeframe: str = '15min') -> pd.DataFrame:
        """
        指定された時間足にリサンプリングする
        
        Parameters
        ----------
        timeframe : str, default '15min'
            リサンプリングする時間足（pandas resampleの形式）
            例: '15min'=15分, '1H'=1時間
        
        Returns
        -------
        pd.DataFrame
            リサンプリングされたデータ
        """
        resampled = self.data.resample(timeframe).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return resampled
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を追加する
        
        Parameters
        ----------
        df : pd.DataFrame
            テクニカル指標を追加するDataFrame
            
        Returns
        -------
        pd.DataFrame
            テクニカル指標が追加されたDataFrame
        """
        df = df.copy()
        
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        
        rsi = RSIIndicator(close=df['Close'], window=14)
        df['rsi'] = rsi.rsi()
        
        df['rsi_divergence'] = 0  # 0=ダイバージェンスなし、1=ブルダイバージェンス、-1=ベアダイバージェンス
        
        for i in range(5, len(df)):
            if (df['Low'].iloc[i] < df['Low'].iloc[i-5]) and (df['rsi'].iloc[i] > df['rsi'].iloc[i-5]):
                df.loc[df.index[i], 'rsi_divergence'] = 1
            
            elif (df['High'].iloc[i] > df['High'].iloc[i-5]) and (df['rsi'].iloc[i] < df['rsi'].iloc[i-5]):
                df.loc[df.index[i], 'rsi_divergence'] = -1
        
        adx = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()  # +DI
        df['adx_neg'] = adx.adx_neg()  # -DI
        
        atr = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['atr'] = atr.average_true_range()
        
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        df['ma_short'] = df['Close'].rolling(window=5).mean()
        df['ma_long'] = df['Close'].rolling(window=20).mean()
        
        df['ma_cross'] = 0  # 0=クロスなし、1=ゴールデンクロス、-1=デッドクロス
        
        for i in range(1, len(df)):
            if pd.notna(df['ma_short'].iloc[i]) and pd.notna(df['ma_long'].iloc[i]) and pd.notna(df['ma_short'].iloc[i-1]) and pd.notna(df['ma_long'].iloc[i-1]):
                if df['ma_short'].iloc[i] > df['ma_long'].iloc[i] and df['ma_short'].iloc[i-1] <= df['ma_long'].iloc[i-1]:
                    df.loc[df.index[i], 'ma_cross'] = 1
                
                elif df['ma_short'].iloc[i] < df['ma_long'].iloc[i] and df['ma_short'].iloc[i-1] >= df['ma_long'].iloc[i-1]:
                    df.loc[df.index[i], 'ma_cross'] = -1
        
        return df
    
    def detect_market_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        市場環境（トレンド/レンジ）を判断し、データフレームに追加する
        
        Parameters
        ----------
        df : pd.DataFrame
            市場環境を追加するDataFrame
            
        Returns
        -------
        pd.DataFrame
            市場環境が追加されたDataFrame
        """
        df['is_trend'] = df['adx'] >= 25
        
        df['trend_direction'] = 0  # 0=中立
        df.loc[(df['is_trend']) & (df['adx_pos'] > df['adx_neg']), 'trend_direction'] = 1  # 1=上昇トレンド
        df.loc[(df['is_trend']) & (df['adx_pos'] < df['adx_neg']), 'trend_direction'] = -1  # -1=下降トレンド
        
        return df
    
    def get_tokyo_session_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        東京時間のレンジ（高値・安値）を追加する
        
        Parameters
        ----------
        df : pd.DataFrame
            東京時間のレンジを追加するDataFrame
            
        Returns
        -------
        pd.DataFrame
            東京時間のレンジが追加されたDataFrame
        """
        df_jst = df.copy()
        df_jst.index = df_jst.index + pd.Timedelta(hours=9)
        
        df_jst['date'] = df_jst.index.to_series().dt.date
        
        tokyo_session = df_jst.between_time('09:00', '15:00')
        
        daily_highs = tokyo_session.groupby('date')['High'].max()
        daily_lows = tokyo_session.groupby('date')['Low'].min()
        
        df['date'] = df.index.to_series().dt.date
        df = df.merge(
            pd.DataFrame({'tokyo_high': daily_highs, 'tokyo_low': daily_lows}),
            left_on='date',
            right_index=True,
            how='left'
        )
        
        for group_name, group_data in df.groupby('date'):
            mask = group_data.index
            df.loc[mask, ['tokyo_high', 'tokyo_low']] = group_data[['tokyo_high', 'tokyo_low']].ffill()
        
        df = df.drop('date', axis=1)
        
        return df
        
    def process_multiple_timeframes(self, timeframes: list = ['15min', '1H']) -> dict:
        """
        複数の時間足でデータを処理する
        
        Parameters
        ----------
        timeframes : list, default ['15min', '1H']
            処理する時間足のリスト
            
        Returns
        -------
        dict
            時間足をキー、データフレームを値とする辞書
        """
        result = {}
        for tf in timeframes:
            df = self.resample(tf)
            df = self.add_technical_indicators(df)
            df = self.detect_market_condition(df)
            result[tf] = df
        
        return result
        
    def detect_support_resistance_levels(self, df: pd.DataFrame, window: int = 5, min_touches: int = 3, threshold_pips: float = 5.0, max_levels: int = 10) -> pd.DataFrame:
        """
        サポート/レジスタンスレベルを検出する（最適化版）
        
        Parameters
        ----------
        df : pd.DataFrame
            サポート/レジスタンスレベルを検出するDataFrame
        window : int, default 5
            スイングハイ/ローを検出するためのウィンドウサイズ（小さいほど高速）
        min_touches : int, default 3
            レベルとみなすための最小タッチ回数（3回以上で強いレベルと判断）
        threshold_pips : float, default 5.0
            レベルをまとめるための閾値（pips）
        max_levels : int, default 10
            検出する最大レベル数（少ないほど高速）
            
        Returns
        -------
        pd.DataFrame
            サポート/レジスタンスレベルが追加されたDataFrame
        """
        df = df.copy()
        
        if len(df) > 5000:
            df_subset = df.iloc[-5000:].copy()
        else:
            df_subset = df.copy()
        
        # スイングハイ/ローを検出（ベクトル化操作で高速化）
        highs = df_subset['High'].rolling(window=window*2+1, center=True).max()
        lows = df_subset['Low'].rolling(window=window*2+1, center=True).min()
        
        swing_highs = (df_subset['High'] == highs) & (df_subset['High'] > df_subset['High'].shift(1)) & (df_subset['High'] > df_subset['High'].shift(-1))
        swing_lows = (df_subset['Low'] == lows) & (df_subset['Low'] < df_subset['Low'].shift(1)) & (df_subset['Low'] < df_subset['Low'].shift(-1))
        
        resistance_levels = df_subset.loc[swing_highs, 'High'].tolist()
        support_levels = df_subset.loc[swing_lows, 'Low'].tolist()
        
        def cluster_levels(levels, threshold):
            if not levels:
                return []
            
            levels = sorted(levels)
            clusters = [[levels[0]]]
            
            for level in levels[1:]:
                if level - clusters[-1][-1] <= threshold * 0.01:  # threshold pips以内なら同じクラスタ
                    clusters[-1].append(level)
                else:
                    clusters.append([level])
            
            return [sum(cluster) / len(cluster) for cluster in clusters]
        
        resistance_levels = cluster_levels(resistance_levels, threshold_pips)
        support_levels = cluster_levels(support_levels, threshold_pips)
        
        if len(resistance_levels) > max_levels:
            resistance_levels = sorted(resistance_levels, reverse=True)[:max_levels]  # 高い順に取得
        if len(support_levels) > max_levels:
            support_levels = sorted(support_levels)[:max_levels]  # 低い順に取得
        
        def count_touches_vectorized(df, levels, threshold):
            touches = {}
            strength = {}
            threshold_val = threshold * 0.01
            
            for level in levels:
                high_touches = ((df['High'] >= level - threshold_val) & (df['High'] <= level + threshold_val)).sum()
                low_touches = ((df['Low'] >= level - threshold_val) & (df['Low'] <= level + threshold_val)).sum()
                total_touches = high_touches + low_touches
                touches[level] = total_touches
                
                if total_touches >= 5:
                    strength[level] = 2.0  # 非常に強いレベル
                elif total_touches >= 3:
                    strength[level] = 1.5  # 強いレベル
                else:
                    strength[level] = 1.0  # 通常のレベル
            
            return touches, strength
        
        resistance_touches, resistance_strength = count_touches_vectorized(df_subset, resistance_levels, threshold_pips)
        support_touches, support_strength = count_touches_vectorized(df_subset, support_levels, threshold_pips)
        
        resistance_levels = [level for level, touches in resistance_touches.items() if touches >= min_touches]
        support_levels = [level for level, touches in support_touches.items() if touches >= min_touches]
        
        df['nearest_support'] = np.nan
        df['nearest_resistance'] = np.nan
        df['support_strength'] = 1.0  # デフォルト強度
        df['resistance_strength'] = 1.0  # デフォルト強度
        df['near_support'] = False  # サポートに近いかどうか
        df['near_resistance'] = False  # レジスタンスに近いかどうか
        
        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            
            current_supports = [s for s in support_levels if s < current_price]
            if current_supports:
                nearest_support = max(current_supports)  # 最も近いサポート
                df.loc[df.index[i], 'nearest_support'] = nearest_support
                df.loc[df.index[i], 'support_strength'] = support_strength.get(nearest_support, 1.0)
                
                if abs(current_price - nearest_support) <= 10 * 0.01:
                    df.loc[df.index[i], 'near_support'] = True
            
            current_resistances = [r for r in resistance_levels if r > current_price]
            if current_resistances:
                nearest_resistance = min(current_resistances)  # 最も近いレジスタンス
                df.loc[df.index[i], 'nearest_resistance'] = nearest_resistance
                df.loc[df.index[i], 'resistance_strength'] = resistance_strength.get(nearest_resistance, 1.0)
                
                if abs(current_price - nearest_resistance) <= 10 * 0.01:
                    df.loc[df.index[i], 'near_resistance'] = True
        
        return df
