#!/usr/bin/env python3
"""
Enhanced Trinity ML Strategy - Stage 1 Improved
段階1改善版: 目標月5万円達成に向けた調整
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Tuple, Dict
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.strategies.ultra_fast_ml_predictor import UltraFastMLPredictor
from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer

class EnhancedTrinityMLStage1Improved:
    """
    Enhanced Trinity ML 段階1改善版
    
    前回の段階1からの改善:
    - 信頼度閾値: 0.15 → 0.10（取引頻度大幅向上）
    - TP/SL: 20/12 → 15/8（早期利確・損切り）
    - ポジションサイズ: 固定 → 動的調整
    - 時間フィルター: より柔軟に
    - 感情分析: より積極活用
    
    目標: 月平均5万円達成（前回-4,689円から改善）
    """
    
    def __init__(self,
                 base_confidence_threshold: float = 0.10,  # 0.15 → 0.10
                 prediction_horizon: int = 4,
                 max_cores: int = 24,
                 sentiment_weight: float = 0.25,  # 0.20 → 0.25
                 sentiment_hours_back: int = 12,
                 training_size: int = 1500,
                 processing_interval: int = 4):
        """
        段階1改善版初期化
        """
        
        print("=== Enhanced Trinity ML 段階1改善版 ===")
        print("前回段階1の問題点改善:")
        print("  - 取引頻度不足（4取引のみ）→ 信頼度閾値緩和")
        print("  - 全敗（0%勝率）→ TP/SL比率改善")
        print("  - 固定サイジング → 動的調整導入")
        print("改善内容:")
        print("  - 信頼度閾値: 0.15 → 0.10（取引機会大幅拡大）")
        print("  - TP/SL: 20/12 → 15/8（1.9:1 → 1.9:1、早期決済）")
        print("  - ポジションサイズ: 動的調整導入")
        print("  - 感情分析重み: 20% → 25%")
        print("  - 目標: 月平均5万円達成")
        
        # Ultra Fast ML Predictor初期化
        self.ml_predictor = UltraFastMLPredictor(
            base_confidence_threshold=base_confidence_threshold,
            prediction_horizon=prediction_horizon,
            max_cores=max_cores,
            dynamic_threshold=False  # 段階1では固定閾値
        )
        
        # 感情分析システム
        self.sentiment_analyzer = ClaudeSentimentAnalyzer()
        
        # パラメータ
        self.base_confidence_threshold = base_confidence_threshold
        self.sentiment_weight = sentiment_weight
        self.sentiment_hours_back = sentiment_hours_back
        self.training_size = training_size
        self.processing_interval = processing_interval
        
        # 段階1改善版専用設定
        self.improved_tp_pips = 15  # 20 → 15（早期利確）
        self.improved_sl_pips = 8   # 12 → 8（早期損切り）
        self.max_positions = 3      # 最大3ポジション維持
        
        # 統計情報
        self.signals_generated = 0
        self.sentiment_enhanced_signals = 0
        
        print(f"\\n初期化完了:")
        print(f"  信頼度閾値: {base_confidence_threshold}")
        print(f"  TP/SL: {self.improved_tp_pips}/{self.improved_sl_pips}")
        print(f"  感情重み: {sentiment_weight}")
    
    def calculate_dynamic_position_size(self, confidence: float, max_lot_size: float,
                                      sentiment_boost: float = 0.0) -> float:
        """
        動的ポジションサイズ計算（段階1改善版）
        """
        # ベースサイズ（控えめ）
        base_size = 0.3  # 最小ベース
        
        # 信頼度に基づく調整
        confidence_multiplier = 1.0 + (confidence - 0.10) * 2.0  # 0.10超過分を2倍で計算
        
        # 感情分析ブースト
        sentiment_multiplier = 1.0 + max(0, sentiment_boost) * 1.5
        
        # 計算
        desired_size = base_size * confidence_multiplier * sentiment_multiplier
        
        # 制限適用
        final_size = min(desired_size, max_lot_size, 1.2)  # 最大1.2ロット
        
        return max(0.01, final_size)  # 最小0.01ロット
    
    def enhanced_tp_sl_calculation(self, confidence: float, sentiment_score: float,
                                 market_volatility: float = 0.1) -> Tuple[float, float]:
        """
        改善版TP/SL計算
        """
        tp_base = self.improved_tp_pips
        sl_base = self.improved_sl_pips
        
        # 信頼度による調整
        if confidence > 0.15:
            tp_base *= 1.2  # 高信頼度時は利益を伸ばす
        elif confidence < 0.12:
            tp_base *= 0.9  # 低信頼度時は控えめ
            sl_base *= 0.9
        
        # 感情分析による調整
        if abs(sentiment_score) > 0.3:
            if sentiment_score > 0:  # ポジティブ感情
                tp_base *= 1.1
            else:  # ネガティブ感情
                sl_base *= 0.9  # 早期損切り
        
        # ボラティリティ調整
        if market_volatility > 0.15:  # 高ボラティリティ
            tp_base *= 1.3
            sl_base *= 1.2
        elif market_volatility < 0.08:  # 低ボラティリティ
            tp_base *= 0.8
            sl_base *= 0.8
        
        # 最終制限
        tp_pips = np.clip(tp_base, 10, 25)  # 10-25 pips
        sl_pips = np.clip(sl_base, 5, 15)   # 5-15 pips
        
        return tp_pips, sl_pips
    
    def is_trading_time_improved(self, timestamp: pd.Timestamp) -> bool:
        """
        改善版取引時間フィルター（より柔軟）
        """
        hour = timestamp.hour
        
        # より多くの時間帯を許可（前回より緩い）
        active_hours = [
            range(8, 12),   # 東京朝
            range(9, 16),   # 東京全般
            range(15, 19),  # ロンドン開始
            range(16, 24),  # ロンドン・NY
            range(21, 24),  # NY主要時間
        ]
        
        for hours in active_hours:
            if hour in hours:
                return True
        
        return False
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        段階1改善版シグナル生成
        """
        print("\\n" + "=" * 60)
        print("Enhanced Trinity ML 段階1改善版 - シグナル生成開始")
        print("=" * 60)
        print("改善ポイント:")
        print("  - 信頼度閾値を0.10に緩和（取引頻度向上）")
        print("  - 動的ポジションサイジング導入")
        print("  - TP/SL早期決済で勝率改善狙い")
        
        # 感情分析の時系列整合性チェック
        backtest_start = data.index.min()
        backtest_end = data.index.max()
        
        use_sentiment = self.sentiment_analyzer.is_valid_for_backtest(backtest_start, backtest_end)
        
        if use_sentiment:
            print(f"感情分析データ使用（重み: {self.sentiment_weight}）")
        else:
            print("感情分析無効 - 技術分析のみ")
            self.sentiment_weight = 0.0
        
        # シグナルDataFrame準備
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Confidence'] = 0.0
        signals['SentimentScore'] = 0.0
        signals['TP_pips'] = 0.0
        signals['SL_pips'] = 0.0
        signals['Position_Size'] = 0.0
        
        # 学習開始
        last_training = 0
        
        for i in range(self.training_size, len(data), self.processing_interval):
            if i >= len(data):
                break
                
            # 定期再学習
            if i - last_training >= 500:  # 500本ごと
                print(f"[{data.index[i]}] モデル再学習...")
                train_data = data.iloc[max(0, i-self.training_size):i]
                self.ml_predictor.train_model_parallel(train_data)
                last_training = i
            
            current_data = data.iloc[:i+1]
            current_time = data.index[i]
            
            # 改善版時間フィルター
            if not self.is_trading_time_improved(current_time):
                continue
            
            # ML予測
            try:
                prediction = self.ml_predictor.predict_ultra_fast(current_data.tail(200))
                
                if prediction is None:
                    continue
                
                # 感情分析（時系列整合性確保）
                sentiment_score = 0.0
                sentiment_boost = 0.0
                
                if use_sentiment:
                    sentiment_features = self.sentiment_analyzer.get_recent_sentiment_features(
                        reference_time=current_time,
                        hours_back=self.sentiment_hours_back
                    )
                    sentiment_score = sentiment_features.get('news_sentiment', 0.0)
                    sentiment_boost = abs(sentiment_score) * self.sentiment_weight
                
                # 統合信頼度計算
                base_confidence = prediction.get('confidence', 0.0)
                integrated_confidence = base_confidence + sentiment_boost
                
                # 改善版シグナル判定（緩い閾値）
                if integrated_confidence >= self.base_confidence_threshold:
                    direction = prediction.get('direction', 0)
                    signal = 1 if direction > 0 else -1 if direction < 0 else 0
                    
                    if signal != 0:
                        # 改善版TP/SL計算
                        market_vol = data.iloc[i-20:i]['Close'].std() / data.iloc[i]['Close'] if i >= 20 else 0.1
                        tp_pips, sl_pips = self.enhanced_tp_sl_calculation(
                            integrated_confidence, sentiment_score, market_vol
                        )
                        
                        # シグナル記録
                        signals.loc[current_time, 'Signal'] = signal
                        signals.loc[current_time, 'Confidence'] = integrated_confidence
                        signals.loc[current_time, 'SentimentScore'] = sentiment_score
                        signals.loc[current_time, 'TP_pips'] = tp_pips
                        signals.loc[current_time, 'SL_pips'] = sl_pips
                        
                        self.signals_generated += 1
                        
                        if sentiment_boost > 0.05:
                            self.sentiment_enhanced_signals += 1
                
            except Exception as e:
                if i % 1000 == 0:  # 1000回に1回エラー表示
                    print(f"  予測エラー: {e}")
                continue
        
        print(f"\\n段階1改善版シグナル生成完了:")
        print(f"  生成シグナル数: {self.signals_generated}")
        print(f"  感情強化シグナル: {self.sentiment_enhanced_signals}")
        print(f"  改善率: {self.sentiment_enhanced_signals/max(1,self.signals_generated)*100:.1f}%")
        
        return signals
    
    def get_improvement_statistics(self) -> Dict:
        """
        段階1改善版統計
        """
        return {
            'version': 'Stage1_Improved',
            'target_monthly_profit': 50000,
            'previous_monthly_result': -4689,
            'signals_generated': self.signals_generated,
            'sentiment_enhanced_signals': self.sentiment_enhanced_signals,
            'confidence_threshold': self.base_confidence_threshold,
            'tp_sl_ratio': self.improved_tp_pips / self.improved_sl_pips,
            'improvements': [
                'confidence_threshold_relaxed',
                'dynamic_position_sizing',
                'improved_tp_sl',
                'flexible_time_filter',
                'enhanced_sentiment_weight'
            ]
        }


def create_stage1_improved_strategy():
    """
    段階1改善版戦略作成
    """
    return EnhancedTrinityMLStage1Improved(
        base_confidence_threshold=0.10,
        prediction_horizon=4,
        max_cores=24,
        sentiment_weight=0.25,
        sentiment_hours_back=12,
        training_size=1500,
        processing_interval=4
    )


if __name__ == "__main__":
    print("Enhanced Trinity ML Stage 1 Improved Strategy")
    print("段階1改善版: 前回-4,689円/月から月5万円目標達成へ")
    
    strategy = create_stage1_improved_strategy()
    print("段階1改善版初期化完了")