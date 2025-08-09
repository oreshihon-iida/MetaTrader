import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from ..utils.logger import Logger

class ProfitTargetStrategy:
    """
    月利益50万円（年間600万円）を目指す高利益目標戦略
    
    3層アーキテクチャ：
    1. コア戦略（50%）: 改良版MT戦略
    2. アグレッシブ戦略（30%）: スキャルピング
    3. 安定戦略（20%）: 長期マクロ戦略
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 monthly_profit_target: float = 500000,
                 max_risk_per_trade: float = 0.015,
                 max_daily_loss: float = 0.05,
                 max_drawdown: float = 0.20,
                 scaling_phase: str = 'initial'):  # 'initial', 'growth', 'stable'
        """
        初期化
        
        Parameters
        ----------
        initial_balance : float
            初期資金（円）デフォルト300万円
        monthly_profit_target : float
            月間利益目標（円）
        max_risk_per_trade : float
            1取引あたりの最大リスク（口座残高に対する比率）
        max_daily_loss : float
            1日の最大損失（口座残高に対する比率）
        max_drawdown : float
            最大ドローダウン（口座残高に対する比率）
        scaling_phase : str
            スケーリングフェーズ（initial/growth/stable）
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.monthly_profit_target = monthly_profit_target
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.scaling_phase = scaling_phase
        
        # ロットサイズ倍率（フェーズに応じて調整）
        self.lot_multipliers = {
            'initial': 0.4,    # 初期段階: 40%
            'growth': 0.7,     # 成長段階: 70%
            'stable': 1.0      # 安定段階: 100%
        }
        
        # 戦略別の基本ロットサイズ（300万円ベース）
        self.base_lot_sizes = {
            'core': 0.5,       # コア戦略
            'aggressive': 0.3, # アグレッシブ戦略
            'stable': 1.0      # 安定戦略
        }
        
        # 戦略別の目標（300万円ベース）
        self.strategy_targets = {
            'core': {
                'monthly_pips': 500,
                'win_rate': 0.70,
                'monthly_trades': 45,
                'allocated_capital': initial_balance * 0.5  # 150万円
            },
            'aggressive': {
                'monthly_pips': 500,
                'win_rate': 0.60,
                'monthly_trades': 175,
                'allocated_capital': initial_balance * 0.3  # 90万円
            },
            'stable': {
                'monthly_pips': 100,
                'win_rate': 0.75,
                'monthly_trades': 10,
                'allocated_capital': initial_balance * 0.2  # 60万円
            }
        }
        
        # パフォーマンス追跡
        self.daily_pnl = 0
        self.monthly_pnl = 0
        self.peak_balance = initial_balance
        self.current_drawdown = 0
        self.trade_count = {'core': 0, 'aggressive': 0, 'stable': 0}
        self.win_count = {'core': 0, 'aggressive': 0, 'stable': 0}
    
    def calculate_optimal_lot_size(self, strategy_type: str, stop_loss_pips: float) -> float:
        """
        最適なロットサイズを計算
        
        Parameters
        ----------
        strategy_type : str
            戦略タイプ（core/aggressive/stable）
        stop_loss_pips : float
            ストップロス幅（pips）
        
        Returns
        -------
        float
            最適なロットサイズ
        """
        # リスク許容額を計算
        risk_amount = self.current_balance * self.max_risk_per_trade
        
        # 基本ロットサイズを取得
        base_lot = self.base_lot_sizes.get(strategy_type, 0.1)
        
        # フェーズに応じた調整
        phase_multiplier = self.lot_multipliers.get(self.scaling_phase, 0.5)
        
        # pip価値を計算（1ロット = 100,000通貨の場合）
        pip_value_per_lot = 1000  # 円/pip（1ロットあたり）
        
        # 最適ロットサイズを計算
        optimal_lot = (risk_amount / (stop_loss_pips * pip_value_per_lot))
        
        # 基本ロットサイズとフェーズ調整を適用
        adjusted_lot = min(optimal_lot, base_lot) * phase_multiplier
        
        # 最大ロットサイズの制限（リスク管理）
        max_lot = 1.0  # 最大1ロット
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
            # ログは外部で記録
            return False
        
        # ドローダウンチェック
        if self.current_balance < self.peak_balance:
            self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if self.current_drawdown >= self.max_drawdown:
                # ログは外部で記録
                return False
        
        return True
    
    def generate_core_signal(self, data: pd.DataFrame) -> int:
        """
        コア戦略（改良版MT戦略）のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 50:
            return 0
        
        # 複数時間足の確認（簡略版）
        # 実際の実装では MultiTimeframeDataManager を使用
        
        # カラム名を統一（大文字小文字対応）
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # ボリンジャーバンド（緩和版）
        sma = data[close_col].rolling(20).mean()
        std = data[close_col].rolling(20).std()
        upper_band = sma + (1.8 * std)  # 2.0σ → 1.8σに緩和
        lower_band = sma - (1.8 * std)
        
        # RSI（緩和版）
        delta = data[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = data[close_col].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 買いシグナル（条件緩和）
        if current_price < lower_band.iloc[-1] and current_rsi < 35:  # 30 → 35
            return 1
        
        # 売りシグナル（条件緩和）
        if current_price > upper_band.iloc[-1] and current_rsi > 65:  # 70 → 65
            return -1
        
        return 0
    
    def generate_aggressive_signal(self, data: pd.DataFrame) -> int:
        """
        アグレッシブ戦略（スキャルピング）のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ（5分足推奨）
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 20:
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
        
        # 時間帯フィルター（東京・ロンドン時間）
        current_hour = pd.to_datetime(data.index[-1]).hour
        is_active_time = (8 <= current_hour <= 11) or (16 <= current_hour <= 19)
        
        if not is_active_time:
            return 0
        
        # 買いシグナル
        if (sma_5.iloc[-1] > sma_10.iloc[-1] > sma_20.iloc[-1] and 
            momentum > current_atr * 0.5):
            return 1
        
        # 売りシグナル
        if (sma_5.iloc[-1] < sma_10.iloc[-1] < sma_20.iloc[-1] and 
            momentum < -current_atr * 0.5):
            return -1
        
        return 0
    
    def generate_stable_signal(self, data: pd.DataFrame) -> int:
        """
        安定戦略（長期マクロ戦略）のシグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ（日足推奨）
        
        Returns
        -------
        int
            1: 買い, -1: 売り, 0: シグナルなし
        """
        if len(data) < 200:
            return 0
        
        # カラム名を統一
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # 長期トレンド
        sma_50 = data[close_col].rolling(50).mean()
        sma_100 = data[close_col].rolling(100).mean()
        sma_200 = data[close_col].rolling(200).mean()
        
        # MACD
        exp1 = data[close_col].ewm(span=12, adjust=False).mean()
        exp2 = data[close_col].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        current_price = data[close_col].iloc[-1]
        
        # 買いシグナル（強いトレンド確認）
        if (current_price > sma_50.iloc[-1] > sma_100.iloc[-1] > sma_200.iloc[-1] and
            macd.iloc[-1] > signal.iloc[-1] and
            macd.iloc[-2] <= signal.iloc[-2]):
            return 1
        
        # 売りシグナル（強いトレンド確認）
        if (current_price < sma_50.iloc[-1] < sma_100.iloc[-1] < sma_200.iloc[-1] and
            macd.iloc[-1] < signal.iloc[-1] and
            macd.iloc[-2] >= signal.iloc[-2]):
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
            計算期間
        
        Returns
        -------
        pd.Series
            ATR値
        """
        # カラム名を統一
        high_col = 'High' if 'High' in data.columns else 'high'
        low_col = 'Low' if 'Low' in data.columns else 'low'
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        high = data[high_col]
        low = data[low_col]
        close = data[close_col]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def execute_trade(self, signal: int, strategy_type: str, data: pd.DataFrame) -> Dict:
        """
        取引を実行
        
        Parameters
        ----------
        signal : int
            取引シグナル
        strategy_type : str
            戦略タイプ
        data : pd.DataFrame
            価格データ
        
        Returns
        -------
        Dict
            取引結果
        """
        if signal == 0 or not self.check_risk_limits():
            return {}
        
        # ストップロスと利確の設定
        sl_tp_configs = {
            'core': {'sl': 10, 'tp': 30},      # 1:3のリスクリワード
            'aggressive': {'sl': 5, 'tp': 10},  # 1:2のリスクリワード
            'stable': {'sl': 20, 'tp': 60}      # 1:3のリスクリワード
        }
        
        config = sl_tp_configs.get(strategy_type, {'sl': 10, 'tp': 20})
        lot_size = self.calculate_optimal_lot_size(strategy_type, config['sl'])
        
        # カラム名を統一
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        trade = {
            'timestamp': data.index[-1],
            'strategy': strategy_type,
            'signal': signal,
            'entry_price': data[close_col].iloc[-1],
            'stop_loss': config['sl'],
            'take_profit': config['tp'],
            'lot_size': lot_size,
            'risk_amount': self.current_balance * self.max_risk_per_trade
        }
        
        self.trade_count[strategy_type] += 1
        
        return trade
    
    def update_performance(self, trade_result: Dict):
        """
        パフォーマンスを更新
        
        Parameters
        ----------
        trade_result : Dict
            取引結果
        """
        pnl = trade_result.get('pnl', 0)
        strategy = trade_result.get('strategy', '')
        
        self.daily_pnl += pnl
        self.monthly_pnl += pnl
        self.current_balance += pnl
        
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        if pnl > 0 and strategy:
            self.win_count[strategy] += 1
    
    def get_performance_summary(self) -> Dict:
        """
        パフォーマンスサマリーを取得
        
        Returns
        -------
        Dict
            パフォーマンス指標
        """
        total_trades = sum(self.trade_count.values())
        total_wins = sum(self.win_count.values())
        
        summary = {
            'current_balance': self.current_balance,
            'total_pnl': self.current_balance - self.initial_balance,
            'monthly_pnl': self.monthly_pnl,
            'monthly_target_achievement': (self.monthly_pnl / self.monthly_profit_target) * 100,
            'total_trades': total_trades,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'current_drawdown': self.current_drawdown * 100,
            'scaling_phase': self.scaling_phase,
            'strategy_breakdown': {
                strategy: {
                    'trades': self.trade_count[strategy],
                    'wins': self.win_count[strategy],
                    'win_rate': (self.win_count[strategy] / self.trade_count[strategy] * 100) 
                                if self.trade_count[strategy] > 0 else 0
                }
                for strategy in ['core', 'aggressive', 'stable']
            }
        }
        
        return summary
    
    def adjust_scaling_phase(self):
        """
        実績に基づいてスケーリングフェーズを調整
        """
        # 3ヶ月連続で月間目標の50%以上達成したら次のフェーズへ
        if self.scaling_phase == 'initial' and self.monthly_pnl >= self.monthly_profit_target * 0.5:
            self.scaling_phase = 'growth'
            # ログは外部で記録
        
        elif self.scaling_phase == 'growth' and self.monthly_pnl >= self.monthly_profit_target * 0.75:
            self.scaling_phase = 'stable'
            # ログは外部で記録
    
    def reset_daily_metrics(self):
        """日次メトリクスをリセット"""
        self.daily_pnl = 0
    
    def reset_monthly_metrics(self):
        """月次メトリクスをリセット"""
        self.monthly_pnl = 0
        self.adjust_scaling_phase()