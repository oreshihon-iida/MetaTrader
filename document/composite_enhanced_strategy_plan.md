# 複合指標とリスク管理強化によるボリンジャーバンド＋RSI戦略改善計画

## 1. 概要

複数時間足ボリンジャーバンド＋RSI戦略の性能を向上させるために、以下の2つの主要な改善アプローチを提案します：

1. **複合テクニカル指標の開発**
2. **高度なリスク管理システムの実装**

これらの改善により、勝率70%以上、プロフィットファクター2.0以上の目標達成を目指します。

## 2. 現状分析

現在の戦略は以下の特徴を持ちます：

- 複数時間足（15分足、1時間足、4時間足）のシグナルを重み付けして組み合わせる
- ボリンジャーバンドとRSIの逆張り（オーバーシュート時に逆張り）
- 季節性フィルター、価格アクションパターン、ボラティリティフィルターを適用

パフォーマンスの推移：
- 2000-2020年：平均勝率71.08%
- 2024-2025年：勝率42.86%、プロフィットファクター0.63

この性能低下は市場環境の変化によるものと考えられ、戦略の適応性を高める必要があります。

## 3. 複合テクニカル指標の開発

### 3.1 実装アプローチ

複数の指標を組み合わせて、より正確なシグナルを生成する複合指標を開発します。

#### 3.1.1 トレンド強度指標（Trend Strength Index）

ボリンジャーバンドとRSIに加えて、複数の移動平均線やMACDを組み合わせたトレンド強度指標を実装します。

```python
class TrendStrengthIndex:
    def __init__(self, price_data, window_short=20, window_med=50, window_long=200):
        self.data = price_data
        self.window_short = window_short
        self.window_med = window_med
        self.window_long = window_long
    
    def calculate(self):
        # 短期、中期、長期の移動平均線
        ma_short = self.data['Close'].rolling(self.window_short).mean()
        ma_med = self.data['Close'].rolling(self.window_med).mean()
        ma_long = self.data['Close'].rolling(self.window_long).mean()
        
        # 移動平均線の配列
        trend_alignment = pd.Series(0, index=self.data.index)
        
        # 上昇トレンドの強度計算
        uptrend = (ma_short > ma_med) & (ma_med > ma_long) & (self.data['Close'] > ma_short)
        downtrend = (ma_short < ma_med) & (ma_med < ma_long) & (self.data['Close'] < ma_short)
        
        # マルチタイムフレームRSIとの組み合わせ
        rsi = RSIIndicator(close=self.data['Close'], window=14).rsi()
        
        # トレンド強度指標
        trend_strength = pd.Series(0, index=self.data.index)
        
        # 上昇トレンド
        trend_strength[uptrend] = 1
        
        # 下降トレンド
        trend_strength[downtrend] = -1
        
        # RSIによる確認
        trend_strength[(uptrend) & (rsi > 50)] += 0.5
        trend_strength[(downtrend) & (rsi < 50)] -= 0.5
        
        # 正規化
        trend_strength = trend_strength / 1.5
        
        return trend_strength
```

#### 3.1.2 ボラティリティ調整型オシレーター（Volatility-Adjusted Oscillator）

ボラティリティに応じてRSIの感度を調整する新しいオシレーターを実装します。

```python
class VolatilityAdjustedOscillator:
    def __init__(self, price_data, rsi_window=14, vol_window=20):
        self.data = price_data
        self.rsi_window = rsi_window
        self.vol_window = vol_window
    
    def calculate(self):
        # 標準的なRSI
        rsi = RSIIndicator(close=self.data['Close'], window=self.rsi_window).rsi()
        
        # ボラティリティ（ATR）
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.rolling(self.vol_window).mean()
        
        # 平均ATR
        avg_atr = atr.rolling(100).mean()
        
        # ボラティリティ比率
        vol_ratio = atr / avg_atr
        
        # ボラティリティに応じたRSI閾値の調整
        adjusted_upper = 50 + (25 * vol_ratio).clip(20, 30)
        adjusted_lower = 50 - (25 * vol_ratio).clip(20, 30)
        
        # ボラティリティ調整型オシレーター値
        vao = pd.Series(0, index=self.data.index)
        
        # オーバーボートゾーン
        vao[rsi > adjusted_upper] = 1
        
        # オーバーソールドゾーン
        vao[rsi < adjusted_lower] = -1
        
        # 中間ゾーン
        mid_zone = (rsi >= adjusted_lower) & (rsi <= adjusted_upper)
        vao[mid_zone] = (rsi[mid_zone] - 50) / (adjusted_upper.mean() - 50)
        
        return vao, adjusted_upper, adjusted_lower
```

#### 3.1.3 マルチタイムフレーム確認指標（Multi-Timeframe Confirmation Index）

複数の時間足からの確認を行い、偽シグナルを減らす指標を実装します。

```python
class MultiTimeframeConfirmationIndex:
    def __init__(self, tf_data_dict, indicator_func):
        self.tf_data = tf_data_dict  # {'15min': df_15min, '1H': df_1h, '4H': df_4h}
        self.indicator_func = indicator_func  # 指標計算関数
        
    def calculate(self, base_tf='15min', weights=None):
        # デフォルトの重み
        if weights is None:
            weights = {
                '15min': 1.0,
                '1H': 2.0,
                '4H': 3.0
            }
        
        # 各時間足の指標値を計算
        tf_indicators = {}
        for tf, df in self.tf_data.items():
            tf_indicators[tf] = self.indicator_func(df)
        
        # ベース時間足のインデックス
        base_index = self.tf_data[base_tf].index
        
        # 確認指標の初期化
        confirmation_index = pd.Series(0.0, index=base_index)
        
        # 各時間足の指標を合成
        total_weight = sum(weights.values())
        
        for tf, indicator in tf_indicators.items():
            if tf == base_tf:
                resampled_indicator = indicator
            else:
                # 大きな時間足の指標をベース時間足にリサンプリング
                resampled_indicator = indicator.reindex(base_index, method='ffill')
            
            # 重み付けして合成
            confirmation_index += (resampled_indicator * weights[tf]) / total_weight
        
        return confirmation_index
```

### 3.2 統合方法

複合指標をボリンジャーバンド＋RSI戦略に統合します。

```python
class CompositeIndicatorStrategy(BollingerRsiEnhancedMTStrategy):
    def __init__(self, use_composite_indicators=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_composite_indicators = use_composite_indicators
        self.name = "複合指標拡張版ボリンジャーバンド＋RSI戦略"
    
    def generate_signals(self, df, year, processed_dir='data/processed'):
        # 通常の処理を実行
        result_df = super().generate_signals(df, year, processed_dir)
        
        if not self.use_composite_indicators:
            return result_df
        
        # 各時間足のデータを読み込む
        multi_tf_data = self.load_multi_timeframe_data(year, processed_dir)
        
        # トレンド強度指標の計算
        tsi = TrendStrengthIndex(result_df)
        trend_strength = tsi.calculate()
        result_df['trend_strength'] = trend_strength
        
        # ボラティリティ調整型オシレーターの計算
        vao = VolatilityAdjustedOscillator(result_df)
        vao_values, adj_upper, adj_lower = vao.calculate()
        result_df['vao'] = vao_values
        result_df['vao_upper'] = adj_upper
        result_df['vao_lower'] = adj_lower
        
        # マルチタイムフレーム確認関数の定義
        def calc_rsi(df):
            return RSIIndicator(close=df['Close'], window=14).rsi()
        
        # マルチタイムフレーム確認指標の計算
        mtci = MultiTimeframeConfirmationIndex(multi_tf_data, calc_rsi)
        confirmation_index = mtci.calculate(weights=self.timeframe_weights)
        result_df['confirmation_index'] = confirmation_index
        
        # シグナルの再評価と質の向上
        for i in range(1, len(result_df)):
            current_signal = result_df.iloc[i]['signal']
            
            if current_signal != 0:
                # 複合指標を使用したシグナル確認
                trend_str = result_df.iloc[i]['trend_strength']
                vao_val = result_df.iloc[i]['vao']
                confirm_val = result_df.iloc[i]['confirmation_index']
                
                signal_quality = 0
                
                # 買いシグナルの確認
                if current_signal == 1:
                    # トレンドとの一致（レンジ相場またはトレンドの方向への順張り）
                    if trend_str >= -0.3:  # トレンドに反していない
                        signal_quality += 1
                    
                    # VAOとの一致
                    if vao_val <= -0.5:  # オーバーソールド
                        signal_quality += 1
                    
                    # 時間足間の確認
                    if confirm_val <= -0.3:  # 複数時間足でのRSIオーバーソールド確認
                        signal_quality += 1
                
                # 売りシグナルの確認
                elif current_signal == -1:
                    # トレンドとの一致
                    if trend_str <= 0.3:  # トレンドに反していない
                        signal_quality += 1
                    
                    # VAOとの一致
                    if vao_val >= 0.5:  # オーバーボート
                        signal_quality += 1
                    
                    # 時間足間の確認
                    if confirm_val >= 0.3:  # 複数時間足でのRSIオーバーボート確認
                        signal_quality += 1
                
                # シグナル品質が低い場合はシグナルをキャンセル
                if signal_quality < 2:  # 最低2つの確認が必要
                    result_df.loc[result_df.index[i], 'signal'] = 0
                    result_df.loc[result_df.index[i], 'entry_price'] = np.nan
                    result_df.loc[result_df.index[i], 'sl_price'] = np.nan
                    result_df.loc[result_df.index[i], 'tp_price'] = np.nan
                    result_df.loc[result_df.index[i], 'strategy'] = None
                else:
                    # シグナル品質が高い場合は、リスク/リワード比を改善
                    if signal_quality == 3:  # 全ての確認がある場合
                        # リスク/リワード比を改善（より小さなSLとより大きなTP）
                        current_signal = result_df.iloc[i]['signal']
                        current_entry = result_df.iloc[i]['entry_price']
                        current_sl = result_df.iloc[i]['sl_price']
                        current_tp = result_df.iloc[i]['tp_price']
                        
                        # 利確レベルを20%拡大
                        tp_distance = abs(current_tp - current_entry)
                        new_tp_distance = tp_distance * 1.2
                        
                        # 損切りレベルを10%縮小
                        sl_distance = abs(current_sl - current_entry)
                        new_sl_distance = sl_distance * 0.9
                        
                        # 新しいSL/TPレベルを設定
                        if current_signal == 1:  # 買いシグナル
                            new_sl = current_entry - new_sl_distance
                            new_tp = current_entry + new_tp_distance
                        else:  # 売りシグナル
                            new_sl = current_entry + new_sl_distance
                            new_tp = current_entry - new_tp_distance
                        
                        result_df.loc[result_df.index[i], 'sl_price'] = new_sl
                        result_df.loc[result_df.index[i], 'tp_price'] = new_tp
        
        return result_df
```

## 4. 高度なリスク管理システムの実装

リスク管理を強化して、より安定したパフォーマンスを実現します。

### 4.1 実装アプローチ

#### 4.1.1 動的ポジションサイジング

市場環境とシグナル品質に基づいて、ポジションサイズを動的に調整します。

```python
class DynamicPositionSizer:
    def __init__(self, base_lot_size=0.01, max_risk_per_trade=0.02):
        self.base_lot_size = base_lot_size
        self.max_risk_per_trade = max_risk_per_trade  # 1トレードあたりの最大リスク（資金の2%）
    
    def calculate_position_size(self, account_balance, signal_quality, market_volatility, sl_pips):
        # 基本的なリスク計算
        risk_amount = account_balance * self.max_risk_per_trade
        
        # シグナル品質による調整（0.5〜1.5の範囲）
        quality_factor = 0.5 + (signal_quality / 3)  # signal_qualityは0〜3の範囲
        
        # ボラティリティによる調整（高ボラティリティでは小さなポジション）
        volatility_factor = 1.0 / market_volatility if market_volatility > 0 else 1.0
        volatility_factor = max(0.5, min(1.5, volatility_factor))  # 0.5〜1.5の範囲に制限
        
        # 損切り幅による調整
        risk_per_pip = risk_amount / sl_pips if sl_pips > 0 else risk_amount
        
        # 最終的なロットサイズ計算
        adjusted_lot_size = self.base_lot_size * quality_factor * volatility_factor
        
        # 最大リスクを超えないように調整
        max_lot_size = risk_per_pip / (sl_pips * 100)  # 1pipあたり100円と仮定
        
        # 最終的なロットサイズ（最大値を超えないように）
        final_lot_size = min(adjusted_lot_size, max_lot_size)
        
        # 最小ロットサイズ制限
        final_lot_size = max(self.base_lot_size, final_lot_size)
        
        return final_lot_size
```

#### 4.1.2 適応型損切り・利確レベル

市場ボラティリティとシグナル品質に基づいて、損切り・利確レベルを動的に調整します。

```python
class AdaptiveStopLossTakeProfit:
    def __init__(self, base_sl_pips=10.0, base_tp_pips=20.0, atr_multiplier=1.5):
        self.base_sl_pips = base_sl_pips
        self.base_tp_pips = base_tp_pips
        self.atr_multiplier = atr_multiplier
    
    def calculate_levels(self, df, index, signal, signal_quality, market_environment):
        current = df.iloc[index]
        entry_price = current['entry_price']
        
        # ATRの取得
        atr = current.get('atr', self.base_sl_pips)
        
        # 市場環境に基づく調整
        env_factors = {
            0: {'sl': 1.0, 'tp': 1.0},    # レンジ相場
            1: {'sl': 1.2, 'tp': 1.5},    # 上昇トレンド
            2: {'sl': 1.2, 'tp': 1.5},    # 下降トレンド
            3: {'sl': 1.5, 'tp': 2.0}     # 高ボラティリティ
        }
        
        env = market_environment if market_environment in env_factors else 0
        env_factor_sl = env_factors[env]['sl']
        env_factor_tp = env_factors[env]['tp']
        
        # シグナル品質による調整
        quality_factor_sl = 1.0 - (signal_quality * 0.1)  # 高品質シグナルでは小さなSL
        quality_factor_tp = 1.0 + (signal_quality * 0.1)  # 高品質シグナルでは大きなTP
        
        # 最終的なSL/TPの計算
        sl_pips = self.base_sl_pips * env_factor_sl * quality_factor_sl
        tp_pips = self.base_tp_pips * env_factor_tp * quality_factor_tp
        
        # ATRベースの調整
        sl_pips = max(sl_pips, atr * self.atr_multiplier * 0.5)
        tp_pips = max(tp_pips, atr * self.atr_multiplier * 1.0)
        
        # リスク/リワード比の確認と調整
        rr_ratio = tp_pips / sl_pips
        if rr_ratio < 1.5:
            # 最低でも1.5のリスク/リワード比を確保
            tp_pips = sl_pips * 1.5
        
        # 価格レベルの計算
        if signal == 1:  # 買いシグナル
            sl_price = entry_price - (sl_pips * 0.01)
            tp_price = entry_price + (tp_pips * 0.01)
        else:  # 売りシグナル
            sl_price = entry_price + (sl_pips * 0.01)
            tp_price = entry_price - (tp_pips * 0.01)
        
        return sl_price, tp_price, sl_pips, tp_pips
```

#### 4.1.3 ドローダウン制限とエクスポージャー管理

最大ドローダウンを制限し、市場エクスポージャーを管理します。

```python
class RiskManager:
    def __init__(self, max_drawdown_pct=10.0, max_exposure_pct=20.0, max_consecutive_losses=3):
        self.max_drawdown_pct = max_drawdown_pct  # 最大許容ドローダウン（%）
        self.max_exposure_pct = max_exposure_pct  # 最大市場エクスポージャー（%）
        self.max_consecutive_losses = max_consecutive_losses  # 連続損失の最大許容数
        
        self.peak_balance = 0
        self.current_drawdown_pct = 0
        self.current_exposure_pct = 0
        self.consecutive_losses = 0
    
    def update_metrics(self, current_balance, open_positions_value):
        # ピークバランスの更新
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # 現在のドローダウン計算
        if self.peak_balance > 0:
            self.current_drawdown_pct = (self.peak_balance - current_balance) / self.peak_balance * 100
        
        # 現在のエクスポージャー計算
        if current_balance > 0:
            self.current_exposure_pct = open_positions_value / current_balance * 100
    
    def can_open_position(self, is_winning_last=None):
        # 連続損失の更新
        if is_winning_last is not None:
            if is_winning_last:
                self.consecutive_losses = 0
            else:
                self.consecutive_losses += 1
        
        # トレード可能かどうかのチェック
        if self.current_drawdown_pct >= self.max_drawdown_pct:
            return False, "最大ドローダウン制限に達しました"
        
        if self.current_exposure_pct >= self.max_exposure_pct:
            return False, "最大エクスポージャー制限に達しました"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, "連続損失制限に達しました"
        
        return True, ""
    
    def adjust_position_size(self, base_position_size):
        # ドローダウンに基づくポジションサイズの調整
        drawdown_factor = 1.0 - (self.current_drawdown_pct / self.max_drawdown_pct)
        drawdown_factor = max(0.25, min(1.0, drawdown_factor))  # 最小25%、最大100%
        
        # 連続損失に基づく調整
        loss_factor = 1.0 - (self.consecutive_losses / self.max_consecutive_losses * 0.5)
        loss_factor = max(0.5, min(1.0, loss_factor))  # 最小50%、最大100%
        
        # 最終的な調整係数
        adjustment_factor = drawdown_factor * loss_factor
        
        return base_position_size * adjustment_factor
```

### 4.2 統合方法

リスク管理システムを戦略クラスに統合します。

```python
class EnhancedRiskManagementStrategy(CompositeIndicatorStrategy):
    def __init__(self, use_enhanced_risk=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_enhanced_risk = use_enhanced_risk
        self.name = "リスク管理強化版ボリンジャーバンド＋RSI戦略"
        
        self.position_sizer = DynamicPositionSizer()
        self.sl_tp_calculator = AdaptiveStopLossTakeProfit()
        self.risk_manager = RiskManager()
        
        self.account_balance = 200000  # 初期資金
        self.open_positions_value = 0
        self.last_trade_result = None
    
    def generate_signals(self, df, year, processed_dir='data/processed'):
        # 通常の処理を実行
        result_df = super().generate_signals(df, year, processed_dir)
        
        if not self.use_enhanced_risk:
            return result_df
        
        # ATRの計算
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1).fillna(df['Close'].iloc[0])
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.rolling(14).mean()
        
        result_df['atr'] = atr
        
        # シグナルの再評価とリスク管理の適用
        for i in range(1, len(result_df)):
            current_signal = result_df.iloc[i]['signal']
            
            if current_signal != 0:
                # シグナル品質の取得（複合指標から）
                signal_quality = 0
                
                if 'trend_strength' in result_df.columns:
                    trend_str = result_df.iloc[i]['trend_strength']
                    if (current_signal == 1 and trend_str >= -0.3) or (current_signal == -1 and trend_str <= 0.3):
                        signal_quality += 1
                
                if 'vao' in result_df.columns:
                    vao_val = result_df.iloc[i]['vao']
                    if (current_signal == 1 and vao_val <= -0.5) or (current_signal == -1 and vao_val >= 0.5):
                        signal_quality += 1
                
                if 'confirmation_index' in result_df.columns:
                    confirm_val = result_df.iloc[i]['confirmation_index']
                    if (current_signal == 1 and confirm_val <= -0.3) or (current_signal == -1 and confirm_val >= 0.3):
                        signal_quality += 1
                
                # 市場環境の取得
                market_env = 0  # デフォルトはレンジ相場
                
                # トレンド強度に基づく市場環境の判断
                if 'trend_strength' in result_df.columns:
                    trend_str = result_df.iloc[i]['trend_strength']
                    if trend_str > 0.5:
                        market_env = 1  # 上昇トレンド
                    elif trend_str < -0.5:
                        market_env = 2  # 下降トレンド
                
                # ボラティリティに基づく市場環境の判断
                if 'atr' in result_df.columns:
                    volatility = result_df.iloc[i]['atr'] / result_df.iloc[i]['Close']
                    avg_volatility = result_df['atr'].rolling(100).mean().iloc[i] / result_df['Close'].rolling(100).mean().iloc[i]
                    
                    if volatility > avg_volatility * 1.5:
                        market_env = 3  # 高ボラティリティ
                
                # リスク管理チェック
                can_trade, reason = self.risk_manager.can_open_position(self.last_trade_result)
                
                if not can_trade:
                    # トレード制限によりシグナルをキャンセル
                    result_df.loc[result_df.index[i], 'signal'] = 0
                    result_df.loc[result_df.index[i], 'entry_price'] = np.nan
                    result_df.loc[result_df.index[i], 'sl_price'] = np.nan
                    result_df.loc[result_df.index[i], 'tp_price'] = np.nan
                    result_df.loc[result_df.index[i], 'strategy'] = None
                    result_df.loc[result_df.index[i], 'risk_note'] = reason
                    continue
                
                # 適応型損切り・利確レベルの計算
                sl_price, tp_price, sl_pips, tp_pips = self.sl_tp_calculator.calculate_levels(
                    result_df, i, current_signal, signal_quality, market_env
                )
                
                # 市場ボラティリティの計算
                market_volatility = result_df.iloc[i]['atr'] / result_df.iloc[i]['Close']
                
                # 動的ポジションサイジング
                position_size = self.position_sizer.calculate_position_size(
                    self.account_balance, signal_quality, market_volatility, sl_pips
                )
                
                # リスク管理に基づく調整
                adjusted_position_size = self.risk_manager.adjust_position_size(position_size)
                
                # 結果の更新
                result_df.loc[result_df.index[i], 'sl_price'] = sl_price
                result_df.loc[result_df.index[i], 'tp_price'] = tp_price
                result_df.loc[result_df.index[i], 'position_size'] = adjusted_position_size
        
        return result_df
    
    def update_account_metrics(self, trade_result):
        # トレード結果に基づく口座情報の更新
        if trade_result['profit'] > 0:
            self.last_trade_result = True
        else:
            self.last_trade_result = False
        
        self.account_balance += trade_result['profit']
        self.open_positions_value = trade_result['open_positions_value']
        
        self.risk_manager.update_metrics(self.account_balance, self.open_positions_value)
```

## 5. 最終的な統合戦略

上記の2つの改善アプローチを統合した最終戦略を実装します。

```python
class CompositeEnhancedBollingerRsiStrategy(EnhancedRiskManagementStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "複合指標・リスク管理強化版ボリンジャーバンド＋RSI戦略"
    
    def backtest(self, df, year, processed_dir='data/processed'):
        # 通常のバックテスト処理
        signals_df = self.generate_signals(df, year, processed_dir)
        
        # バックテストエンジンの実行
        # (実装は省略)
        
        return signals_df
```

## 6. 実装と検証計画

### 6.1 実装ステップ

1. 複合指標の実装と検証
   - トレンド強度指標の実装
   - ボラティリティ調整型オシレーターの実装
   - マルチタイムフレーム確認指標の実装
   - 指標の評価と調整

2. リスク管理システムの実装と検証
   - 動的ポジションサイジングの実装
   - 適応型損切り・利確レベルの実装
   - ドローダウン制限とエクスポージャー管理の実装
   - リスク管理システムの評価と調整

3. 統合戦略の実装と検証
   - 各コンポーネントの統合
   - 全期間（2000-2025年）でのバックテスト
   - 最近の期間（2024-2025年）での詳細評価
   - パラメータの最終調整

### 6.2 検証方法

1. **時間分割検証**
   - トレーニング期間：2000-2020年
   - 検証期間：2021-2023年
   - テスト期間：2024-2025年

2. **パフォーマンス指標**
   - 勝率（目標：70%以上）
   - プロフィットファクター（目標：2.0以上）
   - 最大ドローダウン
   - シャープレシオ
   - 月別・年別パフォーマンス

3. **ロバスト性テスト**
   - 異なる市場環境でのパフォーマンス評価
   - パラメータ感度分析
   - ウォークフォワードテスト

## 7. 期待される効果

1. **シグナル品質の向上**
   - 複合指標による偽シグナルの削減
   - 高品質シグナルの特定と強化

2. **リスク管理の最適化**
   - 動的ポジションサイジングによる資金管理の改善
   - 適応型損切り・利確レベルによるリスク/リワード比の最適化
   - ドローダウン制限による資金保全

3. **全体的なパフォーマンス向上**
   - 勝率の向上（目標：70%以上）
   - プロフィットファクターの向上（目標：2.0以上）
   - 最大ドローダウンの削減

## 8. 結論

本計画では、複合指標と高度なリスク管理を組み合わせた包括的な戦略改善アプローチを提案しました。これらの改善により、変化する市場環境に適応し、一貫したパフォーマンスを実現することを目指します。

特に、複合指標の導入により、より正確なシグナル生成が可能になり、高度なリスク管理システムによって、資金の保全と効率的な運用が実現できます。

これらの改善を段階的に実装し、徹底的な検証を行うことで、目標とする勝率70%以上、プロフィットファクター2.0以上の達成を目指します。
