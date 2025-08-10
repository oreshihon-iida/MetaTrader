#!/usr/bin/env python3
"""
Optimized ML Predictor Strategy (最適化版機械学習予測モデル)
処理高速化と予測精度向上版

特徴:
- 簡略化された特徴量生成
- 効率的な予測処理
- 品質重視の取引判断
- 月20万円利益目標
"""

import pandas as pd
import numpy as np
import talib
from typing import Tuple, Dict, Optional
from datetime import datetime
import pickle
import os
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

class OptimizedMLPredictor:
    """
    最適化された機械学習予測戦略
    
    高速処理と高精度予測を両立
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 lookback_periods: int = 30,
                 prediction_horizon: int = 8,  # 2時間先
                 confidence_threshold: float = 0.7,  # 高い閾値を維持
                 max_positions: int = 2,
                 risk_per_trade: float = 0.02,
                 model_type: str = 'random_forest'):
        """
        初期化
        
        Parameters
        ----------
        confidence_threshold : float
            品質重視のため高い閾値を設定
        """
        self.initial_balance = initial_balance
        self.lookback_periods = lookback_periods
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.model_type = model_type
        
        # アンサンブルモデル関連
        self.models = {}
        self.ensemble_weights = {}
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.feature_importance = None
        self.is_trained = False
        self.last_training_date = None
        self.training_score = 0
        self.prediction_accuracy = 0
        
        # キャッシュ（高速化）
        self._feature_cache = {}
        self._cache_size = 100
        
        # モデル保存パス
        self.model_dir = "models/optimized_ml"
        os.makedirs(self.model_dir, exist_ok=True)
    
    def create_features_optimized(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        最適化された特徴量生成（高速版）
        
        重要な特徴量のみに絞って処理時間を短縮
        """
        # キャッシュチェック
        data_hash = hash(str(data.index[-1]) + str(len(data)))
        if data_hash in self._feature_cache:
            return self._feature_cache[data_hash]
        
        features = pd.DataFrame(index=data.index)
        
        close = data['Close'] if 'Close' in data.columns else data['close']
        high = data['High'] if 'High' in data.columns else data['high']
        low = data['Low'] if 'Low' in data.columns else data['low']
        
        # 最重要特徴量のみ（計算時間削減）
        # 1. 価格リターン（3種類のみ）
        features['returns_5'] = close.pct_change(5)
        features['returns_10'] = close.pct_change(10)
        features['returns_20'] = close.pct_change(20)
        
        # 2. ボラティリティ（2種類のみ）
        features['volatility_10'] = features['returns_5'].rolling(10).std()
        features['volatility_20'] = features['returns_5'].rolling(20).std()
        
        # 3. 価格位置（1種類のみ）
        features['price_position'] = (close - low.rolling(20).min()) / (
            high.rolling(20).max() - low.rolling(20).min() + 0.0001
        )
        
        # 4. テクニカル指標（最重要3つのみ）
        # RSI
        features['rsi'] = talib.RSI(close, timeperiod=14) / 100
        
        # MACD
        macd, signal, _ = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        features['macd_signal'] = (macd - signal) / close
        
        # ATR（ボラティリティ指標）
        features['atr'] = talib.ATR(high, low, close, timeperiod=14) / close
        
        # 5. 移動平均（シンプル版）
        sma_20 = talib.SMA(close, timeperiod=20)
        features['sma_distance'] = (close - sma_20) / sma_20
        
        # 欠損値処理（高速化のため前方補完のみ）
        features = features.ffill().fillna(0)
        
        # キャッシュ更新
        if len(self._feature_cache) > self._cache_size:
            # 古いキャッシュを削除
            self._feature_cache = {}
        self._feature_cache[data_hash] = features
        
        return features
    
    def create_features_extended(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        拡張特徴量生成 - 高性能PC版
        50+個の多様な特徴量で劇的な精度向上を目指す
        """
        # キャッシュチェック
        data_hash = hash(str(data.index[-1]) + str(len(data)) + "extended")
        if data_hash in self._feature_cache:
            return self._feature_cache[data_hash]

        features = pd.DataFrame(index=data.index)
        
        # 基本価格データ
        close = data['Close'] if 'Close' in data.columns else data['close']
        high = data['High'] if 'High' in data.columns else data['high']
        low = data['Low'] if 'Low' in data.columns else data['low']
        open_price = data['Open'] if 'Open' in data.columns else data['open']
        volume = data['Volume'] if 'Volume' in data.columns else pd.Series(index=data.index, data=1)
        
        # === 1. 多期間リターン系特徴量 (8個) ===
        for period in [3, 5, 8, 10, 15, 20, 30, 45]:
            features[f'returns_{period}'] = close.pct_change(period)
        
        # === 2. ボラティリティ系特徴量 (6個) ===
        for period in [5, 10, 15, 20, 30, 45]:
            features[f'volatility_{period}'] = close.pct_change().rolling(period).std()
        
        # === 3. 価格位置・レンジ系特徴量 (4個) ===
        for period in [10, 20, 30, 50]:
            features[f'price_position_{period}'] = (close - low.rolling(period).min()) / (
                high.rolling(period).max() - low.rolling(period).min() + 1e-8
            )
        
        # === 4. テクニカル指標群 (12個) ===
        # RSI系
        features['rsi_14'] = talib.RSI(close, timeperiod=14) / 100
        features['rsi_21'] = talib.RSI(close, timeperiod=21) / 100
        features['rsi_momentum'] = features['rsi_14'] - features['rsi_14'].shift(5)
        
        # MACD系
        macd_12_26, signal_12_26, _ = talib.MACD(close, fastperiod=12, slowperiod=26)
        macd_8_21, signal_8_21, _ = talib.MACD(close, fastperiod=8, slowperiod=21)
        features['macd_signal_12_26'] = (macd_12_26 - signal_12_26) / close
        features['macd_signal_8_21'] = (macd_8_21 - signal_8_21) / close
        features['macd_histogram'] = talib.MACD(close)[2] / close
        
        # ボリンジャーバンド
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower + 1e-8)
        features['bb_width'] = (bb_upper - bb_lower) / bb_middle
        
        # ストキャスティクス
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
        features['stoch_k'] = slowk / 100
        features['stoch_d'] = slowd / 100
        features['stoch_momentum'] = (slowk - slowd) / 100
        
        # === 5. 移動平均系特徴量 (8個) ===
        for period in [5, 10, 15, 20, 30, 45, 60, 90]:
            sma = talib.SMA(close, timeperiod=period)
            features[f'sma_distance_{period}'] = (close - sma) / sma
        
        # === 6. 高度なテクニカル指標 (6個) ===
        # ATR系
        features['atr_14'] = talib.ATR(high, low, close, timeperiod=14) / close
        features['atr_21'] = talib.ATR(high, low, close, timeperiod=21) / close
        
        # CCI (商品チャンネル指数)
        features['cci'] = talib.CCI(high, low, close, timeperiod=14) / 100
        
        # Williams %R
        features['williams_r'] = talib.WILLR(high, low, close, timeperiod=14) / -100
        
        # MFI (マネーフローインデックス)
        features['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14) / 100
        
        # ADX (方向性指標)
        features['adx'] = talib.ADX(high, low, close, timeperiod=14) / 100
        
        # === 7. 価格パターン特徴量 (5個) ===
        # 実体とヒゲの比率
        body_size = abs(close - open_price)
        upper_shadow = high - np.maximum(close, open_price)
        lower_shadow = np.minimum(close, open_price) - low
        total_range = high - low + 1e-8
        
        features['body_ratio'] = body_size / total_range
        features['upper_shadow_ratio'] = upper_shadow / total_range
        features['lower_shadow_ratio'] = lower_shadow / total_range
        features['doji_score'] = 1 - (body_size / total_range)
        
        # 前日比較
        features['gap'] = (open_price - close.shift(1)) / close.shift(1)
        
        # === 8. モメンタム・オシレーター系 (4個) ===
        features['momentum_10'] = close / close.shift(10) - 1
        features['momentum_20'] = close / close.shift(20) - 1
        features['roc_14'] = talib.ROC(close, timeperiod=14) / 100
        features['trix'] = talib.TRIX(close, timeperiod=14) / 100
        
        # === 9. 相関・統計特徴量 (2個) ===
        # トレンド強度
        features['trend_strength'] = talib.LINEARREG_SLOPE(close, timeperiod=14) / close
        
        # 価格分散
        features['price_dispersion'] = close.rolling(20).std() / close.rolling(20).mean()
        
        # 欠損値処理（高速化のため前方補完のみ）
        features = features.ffill().fillna(0)
        
        # キャッシュ更新
        if len(self._feature_cache) > self._cache_size:
            self._feature_cache = {}
        self._feature_cache[data_hash] = features
        
        return features
    
    def build_ensemble_models(self):
        """
        アンサンブルモデル構築（高性能PC版）
        """
        models = {}
        
        # 1. Random Forest - 安定性重視
        models['rf'] = RandomForestRegressor(
            n_estimators=200,  # 拡張
            max_depth=15,      # 深くする
            min_samples_split=3,
            min_samples_leaf=2,
            max_features='sqrt',
            n_jobs=-1,
            random_state=42
        )
        
        # 2. XGBoost - 精度重視
        models['xgb'] = XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        # 3. LightGBM - 高速・高精度
        models['lgb'] = lgb.LGBMRegressor(
            n_estimators=200,
            max_depth=10,
            learning_rate=0.05,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        
        # 4. Gradient Boosting - 堅実性重視
        models['gb'] = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.08,
            subsample=0.8,
            random_state=42
        )
        
        return models
    
    def train_model(self, data: pd.DataFrame):
        """
        モデル学習（高速版）
        """
        print(f"最適化モデル学習開始（拡張特徴量版）...")
        
        # 拡張特徴量生成（高性能PC版）
        print("拡張特徴量生成中...")
        features = self.create_features_extended(data)
        
        # 目的変数
        close = data['Close'] if 'Close' in data.columns else data['close']
        future_returns = close.shift(-self.prediction_horizon).pct_change(
            self.prediction_horizon, fill_method=None
        )
        
        # 有効データ抽出
        valid_idx = ~(features.isna().any(axis=1) | future_returns.isna())
        X = features[valid_idx].values
        y = future_returns[valid_idx].values
        
        if len(X) < 100:
            print("学習データ不足")
            return
        
        # データ分割（高速化のため検証セットを小さく）
        split_idx = int(len(X) * 0.85)
        X_train = X[:split_idx]
        y_train = y[:split_idx]
        X_val = X[split_idx:]
        y_val = y[split_idx:]
        
        # スケーリング
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        X_val_scaled = self.scaler_X.transform(X_val)
        y_train_scaled = self.scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        y_val_scaled = self.scaler_y.transform(y_val.reshape(-1, 1)).flatten()
        
        # アンサンブル学習（高性能PC版）
        print("アンサンブル学習開始...")
        self.models = self.build_ensemble_models()
        model_scores = {}
        model_predictions = {}
        
        for name, model in self.models.items():
            print(f"  {name}モデル学習中...")
            model.fit(X_train_scaled, y_train_scaled)
            y_pred = model.predict(X_val_scaled)
            score = mean_absolute_error(y_val_scaled, y_pred)
            model_scores[name] = score
            model_predictions[name] = y_pred
            print(f"  {name} MAE: {score:.6f}")
        
        # 重み計算（逆MAE重み付け）
        total_inverse_score = sum(1/score for score in model_scores.values())
        self.ensemble_weights = {name: (1/score)/total_inverse_score 
                               for name, score in model_scores.items()}
        
        # アンサンブル予測
        y_pred_ensemble = sum(self.ensemble_weights[name] * pred 
                             for name, pred in model_predictions.items())
        val_mae = mean_absolute_error(y_val_scaled, y_pred_ensemble)
        
        print(f"アンサンブル重み: {self.ensemble_weights}")
        print(f"個別MAE: {model_scores}")
        print(f"アンサンブルMAE: {val_mae:.6f}")
        
        # 予測精度計算（方向の正確性）
        y_pred_orig = self.scaler_y.inverse_transform(y_pred.reshape(-1, 1)).flatten()
        direction_accuracy = np.mean(np.sign(y_pred_orig) == np.sign(y_val))
        self.prediction_accuracy = direction_accuracy
        
        # スコア計算（MAEと方向精度の組み合わせ）
        self.training_score = (1 / (1 + val_mae)) * direction_accuracy
        
        self.is_trained = True
        self.last_training_date = datetime.now()
        
        print(f"学習完了。MAE: {val_mae:.4f}, 方向精度: {direction_accuracy:.2%}")
        print(f"総合スコア: {self.training_score:.3f}")
    
    def predict_fast(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        高速予測
        """
        if not self.is_trained or not self.models:
            return 0.0, 0.0
        
        # 拡張特徴量生成（高性能PC版）
        features = self.create_features_extended(data)
        
        if len(features) == 0:
            return 0.0, 0.0
        
        # 最新データ
        X = features.iloc[-1:].values
        X_scaled = self.scaler_X.transform(X)
        
        # アンサンブル予測
        predictions = {}
        for name, model in self.models.items():
            pred_scaled = model.predict(X_scaled)[0]
            predictions[name] = pred_scaled
        
        # 重み付けアンサンブル
        prediction_scaled = sum(self.ensemble_weights[name] * pred 
                              for name, pred in predictions.items())
        prediction = self.scaler_y.inverse_transform([[prediction_scaled]])[0, 0]
        
        # 信頼度計算（予測の大きさと学習スコアに基づく）
        # 月20万円目標のため、品質重視
        prediction_strength = min(abs(prediction) * 100, 1.0)
        confidence = self.training_score * prediction_strength * self.prediction_accuracy
        
        return prediction, confidence
    
    def generate_quality_signal(self, data: pd.DataFrame, 
                                current_positions: int = 0) -> Tuple[int, Dict]:
        """
        品質重視のシグナル生成
        
        月20万円目標のため、精度の高い取引のみ実行
        """
        if current_positions >= self.max_positions:
            return 0, {'reason': 'max_positions_reached'}
        
        # 予測
        prediction, confidence = self.predict_fast(data)
        
        analysis = {
            'prediction': prediction,
            'confidence': confidence,
            'threshold': self.confidence_threshold,
            'accuracy': self.prediction_accuracy
        }
        
        # 品質チェック（厳格）
        if confidence < self.confidence_threshold:
            return 0, {**analysis, 'reason': 'low_confidence'}
        
        # 予測精度チェック
        if self.prediction_accuracy < 0.55:  # 55%以上の方向精度が必要
            return 0, {**analysis, 'reason': 'low_accuracy'}
        
        # シグナル決定（月20万円目標のため慎重に）
        if prediction > 0.002 and confidence > 0.75:  # 0.2%以上の上昇 + 高信頼度
            signal = 1
        elif prediction < -0.002 and confidence > 0.75:  # 0.2%以上の下落 + 高信頼度
            signal = -1
        else:
            signal = 0
            analysis['reason'] = 'insufficient_prediction'
        
        return signal, analysis
    
    def calculate_position_size_for_profit(self, confidence: float, 
                                          current_balance: float,
                                          monthly_target: float = 200000) -> float:
        """
        月間利益目標に基づくポジションサイズ計算
        
        Parameters
        ----------
        monthly_target : float
            月間目標利益（デフォルト20万円）
        """
        # 月20取引想定で1取引あたり1万円の利益が必要
        target_profit_per_trade = monthly_target / 20
        
        # 期待利益率を15pips（0.15円）と想定
        expected_pips = 15
        pip_value = 100  # 1pip = 100円
        
        # 必要ロット数計算
        required_lots = target_profit_per_trade / (expected_pips * pip_value)
        
        # 信頼度によるサイズ調整
        confidence_multiplier = min(confidence * 1.5, 1.2)
        adjusted_lots = required_lots * confidence_multiplier
        
        # リスク制限
        max_risk_lots = (current_balance * self.risk_per_trade) / (20 * pip_value)
        
        return np.clip(adjusted_lots, 0.5, min(3.0, max_risk_lots))


def optimized_ml_wrapper(data: pd.DataFrame, executor, metadata: Dict = None):
    """
    最適化版ML予測戦略のラッパー
    
    月20万円利益を目指す品質重視の取引
    """
    
    strategy = OptimizedMLPredictor(
        initial_balance=3000000,
        lookback_periods=30,
        prediction_horizon=8,
        confidence_threshold=0.7,
        max_positions=2,
        risk_per_trade=0.02,
        model_type='random_forest'
    )
    
    print("最適化ML予測戦略 - 月20万円目標")
    print("品質重視の取引実行")
    
    # 初回学習
    training_size = min(3000, len(data) // 4)
    if len(data) > training_size:
        training_data = data.iloc[:training_size]
        strategy.train_model(training_data)
    else:
        print("学習データ不足")
        return
    
    signals_generated = 0
    trades_executed = 0
    monthly_profit = 0
    current_month = None
    
    # メインループ（200本ごと = 50時間ごとで高速化）
    for i in range(training_size, len(data), 200):
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        price_col = 'Close' if 'Close' in data.columns else 'close'
        current_price = data[price_col].iloc[i]
        
        # 月変更チェック
        if current_month != current_time.month:
            if current_month is not None:
                print(f"月間利益: {monthly_profit:,.0f}円")
            monthly_profit = 0
            current_month = current_time.month
        
        # ポジションチェック
        executor.check_positions(current_price, current_time)
        
        # 週次再学習（10000本ごと = 約100日ごと）
        if (i - training_size) % 10000 == 0 and i > training_size:
            print(f"モデル再学習: {current_time}")
            recent_data = data.iloc[max(0, i-5000):i+1]
            strategy.train_model(recent_data)
        
        # シグナル生成（品質重視）
        current_positions = len(executor.positions) if hasattr(executor, 'positions') else 0
        signal, analysis = strategy.generate_quality_signal(current_data, current_positions)
        
        if signal != 0:
            signals_generated += 1
            
            # 月20万円目標のポジションサイズ
            lot_size = strategy.calculate_position_size_for_profit(
                analysis['confidence'],
                getattr(executor, 'current_balance', executor.initial_balance),
                monthly_target=200000
            )
            
            # TP/SL設定（予測に基づく）
            if abs(analysis['prediction']) > 0.003:
                tp_pips = 30
                sl_pips = 15
            else:
                tp_pips = 20
                sl_pips = 12
            
            # ポジション開設
            position = executor.open_position(
                signal=signal,
                price=current_price,
                lot_size=lot_size,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                timestamp=current_time,
                strategy='optimized_ml'
            )
            
            if position:
                trades_executed += 1
                print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} @ {current_price:.3f} "
                      f"Lot:{lot_size:.2f} 信頼度:{analysis['confidence']:.2f}")
        
        # 資産更新
        executor.update_equity(current_price)
    
    # 結果表示
    final_stats = executor.get_statistics()
    print(f"\n=== 最適化ML予測戦略 結果 ===")
    print(f"実行取引数: {trades_executed}")
    print(f"最終損益: {final_stats['total_pnl']:,.0f}円")
    
    if trades_executed > 0:
        monthly_avg = final_stats['total_pnl'] / (len(data) / (20 * 96))  # 月数計算
        print(f"月平均利益: {monthly_avg:,.0f}円")
        if monthly_avg >= 200000:
            print("✅ 月20万円目標達成！")
        else:
            print(f"目標まで: {200000 - monthly_avg:,.0f}円/月")