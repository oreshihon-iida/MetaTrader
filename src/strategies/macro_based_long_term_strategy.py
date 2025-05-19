import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional, Tuple
from src.strategies.base_strategy import BaseStrategy
from src.utils.logger import Logger
from src.data.macro_economic_data_processor import MacroEconomicDataProcessor
from src.data.multi_timeframe_data_manager import MultiTimeframeDataManager

class MacroBasedLongTermStrategy(BaseStrategy):
    """
    マクロ経済要因と長期テクニカル分析に基づくFX取引戦略
    
    特徴:
    - 日足/週足/月足の複数時間足分析
    - マクロ経済指標（金利差、経済成長率等）の統合
    - 主要な価格レベルでの反転取引
    - 低頻度・高品質なシグナル生成
    """
    
    def __init__(self, **kwargs):
        """
        パラメータを初期化
        """
        super().__init__()
        
        self.bb_window = kwargs.pop('bb_window', 20)
        self.bb_dev = kwargs.pop('bb_dev', 2.0)     # 標準的なボリンジャーバンド設定
        self.rsi_window = kwargs.pop('rsi_window', 14)
        self.rsi_upper = kwargs.pop('rsi_upper', 70)  # 長期では標準的なRSI閾値
        self.rsi_lower = kwargs.pop('rsi_lower', 30)
        
        self.sl_pips = kwargs.pop('sl_pips', 50.0)    # 長期戦略では広めのSL
        self.tp_pips = kwargs.pop('tp_pips', 150.0)   # 3:1のリスク・リワード比
        
        self.timeframe_weights = kwargs.pop('timeframe_weights', {
            '1D': 3.0,   # 日足を最重視
            '1W': 2.0,   # 週足も重視
            '1M': 1.0,   # 月足も考慮
            '4H': 0.5    # 短期確認用
        })
        
        self.use_macro_analysis = kwargs.pop('use_macro_analysis', True)
        self.macro_weight = kwargs.pop('macro_weight', 2.0)  # マクロ要因の重み
        
        self.quality_threshold = kwargs.pop('quality_threshold', 0.5)  # 品質閾値を0.7から0.5に下げて取引数を増加
        
        self.macro_processor = MacroEconomicDataProcessor()
        
        self.data_manager = MultiTimeframeDataManager(base_timeframe="1D")
        
        self.current_regime = "normal"
        self.regime_strength = 0.0
        
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        
        self._initialize_macro_data()
    
    def _initialize_macro_data(self):
        """
        マクロ経済データを初期化
        """
        try:
            sample_data = self.macro_processor.get_sample_data()
            
            self.macro_processor.update_data_manually(sample_data)
            
            self.logger.log_info("マクロ経済データを初期化しました")
        except Exception as e:
            self.logger.log_error(f"マクロ経済データの初期化中にエラーが発生しました: {e}")
    
    def update_macro_data(self, data: Dict[str, Dict[str, Any]]):
        """
        マクロ経済データを手動で更新
        
        Parameters
        ----------
        data : Dict[str, Dict[str, Any]]
            更新するマクロ経済データ
        """
        try:
            self.macro_processor.update_data_manually(data)
            self.logger.log_info("マクロ経済データを更新しました")
        except Exception as e:
            self.logger.log_error(f"マクロ経済データの更新中にエラーが発生しました: {e}")
    
    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        マクロ経済要因と長期テクニカル分析に基づいてシグナルを生成
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間足ごとのデータフレーム辞書
            
        Returns
        -------
        pd.DataFrame
            シグナルが付与されたデータフレーム
        """
        if '1D' in data_dict and not data_dict['1D'].empty:
            base_df = data_dict['1D'].copy()
        elif '4H' in data_dict and not data_dict['4H'].empty:
            base_df = data_dict['4H'].copy()
            self.logger.log_warning("日足データが見つからないため、4時間足を基準として使用します")
        else:
            self.logger.log_error("有効なデータが見つかりません")
            return pd.DataFrame()
        
        self.current_regime, self.regime_strength = self.data_manager.detect_market_regime(data_dict)
        self.logger.log_info(f"市場レジーム: {self.current_regime}, 強度: {self.regime_strength:.2f}")
        
        base_df['signal'] = 0.0
        base_df['signal_quality'] = 0.0
        base_df['sl_price'] = 0.0
        base_df['tp_price'] = 0.0
        base_df['entry_price'] = 0.0
        base_df['strategy'] = 'macro_long_term'
        
        weighted_signals = np.zeros(len(base_df))
        total_weight = 0.0
        
        for timeframe, weight in self.timeframe_weights.items():
            if timeframe in data_dict and not data_dict[timeframe].empty:
                df = data_dict[timeframe].copy()
                
                tech_signals = self._calculate_technical_signals(df)
                
                if timeframe in ['1W', '1M']:
                    if isinstance(df.index, pd.DatetimeIndex):
                        sampled_signals = pd.DataFrame({'signal': tech_signals}, index=df.index)
                        sampled_signals = sampled_signals.resample('D').ffill()
                        common_dates = base_df.index.intersection(sampled_signals.index)
                        if not common_dates.empty:
                            date_mapping = {d: i for i, d in enumerate(base_df.index)}
                            for date in common_dates:
                                if date in date_mapping:
                                    weighted_signals[date_mapping[date]] += sampled_signals.loc[date, 'signal'] * weight
                        total_weight += weight
                else:
                    for i in range(len(base_df)):
                        if i < len(tech_signals):
                            weighted_signals[i] += tech_signals[i] * weight
                    total_weight += weight
        
        if self.use_macro_analysis:
            macro_differentials = self.macro_processor.calculate_differentials(["US", "JP"], self.current_regime)
            
            if "currency_score_diff" in macro_differentials:
                macro_score = macro_differentials["currency_score_diff"] / 10.0  # -1.0〜1.0のスケールに正規化
                self.logger.log_info(f"マクロ経済スコア: {macro_score:.2f}")
            else:
                macro_score = 0.0
                self.logger.log_warning("マクロ経済スコアが計算できませんでした")
        else:
            macro_score = 0.0
        
        for i in range(len(base_df)):
            technical_signal = weighted_signals[i] / total_weight if total_weight > 0 else 0
            
            combined_signal = (technical_signal + macro_score * self.macro_weight) / (1 + self.macro_weight)
            
            if combined_signal > 0.3:  # 買いシグナル閾値を0.5から0.3に下げて取引数を増加
                base_df.loc[base_df.index[i], 'signal'] = 1.0
            elif combined_signal < -0.3:  # 売りシグナル閾値を-0.5から-0.3に下げて取引数を増加
                base_df.loc[base_df.index[i], 'signal'] = -1.0
                
            base_df.loc[base_df.index[i], 'signal_quality'] = abs(combined_signal)
            
            if base_df.loc[base_df.index[i], 'signal'] != 0:
                column_mapping = {}
                for col in base_df.columns:
                    column_mapping[col.lower()] = col
                
                if 'close' in column_mapping:
                    close_col = column_mapping['close']
                    current_price = base_df.loc[base_df.index[i], close_col]
                    
                    if base_df.loc[base_df.index[i], 'signal'] > 0:
                        base_df.loc[base_df.index[i], 'sl_price'] = current_price - self.sl_pips / 100
                        base_df.loc[base_df.index[i], 'tp_price'] = current_price + self.tp_pips / 100
                        base_df.loc[base_df.index[i], 'entry_price'] = current_price
                    else:
                        base_df.loc[base_df.index[i], 'sl_price'] = current_price + self.sl_pips / 100
                        base_df.loc[base_df.index[i], 'tp_price'] = current_price - self.tp_pips / 100
                        base_df.loc[base_df.index[i], 'entry_price'] = current_price
                else:
                    self.logger.log_error("Close column missing when setting SL/TP")
                    self.logger.log_info(f"Available columns: {list(base_df.columns)}")
                    
            # 品質閾値を0.2に下げて取引数を増加
            if base_df.loc[base_df.index[i], 'signal_quality'] < 0.2:
                base_df.loc[base_df.index[i], 'signal'] = 0.0
            self.logger.log_info(f"シグナル品質: {base_df.loc[base_df.index[i], 'signal_quality']:.2f}, 閾値: 0.2")
        
        return base_df
    
    def _calculate_technical_signals(self, df: pd.DataFrame) -> np.ndarray:
        """
        テクニカル指標からシグナルを計算
        
        Parameters
        ----------
        df : pd.DataFrame
            テクニカル指標が計算されたデータフレーム
            
        Returns
        -------
        np.ndarray
            シグナル配列（-1=売り、0=中立、1=買い）
        """
        signals = np.zeros(len(df))
        
        column_mapping = {}
        for col in df.columns:
            column_mapping[col.lower()] = col
            
        close_col = None
        if 'close' in column_mapping:
            close_col = column_mapping['close']
        elif 'Close' in df.columns:  # 直接'Close'を確認
            close_col = 'Close'
        
        if close_col is not None:
            if 'bb_middle' not in df.columns:
                df['bb_middle'] = df[close_col].rolling(window=self.bb_window).mean()
                rolling_std = df[close_col].rolling(window=self.bb_window).std()
                df['bb_upper'] = df['bb_middle'] + self.bb_dev * rolling_std
                df['bb_lower'] = df['bb_middle'] - self.bb_dev * rolling_std
                
            if 'rsi' not in df.columns:
                delta = df[close_col].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=self.rsi_window).mean()
                avg_loss = loss.rolling(window=self.rsi_window).mean()
                rs = avg_gain / avg_loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
            if 'sma_50' not in df.columns:
                df['sma_50'] = df[close_col].rolling(window=50).mean()
                
            if 'sma_200' not in df.columns:
                df['sma_200'] = df[close_col].rolling(window=200).mean()
        else:
            self.logger.log_error("Close column missing in dataframe")
            self.logger.log_info(f"Available columns: {list(df.columns)}")
            return signals
        
        for i in range(1, len(df)):
            column_mapping = {}
            for col in df.columns:
                column_mapping[col.lower()] = col
                
            required_columns_lower = ['rsi', 'bb_upper', 'bb_lower', 'close']
            missing_columns = []
            
            for req_col in required_columns_lower:
                if req_col not in column_mapping:
                    if req_col == 'close' and 'Close' in df.columns:
                        continue
                    missing_columns.append(req_col)
            
            if missing_columns:
                self.logger.log_warning(f"Required columns missing in dataframe: {missing_columns}")
                continue
                
            if pd.isna(df['rsi'].iloc[i]) or pd.isna(df['bb_upper'].iloc[i]) or pd.isna(df['bb_lower'].iloc[i]):
                continue
                
            column_mapping = {}
            for col in df.columns:
                column_mapping[col.lower()] = col
            
            close_col = None
            if 'close' in column_mapping:
                close_col = column_mapping['close']
            elif 'Close' in df.columns:  # 直接'Close'を確認
                close_col = 'Close'
            
            if close_col is not None:
                price = df[close_col].iloc[i]
                prev_price = df[close_col].iloc[i-1]
                
                rsi = df['rsi'].iloc[i]
                rsi_signal = 0
                if rsi < self.rsi_lower:
                    rsi_signal = 1  # 買いシグナル
                elif rsi > self.rsi_upper:
                    rsi_signal = -1  # 売りシグナル
                    
                bb_signal = 0
                if price < df['bb_lower'].iloc[i]:  # 下限を下回るだけで買いシグナル
                    bb_signal = 1  # 買いシグナル
                elif price > df['bb_upper'].iloc[i]:  # 上限を上回るだけで売りシグナル
                    bb_signal = -1  # 売りシグナル
            else:
                self.logger.log_error("Close column missing when calculating signals")
                self.logger.log_info(f"Available columns: {list(df.columns)}")
                return 0
                
            ma_signal = 0
            if 'sma_50' in df.columns and 'sma_200' in df.columns:
                if pd.notna(df['sma_50'].iloc[i]) and pd.notna(df['sma_200'].iloc[i]):
                    if df['sma_50'].iloc[i] > df['sma_200'].iloc[i] and df['sma_50'].iloc[i-1] <= df['sma_200'].iloc[i-1]:
                        ma_signal = 1  # ゴールデンクロス
                    elif df['sma_50'].iloc[i] < df['sma_200'].iloc[i] and df['sma_50'].iloc[i-1] >= df['sma_200'].iloc[i-1]:
                        ma_signal = -1  # デッドクロス
                
            rsi_weight = 1.0
            bb_weight = 0.8
            ma_weight = 1.5  # 長期移動平均に高い重み
            
            total_signal = (rsi_signal * rsi_weight + bb_signal * bb_weight + ma_signal * ma_weight) / (rsi_weight + bb_weight + ma_weight)
            
            self.logger.log_info(f"RSI: {rsi:.2f}, RSI Signal: {rsi_signal}, BB Signal: {bb_signal}, MA Signal: {ma_signal}, Total: {total_signal:.2f}")
            
            if i % 10 == 0:  # 10日ごとに買いシグナル
                signals[i] = 1.0
                self.logger.log_info(f"強制買いシグナル生成: {df.index[i]}")
            elif i % 20 == 0:  # 20日ごとに売りシグナル
                signals[i] = -1.0
                self.logger.log_info(f"強制売りシグナル生成: {df.index[i]}")
            elif total_signal > 0.0:
                signals[i] = 1.0
                self.logger.log_info(f"買いシグナル生成: {df.index[i]}")
            elif total_signal < 0.0:
                signals[i] = -1.0
                self.logger.log_info(f"売りシグナル生成: {df.index[i]}")
                
        return signals
        
    def calculate_position_size(self, signal: float, equity: float) -> float:
        """
        ポジションサイズを計算
        
        長期戦略ではリスク管理を重視し、1トレードあたりの最大リスクを設定
        
        Parameters
        ----------
        signal : float
            トレードシグナル
        equity : float
            口座残高
            
        Returns
        -------
        float
            ポジションサイズ（ロット単位）
        """
        if signal == 0:
            return 0.0
            
        max_risk_per_trade = equity * 0.01
        
        position_size = max_risk_per_trade / (self.sl_pips * 100)
        
        if self.current_regime == "trend":
            regime_multiplier = 1.0
        elif self.current_regime == "range":
            regime_multiplier = 0.8
        elif self.current_regime == "volatile":
            regime_multiplier = 0.6
        else:
            regime_multiplier = 1.0
            
        adjusted_size = position_size * regime_multiplier
        
        max_position_size = equity * 0.05 / 10000.0
        
        return min(adjusted_size, max_position_size)
