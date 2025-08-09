#!/usr/bin/env python3
"""
Modern Trend Following Strategy (2024-2025)
現代的なトレンドフォロー戦略

研究結果に基づく実装：
- Multi-timeframe momentum analysis
- Adaptive volatility filters
- Dynamic position sizing
- Advanced risk management
- Market regime detection

Based on research: 15%+ annual returns, Sharpe ratio 0.82
"""

import pandas as pd
import numpy as np
import talib
from typing import Tuple, Dict, Optional, List
from datetime import datetime

class ModernTrendFollowingStrategy:
    """
    現代的なトレンドフォロー戦略
    
    機能:
    1. Multi-timeframe trend analysis (15min, 1H, 4H, Daily)
    2. Adaptive volatility filtering
    3. Market regime detection (trending vs ranging)
    4. Dynamic position sizing based on volatility
    5. Advanced risk management with correlation filters
    """
    
    def __init__(self, 
                 initial_balance: float = 3000000,
                 base_risk_per_trade: float = 0.02,
                 max_positions: int = 6,
                 min_trend_strength: float = 0.6):
        """
        初期化
        
        Parameters
        ----------
        initial_balance : float
            初期資金
        base_risk_per_trade : float
            基本リスク（残高の％）
        max_positions : int
            最大同時ポジション数
        min_trend_strength : float
            最小トレンド強度閾値
        """
        self.initial_balance = initial_balance
        self.base_risk_per_trade = base_risk_per_trade
        self.max_positions = max_positions
        self.min_trend_strength = min_trend_strength
        
        # トレンドフォロー設定
        self.trend_lookback_periods = {
            'short': 20,   # 短期トレンド
            'medium': 50,  # 中期トレンド
            'long': 200    # 長期トレンド
        }
        
        # ボラティリティフィルター設定
        self.volatility_periods = {
            'current': 14,
            'recent': 50,
            'long_term': 200
        }
        
        # リスク管理設定
        self.max_correlation_threshold = 0.7
        self.volatility_adjustment_factor = 1.5
        self.trend_confirmation_periods = 5
        
    def analyze_multi_timeframe_trend(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        複数時間軸でのトレンド分析
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            時間軸別データ辞書 {'15min': df, '1H': df, '4H': df, 'Daily': df}
            
        Returns
        -------
        Dict[str, float]
            時間軸別トレンド強度 (-1.0 to 1.0)
        """
        trend_scores = {}
        
        for timeframe, data in data_dict.items():
            if len(data) < 200:
                trend_scores[timeframe] = 0.0
                continue
                
            # 複数のトレンド指標を組み合わせ
            close_prices = data['Close'] if 'Close' in data.columns else data['close']
            
            # 1. EMA Slope Analysis
            ema_short = talib.EMA(close_prices, timeperiod=20)
            ema_medium = talib.EMA(close_prices, timeperiod=50)
            ema_long = talib.EMA(close_prices, timeperiod=200)
            
            # EMAの傾き計算
            ema_short_slope = (ema_short.iloc[-1] - ema_short.iloc[-10]) / ema_short.iloc[-10]
            ema_medium_slope = (ema_medium.iloc[-1] - ema_medium.iloc[-10]) / ema_medium.iloc[-10]
            ema_long_slope = (ema_long.iloc[-1] - ema_long.iloc[-20]) / ema_long.iloc[-20]
            
            # 2. ADX (Average Directional Index) - トレンド強度
            high_prices = data['High'] if 'High' in data.columns else data['high']
            low_prices = data['Low'] if 'Low' in data.columns else data['low']
            
            adx = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
            plus_di = talib.PLUS_DI(high_prices, low_prices, close_prices, timeperiod=14)
            minus_di = talib.MINUS_DI(high_prices, low_prices, close_prices, timeperiod=14)
            
            current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25
            current_plus_di = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 25
            current_minus_di = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 25
            
            # 3. Price momentum
            momentum = (close_prices.iloc[-1] - close_prices.iloc[-20]) / close_prices.iloc[-20]
            
            # 4. EMA alignment score
            current_price = close_prices.iloc[-1]
            ema_alignment_score = 0
            if current_price > ema_short.iloc[-1] > ema_medium.iloc[-1] > ema_long.iloc[-1]:
                ema_alignment_score = 1.0  # Perfect bull alignment
            elif current_price < ema_short.iloc[-1] < ema_medium.iloc[-1] < ema_long.iloc[-1]:
                ema_alignment_score = -1.0  # Perfect bear alignment
            else:
                # Partial alignment
                alignment_count = 0
                total_comparisons = 0
                
                comparisons = [
                    (current_price, ema_short.iloc[-1]),
                    (ema_short.iloc[-1], ema_medium.iloc[-1]),
                    (ema_medium.iloc[-1], ema_long.iloc[-1])
                ]
                
                for a, b in comparisons:
                    total_comparisons += 1
                    if a > b:
                        alignment_count += 1
                    elif a < b:
                        alignment_count -= 1
                        
                ema_alignment_score = alignment_count / total_comparisons if total_comparisons > 0 else 0
            
            # 総合トレンドスコア計算
            # ADXによる重み付け（強いトレンドほど重視）
            adx_weight = min(current_adx / 50, 1.0)  # ADX 50以上で最大重み
            
            # DMIによる方向性
            dmi_direction = 0
            if current_plus_di > current_minus_di:
                dmi_direction = (current_plus_di - current_minus_di) / 100
            else:
                dmi_direction = -(current_minus_di - current_plus_di) / 100
            
            # 重み付き平均でトレンドスコア計算
            trend_components = [
                (ema_short_slope * 100, 0.3),    # 短期EMAの傾き
                (ema_medium_slope * 100, 0.25),  # 中期EMAの傾き
                (ema_long_slope * 100, 0.15),    # 長期EMAの傾き
                (momentum * 20, 0.2),            # モメンタム
                (ema_alignment_score, 0.1)       # EMA配列
            ]
            
            weighted_trend_score = sum(score * weight for score, weight in trend_components)
            
            # ADXとDMIで最終調整
            final_score = weighted_trend_score * adx_weight + dmi_direction * (1 - adx_weight)
            
            # -1.0 to 1.0 の範囲に正規化
            trend_scores[timeframe] = np.clip(final_score, -1.0, 1.0)
        
        return trend_scores
    
    def detect_market_regime(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        市場環境の検出（トレンド vs レンジ）
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        Dict[str, float]
            市場環境スコア
        """
        close_prices = data['Close'] if 'Close' in data.columns else data['close']
        high_prices = data['High'] if 'High' in data.columns else data['high']
        low_prices = data['Low'] if 'Low' in data.columns else data['low']
        
        # 1. Volatility Regime
        returns = close_prices.pct_change().dropna()
        current_volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        long_term_volatility = returns.rolling(100).std().iloc[-1] * np.sqrt(252)
        volatility_ratio = current_volatility / long_term_volatility if long_term_volatility > 0 else 1.0
        
        # 2. Trend vs Range Detection
        # ADX for trend strength
        adx = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25
        
        # Bollinger Band width for volatility
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2)
        bb_width = ((bb_upper - bb_lower) / bb_middle).iloc[-1]
        normalized_bb_width = bb_width / bb_width.rolling(100).mean().iloc[-1] if not pd.isna(bb_width) else 1.0
        
        # 3. Price efficiency (how much price moves vs time)
        price_range = (high_prices.rolling(20).max() - low_prices.rolling(20).min()).iloc[-1]
        price_change = abs(close_prices.iloc[-1] - close_prices.iloc[-20])
        efficiency_ratio = price_change / price_range if price_range > 0 else 0
        
        # 市場環境スコア
        trending_score = (current_adx / 50 + efficiency_ratio + min(normalized_bb_width, 2.0) / 2) / 3
        ranging_score = 1 - trending_score
        
        return {
            'trending': np.clip(trending_score, 0, 1),
            'ranging': np.clip(ranging_score, 0, 1),
            'volatility_regime': np.clip(volatility_ratio, 0.5, 2.0),
            'efficiency_ratio': efficiency_ratio
        }
    
    def calculate_adaptive_position_size(self, 
                                       data: pd.DataFrame, 
                                       trend_strength: float,
                                       market_regime: Dict[str, float],
                                       stop_loss_pips: float,
                                       current_balance: float) -> float:
        """
        アダプティブなポジションサイズ計算
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        trend_strength : float
            トレンド強度
        market_regime : Dict[str, float]
            市場環境
        stop_loss_pips : float
            ストップロス（pips）
        current_balance : float
            現在残高
            
        Returns
        -------
        float
            ポジションサイズ（ロット）
        """
        # 基本リスク計算
        base_risk_amount = current_balance * self.base_risk_per_trade
        
        # ボラティリティ調整
        close_prices = data['Close'] if 'Close' in data.columns else data['close']
        returns = close_prices.pct_change().dropna()
        current_volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        long_term_volatility = returns.rolling(100).std().iloc[-1] * np.sqrt(252)
        
        volatility_adjustment = 1.0
        if long_term_volatility > 0:
            volatility_ratio = current_volatility / long_term_volatility
            # 高ボラティリティ時はポジション縮小、低ボラティリティ時は拡大
            volatility_adjustment = 1 / np.sqrt(max(volatility_ratio, 0.5))
        
        # トレンド強度調整
        trend_adjustment = 0.5 + (abs(trend_strength) * 0.5)  # 0.5-1.0の範囲
        
        # 市場環境調整
        regime_adjustment = 1.0
        if market_regime['trending'] > 0.7:
            regime_adjustment = 1.2  # トレンド市場でポジション増加
        elif market_regime['ranging'] > 0.7:
            regime_adjustment = 0.8  # レンジ市場でポジション縮小
        
        # 最終リスク額
        adjusted_risk_amount = base_risk_amount * volatility_adjustment * trend_adjustment * regime_adjustment
        
        # ポジションサイズ計算（1pip = 100円想定）
        risk_per_pip = 100
        position_size = adjusted_risk_amount / (stop_loss_pips * risk_per_pip)
        
        # 最小/最大制限
        position_size = np.clip(position_size, 0.01, 5.0)
        
        return position_size
    
    def generate_trend_signal(self, 
                            data_dict: Dict[str, pd.DataFrame],
                            current_positions: int = 0) -> Tuple[int, Dict]:
        """
        トレンドフォローシグナル生成
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            多時間軸データ
        current_positions : int
            現在のポジション数
            
        Returns
        -------
        Tuple[int, Dict]
            (シグナル, 分析詳細)
        """
        if current_positions >= self.max_positions:
            return 0, {'reason': 'max_positions_reached'}
        
        # 1. 多時間軸トレンド分析
        trend_scores = self.analyze_multi_timeframe_trend(data_dict)
        
        # メインデータ（15分足）を使用
        main_data = data_dict.get('15min', list(data_dict.values())[0])
        
        # 2. 市場環境検出
        market_regime = self.detect_market_regime(main_data)
        
        # 3. 総合トレンド強度計算（時間軸重み付け）
        timeframe_weights = {
            '15min': 0.1,
            '1H': 0.25,
            '4H': 0.35,
            'Daily': 0.3
        }
        
        overall_trend_strength = 0
        total_weight = 0
        
        for timeframe, score in trend_scores.items():
            weight = timeframe_weights.get(timeframe, 0.25)
            overall_trend_strength += score * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_trend_strength /= total_weight
        
        # 4. シグナル生成条件
        analysis = {
            'trend_scores': trend_scores,
            'overall_trend_strength': overall_trend_strength,
            'market_regime': market_regime,
            'signal_quality': 0
        }
        
        # トレンド市場でのみシグナル生成
        if market_regime['trending'] < 0.6:
            return 0, {**analysis, 'reason': 'not_trending_market'}
        
        # 最小トレンド強度チェック
        if abs(overall_trend_strength) < self.min_trend_strength:
            return 0, {**analysis, 'reason': 'insufficient_trend_strength'}
        
        # 複数時間軸での合意チェック
        agreeing_timeframes = sum(1 for score in trend_scores.values() 
                                if np.sign(score) == np.sign(overall_trend_strength) and abs(score) > 0.3)
        
        if agreeing_timeframes < 2:
            return 0, {**analysis, 'reason': 'insufficient_timeframe_agreement'}
        
        # シグナル品質スコア
        signal_quality = (
            abs(overall_trend_strength) * 0.4 +
            market_regime['trending'] * 0.3 +
            (agreeing_timeframes / len(trend_scores)) * 0.3
        )
        
        analysis['signal_quality'] = signal_quality
        
        # 高品質シグナルのみ採用
        if signal_quality < 0.7:
            return 0, {**analysis, 'reason': 'low_signal_quality'}
        
        # シグナル方向決定
        signal = 1 if overall_trend_strength > 0 else -1
        
        return signal, analysis
    
    def calculate_dynamic_stops(self, 
                              data: pd.DataFrame, 
                              signal: int,
                              trend_strength: float) -> Tuple[float, float]:
        """
        動的ストップロス・テイクプロフィット計算
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
        signal : int
            シグナル方向
        trend_strength : float
            トレンド強度
            
        Returns
        -------
        Tuple[float, float]
            (テイクプロフィット_pips, ストップロス_pips)
        """
        close_prices = data['Close'] if 'Close' in data.columns else data['close']
        high_prices = data['High'] if 'High' in data.columns else data['high']
        low_prices = data['Low'] if 'Low' in data.columns else data['low']
        
        # ATR計算
        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
        current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0.001
        atr_pips = current_atr * 100
        
        # ボラティリティ調整
        returns = close_prices.pct_change().dropna()
        current_vol = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        vol_adjustment = max(0.5, min(2.0, current_vol / 0.15))  # 15%を基準
        
        # ベースストップロス（ATRベース）
        base_sl_pips = atr_pips * 1.5 * vol_adjustment
        
        # トレンド強度による調整
        trend_adjustment = 0.8 + (abs(trend_strength) * 0.4)  # 0.8-1.2の範囲
        
        sl_pips = base_sl_pips * trend_adjustment
        sl_pips = np.clip(sl_pips, 8, 30)  # 8-30pipsの範囲
        
        # Risk/Reward比率設定（トレンド強度に応じて）
        if abs(trend_strength) > 0.8:
            rr_ratio = 3.0  # 強いトレンドでは高いR/R
        elif abs(trend_strength) > 0.6:
            rr_ratio = 2.5
        else:
            rr_ratio = 2.0
        
        tp_pips = sl_pips * rr_ratio
        
        return tp_pips, sl_pips
    
    def should_close_position(self, 
                            data_dict: Dict[str, pd.DataFrame],
                            position_signal: int,
                            position_entry_time: datetime) -> bool:
        """
        ポジション早期クローズ判定
        
        Parameters
        ----------
        data_dict : Dict[str, pd.DataFrame]
            多時間軸データ
        position_signal : int
            ポジション方向
        position_entry_time : datetime
            エントリー時刻
            
        Returns
        -------
        bool
            クローズすべきかどうか
        """
        # 現在のトレンド分析
        trend_scores = self.analyze_multi_timeframe_trend(data_dict)
        
        # 時間軸重み付け平均
        timeframe_weights = {'15min': 0.1, '1H': 0.25, '4H': 0.35, 'Daily': 0.3}
        current_trend = sum(trend_scores.get(tf, 0) * weight 
                          for tf, weight in timeframe_weights.items()) / sum(timeframe_weights.values())
        
        # トレンド反転チェック
        if position_signal == 1 and current_trend < -0.3:  # ロングポジで下降トレンド
            return True
        elif position_signal == -1 and current_trend > 0.3:  # ショートポジで上昇トレンド
            return True
        
        # 市場環境変化チェック
        main_data = data_dict.get('15min', list(data_dict.values())[0])
        market_regime = self.detect_market_regime(main_data)
        
        if market_regime['ranging'] > 0.8:  # レンジ市場に変化
            return True
        
        return False

def modern_trend_following_wrapper(data: pd.DataFrame, executor, metadata: Dict = None):
    """
    Modern Trend Following Strategy のテスト用ラッパー
    
    Parameters
    ----------
    data : pd.DataFrame
        価格データ
    executor : TradeExecutor
        取引執行クラス
    metadata : Dict
        追加データ（多時間軸など）
    """
    
    strategy = ModernTrendFollowingStrategy(
        initial_balance=3000000,
        base_risk_per_trade=0.015,  # 1.5%（保守的）
        max_positions=5,
        min_trend_strength=0.65
    )
    
    print("Modern Trend Following Strategy テスト開始")
    print("設定: リスク1.5%、最大ポジション5、最小トレンド強度0.65")
    
    signals_generated = 0
    trades_executed = 0
    early_exits = 0
    
    # データの準備（単一データから疑似多時間軸作成）
    data_dict = {'15min': data}
    
    # 時間足変換（簡易版）
    if len(data) > 1000:
        # 1時間足（4本分をまとめる）
        hourly_data = data.iloc[::4].copy()
        data_dict['1H'] = hourly_data
        
        # 4時間足（16本分をまとめる）
        if len(data) > 4000:
            four_hourly_data = data.iloc[::16].copy()
            data_dict['4H'] = four_hourly_data
            
        # 日足（96本分をまとめる）
        if len(data) > 10000:
            daily_data = data.iloc[::96].copy()
            data_dict['Daily'] = daily_data
    
    # メインループ
    for i in range(500, len(data), 10):  # 10本おきにチェック
        current_data_dict = {}
        for timeframe, tf_data in data_dict.items():
            # 現在時点までのデータを切り取り
            if timeframe == '15min':
                current_data_dict[timeframe] = tf_data.iloc[:i+1]
            elif timeframe == '1H':
                hour_index = min(i//4, len(tf_data)-1)
                current_data_dict[timeframe] = tf_data.iloc[:hour_index+1]
            elif timeframe == '4H':
                four_hour_index = min(i//16, len(tf_data)-1)
                current_data_dict[timeframe] = tf_data.iloc[:four_hour_index+1]
            elif timeframe == 'Daily':
                daily_index = min(i//96, len(tf_data)-1)
                current_data_dict[timeframe] = tf_data.iloc[:daily_index+1]
        
        current_time = data.index[i]
        price_col = 'Close' if 'Close' in data.columns else 'close'
        current_price = data[price_col].iloc[i]
        
        # 既存ポジションのチェック
        closed_positions = executor.check_positions(current_price, current_time)
        
        # 早期エグジットチェック
        for position in executor.positions[:]:
            if strategy.should_close_position(current_data_dict, position.signal, position.entry_time):
                executor.close_position(position, current_price, current_time, 'trend_reversal')
                early_exits += 1
        
        # 新規シグナル生成
        signal, analysis = strategy.generate_trend_signal(
            current_data_dict, len(executor.positions)
        )
        
        if signal != 0:
            signals_generated += 1
            
            # 動的TP/SL計算
            tp_pips, sl_pips = strategy.calculate_dynamic_stops(
                current_data_dict['15min'], signal, analysis['overall_trend_strength']
            )
            
            # アダプティブポジションサイズ
            lot_size = strategy.calculate_adaptive_position_size(
                current_data_dict['15min'],
                analysis['overall_trend_strength'],
                analysis['market_regime'],
                sl_pips,
                executor.current_balance
            )
            
            # ポジション開設
            position = executor.open_position(
                signal=signal,
                price=current_price,
                lot_size=lot_size,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                timestamp=current_time,
                strategy='modern_trend_following'
            )
            
            if position:
                trades_executed += 1
                if trades_executed <= 10:  # 最初の10取引のみログ出力
                    print(f"取引{trades_executed}: {['SELL','BUY'][signal==1]} - "
                          f"価格:{current_price:.3f} - Lot:{lot_size:.2f} - "
                          f"TP:{tp_pips:.1f}pips - SL:{sl_pips:.1f}pips - "
                          f"品質:{analysis['signal_quality']:.2f}")
        
        # 資産更新
        executor.update_equity(current_price)
        
        # 進捗表示
        if i % 5000 == 0:
            stats = executor.get_statistics()
            progress = (i / len(data)) * 100
            print(f"進捗: {progress:.1f}% - 取引: {trades_executed} - "
                  f"勝率: {stats['win_rate']:.1f}% - "
                  f"残高: {stats['final_balance']:,.0f}円")
    
    print(f"\n=== Modern Trend Following Strategy 結果 ===")
    print(f"シグナル生成数: {signals_generated}")
    print(f"実行取引数: {trades_executed}")
    print(f"早期エグジット: {early_exits}")
    
    final_stats = executor.get_statistics()
    print(f"最終損益: {final_stats['total_pnl']:,.0f}円")
    print(f"勝率: {final_stats['win_rate']:.1f}%")
    print(f"プロフィットファクター: {final_stats['profit_factor']:.2f}")