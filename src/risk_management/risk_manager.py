import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional

class DynamicPositionSizer:
    """
    動的ポジションサイジング
    
    市場環境とシグナル品質に基づいて、ポジションサイズを動的に調整する
    """
    
    def __init__(self, base_lot_size: float = 0.01, max_risk_per_trade: float = 0.02):
        """
        初期化
        
        Parameters
        ----------
        base_lot_size : float, default 0.01
            基本ロットサイズ
        max_risk_per_trade : float, default 0.02
            1トレードあたりの最大リスク（資金の割合、例: 0.02 = 2%）
        """
        self.base_lot_size = base_lot_size
        self.max_risk_per_trade = max_risk_per_trade
    
    def calculate_position_size(self, account_balance: float, signal_quality: int, 
                               market_volatility: float, sl_pips: float) -> float:
        """
        ポジションサイズを計算する
        
        Parameters
        ----------
        account_balance : float
            口座残高
        signal_quality : int
            シグナル品質（0〜3の範囲）
        market_volatility : float
            市場ボラティリティ
        sl_pips : float
            損切り幅（pips）
            
        Returns
        -------
        float
            計算されたロットサイズ
        """
        risk_amount = account_balance * self.max_risk_per_trade
        
        quality_factor = 0.5 + (signal_quality / 3)
        
        volatility_factor = 1.0 / market_volatility if market_volatility > 0 else 1.0
        volatility_factor = max(0.5, min(1.5, volatility_factor))
        
        risk_per_pip = risk_amount / sl_pips if sl_pips > 0 else risk_amount
        
        adjusted_lot_size = self.base_lot_size * quality_factor * volatility_factor
        
        max_lot_size = risk_per_pip / (sl_pips * 100)  # 1pipあたり100円と仮定
        
        final_lot_size = min(adjusted_lot_size, max_lot_size)
        
        final_lot_size = max(self.base_lot_size, final_lot_size)
        
        return final_lot_size


class AdaptiveStopLossTakeProfit:
    """
    適応型損切り・利確レベル
    
    市場ボラティリティとシグナル品質に基づいて、損切り・利確レベルを動的に調整する
    """
    
    def __init__(self, base_sl_pips: float = 10.0, base_tp_pips: float = 20.0, atr_multiplier: float = 1.5):
        """
        初期化
        
        Parameters
        ----------
        base_sl_pips : float, default 10.0
            基本損切り幅（pips）
        base_tp_pips : float, default 20.0
            基本利確幅（pips）
        atr_multiplier : float, default 1.5
            ATRに対する乗数
        """
        self.base_sl_pips = base_sl_pips
        self.base_tp_pips = base_tp_pips
        self.atr_multiplier = atr_multiplier
    
    def calculate_levels(self, df: pd.DataFrame, index: int, signal: int, 
                        signal_quality: int, market_environment: int) -> Tuple[float, float, float, float]:
        """
        損切り・利確レベルを計算する
        
        Parameters
        ----------
        df : pd.DataFrame
            処理対象のデータ
        index : int
            現在の行のインデックス
        signal : int
            シグナルの方向（1: 買い、-1: 売り）
        signal_quality : int
            シグナル品質（0〜3の範囲）
        market_environment : int
            市場環境（0: レンジ相場、1: 上昇トレンド、2: 下降トレンド、3: 高ボラティリティ）
            
        Returns
        -------
        Tuple[float, float, float, float]
            (損切りレベル, 利確レベル, 損切り幅(pips), 利確幅(pips))
        """
        current = df.iloc[index]
        entry_price = current['entry_price']
        
        atr = current.get('atr', self.base_sl_pips * 0.01)
        
        env_factors = {
            0: {'sl': 1.0, 'tp': 1.0},    # レンジ相場
            1: {'sl': 1.2, 'tp': 1.5},    # 上昇トレンド
            2: {'sl': 1.2, 'tp': 1.5},    # 下降トレンド
            3: {'sl': 1.5, 'tp': 2.0}     # 高ボラティリティ
        }
        
        env = market_environment if market_environment in env_factors else 0
        env_factor_sl = env_factors[env]['sl']
        env_factor_tp = env_factors[env]['tp']
        
        quality_factor_sl = 1.0 - (signal_quality * 0.1)  # 高品質シグナルでは小さなSL
        quality_factor_tp = 1.0 + (signal_quality * 0.1)  # 高品質シグナルでは大きなTP
        
        sl_pips = self.base_sl_pips * env_factor_sl * quality_factor_sl
        tp_pips = self.base_tp_pips * env_factor_tp * quality_factor_tp
        
        sl_pips = max(sl_pips, atr * 100 * self.atr_multiplier * 0.5)  # ATRをpipsに変換（×100）
        tp_pips = max(tp_pips, atr * 100 * self.atr_multiplier * 1.0)  # ATRをpipsに変換（×100）
        
        rr_ratio = tp_pips / sl_pips
        if rr_ratio < 1.5:
            tp_pips = sl_pips * 1.5
        
        if signal == 1:  # 買いシグナル
            sl_price = entry_price - (sl_pips * 0.01)
            tp_price = entry_price + (tp_pips * 0.01)
        else:  # 売りシグナル
            sl_price = entry_price + (sl_pips * 0.01)
            tp_price = entry_price - (tp_pips * 0.01)
        
        return sl_price, tp_price, sl_pips, tp_pips


class RiskManager:
    """
    リスクマネージャー
    
    最大ドローダウンを制限し、市場エクスポージャーを管理する
    """
    
    def __init__(self, max_drawdown_pct: float = 10.0, max_exposure_pct: float = 20.0, 
                max_consecutive_losses: int = 3):
        """
        初期化
        
        Parameters
        ----------
        max_drawdown_pct : float, default 10.0
            最大許容ドローダウン（%）
        max_exposure_pct : float, default 20.0
            最大市場エクスポージャー（%）
        max_consecutive_losses : int, default 3
            連続損失の最大許容数
        """
        self.max_drawdown_pct = max_drawdown_pct
        self.max_exposure_pct = max_exposure_pct
        self.max_consecutive_losses = max_consecutive_losses
        
        self.peak_balance = 0
        self.current_drawdown_pct = 0
        self.current_exposure_pct = 0
        self.consecutive_losses = 0
    
    def update_metrics(self, current_balance: float, open_positions_value: float) -> None:
        """
        メトリクスを更新する
        
        Parameters
        ----------
        current_balance : float
            現在の口座残高
        open_positions_value : float
            オープンポジションの価値
        """
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        if self.peak_balance > 0:
            self.current_drawdown_pct = (self.peak_balance - current_balance) / self.peak_balance * 100
        
        if current_balance > 0:
            self.current_exposure_pct = open_positions_value / current_balance * 100
    
    def can_open_position(self, is_winning_last: Optional[bool] = None) -> Tuple[bool, str]:
        """
        ポジションを開くことができるかどうかを判断する
        
        Parameters
        ----------
        is_winning_last : bool, optional
            直前のトレードが勝ちだったかどうか
            
        Returns
        -------
        Tuple[bool, str]
            (ポジションを開くことができるかどうか, 理由)
        """
        if is_winning_last is not None:
            if is_winning_last:
                self.consecutive_losses = 0
            else:
                self.consecutive_losses += 1
        
        if self.current_drawdown_pct >= self.max_drawdown_pct:
            return False, "最大ドローダウン制限に達しました"
        
        if self.current_exposure_pct >= self.max_exposure_pct:
            return False, "最大エクスポージャー制限に達しました"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, "連続損失制限に達しました"
        
        return True, ""
    
    def adjust_position_size(self, base_position_size: float) -> float:
        """
        ポジションサイズを調整する
        
        Parameters
        ----------
        base_position_size : float
            基本ポジションサイズ
            
        Returns
        -------
        float
            調整後のポジションサイズ
        """
        drawdown_factor = 1.0 - (self.current_drawdown_pct / self.max_drawdown_pct)
        drawdown_factor = max(0.25, min(1.0, drawdown_factor))  # 最小25%、最大100%
        
        loss_factor = 1.0 - (self.consecutive_losses / self.max_consecutive_losses * 0.5)
        loss_factor = max(0.5, min(1.0, loss_factor))  # 最小50%、最大100%
        
        adjustment_factor = drawdown_factor * loss_factor
        
        return base_position_size * adjustment_factor
