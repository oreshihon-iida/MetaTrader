# 短期版戦略の最適化計画

## 現状分析

### 現在のパラメータ設定
```python
default_params = {
    'bb_window': 20,
    'bb_dev': 1.6,          # 標準偏差を1.4から1.6に調整してノイズを減少
    'rsi_window': 14,
    'rsi_upper': 55,        # RSI閾値を60から55に調整して高品質シグナルに限定
    'rsi_lower': 45,        # RSI閾値を40から45に調整して高品質シグナルに限定
    'sl_pips': 3.0,         # 損切り幅は維持
    'tp_pips': 7.5,         # 利確幅を6.0から7.5に拡大してリスク・リワード比を改善
    'atr_window': 14,
    'atr_sl_multiplier': 0.8,
    'atr_tp_multiplier': 2.0,  # ATRベースの利確乗数を1.6から2.0に拡大
    'use_adaptive_params': True,
    'trend_filter': False,
    'vol_filter': True,     # ボラティリティフィルターを有効化して高ボラティリティ時のみ取引
    'time_filter': True,
    'use_multi_timeframe': True,
    'timeframe_weights': {'15min': 1.0},  # 15分足のみを使用
    'use_seasonal_filter': False,
    'use_price_action': False,
    'consecutive_limit': 2
}
```

### 現在のフィルター設定
```python
def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
    if not super()._apply_filters(df, i):
        return False
        
    if self.vol_filter:
        atr = df['atr'].iloc[i]
        atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.8
        if atr < atr_threshold:
            return False
    
    if self.time_filter:
        hour = df.index[i].hour
        if not ((0 <= hour < 2) or (8 <= hour < 10) or (13 <= hour < 15)):
            return False
            
    return True
```

### 年別パフォーマンス
| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |
| --- | --- | --- | --- | --- |
| 2023 | 489 | 27.81 | 1.08 | 46.07 |
| 2024 | 566 | 27.92 | 0.98 | -13.62 |
| 2025 | 174 | 31.03 | 1.27 | 62.43 |
| **合計** | **1,229** | **28.32** | **1.27** | **94.88** |

### 問題点
1. 勝率が目標（70%）に対して大幅に低い（28.32%）
2. プロフィットファクターが目標（2.0）に対して低い（1.27）
3. 2024年は赤字（-13.62）
4. 2025年は取引数が少ない（174）が、最も高いPF（1.27）と勝率（31.03%）を記録

## 2025年の成功要因分析

2025年のパフォーマンスが最も良かった理由を分析します：

1. **取引数の減少**: 2023年（489）、2024年（566）と比較して2025年（174）は取引数が大幅に減少しています。これは、より厳格なフィルタリングによって低品質のシグナルが除外された可能性があります。

2. **勝率の向上**: 2025年の勝率（31.03%）は他の年と比較して高くなっています。これは、シグナル品質の向上を示しています。

3. **プロフィットファクターの向上**: 2025年のPF（1.27）は他の年と比較して高くなっています。これは、リスク・リワード比の改善を示しています。

4. **市場環境の違い**: 2025年の市場環境が戦略のパラメータに適していた可能性があります。

## 最適化提案

### 中間目標
- 勝率: 50%
- プロフィットファクター: 1.0

### 1. シグナル生成条件の最適化

```python
# 現在の条件
if (previous['Close'] >= previous['bb_upper'] * 0.75 or previous['rsi'] >= self.rsi_upper * 0.60):
    # 売りシグナル
elif (previous['Close'] <= previous['bb_lower'] * 1.25 or previous['rsi'] <= self.rsi_lower * 1.40):
    # 買いシグナル
```

**提案**:
```python
# 最適化条件
if (previous['Close'] >= previous['bb_upper'] * 0.85 and previous['rsi'] >= self.rsi_upper * 0.80):
    # 売りシグナル
elif (previous['Close'] <= previous['bb_lower'] * 1.15 and previous['rsi'] <= self.rsi_lower * 1.20):
    # 買いシグナル
```

理由: 条件を「or」から「and」に変更し、閾値を厳格化することで、シグナル品質を向上させます。これにより取引数は減少しますが、勝率とPFが向上する可能性があります。

### 2. RSI閾値の調整

```python
# 現在の設定
'rsi_upper': 55,
'rsi_lower': 45,
```

**提案**:
```python
# 最適化設定
'rsi_upper': 60,
'rsi_lower': 40,
```

理由: RSI閾値の範囲を広げることで、より極端な過買い・過売り状態でのみシグナルを生成します。これにより、勝率が向上する可能性があります。

### 3. ボリンジャーバンド幅の調整

```python
# 現在の設定
'bb_dev': 1.6,
```

**提案**:
```python
# 最適化設定
'bb_dev': 1.8,
```

理由: ボリンジャーバンド幅を広げることで、より極端な価格変動でのみシグナルを生成します。これにより、ノイズを減少させ、勝率が向上する可能性があります。

### 4. リスク・リワード比の最適化

```python
# 現在の設定
'sl_pips': 3.0,
'tp_pips': 7.5,
'atr_sl_multiplier': 0.8,
'atr_tp_multiplier': 2.0,
```

**提案**:
```python
# 最適化設定
'sl_pips': 2.5,
'tp_pips': 8.0,
'atr_sl_multiplier': 0.7,
'atr_tp_multiplier': 2.2,
```

理由: 損切り幅を小さく、利確幅を大きくすることで、リスク・リワード比を改善します。これにより、勝率が低くてもプロフィットファクターが向上する可能性があります。

### 5. 時間フィルターの最適化

```python
# 現在の設定
if not ((0 <= hour < 2) or (8 <= hour < 10) or (13 <= hour < 15)):
    return False
```

**提案**:
```python
# 最適化設定
if not ((1 <= hour < 3) or (8 <= hour < 10) or (14 <= hour < 16)):
    return False
```

理由: 2025年のデータ分析に基づいて、最も勝率の高い時間帯に調整します。これにより、シグナル品質が向上する可能性があります。

### 6. ボラティリティフィルターの最適化

```python
# 現在の設定
atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.8
if atr < atr_threshold:
    return False
```

**提案**:
```python
# 最適化設定
atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.9
if atr < atr_threshold:
    return False

# 高ボラティリティ時のフィルターも追加
atr_upper_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 1.8
if atr > atr_upper_threshold:
    return False
```

理由: ボラティリティが低すぎる場合と高すぎる場合の両方をフィルタリングすることで、適切なボラティリティ環境でのみ取引を行います。これにより、シグナル品質が向上する可能性があります。

### 7. 価格アクションパターンの導入

```python
# 新規追加
'use_price_action': True,
```

理由: 価格アクションパターン（ピンバー、エンゲルフィングなど）を導入することで、シグナル品質を向上させます。これにより、勝率が向上する可能性があります。

### 8. 連続損失管理の強化

```python
# 現在の設定
self.consecutive_losses = 0
self.max_consecutive_losses = 3

if self.consecutive_losses >= self.max_consecutive_losses:
    return base_size * 0.5
```

**提案**:
```python
# 最適化設定
self.consecutive_losses = 0
self.max_consecutive_losses = 2
self.win_streak = 0
self.max_win_streak = 3

if self.consecutive_losses >= self.max_consecutive_losses:
    return base_size * 0.5
elif self.win_streak >= self.max_win_streak:
    return base_size * 1.5
```

理由: 連続損失時のポジションサイズ削減に加えて、連続勝利時のポジションサイズ増加を導入します。これにより、勝率の高い期間での利益を最大化する可能性があります。

## 実装ステップ

1. **シグナル生成条件の最適化**: シグナル生成条件を「or」から「and」に変更し、閾値を調整します。
2. **RSI閾値とボリンジャーバンド幅の調整**: RSI閾値の範囲を広げ、ボリンジャーバンド幅を広げます。
3. **リスク・リワード比の最適化**: 損切り幅を小さく、利確幅を大きくします。
4. **時間フィルターとボラティリティフィルターの最適化**: 最も勝率の高い時間帯に調整し、適切なボラティリティ環境でのみ取引を行います。
5. **価格アクションパターンの導入**: 価格アクションパターンを導入します。
6. **連続損失管理の強化**: 連続損失時のポジションサイズ削減に加えて、連続勝利時のポジションサイズ増加を導入します。

## 検証方法

1. 各最適化ステップごとにバックテストを実行し、勝率とプロフィットファクターの変化を確認します。
2. 最も効果的な最適化ステップを特定し、組み合わせて最終的な最適化を行います。
3. 2023年、2024年、2025年の全期間でバックテストを実行し、一貫したパフォーマンス向上を確認します。

## 期待される結果

- 勝率: 28.32% → 50%（中間目標）→ 70%（最終目標）
- プロフィットファクター: 1.27 → 1.5（中間目標）→ 2.0（最終目標）
- 純利益: 94.88 → 150+（中間目標）→ 300+（最終目標）
