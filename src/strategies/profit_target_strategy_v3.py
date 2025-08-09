import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from ..utils.logger import Logger

class ProfitTargetStrategyV3:
    """
    月利益20万円を目指す最適化版戦略（V3）
    
    V2からの改良点:
    1. フィルター条件の緩和（時間帯拡大、トレンド判定緩和）
    2. ロットサイズの調整（stableフェーズで1.7倍）
    3. エントリー条件の最適化（RSI/BB閾値の調整）
    4. リスク許容度の向上（2%→3%）
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 monthly_profit_target: float = 200000,
                 max_risk_per_trade: float = 0.03,  # 2%→3%に増加
                 max_daily_loss: float = 0.05,
                 max_drawdown: float = 0.20,
                 scaling_phase: str = 'stable'):  # stableフェーズで開始
        """
        初期化（最適化版パラメータ）
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.monthly_profit_target = monthly_profit_target
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.scaling_phase = scaling_phase
        
        # 最適化版パラメータ
        self.rsi_oversold = 30    # 25→30に緩和
        self.rsi_overbought = 70  # 75→70に緩和
        self.bb_width = 2.0        # 2.2→2.0に緩和
        
        # ロットサイズ倍率（最適化）
        self.lot_multipliers = {
            'initial': 0.6,
            'growth': 1.2,     # 1.0→1.2に増加
            'stable': 1.7      # 目標達成のため1.7倍
        }
        
        # 戦略別の基本ロットサイズ（最適化）
        self.base_lot_sizes = {
            'core': 0.6,       # 0.5→0.6に増加
            'aggressive': 0.4, # 0.3→0.4に増加
            'stable': 1.2      # 1.0→1.2に増加
        }
        
        # パフォーマンス追跡
        self.daily_pnl = 0
        self.monthly_pnl = 0
        self.peak_balance = initial_balance
        self.current_drawdown = 0
        self.trade_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        self.win_count = {'core': 0, 'aggressive': 0, 'stable': 0}
    
    def is_good_trading_time(self, timestamp: pd.Timestamp) -> bool:
        """
        高勝率時間帯（緩和版）
        
        V2: 9時間のみ → V3: 12時間に拡大
        """
        hour = timestamp.hour
        
        # 時間帯を拡大（取引機会増加）
        # 東京時間拡大（8-12時）
        if 8 <= hour <= 12:
            return True
        
        # ロンドン時間拡大（15-19時）
        if 15 <= hour <= 19:
            return True
        
        # NY時間拡大（20-24時）
        if 20 <= hour <= 23:
            return True
        
        return False
    
    def check_trend_alignment(self, data: pd.DataFrame) -> int:
        """
        複数時間軸のトレンド一致確認（緩和版）
        
        V2: EMA20/50/200 → V3: EMA20/50のみ（条件緩和）
        """
        if len(data) < 50:  # 200→50に緩和
            return 0
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # EMA計算（短縮版）
        ema20 = data[close_col].ewm(span=20, adjust=False).mean()
        ema50 = data[close_col].ewm(span=50, adjust=False).mean()
        
        current_price = data[close_col].iloc[-1]
        
        # 上昇トレンド（条件緩和）: 価格 > EMA20 > EMA50
        if (current_price > ema20.iloc[-1] and 
            ema20.iloc[-1] > ema50.iloc[-1]):
            return 1
        
        # 下降トレンド（条件緩和）: 価格 < EMA20 < EMA50
        if (current_price < ema20.iloc[-1] and 
            ema20.iloc[-1] < ema50.iloc[-1]):
            return -1
        
        # レンジ相場も取引対象に（V2では除外していた）
        return 0  # レンジでも取引可能
    
    def calculate_dynamic_tp_sl(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        ボラティリティに基づく動的TP/SL設定（最適化版）
        """
        if len(data) < 14:
            return 25.0, 10.0  # デフォルト値を調整
        
        atr = self._calculate_atr(data, 14)
        if atr.empty:
            return 25.0, 10.0
        
        current_atr = atr.iloc[-1]
        
        # ATRベースの設定（最適化）
        sl_pips = max(8, min(15, current_atr * 80))  # 範囲を8-15pipsに調整
        tp_pips = sl_pips * 2.8  # R/R比2.8に向上
        
        # ボラティリティ調整
        volatility = current_atr / data['Close' if 'Close' in data.columns else 'close'].iloc[-1]
        
        if volatility > 0.007:  # 閾値を0.8%→0.7%に緩和
            sl_pips *= 1.1  # 調整幅を縮小
            tp_pips *= 1.2
        
        return round(tp_pips, 1), round(sl_pips, 1)
    
    def generate_core_signal(self, data: pd.DataFrame) -> int:
        """
        最適化版コア戦略のシグナル生成
        """
        if len(data) < 50:  # 200→50に緩和
            return 0
        
        # 時間帯チェック（緩和版）
        if not self.is_good_trading_time(data.index[-1]):
            return 0
        
        # トレンドチェック（緩和版）
        trend = self.check_trend_alignment(data)
        # V3: レンジ相場でも取引可能（trend == 0でもOK）
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # ボリンジャーバンド（最適化版）
        sma = data[close_col].rolling(20).mean()
        std = data[close_col].rolling(20).std()
        upper_band = sma + (self.bb_width * std)
        lower_band = sma - (self.bb_width * std)
        
        # RSI（最適化版）
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = data[close_col].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 買いシグナル（条件緩和）
        if (current_price < lower_band.iloc[-1] and 
            current_rsi < self.rsi_oversold):
            # トレンドが上昇または中立なら取引
            if trend >= 0:  # trend == 1 または trend == 0
                return 1
        
        # 売りシグナル（条件緩和）
        if (current_price > upper_band.iloc[-1] and 
            current_rsi > self.rsi_overbought):
            # トレンドが下降または中立なら取引
            if trend <= 0:  # trend == -1 または trend == 0
                return -1
        
        return 0
    
    def generate_enhanced_aggressive_signal(self, data: pd.DataFrame) -> int:
        """
        強化版アグレッシブ戦略
        """
        if len(data) < 20:
            return 0
        
        # 時間帯チェック（さらに緩和）
        hour = data.index[-1].hour
        if not (6 <= hour <= 23):  # 6-23時（17時間）
            return 0
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # 短期移動平均
        sma_5 = data[close_col].rolling(5).mean()
        sma_10 = data[close_col].rolling(10).mean()
        sma_20 = data[close_col].rolling(20).mean()
        
        # モメンタム指標追加
        momentum_3 = data[close_col].iloc[-1] - data[close_col].iloc[-3]  # 3期間前との差
        momentum_5 = data[close_col].iloc[-1] - data[close_col].iloc[-5]  # 5期間前との差
        
        # ボラティリティ
        atr = self._calculate_atr(data, 14)
        current_atr = atr.iloc[-1] if not atr.empty else 0
        
        # 価格変動率
        price_change_pct = (data[close_col].iloc[-1] - data[close_col].iloc[-10]) / data[close_col].iloc[-10]
        
        # 買いシグナル（強化版）
        if (sma_5.iloc[-1] > sma_10.iloc[-1] > sma_20.iloc[-1] and 
            momentum_3 > 0 and momentum_5 > current_atr * 0.3 and  # 条件緩和
            price_change_pct > 0.001):  # 0.1%以上の上昇
            return 1
        
        # 売りシグナル（強化版）
        if (sma_5.iloc[-1] < sma_10.iloc[-1] < sma_20.iloc[-1] and 
            momentum_3 < 0 and momentum_5 < -current_atr * 0.3 and
            price_change_pct < -0.001):  # 0.1%以上の下落
            return -1
        
        return 0
    
    def generate_stable_signal(self, data: pd.DataFrame) -> int:
        """
        最適化版安定戦略
        """
        if len(data) < 50:  # 100→50にさらに緩和
            return 0
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # 移動平均（期間短縮）
        sma_25 = data[close_col].rolling(25).mean()  # 50→25
        sma_50 = data[close_col].rolling(50).mean()  # 100→50
        
        # MACD（パラメータ調整）
        ema_10 = data[close_col].ewm(span=10, adjust=False).mean()  # 12→10
        ema_20 = data[close_col].ewm(span=20, adjust=False).mean()  # 26→20
        macd = ema_10 - ema_20
        signal_line = macd.ewm(span=7, adjust=False).mean()  # 9→7
        
        # 買いシグナル（条件大幅緩和）
        if (sma_25.iloc[-1] > sma_50.iloc[-1] and
            macd.iloc[-1] > signal_line.iloc[-1]):
            return 1
        
        # 売りシグナル（条件大幅緩和）
        if (sma_25.iloc[-1] < sma_50.iloc[-1] and
            macd.iloc[-1] < signal_line.iloc[-1]):
            return -1
        
        return 0
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR計算（V2と同じ）"""
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
    
    def calculate_optimal_lot_size(self, strategy_type: str, stop_loss_pips: float) -> float:
        """
        最適なロットサイズ計算（最適化版）
        """
        base_lot = self.base_lot_sizes.get(strategy_type, 0.6)
        phase_multiplier = self.lot_multipliers.get(self.scaling_phase, 1.7)
        
        # リスク計算（3%に増加）
        risk_amount = self.current_balance * self.max_risk_per_trade
        pip_value_per_lot = 1000
        
        # 最適ロットサイズ
        optimal_lot = (risk_amount / (stop_loss_pips * pip_value_per_lot))
        
        # 調整適用
        adjusted_lot = min(optimal_lot, base_lot) * phase_multiplier
        
        # 最大ロットサイズ
        max_lot = 3.0  # 2.0→3.0に増加
        final_lot = min(adjusted_lot, max_lot)
        
        return round(final_lot, 2)
    
    def check_risk_limits(self) -> bool:
        """リスク制限チェック"""
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