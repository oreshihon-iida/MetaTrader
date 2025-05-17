import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from ..indicators.composite_indicators import TrendStrengthIndex, VolatilityAdjustedOscillator, MultiTimeframeConfirmationIndex
from ..risk_management.risk_manager import DynamicPositionSizer, AdaptiveStopLossTakeProfit, RiskManager
from ta.momentum import RSIIndicator

class CompositeIndicatorStrategy(BollingerRsiEnhancedMTStrategy):
    """
    複合指標拡張版ボリンジャーバンド＋RSI戦略
    
    複数の指標を組み合わせて、より正確なシグナルを生成する戦略
    """
    
    def __init__(self, use_composite_indicators: bool = True, *args, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        use_composite_indicators : bool, default True
            複合指標を使用するかどうか
        *args, **kwargs
            親クラスに渡す引数
        """
        super().__init__(*args, **kwargs)
        self.use_composite_indicators = use_composite_indicators
        self.name = "複合指標拡張版ボリンジャーバンド＋RSI戦略"
    
    def generate_signals(self, df: pd.DataFrame, year: int = 2020, 
                       processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        複合指標を用いてトレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            主要時間足（15分足）のデータ
        year : int, default 2020
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        result_df = super().generate_signals(df, year, processed_dir)
        
        if not self.use_composite_indicators:
            return result_df
        
        multi_tf_data = self.load_multi_timeframe_data(year, processed_dir)
        
        tsi = TrendStrengthIndex(result_df)
        trend_strength = tsi.calculate()
        result_df['trend_strength'] = trend_strength
        
        vao = VolatilityAdjustedOscillator(result_df)
        vao_values, adj_upper, adj_lower = vao.calculate()
        result_df['vao'] = vao_values
        result_df['vao_upper'] = adj_upper
        result_df['vao_lower'] = adj_lower
        
        def calc_rsi(df):
            return RSIIndicator(close=df['Close'], window=14).rsi()
        
        if len(multi_tf_data) >= 2:
            mtci = MultiTimeframeConfirmationIndex(multi_tf_data, calc_rsi)
            confirmation_index = mtci.calculate(weights=self.timeframe_weights)
            result_df['confirmation_index'] = confirmation_index
        
        for i in range(1, len(result_df)):
            current_signal = result_df.iloc[i]['signal']
            
            if current_signal != 0:
                trend_str = result_df.iloc[i].get('trend_strength', 0)
                vao_val = result_df.iloc[i].get('vao', 0)
                confirm_val = result_df.iloc[i].get('confirmation_index', 0)
                
                signal_quality = 0
                
                if current_signal == 1:
                    if trend_str >= -0.3:  # トレンドに反していない
                        signal_quality += 1
                    
                    if vao_val <= -0.5:  # オーバーソールド
                        signal_quality += 1
                    
                    if confirm_val <= -0.3:  # 複数時間足でのRSIオーバーソールド確認
                        signal_quality += 1
                
                elif current_signal == -1:
                    if trend_str <= 0.3:  # トレンドに反していない
                        signal_quality += 1
                    
                    if vao_val >= 0.5:  # オーバーボート
                        signal_quality += 1
                    
                    if confirm_val >= 0.3:  # 複数時間足でのRSIオーバーボート確認
                        signal_quality += 1
                
                if signal_quality < 2:  # 最低2つの確認が必要
                    result_df.loc[result_df.index[i], 'signal'] = 0
                    result_df.loc[result_df.index[i], 'entry_price'] = np.nan
                    result_df.loc[result_df.index[i], 'sl_price'] = np.nan
                    result_df.loc[result_df.index[i], 'tp_price'] = np.nan
                    result_df.loc[result_df.index[i], 'strategy'] = None
                else:
                    if signal_quality == 3:  # 全ての確認がある場合
                        current_signal = result_df.iloc[i]['signal']
                        current_entry = result_df.iloc[i]['entry_price']
                        current_sl = result_df.iloc[i]['sl_price']
                        current_tp = result_df.iloc[i]['tp_price']
                        
                        tp_distance = abs(current_tp - current_entry)
                        new_tp_distance = tp_distance * 1.2
                        
                        sl_distance = abs(current_sl - current_entry)
                        new_sl_distance = sl_distance * 0.9
                        
                        if current_signal == 1:  # 買いシグナル
                            new_sl = current_entry - new_sl_distance
                            new_tp = current_entry + new_tp_distance
                        else:  # 売りシグナル
                            new_sl = current_entry + new_sl_distance
                            new_tp = current_entry - new_tp_distance
                        
                        result_df.loc[result_df.index[i], 'sl_price'] = new_sl
                        result_df.loc[result_df.index[i], 'tp_price'] = new_tp
                    
                    result_df.loc[result_df.index[i], 'signal_quality'] = signal_quality
        
        return result_df


class EnhancedRiskManagementStrategy(CompositeIndicatorStrategy):
    """
    リスク管理強化版ボリンジャーバンド＋RSI戦略
    
    リスク管理を強化して、より安定したパフォーマンスを実現する戦略
    """
    
    def __init__(self, use_enhanced_risk: bool = True, *args, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        use_enhanced_risk : bool, default True
            強化されたリスク管理を使用するかどうか
        *args, **kwargs
            親クラスに渡す引数
        """
        super().__init__(*args, **kwargs)
        self.use_enhanced_risk = use_enhanced_risk
        self.name = "リスク管理強化版ボリンジャーバンド＋RSI戦略"
        
        self.position_sizer = DynamicPositionSizer()
        self.sl_tp_calculator = AdaptiveStopLossTakeProfit()
        self.risk_manager = RiskManager()
        
        self.account_balance = 200000  # 初期資金
        self.open_positions_value = 0
        self.last_trade_result = None
    
    def generate_signals(self, df: pd.DataFrame, year: int = 2020, 
                       processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        リスク管理を強化したトレードシグナルを生成する
        
        Parameters
        ----------
        df : pd.DataFrame
            主要時間足（15分足）のデータ
        year : int, default 2020
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        result_df = super().generate_signals(df, year, processed_dir)
        
        if not self.use_enhanced_risk:
            return result_df
        
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1).fillna(df['Close'].iloc[0])
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.rolling(14).mean()
        
        result_df['atr'] = atr
        
        for i in range(1, len(result_df)):
            current_signal = result_df.iloc[i]['signal']
            
            if current_signal != 0:
                signal_quality = result_df.iloc[i].get('signal_quality', 0)
                
                market_env = 0  # デフォルトはレンジ相場
                
                if 'trend_strength' in result_df.columns:
                    trend_str = result_df.iloc[i]['trend_strength']
                    if trend_str > 0.5:
                        market_env = 1  # 上昇トレンド
                    elif trend_str < -0.5:
                        market_env = 2  # 下降トレンド
                
                if 'atr' in result_df.columns:
                    volatility = result_df.iloc[i]['atr'] / result_df.iloc[i]['Close']
                    avg_volatility = result_df['atr'].rolling(100).mean().iloc[i] / result_df['Close'].rolling(100).mean().iloc[i]
                    
                    if volatility > avg_volatility * 1.5:
                        market_env = 3  # 高ボラティリティ
                
                can_trade, reason = self.risk_manager.can_open_position(self.last_trade_result)
                
                if not can_trade:
                    result_df.loc[result_df.index[i], 'signal'] = 0
                    result_df.loc[result_df.index[i], 'entry_price'] = np.nan
                    result_df.loc[result_df.index[i], 'sl_price'] = np.nan
                    result_df.loc[result_df.index[i], 'tp_price'] = np.nan
                    result_df.loc[result_df.index[i], 'strategy'] = None
                    result_df.loc[result_df.index[i], 'risk_note'] = reason
                    continue
                
                sl_price, tp_price, sl_pips, tp_pips = self.sl_tp_calculator.calculate_levels(
                    result_df, i, current_signal, signal_quality, market_env
                )
                
                market_volatility = result_df.iloc[i]['atr'] / result_df.iloc[i]['Close']
                
                position_size = self.position_sizer.calculate_position_size(
                    self.account_balance, signal_quality, market_volatility, sl_pips
                )
                
                adjusted_position_size = self.risk_manager.adjust_position_size(position_size)
                
                result_df.loc[result_df.index[i], 'sl_price'] = sl_price
                result_df.loc[result_df.index[i], 'tp_price'] = tp_price
                result_df.loc[result_df.index[i], 'position_size'] = adjusted_position_size
                result_df.loc[result_df.index[i], 'market_environment'] = market_env
        
        return result_df
    
    def update_account_metrics(self, trade_result: Dict) -> None:
        """
        トレード結果に基づいて口座情報を更新する
        
        Parameters
        ----------
        trade_result : Dict
            トレード結果（'profit'と'open_positions_value'を含む辞書）
        """
        if trade_result['profit'] > 0:
            self.last_trade_result = True
        else:
            self.last_trade_result = False
        
        self.account_balance += trade_result['profit']
        self.open_positions_value = trade_result['open_positions_value']
        
        self.risk_manager.update_metrics(self.account_balance, self.open_positions_value)


class CompositeEnhancedBollingerRsiStrategy(EnhancedRiskManagementStrategy):
    """
    複合指標・リスク管理強化版ボリンジャーバンド＋RSI戦略
    
    複合指標とリスク管理を組み合わせた最終的な戦略
    """
    
    def __init__(self, *args, **kwargs):
        """
        初期化
        
        Parameters
        ----------
        *args, **kwargs
            親クラスに渡す引数
        """
        super().__init__(*args, **kwargs)
        self.name = "複合指標・リスク管理強化版ボリンジャーバンド＋RSI戦略"
    
    def backtest(self, df: pd.DataFrame, year: int = 2020, 
               processed_dir: str = 'data/processed') -> pd.DataFrame:
        """
        バックテストを実行する
        
        Parameters
        ----------
        df : pd.DataFrame
            主要時間足（15分足）のデータ
        year : int, default 2020
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        pd.DataFrame
            シグナルが追加されたDataFrame
        """
        signals_df = self.generate_signals(df, year, processed_dir)
        
        
        return signals_df
