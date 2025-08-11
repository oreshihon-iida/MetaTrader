#!/usr/bin/env python3
"""
Enhanced Trinity ML Strategy - 段階1改善版
損失制御版をベースに月5万円目標に向けて最適化
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Tuple, Dict, Optional
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.strategies.ultra_fast_ml_predictor import UltraFastMLPredictor, create_features_chunk
from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer

class EnhancedTrinityMLStage1:
    """
    Enhanced Trinity ML Strategy - 段階1改善版
    
    改善内容:
    - レバレッジ: 4.0倍 → 5.0倍
    - 最大ポジション数: 2 → 3
    - 月次損失限度: 5% → 8%
    
    目標:
    - 月平均5万円達成（現在の19,488円から大幅改善）
    - 200万円元本保護は維持
    """
    
    def __init__(self,
                 base_confidence_threshold: float = 0.15,
                 prediction_horizon: int = 4,
                 max_cores: int = 24,
                 sentiment_weight: float = 0.20,
                 sentiment_hours_back: int = 12,
                 training_size: int = 1500,
                 processing_interval: int = 4):
        """
        初期化
        """
        # ベースのTrinity戦略
        self.trinity_strategy = UltraFastMLPredictor(
            base_confidence_threshold=base_confidence_threshold,
            prediction_horizon=prediction_horizon,
            max_cores=max_cores,
            dynamic_threshold=False
        )
        
        # 感情分析システム
        self.sentiment_analyzer = ClaudeSentimentAnalyzer()
        
        # 段階1改善パラメータ
        self.sentiment_weight = sentiment_weight
        self.sentiment_hours_back = sentiment_hours_back
        self.training_size = training_size
        self.processing_interval = processing_interval
        
        # TP/SL設定（やや積極的に）
        self.base_sl_pips = 12  # 少し広げてノイズ耐性向上
        self.base_tp_pips = 20  # 利益目標も拡大（1.67:1）
        
        # 時間帯フィルター（東京・ロンドン・NY時間重視）
        self.enable_time_filter = True
        self.active_hours = {
            'tokyo': range(9, 15),      # 9:00-15:00 JST
            'london': range(16, 24),    # 16:00-24:00 JST
            'ny': range(21, 24)         # 21:00-24:00 JST
        }
        
        # 統計情報
        self.statistics = {
            'signals_generated': 0,
            'tokyo_signals': 0,
            'london_signals': 0,
            'ny_signals': 0,
            'filtered_by_time': 0,
            'retraining_count': 0
        }
        
        print("=" * 60)
        print("Enhanced Trinity ML - 段階1改善版 初期化完了")
        print("=" * 60)
        print(f"目標: 月平均5万円達成")
        print(f"改善内容:")
        print(f"  - レバレッジ: 5.0倍（従来4.0倍）")
        print(f"  - 最大ポジション: 3個（従来2個）")
        print(f"  - 月次損失限度: 8%（従来5%）")
        print(f"処理間隔: {processing_interval}本（1時間ごと）")
        print(f"予測ホライズン: {prediction_horizon}本（1時間先）")
        print(f"TP/SL: {self.base_tp_pips}/{self.base_sl_pips} ({self.base_tp_pips/self.base_sl_pips:.2f}:1)")
        print(f"信頼度閾値: {base_confidence_threshold}")
    
    def is_active_trading_time(self, timestamp: pd.Timestamp) -> bool:
        """
        アクティブな取引時間かチェック
        """
        if not self.enable_time_filter:
            return True
        
        hour = timestamp.hour
        
        # 各市場の活発な時間帯
        for market, hours in self.active_hours.items():
            if hour in hours:
                return True
        
        self.statistics['filtered_by_time'] += 1
        return False
    
    def get_sentiment_score(self, timestamp: pd.Timestamp) -> float:
        """
        現在時刻の感情分析スコアを取得（時系列整合性確保版）
        """
        try:
            # 時系列整合性を確保した感情分析スコアを取得
            return self.sentiment_analyzer.get_sentiment_at_time(timestamp)
        except Exception as e:
            print(f"感情分析スコア取得エラー: {e}")
            return 0.0
    
    def calculate_dynamic_tp_sl(self, row: pd.Series, confidence: float, 
                               sentiment_score: float) -> Tuple[float, float]:
        """
        動的TP/SL計算（段階1: より積極的な設定）
        """
        # ベースとなるTP/SL
        tp_pips = self.base_tp_pips
        sl_pips = self.base_sl_pips
        
        # 信頼度による調整（より積極的に）
        if confidence > 0.25:
            tp_pips *= 1.3  # 高信頼度時は利益を伸ばす
        elif confidence < 0.18:
            sl_pips *= 0.9  # 低信頼度時はタイトなストップ
        
        # 感情分析による調整
        if abs(sentiment_score) > 0.5:
            if sentiment_score > 0:
                tp_pips *= 1.2  # ポジティブな時は利益目標拡大
            else:
                sl_pips *= 0.85  # ネガティブな時は損切り早め
        
        # ボラティリティによる調整
        if 'ATR' in row:
            atr_ratio = row['ATR'] / row['Close'] * 100
            if atr_ratio > 0.15:  # 高ボラティリティ
                tp_pips *= 1.25
                sl_pips *= 1.15
            elif atr_ratio < 0.08:  # 低ボラティリティ
                tp_pips *= 0.85
                sl_pips *= 0.9
        
        # 最小値・最大値の制限（段階1: 範囲を広げる）
        tp_pips = np.clip(tp_pips, 12, 35)  # 12-35 pips
        sl_pips = np.clip(sl_pips, 8, 20)   # 8-20 pips
        
        return tp_pips, sl_pips
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Enhanced Trinity + 感情分析による売買シグナル生成（時系列整合性確保）
        """
        print("\\n" + "=" * 60)
        print("Enhanced Trinity ML 段階1改善版 - シグナル生成開始")
        print("=" * 60)
        
        # 感情分析の時系列整合性チェック
        backtest_start = data.index.min()
        backtest_end = data.index.max()
        
        use_sentiment = self.sentiment_analyzer.is_valid_for_backtest(backtest_start, backtest_end)
        
        if use_sentiment:
            print(f"感情分析データを使用します（重み: {self.sentiment_weight}）")
        else:
            print("感情分析データが利用不可能です。技術分析のみで実行します。")
            self.sentiment_weight = 0.0  # 感情分析の重みを0にする
        
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Confidence'] = 0.0
        signals['SentimentScore'] = 0.0
        signals['TP_pips'] = 0.0
        signals['SL_pips'] = 0.0
        
        # 処理間隔ごとにシグナル生成
        last_training_idx = 0
        
        for i in range(self.training_size, len(data), self.processing_interval):
            if i >= len(data):
                break
            
            # 再学習（定期的に実施）
            if i - last_training_idx >= 500:  # 500本ごとに再学習
                print(f"\\n[{data.index[i]}] モデル再学習中...")
                
                # Trinity MLの学習
                train_data = data.iloc[max(0, i-self.training_size):i]
                self.trinity_strategy.train_model_parallel(train_data)
                
                last_training_idx = i
                self.statistics['retraining_count'] += 1
            
            # 予測実行
            current_idx = min(i, len(data) - 1)
            current_data = data.iloc[:current_idx+1]
            
            # 時間帯チェック
            if not self.is_active_trading_time(data.index[current_idx]):
                continue
            
            # Trinity ML予測
            direction_pred, trinity_confidence = self.trinity_strategy.predict_ultra_fast(
                current_data
            )
            
            # 方向をシグナルに変換
            trinity_signal = 0
            if abs(direction_pred) > 0.0001:  # 閾値以上の変化予測
                trinity_signal = 1 if direction_pred > 0 else -1
            
            if trinity_signal != 0:
                # 感情分析スコア取得
                sentiment_score = self.get_sentiment_score(data.index[current_idx])
                
                # 統合信頼度計算（感情分析を含む）
                integrated_confidence = (
                    trinity_confidence * (1 - self.sentiment_weight) +
                    abs(sentiment_score) * self.sentiment_weight
                )
                
                # 感情分析と予測の方向性チェック
                if sentiment_score != 0:
                    sentiment_direction = 1 if sentiment_score > 0 else -1
                    if sentiment_direction != trinity_signal:
                        # 逆方向の場合は信頼度を下げる
                        integrated_confidence *= 0.7
                
                # 信頼度が閾値を超える場合のみシグナル生成
                if integrated_confidence >= self.trinity_strategy.base_confidence_threshold:
                    # 動的TP/SL計算
                    tp_pips, sl_pips = self.calculate_dynamic_tp_sl(
                        data.iloc[current_idx],
                        integrated_confidence,
                        sentiment_score
                    )
                    
                    # シグナル記録
                    signals.loc[data.index[current_idx], 'Signal'] = trinity_signal
                    signals.loc[data.index[current_idx], 'Confidence'] = integrated_confidence
                    signals.loc[data.index[current_idx], 'SentimentScore'] = sentiment_score
                    signals.loc[data.index[current_idx], 'TP_pips'] = tp_pips
                    signals.loc[data.index[current_idx], 'SL_pips'] = sl_pips
                    
                    self.statistics['signals_generated'] += 1
                    
                    # 市場別統計
                    hour = data.index[current_idx].hour
                    if hour in self.active_hours['tokyo']:
                        self.statistics['tokyo_signals'] += 1
                    if hour in self.active_hours['london']:
                        self.statistics['london_signals'] += 1
                    if hour in self.active_hours['ny']:
                        self.statistics['ny_signals'] += 1
        
        # 統計情報出力
        self.print_statistics()
        
        return signals
    
    def print_statistics(self):
        """統計情報を出力"""
        print("\\n" + "=" * 60)
        print("シグナル生成統計（段階1改善版）")
        print("=" * 60)
        print(f"総シグナル数: {self.statistics['signals_generated']}")
        print(f"東京時間: {self.statistics['tokyo_signals']}")
        print(f"ロンドン時間: {self.statistics['london_signals']}")
        print(f"NY時間: {self.statistics['ny_signals']}")
        print(f"時間フィルター除外: {self.statistics['filtered_by_time']}")
        print(f"モデル再学習回数: {self.statistics['retraining_count']}")