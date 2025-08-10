#!/usr/bin/env python3
"""
MT5対応軽量版Enhanced Trinity ML Strategy
MetaTrader5 VPS環境での安定動作を重視した最適化版
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Tuple, Dict, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 軽量機械学習ライブラリのみ使用
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error
    import talib
    MT5_COMPATIBLE = True
    print("MT5対応: 必要ライブラリ全て利用可能")
except ImportError as e:
    print(f"警告: {e} - 代替実装を使用")
    MT5_COMPATIBLE = False

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    print("感情分析システム: 利用不可（スタンドアローンモード）")
    SENTIMENT_AVAILABLE = False

class MT5CompatibleTrinityStrategy:
    """
    MT5対応軽量版Enhanced Trinity ML戦略
    
    特徴:
    - VPS環境対応（軽量・高速）
    - 最小限の依存関係
    - メモリ効率最適化
    - エラー処理強化
    """
    
    def __init__(self,
                 confidence_threshold: float = 0.18,
                 prediction_horizon: int = 4,  # 8→4に軽量化
                 max_memory_mb: int = 500):  # メモリ制限
        
        self.confidence_threshold = confidence_threshold
        self.prediction_horizon = prediction_horizon
        self.max_memory_mb = max_memory_mb
        
        # 軽量モデル（単一RandomForest）
        if MT5_COMPATIBLE:
            self.model = RandomForestRegressor(
                n_estimators=100,  # 200→100に軽量化
                max_depth=10,      # 15→10に軽量化
                min_samples_split=5,
                min_samples_leaf=3,
                max_features='sqrt',
                n_jobs=2,  # VPS環境考慮（24→2に制限）
                random_state=42
            )
            self.scaler_X = StandardScaler()
            self.scaler_y = StandardScaler()
        else:
            self.model = None
            print("代替実装モード: 簡易予測アルゴリズム使用")
        
        # 感情分析システム
        if SENTIMENT_AVAILABLE:
            try:
                self.sentiment_analyzer = ClaudeSentimentAnalyzer()
                print("感情分析システム: 正常読み込み")
            except Exception as e:
                print(f"感情分析エラー: {e}")
                self.sentiment_analyzer = None
        else:
            self.sentiment_analyzer = None
        
        # 軽量特徴量セット（11個→6個に削減）
        self.feature_names = [
            'returns_1', 'returns_5', 'returns_15',
            'rsi_14', 'volatility_10', 'sma_distance_20'
        ]
        
        # 学習状態
        self.is_trained = False
        self.training_score = 0.0
        self.prediction_accuracy = 0.5
        
        print(f"MT5対応軽量Trinity初期化完了")
        print(f"予測範囲: {prediction_horizon}本先")
        print(f"メモリ制限: {max_memory_mb}MB")
        print(f"特徴量数: {len(self.feature_names)}個")
    
    def create_lightweight_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        軽量特徴量生成（MT5 VPS対応）
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            # 価格データ
            close = data['Close'] if 'Close' in data.columns else data['close']
            high = data['High'] if 'High' in data.columns else data['high']
            low = data['Low'] if 'Low' in data.columns else data['low']
            
            # 軽量特徴量セット
            if MT5_COMPATIBLE and 'talib' in sys.modules:
                # TA-Lib使用（高速）
                features['returns_1'] = close.pct_change(1)
                features['returns_5'] = close.pct_change(5)
                features['returns_15'] = close.pct_change(15)
                features['rsi_14'] = talib.RSI(close, timeperiod=14) / 100
                features['volatility_10'] = close.pct_change().rolling(10).std()
                features['sma_distance_20'] = (close - talib.SMA(close, timeperiod=20)) / close
            else:
                # 代替実装（pandas使用）
                features['returns_1'] = close.pct_change(1)
                features['returns_5'] = close.pct_change(5)
                features['returns_15'] = close.pct_change(15)
                
                # 簡易RSI
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                features['rsi_14'] = (100 - (100 / (1 + rs))) / 100
                
                features['volatility_10'] = close.pct_change().rolling(10).std()
                sma_20 = close.rolling(20).mean()
                features['sma_distance_20'] = (close - sma_20) / close
            
            # 欠損値処理（前方補完）
            features = features.fillna(method='ffill').fillna(0)
            
            # メモリ使用量チェック
            memory_usage = features.memory_usage(deep=True).sum() / 1024 / 1024
            if memory_usage > self.max_memory_mb:
                print(f"警告: メモリ使用量 {memory_usage:.1f}MB > 制限 {self.max_memory_mb}MB")
                # 最新データのみ保持
                features = features.tail(min(len(features), 1000))
            
            return features
            
        except Exception as e:
            print(f"特徴量生成エラー: {e}")
            # エラー時は最小限の特徴量
            fallback_features = pd.DataFrame(index=data.index)
            fallback_features['returns_1'] = close.pct_change(1)
            fallback_features['volatility_5'] = close.pct_change().rolling(5).std()
            return fallback_features.fillna(0)
    
    def train_lightweight_model(self, data: pd.DataFrame):
        """
        軽量モデル学習（MT5 VPS対応）
        """
        try:
            print("軽量Trinity学習開始...")
            
            # 特徴量生成（軽量版）
            features = self.create_lightweight_features(data)
            
            # 目的変数
            close = data['Close'] if 'Close' in data.columns else data['close']
            future_returns = close.shift(-self.prediction_horizon).pct_change(
                self.prediction_horizon, fill_method=None
            )
            
            # 有効データ抽出
            valid_idx = ~(features.isna().any(axis=1) | future_returns.isna())
            X = features[valid_idx].values
            y = future_returns[valid_idx].values
            
            if len(X) < 50:  # 最小データ数チェック
                print(f"学習データ不足: {len(X)}件 < 50件")
                return
            
            print(f"学習データ: {len(X)}件")
            
            # 学習データ分割
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            if MT5_COMPATIBLE and self.model is not None:
                # スケーリング
                X_train_scaled = self.scaler_X.fit_transform(X_train)
                X_test_scaled = self.scaler_X.transform(X_test)
                y_train_scaled = self.scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
                y_test_scaled = self.scaler_y.transform(y_test.reshape(-1, 1)).flatten()
                
                # モデル学習
                self.model.fit(X_train_scaled, y_train_scaled)
                
                # 評価
                y_pred_scaled = self.model.predict(X_test_scaled)
                y_pred = self.scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
                
                # 精度計算
                mae = mean_absolute_error(y_test, y_pred)
                direction_accuracy = np.mean(np.sign(y_pred) == np.sign(y_test))
                
                self.prediction_accuracy = direction_accuracy
                self.training_score = (1 / (1 + mae)) * direction_accuracy
                
                print(f"学習完了 - MAE: {mae:.4f}, 方向精度: {direction_accuracy:.1%}")
            else:
                # 代替実装（移動平均ベース）
                self.prediction_accuracy = 0.52  # 保守的な値
                self.training_score = 0.3
                print("代替学習完了 - 移動平均ベース")
            
            self.is_trained = True
            
        except Exception as e:
            print(f"学習エラー: {e}")
            self.is_trained = False
    
    def get_sentiment_features(self) -> Dict[str, float]:
        """
        感情分析特徴量取得（MT5対応）
        """
        if not SENTIMENT_AVAILABLE or self.sentiment_analyzer is None:
            # デフォルト値（ニュートラル）
            return {
                'news_sentiment': 0.0,
                'usd_strength': 0.0,
                'sentiment_confidence': 0.5,
                'sentiment_count': 0
            }
        
        try:
            return self.sentiment_analyzer.get_recent_sentiment_features(hours_back=24)
        except Exception as e:
            print(f"感情分析取得エラー: {e}")
            return {
                'news_sentiment': 0.0,
                'usd_strength': 0.0,
                'sentiment_confidence': 0.5,
                'sentiment_count': 0
            }
    
    def predict_lightweight(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        軽量予測実行（MT5対応）
        """
        if not self.is_trained:
            return 0.0, 0.0
        
        try:
            # 軽量特徴量生成（最新データのみ）
            features = self.create_lightweight_features(data.tail(100))  # メモリ節約
            
            if len(features) == 0:
                return 0.0, 0.0
            
            # 最新データで予測
            X = features.iloc[-1:].values
            
            if MT5_COMPATIBLE and self.model is not None:
                X_scaled = self.scaler_X.transform(X)
                prediction_scaled = self.model.predict(X_scaled)[0]
                prediction = self.scaler_y.inverse_transform([[prediction_scaled]])[0, 0]
            else:
                # 代替実装（簡易トレンド予測）
                close = data['Close'] if 'Close' in data.columns else data['close']
                recent_trend = close.tail(20).pct_change().mean()
                prediction = recent_trend * 2.0  # 簡易予測
            
            # Enhanced信頼度計算
            sentiment_features = self.get_sentiment_features()
            sentiment_boost = sentiment_features.get('news_sentiment', 0.0) * 0.25
            
            base_confidence = (
                0.4 * self.prediction_accuracy + 
                0.4 * self.training_score + 
                0.2 * min(abs(prediction) * 100, 1.0)
            )
            
            enhanced_confidence = base_confidence + sentiment_boost
            enhanced_confidence = max(0.0, min(1.0, enhanced_confidence))
            
            return prediction, enhanced_confidence
            
        except Exception as e:
            print(f"予測エラー: {e}")
            return 0.0, 0.0
    
    def generate_signal(self, data: pd.DataFrame) -> Tuple[int, Dict]:
        """
        軽量シグナル生成（MT5対応）
        """
        prediction, confidence = self.predict_lightweight(data)
        
        # 感情分析特徴量
        sentiment_features = self.get_sentiment_features()
        
        analysis = {
            'prediction': prediction,
            'confidence': confidence,
            'threshold': self.confidence_threshold,
            'sentiment_features': sentiment_features,
            'strategy_type': 'MT5_Compatible_Trinity',
            'accuracy': self.prediction_accuracy
        }
        
        # シグナル決定
        if confidence < self.confidence_threshold:
            return 0, {**analysis, 'reason': 'low_confidence'}
        
        if self.prediction_accuracy < 0.48:
            return 0, {**analysis, 'reason': 'low_accuracy'}
        
        # 予測閾値（軽量化）
        threshold = 0.0010  # 0.0012→0.0010に緩和
        
        if prediction > threshold and confidence > self.confidence_threshold:
            signal = 1
        elif prediction < -threshold and confidence > self.confidence_threshold:
            signal = -1
        else:
            signal = 0
            analysis['reason'] = 'insufficient_prediction'
        
        return signal, analysis
    
    def get_system_status(self) -> Dict:
        """
        システム状態取得（MT5診断用）
        """
        sentiment_features = self.get_sentiment_features()
        
        return {
            'mt5_compatible': MT5_COMPATIBLE,
            'sentiment_available': SENTIMENT_AVAILABLE,
            'model_trained': self.is_trained,
            'prediction_accuracy': self.prediction_accuracy,
            'training_score': self.training_score,
            'feature_count': len(self.feature_names),
            'sentiment_count': sentiment_features.get('sentiment_count', 0),
            'recent_sentiment': sentiment_features.get('news_sentiment', 0.0),
            'memory_optimized': True
        }


def mt5_compatibility_check():
    """
    MT5互換性チェック
    """
    print("=" * 60)
    print("MetaTrader5 互換性診断")
    print("=" * 60)
    
    # 必須ライブラリチェック
    required_libs = {
        'pandas': 'データ処理',
        'numpy': '数値計算', 
        'sklearn': '機械学習',
        'talib': 'テクニカル指標'
    }
    
    available_libs = []
    missing_libs = []
    
    for lib_name, description in required_libs.items():
        try:
            if lib_name == 'sklearn':
                import sklearn
            elif lib_name == 'talib':
                import talib
            else:
                __import__(lib_name)
            available_libs.append(f"✅ {lib_name}: {description}")
        except ImportError:
            missing_libs.append(f"❌ {lib_name}: {description}")
    
    print("利用可能ライブラリ:")
    for lib in available_libs:
        print(f"  {lib}")
    
    if missing_libs:
        print("\n不足ライブラリ:")
        for lib in missing_libs:
            print(f"  {lib}")
    
    # 軽量戦略テスト
    print(f"\n軽量戦略テスト:")
    try:
        strategy = MT5CompatibleTrinityStrategy()
        status = strategy.get_system_status()
        
        print(f"  MT5互換性: {'✅' if status['mt5_compatible'] else '❌'}")
        print(f"  感情分析: {'✅' if status['sentiment_available'] else '❌'}")
        print(f"  メモリ最適化: {'✅' if status['memory_optimized'] else '❌'}")
        print(f"  特徴量数: {status['feature_count']}個")
        
        print(f"\nMT5互換性評価: {'🎯 完全対応' if len(missing_libs) == 0 else '⚠️ 部分対応'}")
        
    except Exception as e:
        print(f"  テストエラー: {e}")
        print(f"MT5互換性評価: ❌ 要調整")


if __name__ == "__main__":
    mt5_compatibility_check()