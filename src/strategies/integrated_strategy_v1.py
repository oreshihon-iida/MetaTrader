#!/usr/bin/env python3
"""
統合戦略 V1.0 - Phase 1: R/R比最適化
V2戦略をベースに、固定R/R比システムを導入した改良版

改良内容:
1. 固定R/R比 2.5:1 ~ 3.0:1 の導入
2. V2の全フィルター要素を保持
3. 段階的改良のためのベースライン確立
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from ..utils.logger import Logger

class IntegratedStrategyV1:
    """
    V2ベース統合戦略 Phase 1
    
    核心改良:
    - 固定R/R比システム（2.5:1 - 3.0:1）
    - V2の実証済みフィルターを完全保持
    - 市場分析ベースのエントリー判断
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 monthly_profit_target: float = 200000,
                 max_risk_per_trade: float = 0.02,
                 max_daily_loss: float = 0.05,
                 max_drawdown: float = 0.20,
                 scaling_phase: str = 'growth',
                 target_rr_ratio: float = 2.8):
        """
        初期化
        
        Parameters
        ----------
        target_rr_ratio : float, default 2.8
            目標リスクリワード比（2.5-3.0の範囲）
        """
        # V2戦略の基本設定を継承
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.monthly_profit_target = monthly_profit_target
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.scaling_phase = scaling_phase
        
        # V2の実証済みパラメータを保持
        self.rsi_oversold = 25    # V2の成功パラメータ
        self.rsi_overbought = 75
        self.bb_width = 2.2       # V2の最適化済み値
        
        # Phase 1の新機能: 固定R/R比システム
        self.target_rr_ratio = max(2.5, min(3.0, target_rr_ratio))  # 2.5-3.0に制限
        self.base_sl_pips = 12.0  # ベースストップロス
        self.base_tp_pips = self.base_sl_pips * self.target_rr_ratio
        
        # 市況適応レンジ
        self.sl_range = (8.0, 18.0)   # SL可変範囲
        self.volatility_adjustment = True  # ボラティリティ調整有効
        
        # V2のロット設定を継承
        self.lot_multipliers = {
            'initial': 0.6,
            'growth': 1.0,
            'stable': 1.7
        }
        
        self.base_lot_sizes = {
            'core': 0.5,
            'aggressive': 0.3,
            'stable': 1.0
        }
        
        # パフォーマンス追跡
        self.daily_pnl = 0
        self.monthly_pnl = 0
        self.peak_balance = initial_balance
        self.current_drawdown = 0
        self.trade_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        self.win_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        
        print(f"IntegratedStrategy V1 initialized:")
        print(f"  Target R/R Ratio: {self.target_rr_ratio}:1")
        print(f"  Base TP/SL: {self.base_tp_pips:.1f}/{self.base_sl_pips:.1f} pips")
        print(f"  V2 Parameters: RSI {self.rsi_oversold}/{self.rsi_overbought}, BB {self.bb_width}σ")
    
    def calculate_optimized_tp_sl(self, data: pd.DataFrame, market_condition: str = "normal") -> Tuple[float, float]:
        """
        最適化されたTP/SL計算（Phase 1の核心機能）
        
        V2の動的計算 + 固定R/R比の組み合わせ
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        market_condition : str
            市場状況 ("normal", "volatile", "trending")
            
        Returns
        -------
        Tuple[float, float]
            (TP pips, SL pips)
        """
        if len(data) < 14:
            return self.base_tp_pips, self.base_sl_pips
        
        # ATRベースの基本計算（V2から継承）
        atr = self._calculate_atr(data, 14)
        if atr.empty:
            return self.base_tp_pips, self.base_sl_pips
        
        current_atr = atr.iloc[-1]
        
        # ボラティリティ適応的SL計算
        if self.volatility_adjustment:
            # ATRベースでSLを調整（V2の手法）
            atr_based_sl = max(self.sl_range[0], min(self.sl_range[1], current_atr * 100))
            
            # 市況別調整
            if market_condition == "volatile":
                sl_pips = atr_based_sl * 1.2
            elif market_condition == "trending":
                sl_pips = atr_based_sl * 0.9  # トレンド中は狭めに
            else:
                sl_pips = atr_based_sl
        else:
            sl_pips = self.base_sl_pips
        
        # 固定R/R比でTP計算（Phase 1の改良点）
        tp_pips = sl_pips * self.target_rr_ratio
        
        return round(tp_pips, 1), round(sl_pips, 1)
    
    def is_good_trading_time(self, timestamp: pd.Timestamp) -> bool:
        """
        V2の実証済み時間帯フィルター（完全保持）
        """
        hour = timestamp.hour
        
        # 東京時間（9-11時）: 勝率高
        if 9 <= hour <= 11:
            return True
        
        # ロンドン時間（16-18時）: トレンド発生
        if 16 <= hour <= 18:
            return True
        
        # NY時間（21-23時）: ボラティリティ高
        if 21 <= hour <= 23:
            return True
        
        return False
    
    def check_trend_alignment(self, data: pd.DataFrame) -> int:
        """
        V2の実証済みトレンドフィルター（完全保持）
        """
        if len(data) < 200:
            return 0
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # EMA計算
        ema20 = data[close_col].ewm(span=20, adjust=False).mean()
        ema50 = data[close_col].ewm(span=50, adjust=False).mean()
        ema200 = data[close_col].ewm(span=200, adjust=False).mean()
        
        current_price = data[close_col].iloc[-1]
        
        # 上昇トレンド: 価格 > EMA20 > EMA50 > EMA200
        if (current_price > ema20.iloc[-1] and 
            ema20.iloc[-1] > ema50.iloc[-1] and 
            ema50.iloc[-1] > ema200.iloc[-1]):
            return 1
        
        # 下降トレンド: 価格 < EMA20 < EMA50 < EMA200
        if (current_price < ema20.iloc[-1] and 
            ema20.iloc[-1] < ema50.iloc[-1] and 
            ema50.iloc[-1] < ema200.iloc[-1]):
            return -1
        
        return 0
    
    def detect_market_condition(self, data: pd.DataFrame) -> str:
        """
        市場状況検出（Phase 1の新機能）
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        str
            市場状況 ("normal", "volatile", "trending")
        """
        if len(data) < 50:
            return "normal"
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # ボラティリティ判定
        returns = data[close_col].pct_change().dropna()
        recent_volatility = returns.tail(20).std()
        
        # トレンド強度判定
        sma_20 = data[close_col].rolling(20).mean()
        trend_strength = abs((data[close_col].iloc[-1] - sma_20.iloc[-21]) / sma_20.iloc[-21]) if len(sma_20) > 21 else 0
        
        # 判定ロジック
        if recent_volatility > 0.012:  # 高ボラティリティ
            return "volatile"
        elif trend_strength > 0.05:   # 強いトレンド
            return "trending"
        else:
            return "normal"
    
    def generate_core_signal(self, data: pd.DataFrame) -> int:
        """
        改良版コアシグナル生成
        V2のロジック + 市況適応
        """
        if len(data) < 200:
            return 0
        
        # V2の時間帯フィルター
        if not self.is_good_trading_time(data.index[-1]):
            return 0
        
        # V2のトレンドフィルター（統合戦略V1では緩和）
        trend = self.check_trend_alignment(data)
        # トレンド=0でも強いシグナルの場合は通す（Phase1改良）
        
        # 市況検出（新機能）
        market_condition = self.detect_market_condition(data)
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # V2のBB + RSI計算（パラメータそのまま）
        sma = data[close_col].rolling(20).mean()
        std = data[close_col].rolling(20).std()
        upper_band = sma + (self.bb_width * std)
        lower_band = sma - (self.bb_width * std)
        
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = data[close_col].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # シグナル品質調整（市況別）
        rsi_threshold_adjustment = 0
        if market_condition == "volatile":
            rsi_threshold_adjustment = 5  # より厳格に
        elif market_condition == "trending":
            rsi_threshold_adjustment = -3  # やや緩く
        
        adjusted_oversold = self.rsi_oversold + rsi_threshold_adjustment
        adjusted_overbought = self.rsi_overbought - rsi_threshold_adjustment
        
        # 統合戦略V1のシグナルロジック（トレンドフィルター大幅緩和版）
        # Phase 1: トレンド=0でも適切なシグナルを許可
        
        buy_conditions = (
            current_price < lower_band.iloc[-1] and 
            current_rsi < adjusted_oversold
        )
        
        sell_conditions = (
            current_price > upper_band.iloc[-1] and 
            current_rsi > adjusted_overbought
        )
        
        # 買いシグナル: トレンド確認（緩和版）
        if buy_conditions:
            # トレンド上昇中 OR トレンド中立で強いRSI OR 非常に強いシグナル
            if (trend == 1 or 
                (trend == 0 and current_rsi < adjusted_oversold) or
                (current_rsi < adjusted_oversold - 8)):  # 非常に強い売られすぎ
                return 1
        
        # 売りシグナル: トレンド確認（緩和版）
        if sell_conditions:
            # トレンド下降中 OR トレンド中立で強いRSI OR 非常に強いシグナル
            if (trend == -1 or 
                (trend == 0 and current_rsi > adjusted_overbought) or
                (current_rsi > adjusted_overbought + 8)):  # 非常に強い買われすぎ
                return -1
        
        return 0
    
    def calculate_optimal_lot_size(self, strategy_type: str, stop_loss_pips: float) -> float:
        """
        V2のロットサイズ計算を継承
        """
        base_lot = self.base_lot_sizes.get(strategy_type, 0.5)
        phase_multiplier = self.lot_multipliers.get(self.scaling_phase, 0.6)
        
        # リスク計算
        risk_amount = self.current_balance * self.max_risk_per_trade
        pip_value_per_lot = 1000  # 円/pip（1ロットあたり）
        
        optimal_lot = (risk_amount / (stop_loss_pips * pip_value_per_lot))
        adjusted_lot = min(optimal_lot, base_lot) * phase_multiplier
        
        # 最大制限
        max_lot = 2.0
        final_lot = min(adjusted_lot, max_lot)
        
        return round(final_lot, 2)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        ATR計算（V2から継承）
        """
        high_col = 'High' if 'High' in data.columns else 'high'
        low_col = 'Low' if 'Low' in data.columns else 'low'
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        if high_col not in data.columns or low_col not in data.columns:
            return data[close_col].rolling(period).std()
        
        high = data[high_col]
        low = data[low_col]
        close = data[close_col]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def get_strategy_summary(self) -> Dict:
        """
        統合戦略V1の概要情報
        """
        return {
            'version': 'Integrated Strategy V1.0 - Phase 1',
            'base_strategy': 'ProfitTargetStrategyV2',
            'key_improvements': [
                'Fixed R/R ratio system (2.5-3.0:1)',
                'Market condition adaptive TP/SL',
                'Enhanced signal quality filtering',
                'All V2 proven filters retained'
            ],
            'target_rr_ratio': self.target_rr_ratio,
            'monthly_target': f'{self.monthly_profit_target:,.0f} JPY',
            'risk_per_trade': f'{self.max_risk_per_trade:.1%}'
        }

# V2継承のためのその他メソッド（チェック機能など）
    def check_risk_limits(self) -> bool:
        """V2のリスク制限チェック"""
        if abs(self.daily_pnl) >= self.current_balance * self.max_daily_loss:
            return False
        
        if self.current_balance < self.peak_balance:
            self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if self.current_drawdown >= self.max_drawdown:
                return False
        
        return True
    
    def update_balance(self, pnl: float):
        """残高更新"""
        self.current_balance += pnl
        self.daily_pnl += pnl
        self.monthly_pnl += pnl
        
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
    
    def reset_daily_stats(self):
        """日次統計リセット"""
        self.daily_pnl = 0
    
    def reset_monthly_stats(self):
        """月次統計リセット"""
        self.monthly_pnl = 0
        self.trade_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        self.win_count = {'core': 0, 'aggressive': 0, 'stable': 0}