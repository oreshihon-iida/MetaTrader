import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from ..utils.logger import Logger

class ProfitTargetStrategyV2:
    """
    月利益20万円を目指す改良版戦略
    
    改良点:
    1. エントリーフィルター強化（RSI/BB閾値の最適化）
    2. 時間帯フィルター実装
    3. トレンドフィルター追加
    4. 動的TP/SL設定
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 monthly_profit_target: float = 200000,
                 max_risk_per_trade: float = 0.02,
                 max_daily_loss: float = 0.05,
                 max_drawdown: float = 0.20,
                 scaling_phase: str = 'initial'):
        """
        初期化
        
        Parameters
        ----------
        initial_balance : float
            初期資金（円）デフォルト300万円
        monthly_profit_target : float
            月間利益目標（円）20万円に変更
        max_risk_per_trade : float
            1取引あたりの最大リスク（2%に増加）
        max_daily_loss : float
            1日の最大損失
        max_drawdown : float
            最大ドローダウン
        scaling_phase : str
            スケーリングフェーズ
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.monthly_profit_target = monthly_profit_target
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.scaling_phase = scaling_phase
        
        # 改良版パラメータ
        self.rsi_oversold = 25    # 35 → 25（より強い売られ過ぎ）
        self.rsi_overbought = 75  # 65 → 75（より強い買われ過ぎ）
        self.bb_width = 2.2        # 1.8 → 2.2（より確実なブレイクアウト）
        
        # ロットサイズ倍率（目標達成のため調整）
        self.lot_multipliers = {
            'initial': 0.6,    # 初期段階: 60%（40%から増加）
            'growth': 1.0,     # 成長段階: 100%（70%から増加）
            'stable': 1.7      # 安定段階: 170%（100%から増加）
        }
        
        # 戦略別の基本ロットサイズ
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
    
    def is_good_trading_time(self, timestamp: pd.Timestamp) -> bool:
        """
        高勝率時間帯のみ取引
        
        Parameters
        ----------
        timestamp : pd.Timestamp
            現在時刻
        
        Returns
        -------
        bool
            取引可能時間帯の場合True
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
        複数時間軸のトレンド一致を確認
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        
        Returns
        -------
        int
            1: 上昇トレンド, -1: 下降トレンド, 0: トレンドなし
        """
        if len(data) < 200:
            return 0
        
        # カラム名を統一
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
    
    def calculate_dynamic_tp_sl(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        ボラティリティに基づく動的TP/SL設定
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        
        Returns
        -------
        Tuple[float, float]
            (TP pips, SL pips)
        """
        if len(data) < 14:
            return 30.0, 12.0  # デフォルト値
        
        # ATR計算
        atr = self._calculate_atr(data, 14)
        if atr.empty:
            return 30.0, 12.0
        
        current_atr = atr.iloc[-1]
        
        # ATRベースの設定（pips変換）
        sl_pips = max(10, min(20, current_atr * 100))  # 10-20pips範囲
        tp_pips = sl_pips * 2.5  # R/R比2.5を維持
        
        # ボラティリティレベル判定
        volatility = current_atr / data['Close' if 'Close' in data.columns else 'close'].iloc[-1]
        
        if volatility > 0.008:  # 高ボラティリティ（0.8%以上）
            sl_pips *= 1.2
            tp_pips *= 1.3  # R/R比をさらに改善
        
        return round(tp_pips, 1), round(sl_pips, 1)
    
    def generate_core_signal(self, data: pd.DataFrame) -> int:
        """
        改良版コア戦略のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 200:
            return 0
        
        # 時間帯チェック
        if not self.is_good_trading_time(data.index[-1]):
            return 0
        
        # トレンドチェック
        trend = self.check_trend_alignment(data)
        if trend == 0:
            return 0  # トレンドが不明確な場合は取引しない
        
        # カラム名を統一
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # ボリンジャーバンド（改良版）
        sma = data[close_col].rolling(20).mean()
        std = data[close_col].rolling(20).std()
        upper_band = sma + (self.bb_width * std)
        lower_band = sma - (self.bb_width * std)
        
        # RSI（改良版）
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = data[close_col].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 買いシグナル（トレンド方向と一致する場合のみ）
        if (trend == 1 and 
            current_price < lower_band.iloc[-1] and 
            current_rsi < self.rsi_oversold):
            return 1
        
        # 売りシグナル（トレンド方向と一致する場合のみ）
        if (trend == -1 and 
            current_price > upper_band.iloc[-1] and 
            current_rsi > self.rsi_overbought):
            return -1
        
        return 0
    
    def generate_aggressive_signal(self, data: pd.DataFrame) -> int:
        """
        改良版アグレッシブ戦略のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ（5分足推奨）
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 50:
            return 0
        
        # 時間帯チェック（アグレッシブ戦略は時間制限を緩める）
        hour = data.index[-1].hour
        if not (7 <= hour <= 23):  # 深夜早朝を除く
            return 0
        
        # カラム名を統一
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # 短期移動平均
        sma_5 = data[close_col].rolling(5).mean()
        sma_10 = data[close_col].rolling(10).mean()
        sma_20 = data[close_col].rolling(20).mean()
        
        # モメンタム
        momentum = data[close_col].iloc[-1] - data[close_col].iloc[-5]
        
        # ボラティリティ
        atr = self._calculate_atr(data, 14)
        current_atr = atr.iloc[-1] if not atr.empty else 0
        
        # RSI追加（フィルター強化）
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()  # 短期RSI
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # 買いシグナル（RSI条件追加）
        if (sma_5.iloc[-1] > sma_10.iloc[-1] > sma_20.iloc[-1] and 
            momentum > current_atr * 0.5 and
            30 < current_rsi < 70):  # RSIが極端でない
            return 1
        
        # 売りシグナル（RSI条件追加）
        if (sma_5.iloc[-1] < sma_10.iloc[-1] < sma_20.iloc[-1] and 
            momentum < -current_atr * 0.5 and
            30 < current_rsi < 70):  # RSIが極端でない
            return -1
        
        return 0
    
    def generate_stable_signal(self, data: pd.DataFrame) -> int:
        """
        改良版安定戦略のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ（日足推奨）
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 100:  # 200から100に緩和
            return 0
        
        # カラム名を統一
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # 長期移動平均
        sma_50 = data[close_col].rolling(50).mean()
        sma_100 = data[close_col].rolling(100).mean()
        
        # MACD（改良版パラメータ）
        ema_12 = data[close_col].ewm(span=12, adjust=False).mean()
        ema_26 = data[close_col].ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        
        # RSI（長期）
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(21).mean()  # 長期RSI
        loss = (-delta.where(delta < 0, 0)).rolling(21).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = data[close_col].iloc[-1]
        
        # 買いシグナル（条件緩和）
        if (sma_50.iloc[-1] > sma_100.iloc[-1] and
            macd.iloc[-1] > signal_line.iloc[-1] and
            macd.iloc[-2] <= signal_line.iloc[-2] and  # MACDクロス
            rsi.iloc[-1] < 60):  # RSI条件緩和
            return 1
        
        # 売りシグナル（条件緩和）
        if (sma_50.iloc[-1] < sma_100.iloc[-1] and
            macd.iloc[-1] < signal_line.iloc[-1] and
            macd.iloc[-2] >= signal_line.iloc[-2] and  # MACDクロス
            rsi.iloc[-1] > 40):  # RSI条件緩和
            return -1
        
        return 0
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        ATR（Average True Range）を計算
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        period : int
            期間
        
        Returns
        -------
        pd.Series
            ATR値
        """
        # カラム名を統一
        high_col = 'High' if 'High' in data.columns else 'high'
        low_col = 'Low' if 'Low' in data.columns else 'low'
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        if high_col not in data.columns or low_col not in data.columns:
            # High/Lowがない場合は簡易計算
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
        最適なロットサイズを計算（改良版）
        
        Parameters
        ----------
        strategy_type : str
            戦略タイプ（'core', 'aggressive', 'stable'）
        stop_loss_pips : float
            ストップロス（pips）
        
        Returns
        -------
        float
            最適なロットサイズ
        """
        # 基本ロットサイズ
        base_lot = self.base_lot_sizes.get(strategy_type, 0.5)
        
        # フェーズ調整
        phase_multiplier = self.lot_multipliers.get(self.scaling_phase, 0.6)
        
        # リスク計算
        risk_amount = self.current_balance * self.max_risk_per_trade
        pip_value_per_lot = 1000  # 円/pip（1ロットあたり）
        
        # 最適ロットサイズを計算
        optimal_lot = (risk_amount / (stop_loss_pips * pip_value_per_lot))
        
        # 基本ロットサイズとフェーズ調整を適用
        adjusted_lot = min(optimal_lot, base_lot) * phase_multiplier
        
        # 最大ロットサイズの制限
        max_lot = 2.0  # 最大2ロットに増加（1ロットから変更）
        final_lot = min(adjusted_lot, max_lot)
        
        return round(final_lot, 2)
    
    def check_risk_limits(self) -> bool:
        """
        リスク制限をチェック
        
        Returns
        -------
        bool
            取引可能な場合True
        """
        # 日次損失チェック
        if abs(self.daily_pnl) >= self.current_balance * self.max_daily_loss:
            return False
        
        # ドローダウンチェック
        if self.current_balance < self.peak_balance:
            self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if self.current_drawdown >= self.max_drawdown:
                return False
        
        return True
    
    def update_balance(self, pnl: float):
        """
        残高を更新
        
        Parameters
        ----------
        pnl : float
            損益
        """
        self.current_balance += pnl
        self.daily_pnl += pnl
        self.monthly_pnl += pnl
        
        # ピーク残高更新
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
    
    def reset_daily_stats(self):
        """日次統計をリセット"""
        self.daily_pnl = 0
    
    def reset_monthly_stats(self):
        """月次統計をリセット"""
        self.monthly_pnl = 0
        self.trade_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        self.win_count = {'core': 0, 'aggressive': 0, 'stable': 0}