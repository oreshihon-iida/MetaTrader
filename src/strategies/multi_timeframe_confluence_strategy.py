"""
Issue #002: Multi-Timeframe Confluence Strategy
100回煮詰め完了版 - Issue #001教訓完全統合型

主要改良点:
1. Issue #001のシンプル化成功を継承
2. V10.2の成功パラメータを基本設定に採用
3. V11.3の取引生成成功手法を統合
4. 現実的目標設定（月3-8回、勝率45-55%、PF1.2+）
5. 保守的リスク管理（最大2%、V10.2継承）
"""

import pandas as pd
import numpy as np
import talib as ta
from typing import Dict, Optional, Tuple, List
import logging
from datetime import datetime

class MultiTimeframeConfluenceStrategy:
    def __init__(self):
        self.name = "MultiTimeframe_Confluence_v1_Optimized"
        
        # Issue #001教訓: 現実的目標設定
        self.target_monthly_trades = (3, 8)  # V11.3実績月2.6回を参考
        self.target_win_rate = 0.45  # V10.2実績37.5%を保守的に向上
        self.target_profit_factor = 1.2  # V10.2実績1.23を維持
        
        # Issue #001 V10.2成功パラメータ継承
        self.risk_percent = 1.2  # V10.2で実証済み
        self.max_risk_percent = 2.0  # Issue #001で安全確認済み
        
        # Issue #001 V11.3成功設定継承
        self.rsi_period = 14
        self.rsi_upper = 75  # V11.3成功設定
        self.rsi_lower = 25  # V11.3成功設定
        self.adx_period = 14
        self.adx_minimum = 15  # V11.3成功設定
        
        # 100回煮詰め結果: シンプル化された時間軸重み
        self.timeframe_weights = {
            "D1": 0.5,   # 日足優先（Issue #001教訓）
            "4H": 0.4,   # 4時間足主軸
            "1H": 0.1    # 1時間足補助
        }
        
        # 段階的コンフルエンス閾値（Issue #001 0取引問題対策）
        self.confluence_thresholds = {
            "strong": 70,      # 最強シグナル
            "medium": 50,      # 中強度シグナル
            "weak": 30         # 弱シグナル（条件付き）
        }
        
        # キャッシュシステム（Issue #001高速化継承）
        self.trend_cache = {}
        self.cache_timeout = 15  # 分
        
        self.logger = logging.getLogger(self.name)
        
    def simplified_trend_score(self, data: pd.DataFrame, timeframe: str) -> float:
        """
        Issue #001教訓: 複雑化回避、シンプルな3要素トレンドスコア
        V10.2/V11.3で成功した指標のみ使用
        """
        try:
            # 基本移動平均（Issue #001実証済み）
            ema_20 = ta.EMA(data['Close'], timeperiod=20)
            ema_50 = ta.EMA(data['Close'], timeperiod=50)
            sma_200 = ta.SMA(data['Close'], timeperiod=200)
            
            current_price = data['Close'].iloc[-1]
            current_ema_20 = ema_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            current_sma_200 = sma_200.iloc[-1]
            
            # シンプル3要素スコア（100回煮詰め結果）
            score = 0
            
            # 1. 価格位置（200SMA基準）
            if current_price > current_sma_200:
                score += 30
            else:
                score -= 30
                
            # 2. EMAクロス状態
            if current_ema_20 > current_ema_50:
                score += 35
            else:
                score -= 35
                
            # 3. 価格とEMA20の関係
            if current_price > current_ema_20:
                score += 35
            else:
                score -= 35
            
            return score
            
        except Exception as e:
            self.logger.error(f"Trend score calculation error for {timeframe}: {e}")
            return 0
    
    def get_cached_trend_score(self, data: pd.DataFrame, timeframe: str) -> float:
        """Issue #001高速化手法: キャッシュシステム"""
        cache_key = f"{timeframe}_{len(data)}"
        
        if cache_key in self.trend_cache:
            return self.trend_cache[cache_key]
        
        score = self.simplified_trend_score(data, timeframe)
        self.trend_cache[cache_key] = score
        
        # キャッシュサイズ制限
        if len(self.trend_cache) > 100:
            oldest_key = next(iter(self.trend_cache))
            del self.trend_cache[oldest_key]
            
        return score
    
    def calculate_confluence_score(self, d1_data: pd.DataFrame, 
                                 h4_data: pd.DataFrame, 
                                 h1_data: pd.DataFrame) -> float:
        """
        100回煮詰め結果: シンプル化された重み付きコンフルエンススコア
        """
        # 各時間軸のトレンドスコア取得
        d1_score = self.get_cached_trend_score(d1_data, "D1")
        h4_score = self.get_cached_trend_score(h4_data, "4H")
        h1_score = self.get_cached_trend_score(h1_data, "1H")
        
        # 重み付き平均計算
        weighted_score = (
            d1_score * self.timeframe_weights["D1"] +
            h4_score * self.timeframe_weights["4H"] +
            h1_score * self.timeframe_weights["1H"]
        )
        
        return weighted_score
    
    def simple_timeframe_hierarchy_check(self, d1_data: pd.DataFrame, 
                                       h4_data: pd.DataFrame) -> Optional[str]:
        """
        100回煮詰め結果: シンプルな階層チェック
        Issue #001教訓: 複雑なルールより明確な拒否権
        """
        d1_score = self.get_cached_trend_score(d1_data, "D1")
        h4_score = self.get_cached_trend_score(h4_data, "4H")
        
        # 日足中立は取引なし（Issue #001教訓）
        if abs(d1_score) < 20:
            return "NO_TRADE"
        
        # 日足と4時間足の矛盾は取引なし
        if d1_score * h4_score < 0:
            return "NO_TRADE"
        
        # 両方向一致のみエントリー
        if d1_score > 30 and h4_score > 30:
            return "BUY"
        elif d1_score < -30 and h4_score < -30:
            return "SELL"
        else:
            return "NO_TRADE"
    
    def proven_indicators_check(self, data: pd.DataFrame) -> bool:
        """
        Issue #001で実証された指標のみ使用
        V11.3成功設定を継承
        """
        try:
            # RSIフィルター（V11.3成功設定）
            rsi = ta.RSI(data['Close'], timeperiod=self.rsi_period)
            current_rsi = rsi.iloc[-1]
            rsi_ok = self.rsi_lower < current_rsi < self.rsi_upper
            
            if not rsi_ok:
                return False
            
            # ADXフィルター（V11.3成功設定）
            adx = ta.ADX(data['High'], data['Low'], data['Close'], timeperiod=self.adx_period)
            current_adx = adx.iloc[-1]
            adx_ok = current_adx > self.adx_minimum
            
            return adx_ok
            
        except Exception as e:
            self.logger.error(f"Indicator check error: {e}")
            return False
    
    def conservative_position_sizing(self, confluence_score: float, 
                                   account_balance: float,
                                   atr_value: float) -> float:
        """
        Issue #001 V10.2成功パターンを基本とする保守的ポジションサイジング
        """
        # V10.2実証済みベースリスク
        base_risk = self.risk_percent
        
        # コンフルエンススコアによる微調整のみ
        if abs(confluence_score) > 70:
            risk_multiplier = 1.3
        elif abs(confluence_score) > 50:
            risk_multiplier = 1.0
        else:
            risk_multiplier = 0.8
        
        final_risk = base_risk * risk_multiplier
        final_risk = min(final_risk, self.max_risk_percent)  # 安全上限
        
        # ATRベースストップ距離（Issue #001成功手法）
        stop_distance = atr_value * 2.5
        
        # ポジションサイズ計算
        risk_amount = account_balance * (final_risk / 100)
        position_size = risk_amount / stop_distance
        
        return position_size
    
    def generate_signal(self, d1_data: pd.DataFrame, 
                       h4_data: pd.DataFrame, 
                       h1_data: pd.DataFrame) -> Dict:
        """
        100回煮詰め完了: 最終統合シグナル生成
        Issue #001教訓を完全統合
        """
        try:
            # ステップ1: 階層チェック（Issue #001教訓）
            hierarchy_result = self.simple_timeframe_hierarchy_check(d1_data, h4_data)
            
            if hierarchy_result == "NO_TRADE":
                return {
                    "action": "NO_TRADE",
                    "reason": "timeframe_hierarchy_rejection",
                    "confluence_score": 0,
                    "confidence": 0
                }
            
            # ステップ2: 実証済み指標チェック
            if not self.proven_indicators_check(h4_data):
                return {
                    "action": "NO_TRADE", 
                    "reason": "indicators_not_aligned",
                    "confluence_score": 0,
                    "confidence": 0
                }
            
            # ステップ3: コンフルエンススコア計算
            confluence_score = self.calculate_confluence_score(d1_data, h4_data, h1_data)
            
            # ステップ4: 段階的エントリー判定（Issue #001 0取引対策）
            action = "NO_TRADE"
            confidence = 0
            
            if abs(confluence_score) >= self.confluence_thresholds["strong"]:
                action = "BUY" if confluence_score > 0 else "SELL"
                confidence = 0.9
            elif abs(confluence_score) >= self.confluence_thresholds["medium"]:
                action = "BUY" if confluence_score > 0 else "SELL"
                confidence = 0.7
            elif abs(confluence_score) >= self.confluence_thresholds["weak"]:
                # 弱シグナルは追加条件付き
                rsi = ta.RSI(h4_data['Close'], timeperiod=14)
                if 30 < rsi.iloc[-1] < 70:  # 中立RSI時のみ
                    action = "BUY" if confluence_score > 0 else "SELL"
                    confidence = 0.5
            
            # ステップ5: ポジションサイジング計算
            atr = ta.ATR(h4_data['High'], h4_data['Low'], h4_data['Close'], timeperiod=14)
            position_size = 0
            
            if action != "NO_TRADE":
                position_size = self.conservative_position_sizing(
                    confluence_score, 3000000, atr.iloc[-1]  # 300万円ベース
                )
            
            return {
                "action": action,
                "confluence_score": confluence_score,
                "confidence": confidence,
                "position_size": position_size,
                "stop_loss": atr.iloc[-1] * 2.5,
                "take_profit": atr.iloc[-1] * 4.0,  # 1:1.6 R/R比
                "reason": f"confluence_{abs(confluence_score):.1f}",
                "timeframe_scores": {
                    "D1": self.get_cached_trend_score(d1_data, "D1"),
                    "4H": self.get_cached_trend_score(h4_data, "4H"),
                    "1H": self.get_cached_trend_score(h1_data, "1H")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
            return {
                "action": "NO_TRADE",
                "reason": f"error_{str(e)}",
                "confluence_score": 0,
                "confidence": 0
            }
    
    def get_strategy_info(self) -> Dict:
        """戦略情報の取得"""
        return {
            "name": self.name,
            "version": "1.0.0_Issue001_Integrated",
            "target_monthly_trades": self.target_monthly_trades,
            "target_win_rate": self.target_win_rate,
            "target_profit_factor": self.target_profit_factor,
            "max_risk_percent": self.max_risk_percent,
            "timeframes": ["D1", "4H", "1H"],
            "confluence_thresholds": self.confluence_thresholds,
            "issue_001_integration": {
                "v10_2_success_params": "risk_1.2%, conservative_sizing",
                "v11_3_success_params": "rsi_75/25, adx_15+",
                "simplification_principle": "3_elements_only",
                "realistic_targets": "monthly_3-8_trades"
            }
        }


if __name__ == "__main__":
    # 戦略インスタンス作成
    strategy = MultiTimeframeConfluenceStrategy()
    
    # 戦略情報表示
    info = strategy.get_strategy_info()
    print("=" * 60)
    print(f"🎯 {info['name']} - Issue #001完全統合版")
    print("=" * 60)
    print(f"月間取引目標: {info['target_monthly_trades'][0]}-{info['target_monthly_trades'][1]}回")
    print(f"目標勝率: {info['target_win_rate']*100:.1f}%")
    print(f"目標PF: {info['target_profit_factor']}")
    print(f"最大リスク: {info['max_risk_percent']}%")
    print("\nIssue #001統合要素:")
    for key, value in info['issue_001_integration'].items():
        print(f"  {key}: {value}")
    print("=" * 60)
    print("100回煮詰め完了 - 実装準備完了")