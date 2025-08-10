#!/usr/bin/env python3
"""
Lightweight ML Predictor Strategy (軽量機械学習予測モデル)
TensorFlow不要の軽量版短期売買戦略

特徴:
- RandomForest/XGBoost使用
- 15分〜1時間先の価格予測
- 高速学習・予測
- 高頻度取引（1日5-10回）
"""

import pandas as pd
import numpy as np
import talib
from typing import Tuple, Dict, Optional, List
from datetime import datetime, timedelta
import pickle
import os
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

# XGBoost（オプション）
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

class LightweightMLPredictor:
    """
    軽量機械学習予測戦略
    
    scikit-learnベースの高速予測モデル
    """
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 lookback_periods: int = 20,
                 prediction_horizon: int = 4,  # 4*15分 = 1時間先
                 confidence_threshold: float = 0.6,
                 max_positions: int = 3,
                 risk_per_trade: float = 0.01,
                 model_type: str = 'random_forest'):
        """
        初期化
        
        Parameters
        ----------
        model_type : str
            'random_forest' or 'xgboost'
        """
        self.initial_balance = initial_balance
        self.lookback_periods = lookback_periods
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.model_type = model_type
        
        # モデル関連
        self.model = None
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.feature_importance = None
        self.is_trained = False
        self.last_training_date = None
        self.training_score = 0
        
        # モデル保存パス
        self.model_dir = "models/lightweight_ml"
        os.makedirs(self.model_dir, exist_ok=True)
        
    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        特徴量生成（最適化版）
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        pd.DataFrame
            特徴量データ
        """
        features = pd.DataFrame(index=data.index)
        
        close = data['Close'] if 'Close' in data.columns else data['close']
        high = data['High'] if 'High' in data.columns else data['high']
        low = data['Low'] if 'Low' in data.columns else data['low']
        open_price = data['Open'] if 'Open' in data.columns else data['open']
        
        # 基本的な価格特徴
        features['returns_1'] = close.pct_change(1)
        features['returns_3'] = close.pct_change(3)
        features['returns_5'] = close.pct_change(5)
        features['returns_10'] = close.pct_change(10)
        
        # ボラティリティ
        features['volatility_5'] = features['returns_1'].rolling(5).std()
        features['volatility_10'] = features['returns_1'].rolling(10).std()
        features['volatility_20'] = features['returns_1'].rolling(20).std()
        
        # 価格位置（高値安値に対する現在価格の位置）
        features['price_position_5'] = (close - low.rolling(5).min()) / (high.rolling(5).max() - low.rolling(5).min())
        features['price_position_10'] = (close - low.rolling(10).min()) / (high.rolling(10).max() - low.rolling(10).min())
        features['price_position_20'] = (close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min())
        
        # テクニカル指標
        # RSI
        features['rsi_7'] = talib.RSI(close, timeperiod=7) / 100
        features['rsi_14'] = talib.RSI(close, timeperiod=14) / 100
        features['rsi_21'] = talib.RSI(close, timeperiod=21) / 100
        
        # MACD
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        features['macd'] = macd / close
        features['macd_signal'] = signal / close
        features['macd_hist'] = hist / close
        
        # ボリンジャーバンド
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        features['bb_width'] = (bb_upper - bb_lower) / bb_middle
        features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower)
        
        # ATR
        features['atr_14'] = talib.ATR(high, low, close, timeperiod=14) / close
        
        # 移動平均の傾き
        sma_5 = talib.SMA(close, timeperiod=5)
        sma_10 = talib.SMA(close, timeperiod=10)
        sma_20 = talib.SMA(close, timeperiod=20)
        
        features['sma_5_slope'] = (sma_5 - sma_5.shift(3)) / sma_5.shift(3)
        features['sma_10_slope'] = (sma_10 - sma_10.shift(5)) / sma_10.shift(5)
        features['sma_20_slope'] = (sma_20 - sma_20.shift(10)) / sma_20.shift(10)
        
        # 移動平均との乖離
        features['sma_5_distance'] = (close - sma_5) / sma_5
        features['sma_10_distance'] = (close - sma_10) / sma_10
        features['sma_20_distance'] = (close - sma_20) / sma_20
        
        # モメンタム
        features['momentum_5'] = talib.MOM(close, timeperiod=5) / close
        features['momentum_10'] = talib.MOM(close, timeperiod=10) / close
        
        # 出来高関連（もしあれば）
        if 'Volume' in data.columns or 'volume' in data.columns:
            volume = data['Volume'] if 'Volume' in data.columns else data['volume']
            if not volume.isna().all():
                features['volume_ratio'] = volume / volume.rolling(20).mean()
                features['volume_momentum'] = volume.pct_change(5)
        
        # 時間特徴（市場セッション）
        if hasattr(data.index, 'hour'):
            features['hour'] = data.index.hour / 24
            features['is_tokyo'] = ((data.index.hour >= 9) & (data.index.hour < 15)).astype(int)
            features['is_london'] = ((data.index.hour >= 16) & (data.index.hour < 24)).astype(int)
            features['is_ny'] = ((data.index.hour >= 21) | (data.index.hour < 2)).astype(int)
        
        # ローソク足パターン
        features['body_ratio'] = (close - open_price) / (high - low + 0.0001)
        features['upper_shadow'] = (high - np.maximum(close, open_price)) / (high - low + 0.0001)
        features['lower_shadow'] = (np.minimum(close, open_price) - low) / (high - low + 0.0001)
        
        return features.fillna(method='ffill').fillna(0)
    
    def prepare_training_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        学習データ準備
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (X, y) 学習データ
        """
        # 特徴量生成
        features = self.create_features(data)
        
        # 目的変数（未来のリターン）
        close = data['Close'] if 'Close' in data.columns else data['close']
        future_returns = close.shift(-self.prediction_horizon).pct_change(self.prediction_horizon)
        
        # 有効なデータのみ抽出
        valid_idx = ~(features.isna().any(axis=1) | future_returns.isna())
        X = features[valid_idx].values
        y = future_returns[valid_idx].values
        
        return X, y
    
    def build_model(self):
        """
        モデル構築
        
        Returns
        -------
        model
            構築済みモデル
        """
        if self.model_type == 'xgboost' and XGB_AVAILABLE:
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
        else:
            # RandomForest（デフォルト）
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            )
        
        return model
    
    def train_model(self, data: pd.DataFrame):
        """
        モデル学習
        
        Parameters
        ----------
        data : pd.DataFrame
            学習データ
        """
        print(f"モデル学習開始 ({self.model_type})...")
        
        # データ準備
        X, y = self.prepare_training_data(data)
        
        if len(X) < 100:
            print("学習データ不足")
            return
        
        # データ分割
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # スケーリング
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        X_val_scaled = self.scaler_X.transform(X_val)
        y_train_scaled = self.scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        y_val_scaled = self.scaler_y.transform(y_val.reshape(-1, 1)).flatten()
        
        # モデル構築・学習
        self.model = self.build_model()
        self.model.fit(X_train_scaled, y_train_scaled)
        
        # 検証
        y_pred = self.model.predict(X_val_scaled)
        val_mse = mean_squared_error(y_val_scaled, y_pred)
        val_mae = mean_absolute_error(y_val_scaled, y_pred)
        
        # 特徴量重要度
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = self.model.feature_importances_
        
        # スコア計算（精度指標）
        self.training_score = 1 / (1 + val_mae)  # MAEが小さいほど高スコア
        
        self.is_trained = True
        self.last_training_date = datetime.now()
        
        print(f"学習完了。検証MAE: {val_mae:.6f}, MSE: {val_mse:.6f}")
        print(f"トレーニングスコア: {self.training_score:.3f}")
        
        # モデル保存
        self.save_model()
    
    def predict(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        価格予測
        
        Parameters
        ----------
        data : pd.DataFrame
            直近データ
            
        Returns
        -------
        Tuple[float, float]
            (予測値, 信頼度)
        """
        if not self.is_trained or self.model is None:
            return 0.0, 0.0
        
        # 特徴量生成
        features = self.create_features(data)
        
        if len(features) == 0:
            return 0.0, 0.0
        
        # 最新のデータを取得
        X = features.iloc[-1:].values
        
        # スケーリング
        X_scaled = self.scaler_X.transform(X)
        
        # 予測
        prediction_scaled = self.model.predict(X_scaled)[0]
        
        # 逆スケーリング
        prediction = self.scaler_y.inverse_transform([[prediction_scaled]])[0, 0]
        
        # 信頼度計算（モデルのトレーニングスコアと予測の大きさに基づく）
        prediction_magnitude = min(abs(prediction) * 50, 1.0)
        confidence = self.training_score * prediction_magnitude
        
        return prediction, confidence
    
    def generate_signal(self, data: pd.DataFrame, current_positions: int = 0) -> Tuple[int, Dict]:
        """
        取引シグナル生成
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        current_positions : int
            現在のポジション数
            
        Returns
        -------
        Tuple[int, Dict]
            (シグナル, 分析詳細)
        """
        if current_positions >= self.max_positions:
            return 0, {'reason': 'max_positions_reached'}
        
        # 予測
        prediction, confidence = self.predict(data)
        
        analysis = {
            'prediction': prediction,
            'confidence': confidence,
            'threshold': self.confidence_threshold,
            'model_type': self.model_type
        }
        
        # 信頼度チェック
        if confidence < self.confidence_threshold:
            return 0, {**analysis, 'reason': 'low_confidence'}
        
        # シグナル決定（閾値を調整）
        if prediction > 0.0015:  # 0.15%以上の上昇予測
            signal = 1  # 買い
        elif prediction < -0.0015:  # 0.15%以上の下落予測
            signal = -1  # 売り
        else:
            signal = 0
            analysis['reason'] = 'prediction_too_small'
        
        return signal, analysis
    
    def calculate_position_size(self, confidence: float, current_balance: float) -> float:
        """
        ポジションサイズ計算
        
        Parameters
        ----------
        confidence : float
            予測信頼度
        current_balance : float
            現在残高
            
        Returns
        -------
        float
            ポジションサイズ（ロット）
        """
        # 信頼度に応じたリスク調整
        adjusted_risk = self.risk_per_trade * min(confidence * 1.5, 1.0)
        risk_amount = current_balance * adjusted_risk
        
        # 基本ロットサイズ（1pip = 100円想定）
        base_lot = risk_amount / (15 * 100)  # 15pipsストップロス想定
        
        return np.clip(base_lot, 0.01, 3.0)
    
    def save_model(self):
        """モデル保存"""
        if self.model is None:
            return
        
        # モデルと関連オブジェクト保存
        model_path = os.path.join(self.model_dir, f"{self.model_type}_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler_X': self.scaler_X,
                'scaler_y': self.scaler_y,
                'last_training': self.last_training_date,
                'training_score': self.training_score,
                'feature_importance': self.feature_importance
            }, f)
        
        print(f"モデル保存完了: {model_path}")
    
    def load_model(self):
        """モデル読み込み"""
        model_path = os.path.join(self.model_dir, f"{self.model_type}_model.pkl")
        
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                saved_data = pickle.load(f)
                self.model = saved_data['model']
                self.scaler_X = saved_data['scaler_X']
                self.scaler_y = saved_data['scaler_y']
                self.last_training_date = saved_data['last_training']
                self.training_score = saved_data.get('training_score', 0.5)
                self.feature_importance = saved_data.get('feature_importance', None)
            
            self.is_trained = True
            print(f"モデル読み込み完了。最終学習: {self.last_training_date}")
            return True
        
        return False


def lightweight_ml_wrapper(data: pd.DataFrame, executor, metadata: Dict = None):
    """
    Lightweight ML Predictor Strategy のテスト用ラッパー
    
    Parameters
    ----------
    data : pd.DataFrame
        価格データ
    executor : TradeExecutor
        取引執行クラス
    metadata : Dict
        追加データ
    """
    
    # XGBoostが利用可能ならそれを使用
    model_type = 'xgboost' if XGB_AVAILABLE else 'random_forest'
    
    strategy = LightweightMLPredictor(
        initial_balance=3000000,
        lookback_periods=20,
        prediction_horizon=4,  # 1時間先予測
        confidence_threshold=0.6,
        max_positions=3,
        risk_per_trade=0.01,
        model_type=model_type
    )
    
    print(f"Lightweight ML Predictor Strategy テスト開始 ({model_type})")
    print("設定: 1時間先予測、信頼度閾値0.6、最大ポジション3")
    
    # モデル学習（最初の30日分）
    training_size = min(500, len(data) // 3)
    if len(data) > training_size:
        training_data = data.iloc[:training_size]
        strategy.train_model(training_data)
    else:
        print("学習データ不足")
        return
    
    signals_generated = 0
    trades_executed = 0
    retraining_count = 0
    
    # メインループ
    start_idx = training_size
    
    for i in range(start_idx, len(data), 10):  # 10本ごと（2.5時間ごと）
        current_data = data.iloc[:i+1]
        current_time = data.index[i]
        price_col = 'Close' if 'Close' in data.columns else 'close'
        current_price = data[price_col].iloc[i]
        
        # 既存ポジションチェック
        executor.check_positions(current_price, current_time)
        
        # 定期的な再学習（500本ごと = 約5日ごと）
        if (i - start_idx) % 500 == 0 and i > start_idx:
            retraining_count += 1
            print(f"再学習 #{retraining_count}: {current_time}")
            recent_data = data.iloc[max(0, i-1000):i+1]
            strategy.train_model(recent_data)
        
        # シグナル生成
        current_position_count = len(executor.positions) if hasattr(executor, 'positions') else 0
        signal, analysis = strategy.generate_signal(current_data, current_position_count)
        
        if signal != 0:
            signals_generated += 1
            
            # ポジションサイズ計算
            lot_size = strategy.calculate_position_size(
                analysis['confidence'],
                getattr(executor, 'current_balance', executor.initial_balance)
            )
            
            # TP/SL設定（予測の大きさに基づく）
            if abs(analysis['prediction']) > 0.003:  # 0.3%以上の予測
                tp_pips = 25
                sl_pips = 12
            elif abs(analysis['prediction']) > 0.002:  # 0.2%以上
                tp_pips = 20
                sl_pips = 10
            else:
                tp_pips = 15
                sl_pips = 8
            
            # ポジション開設
            position = executor.open_position(
                signal=signal,
                price=current_price,
                lot_size=lot_size,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                timestamp=current_time,
                strategy='lightweight_ml_predictor'
            )
            
            if position:
                trades_executed += 1
                if trades_executed <= 10:
                    print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} - "
                          f"価格:{current_price:.3f} - Lot:{lot_size:.2f} - "
                          f"予測:{analysis['prediction']:.4f} - "
                          f"信頼度:{analysis['confidence']:.2f}")
        
        # 資産更新
        executor.update_equity(current_price)
        
        # 進捗表示
        if i % 1000 == 0:
            stats = executor.get_statistics()
            progress = (i / len(data)) * 100
            print(f"進捗: {progress:.1f}% - 取引: {trades_executed} - "
                  f"勝率: {stats['win_rate']:.1f}% - "
                  f"残高: {stats['final_balance']:,.0f}円")
    
    print(f"\n=== Lightweight ML Predictor Strategy 結果 ===")
    print(f"使用モデル: {model_type}")
    print(f"シグナル生成数: {signals_generated}")
    print(f"実行取引数: {trades_executed}")
    print(f"再学習回数: {retraining_count}")
    
    final_stats = executor.get_statistics()
    print(f"最終損益: {final_stats['total_pnl']:,.0f}円")
    print(f"勝率: {final_stats['win_rate']:.1f}%")
    print(f"プロフィットファクター: {final_stats['profit_factor']:.2f}")