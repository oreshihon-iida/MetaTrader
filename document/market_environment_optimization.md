# 市場環境適応型パラメータとフィルターの最適化

## 概要
本ドキュメントでは、FX取引戦略の市場環境適応型パラメータとフィルターの最適化について説明します。目標は勝率70%とプロフィットファクター2.0を達成することです。

## 実装内容

### 1. 市場環境検出アルゴリズムの改善

市場環境を4種類（通常、トレンド、高ボラティリティ、レンジ）に分類するアルゴリズムを最適化しました。

```python
def _detect_market_environment(self, df: pd.DataFrame, i: int) -> str:
    if i < 50:
        return 'normal'
    
    recent_atr = df['atr'].iloc[i]
    avg_atr = df['atr'].iloc[i-20:i].mean()
    atr_ratio = recent_atr / avg_atr if avg_atr > 0 else 1.0
    
    price_change = abs(df['Close'].iloc[i] - df['Close'].iloc[i-20])
    price_range = df['High'].iloc[i-20:i].max() - df['Low'].iloc[i-20:i].min()
    price_change_ratio = price_change / price_range if price_range > 0 else 0.5
    
    ma_slope = (df['ma_50'].iloc[i] - df['ma_50'].iloc[i-10]) / 10
    ma_slope_normalized = abs(ma_slope) / df['Close'].iloc[i] * 1000  # 1000pipsあたりの傾き
    
    if atr_ratio > 1.8:  # 1.5から1.8に緩和
        return 'volatile'  # ボラティリティが高い
    elif ma_slope_normalized > 0.4:  # 0.5から0.4に緩和して検出率を向上
        return 'trending'  # トレンドが強い
    elif price_change_ratio < 0.25:  # 0.3から0.25に厳格化してレンジ相場の精度を向上
        return 'ranging'   # レンジ相場
    else:
        return 'normal'    # 通常の市場環境
```

主な変更点：
- ATR比率閾値: 1.5 → 1.8（高ボラティリティ環境の検出精度向上）
- MA傾き閾値: 0.5 → 0.4（トレンド環境の検出率向上）
- 価格変化率閾値: 0.3 → 0.25（レンジ相場の検出精度向上）

### 2. 市場環境別パラメータの最適化

各市場環境に最適なRSI閾値とボリンジャーバンド幅を設定しました。

| 市場環境 | RSI上限 | RSI下限 | BBバンド幅 | SL(pips) | TP(pips) |
|---------|--------|--------|-----------|---------|---------|
| 通常     | 70     | 30     | 2.0       | 2.0     | 10.0    |
| トレンド  | 80     | 25     | 2.2       | 2.5     | 12.5    |
| 高ボラ   | 85     | 15     | 2.5       | 3.0     | 15.0    |
| レンジ   | 65     | 35     | 1.6       | 1.5     | 7.5     |

主な変更点：
- トレンド相場: RSI上限 75 → 80（トレンド相場での逆張りを抑制）
- 高ボラティリティ相場: RSI上限 80 → 85, RSI下限 20 → 15（極端な値を許容）
- レンジ相場: ボリンジャーバンド幅 1.8 → 1.6（シグナル精度向上）

### 3. トレンドフィルターの最適化

トレンドフィルターを改善し、過度なフィルタリングを防止しました。

```python
def _apply_trend_filter(self, df: pd.DataFrame, i: int) -> bool:
    # 省略...
    
    if df['rsi'].iloc[i] < self.rsi_lower and df['Close'].iloc[i] < df['lower_band'].iloc[i]:
        # 買いシグナルの場合
        if ma_20 < ma_50 < ma_100:
            # 強い下降トレンドでの買いを除外
            ma_slope = (ma_20 - df['ma_20'].iloc[i-10]) / 10 if i >= 10 else 0
            if ma_slope < -0.0005:  # 強い下降傾向のみ除外
                return False
        # 以下省略...
    
    elif df['rsi'].iloc[i] > self.rsi_upper and df['Close'].iloc[i] > df['upper_band'].iloc[i]:
        # 売りシグナルの場合
        if ma_20 > ma_50 > ma_100:
            # 強い上昇トレンドでの売りを除外
            ma_slope = (ma_20 - df['ma_20'].iloc[i-10]) / 10 if i >= 10 else 0
            if ma_slope > 0.0005:  # 強い上昇傾向のみ除外
                return False
        # 以下省略...
```

主な変更点：
- 強いトレンドでの逆張りのみを除外する条件に変更
- MA傾きの閾値（±0.0005）を導入して過度なフィルタリングを防止

### 4. 時間帯フィルターの最適化

取引時間帯を最適化し、高品質なシグナルが発生しやすい時間帯に集中しました。

```python
def _apply_time_filter(self, df: pd.DataFrame, i: int) -> bool:
    # 省略...
    
    hour = df.index[i].hour
    weekday = df.index[i].weekday()
    month = df.index[i].month
    
    # アジア・欧州セッションの中心時間帯に限定
    if not ((1 <= hour < 6) or (8 <= hour < 10)):  # UTCで調整
        return False
    
    # 月曜朝と金曜夕方を除外
    if weekday == 0 or weekday == 4:
        if (weekday == 0 and hour < 3) or (weekday == 4 and hour > 12):
            return False
    
    # 低流動性の月を除外
    if month in [2, 8]:
        return False
        
    return True
```

主な変更点：
- 取引時間帯をUTC 1-6時と8-10時に限定（東京・ロンドンセッションの中心時間帯）
- 月曜朝と金曜夕方の不安定な時間帯を除外
- 低流動性の月（2月、8月）を除外

### 5. ボラティリティフィルターの調整

ボラティリティフィルターを調整し、より多くのシグナルを許可しました。

```python
if self.vol_filter:
    atr = df['atr'].iloc[i]
    avg_atr = df['atr'].iloc[i-20:i].mean()
    
    if atr < avg_atr * 0.6:  # 0.7から0.6に緩和
        return False
    
    if atr > avg_atr * 2.0:  # 1.8から2.0に緩和
        return False
```

主な変更点：
- 下限閾値: 0.7 → 0.6（より多くのシグナルを許可）
- 上限閾値: 1.8 → 2.0（極端な高ボラティリティでも取引可能に）

### 6. 損益分岐点勝率の計算と表示

バックテスト結果に損益分岐点勝率を計算・表示する機能を追加しました。

```python
# 損益分岐点となる勝率の計算
avg_win = gross_profit / wins if wins > 0 else 0
avg_loss = gross_loss / losses if losses > 0 else 0
risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

# PFが1の場合は50%、それ以外の場合はPF / (PF + RR)
breakeven_win_rate = 50.0 if profit_factor == 1.0 else (profit_factor / (profit_factor + risk_reward_ratio)) * 100
```

計算式：
- リスク・リワード比（RR）= 平均利益 ÷ 平均損失
- 損益分岐点勝率 = PF / (PF + RR) * 100（PFが1の場合は50%）

## 期待される効果

1. 市場環境検出の精度向上
   - より正確な市場環境分類による適切なパラメータ選択
   - 各市場環境に最適化されたシグナル生成

2. シグナル品質の向上
   - トレンドフィルターの最適化によるシグナル数増加
   - 時間帯フィルターの最適化による高品質シグナルの集中

3. パフォーマンス指標の改善
   - 勝率の向上（目標：70%以上）
   - プロフィットファクターの向上（目標：2.0以上）
   - 総利益の増加

4. リスク管理の強化
   - 市場環境に応じた適切なSL/TP設定
   - 損益分岐点勝率の把握によるリスク評価の向上

## 今後の課題

1. 実際のバックテストデータに基づく検証
   - 複数年のデータでの検証
   - パラメータの微調整

2. 市場環境検出アルゴリズムのさらなる改善
   - 機械学習の導入検討
   - より多くの指標の組み合わせ

3. 複数時間足分析の強化
   - 短期・中期・長期の時間足の組み合わせ最適化
   - 時間足ごとの重み付け調整

4. ポートフォリオアプローチの検討
   - 複数戦略の組み合わせ
   - 資金配分の最適化
