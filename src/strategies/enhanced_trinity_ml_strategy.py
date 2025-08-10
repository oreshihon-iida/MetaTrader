#!/usr/bin/env python3
"""
Enhanced Trinity ML Strategy with Claude Sentiment Analysis
Claude感情分析統合版Trinity戦略
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

class EnhancedTrinityMLStrategy:
    """
    Claude感情分析統合版Trinity ML戦略
    
    特徴:
    - 既存のTrinity MLに感情分析を統合
    - Claude Codeベースの無料感情分析
    - 重み付き加算式の進化版
    """
    
    def __init__(self,
                 base_confidence_threshold: float = 0.18,
                 prediction_horizon: int = 8,
                 max_cores: int = 24,
                 sentiment_weight: float = 0.25,  # 感情分析の重み
                 sentiment_hours_back: int = 24):  # 感情分析の時間範囲
        """
        初期化
        """
        # ベースのTrinity戦略
        self.trinity_strategy = UltraFastMLPredictor(
            base_confidence_threshold=base_confidence_threshold,
            prediction_horizon=prediction_horizon,
            max_cores=max_cores,
            dynamic_threshold=False  # 感情分析版では動的閾値は無効
        )
        
        # 感情分析システム
        self.sentiment_analyzer = ClaudeSentimentAnalyzer()
        
        # 感情分析関連パラメータ
        self.sentiment_weight = sentiment_weight
        self.sentiment_hours_back = sentiment_hours_back
        
        # 統計情報
        self.sentiment_signals_count = 0
        self.trinity_signals_count = 0
        
        print(f"Enhanced Trinity ML初期化完了")
        print(f"感情分析重み: {sentiment_weight:.2f}")
        print(f"感情分析時間範囲: {sentiment_hours_back}時間")
    
    def create_enhanced_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        感情分析統合版特徴量生成
        """
        # ベースのTrinity特徴量
        base_features = self.trinity_strategy.create_features_parallel(data)
        
        # 感情分析特徴量
        sentiment_features = self.sentiment_analyzer.get_recent_sentiment_features(
            hours_back=self.sentiment_hours_back
        )
        
        # 感情特徴量をDataFrameに追加
        for feature_name, value in sentiment_features.items():
            base_features[feature_name] = value
        
        return base_features
    
    def train_enhanced_model(self, data: pd.DataFrame):
        """
        感情分析統合版モデル学習
        """
        print("Enhanced Trinity学習開始...")
        
        # 感情分析特徴量統合
        enhanced_features = self.create_enhanced_features(data)
        
        # ベース戦略の学習（特徴量拡張版）
        self.trinity_strategy.train_model_parallel(data)
        
        print("Enhanced Trinity学習完了")
    
    def calculate_enhanced_confidence(self, 
                                    base_confidence: float,
                                    sentiment_features: Dict[str, float]) -> Tuple[float, Dict]:
        """
        感情分析統合版信頼度計算
        
        従来のTrinity公式:
        confidence = 0.4×accuracy + 0.4×training + 0.2×strength
        
        Enhanced Trinity公式:
        confidence = 0.3×accuracy + 0.3×training + 0.15×strength + 0.25×sentiment
        """
        
        # ベース信頼度の分解（逆算）
        accuracy = self.trinity_strategy.prediction_accuracy
        training_score = self.trinity_strategy.training_score
        
        # 予測強度を推定（簡易的）
        estimated_strength = (base_confidence - 0.4 * accuracy - 0.4 * training_score) / 0.2
        estimated_strength = max(0, min(1, estimated_strength))
        
        # 感情分析複合スコア計算
        sentiment_composite = self._calculate_sentiment_composite(sentiment_features)
        
        # Enhanced Trinity公式
        enhanced_confidence = (
            0.30 * accuracy +
            0.30 * training_score +
            0.15 * estimated_strength +
            0.25 * sentiment_composite
        )
        
        # 感情調整の詳細
        sentiment_adjustment = {
            'news_sentiment': sentiment_features.get('news_sentiment', 0.0),
            'usd_strength': sentiment_features.get('usd_strength', 0.0),
            'market_fear': sentiment_features.get('market_fear', 0.0),
            'sentiment_confidence': sentiment_features.get('sentiment_confidence', 0.5),
            'composite_score': sentiment_composite,
            'sentiment_boost': sentiment_composite * self.sentiment_weight
        }
        
        return enhanced_confidence, sentiment_adjustment
    
    def _calculate_sentiment_composite(self, sentiment_features: Dict[str, float]) -> float:
        """
        感情分析複合スコア計算
        """
        news_sentiment = sentiment_features.get('news_sentiment', 0.0)
        usd_strength = sentiment_features.get('usd_strength', 0.0)
        market_fear = sentiment_features.get('market_fear', 0.0)
        sentiment_confidence = sentiment_features.get('sentiment_confidence', 0.5)
        sentiment_count = sentiment_features.get('sentiment_count', 0)
        
        # 基本感情スコア（USD/JPYに特化）
        usdjpy_sentiment = (news_sentiment + usd_strength - market_fear) / 3.0
        
        # 信頼度による重み付け
        weighted_sentiment = usdjpy_sentiment * sentiment_confidence
        
        # データ不足時の減衰
        data_penalty = 1.0 if sentiment_count > 0 else 0.0
        
        # 正規化（-1.0〜1.0を0.0〜1.0に変換）
        normalized_score = (weighted_sentiment + 1.0) / 2.0
        
        return max(0.0, min(1.0, normalized_score * data_penalty))
    
    def generate_enhanced_signal(self, data: pd.DataFrame) -> Tuple[int, Dict]:
        """
        感情分析統合版シグナル生成
        """
        # ベースのTrinityシグナル
        trinity_signal, trinity_analysis = self.trinity_strategy.generate_ultra_fast_signal(data)
        
        # 感情分析特徴量取得
        sentiment_features = self.sentiment_analyzer.get_recent_sentiment_features(
            hours_back=self.sentiment_hours_back
        )
        
        # Enhanced信頼度計算
        base_confidence = trinity_analysis.get('confidence', 0.0)
        enhanced_confidence, sentiment_adjustment = self.calculate_enhanced_confidence(
            base_confidence, sentiment_features
        )
        
        # 統合分析結果
        enhanced_analysis = {
            **trinity_analysis,
            'enhanced_confidence': enhanced_confidence,
            'base_confidence': base_confidence,
            'sentiment_features': sentiment_features,
            'sentiment_adjustment': sentiment_adjustment,
            'strategy_type': 'Enhanced_Trinity_ML'
        }
        
        # シグナル決定（Enhanced信頼度ベース）
        if enhanced_confidence < self.trinity_strategy.base_confidence_threshold:
            final_signal = 0
            enhanced_analysis['reason'] = 'enhanced_low_confidence'
        elif trinity_signal == 0:
            final_signal = 0
            enhanced_analysis['reason'] = 'trinity_no_signal'
        else:
            final_signal = trinity_signal
            enhanced_analysis['reason'] = 'enhanced_signal_confirmed'
        
        # 統計更新
        if final_signal != 0:
            if sentiment_adjustment['sentiment_boost'] > 0.05:
                self.sentiment_signals_count += 1
            else:
                self.trinity_signals_count += 1
        
        return final_signal, enhanced_analysis
    
    def get_strategy_statistics(self) -> Dict:
        """
        Enhanced Trinity戦略統計
        """
        sentiment_summary = self.sentiment_analyzer.get_sentiment_summary()
        
        total_signals = self.sentiment_signals_count + self.trinity_signals_count
        
        stats = {
            'total_signals': total_signals,
            'sentiment_driven_signals': self.sentiment_signals_count,
            'trinity_driven_signals': self.trinity_signals_count,
            'sentiment_signal_ratio': (self.sentiment_signals_count / total_signals 
                                     if total_signals > 0 else 0.0),
            'sentiment_analyses_count': sentiment_summary.get('total_analyses', 0),
            'recent_sentiment': sentiment_summary.get('recent_sentiment', 0.0),
            'recent_usd_strength': sentiment_summary.get('recent_usd_strength', 0.0),
            'avg_sentiment': sentiment_summary.get('avg_sentiment', 0.0)
        }
        
        return stats
    
    def add_news_sentiment(self, news_text: str, analysis_result: Dict = None):
        """
        ニュース感情分析を追加（手動入力対応）
        """
        if analysis_result is None:
            # 対話式入力
            print(f"\n📰 ニュース感情分析")
            print(f"ニュース: {news_text}")
            analysis_result = self.sentiment_analyzer.interactive_sentiment_input(news_text)
        
        if analysis_result:
            success = self.sentiment_analyzer.add_sentiment_analysis(news_text, analysis_result)
            if success:
                print("✅ 感情分析を追加しました")
                return True
            else:
                print("❌ 感情分析の追加に失敗しました")
                return False
        return False
    
    def display_sentiment_prompt(self, news_text: str):
        """
        Claude Code用プロンプトを表示
        """
        self.sentiment_analyzer.print_analysis_prompt(news_text)
    
    def get_enhanced_features_info(self) -> Dict:
        """
        Enhanced特徴量の情報
        """
        sentiment_features = self.sentiment_analyzer.get_recent_sentiment_features()
        
        return {
            'base_features_count': len(self.trinity_strategy.feature_names) if hasattr(self.trinity_strategy, 'feature_names') else 11,
            'sentiment_features_count': len(sentiment_features),
            'total_features_count': len(self.trinity_strategy.feature_names) + len(sentiment_features) if hasattr(self.trinity_strategy, 'feature_names') else 11 + len(sentiment_features),
            'sentiment_features': sentiment_features,
            'sentiment_weight': self.sentiment_weight
        }


def enhanced_trinity_ml_wrapper(data: pd.DataFrame, executor, metadata: Dict = None):
    """
    Enhanced Trinity ML戦略のラッパー
    """
    
    strategy = EnhancedTrinityMLStrategy(
        base_confidence_threshold=0.18,
        prediction_horizon=8,
        max_cores=24,
        sentiment_weight=0.25,
        sentiment_hours_back=24
    )
    
    print(f"Enhanced Trinity ML戦略 - Claude感情分析統合版")
    print("新機能: Trinity ML + Claude感情分析 + Enhanced信頼度計算")
    
    # 学習データサイズを最適化
    training_size = min(2000, len(data) // 4)
    if len(data) > training_size:
        training_data = data.iloc[:training_size]
        strategy.train_enhanced_model(training_data)
    else:
        print("学習データ不足")
        return
    
    signals_generated = 0
    trades_executed = 0
    
    print(f"\nEnhanced Trinity バックテスト開始 ({training_size} - {len(data)})")
    
    # バックテストループ
    for i in range(training_size, len(data), 50):
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        price_col = 'Close' if 'Close' in data.columns else 'close'
        current_price = data[price_col].iloc[i]
        
        # 進捗表示
        if i % 2000 == 0:
            progress = (i - training_size) / (len(data) - training_size) * 100
            print(f"  進捗: {progress:.1f}% ({i}/{len(data)}) - {trades_executed}取引実行済み")
        
        # ポジション管理
        executor.check_positions(current_price, current_time)
        
        # 定期再学習
        if (i - training_size) % 5000 == 0 and i > training_size:
            print(f"Enhanced Trinity再学習: {current_time}")
            recent_data = data.iloc[max(0, i-1500):i+1]
            strategy.train_enhanced_model(recent_data)
        
        # Enhanced シグナル生成
        current_positions = len(executor.positions) if hasattr(executor, 'positions') else 0
        if current_positions < 3:
            signal, analysis = strategy.generate_enhanced_signal(current_data)
            
            if signal != 0:
                signals_generated += 1
                
                # ポジションサイズ（Enhanced信頼度ベース）
                enhanced_confidence = analysis['enhanced_confidence']
                lot_size = min(1.0 + enhanced_confidence, 2.0)
                
                # TP/SL
                tp_pips = 20
                sl_pips = 12
                
                # 取引実行
                position = executor.open_position(
                    signal=signal,
                    price=current_price,
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips,
                    timestamp=current_time,
                    strategy='Enhanced_Trinity_ML'
                )
                
                if position:
                    trades_executed += 1
                    sentiment_boost = analysis['sentiment_adjustment']['sentiment_boost']
                    print(f"Enhanced取引{trades_executed}: {['SELL','BUY'][signal==1]} @ {current_price:.3f} "
                          f"Lot:{lot_size:.2f} Enhanced信頼度:{enhanced_confidence:.3f} "
                          f"感情ブースト:{sentiment_boost:+.3f}")
        
        # 資産更新
        executor.update_equity(current_price)
    
    # 結果表示
    final_stats = executor.get_statistics()
    strategy_stats = strategy.get_strategy_statistics()
    
    print(f"\n=== Enhanced Trinity ML戦略 結果 ===")
    print(f"シグナル生成数: {signals_generated}")
    print(f"実行取引数: {trades_executed}")
    print(f"最終損益: {final_stats['total_pnl']:,.0f}円")
    print(f"感情駆動シグナル: {strategy_stats['sentiment_driven_signals']}")
    print(f"Trinity駆動シグナル: {strategy_stats['trinity_driven_signals']}")
    print(f"感情分析数: {strategy_stats['sentiment_analyses_count']}")
    
    if trades_executed > 0:
        print(f"勝率: {final_stats['win_rate']:.1f}%")
        print(f"PF: {final_stats.get('profit_factor', 0):.2f}")
        
        # 月平均利益推定
        months = len(data) / (30 * 24 * 4)
        monthly_avg = final_stats['total_pnl'] / months if months > 0 else 0
        print(f"月平均利益（推定）: {monthly_avg:,.0f}円")
        
        if monthly_avg >= 200000:
            print("🎉 月20万円目標達成可能性あり！")
        elif monthly_avg >= 100000:
            print("⭕ 月10万円レベル達成")
    
    return final_stats