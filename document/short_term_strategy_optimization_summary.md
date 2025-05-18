# 短期版戦略最適化サマリー

## 現状分析

### パフォーマンス指標
| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |
| --- | --- | --- | --- | --- |
| 2023 | 489 | 27.81 | 1.08 | 46.07 |
| 2024 | 566 | 27.92 | 0.98 | -13.62 |
| 2025 | 174 | 31.03 | 1.27 | 62.43 |
| **合計** | **1,229** | **28.32** | **1.27** | **94.88** |

### 主要な問題点
1. 勝率が目標（70%）に対して大幅に低い（28.32%）
2. プロフィットファクターが目標（2.0）に対して低い（1.27）
3. 2024年は赤字（-13.62）
4. 取引数が多すぎる可能性（特に2023年と2024年）

### 2025年の成功要因
1. 取引数の減少（174）により、低品質シグナルが除外された
2. 勝率の向上（31.03%）
3. プロフィットファクターの向上（1.27）
4. リスク・リワード比の改善

## 最適化提案（中間目標：勝率50%、PF1.0）

### 1. シグナル生成条件の厳格化
```python
# 現在の条件（OR条件）
if (previous['Close'] >= previous['bb_upper'] * 0.75 or previous['rsi'] >= self.rsi_upper * 0.60):
    # 売りシグナル
elif (previous['Close'] <= previous['bb_lower'] * 1.25 or previous['rsi'] <= self.rsi_lower * 1.40):
    # 買いシグナル

# 提案条件（AND条件）
if (previous['Close'] >= previous['bb_upper'] * 0.85 and previous['rsi'] >= self.rsi_upper * 0.80):
    # 売りシグナル
elif (previous['Close'] <= previous['bb_lower'] * 1.15 and previous['rsi'] <= self.rsi_lower * 1.20):
    # 買いシグナル
```

### 2. RSI閾値とボリンジャーバンド幅の調整
```python
# 現在の設定
'rsi_upper': 55,
'rsi_lower': 45,
'bb_dev': 1.6,

# 提案設定
'rsi_upper': 60,
'rsi_lower': 40,
'bb_dev': 1.8,
```

### 3. リスク・リワード比の最適化
```python
# 現在の設定
'sl_pips': 3.0,
'tp_pips': 7.5,
'atr_sl_multiplier': 0.8,
'atr_tp_multiplier': 2.0,

# 提案設定
'sl_pips': 2.5,
'tp_pips': 8.0,
'atr_sl_multiplier': 0.7,
'atr_tp_multiplier': 2.2,
```

### 4. 時間フィルターとボラティリティフィルターの最適化
```python
# 現在の時間フィルター
if not ((0 <= hour < 2) or (8 <= hour < 10) or (13 <= hour < 15)):
    return False

# 提案時間フィルター（2025年データに基づく）
if not ((1 <= hour < 3) or (8 <= hour < 10) or (14 <= hour < 16)):
    return False

# 現在のボラティリティフィルター
atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.8
if atr < atr_threshold:
    return False

# 提案ボラティリティフィルター（上限と下限）
atr_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 0.9
if atr < atr_threshold:
    return False

atr_upper_threshold = df['atr'].rolling(window=20).mean().iloc[i] * 1.8
if atr > atr_upper_threshold:
    return False
```

### 5. 価格アクションパターンの導入
```python
# 新規追加
'use_price_action': True,
```

### 6. 連続損失管理の強化
```python
# 現在の設定
self.consecutive_losses = 0
self.max_consecutive_losses = 3

if self.consecutive_losses >= self.max_consecutive_losses:
    return base_size * 0.5

# 提案設定（連続勝利時のポジションサイズ増加を追加）
self.consecutive_losses = 0
self.max_consecutive_losses = 2
self.win_streak = 0
self.max_win_streak = 3

if self.consecutive_losses >= self.max_consecutive_losses:
    return base_size * 0.5
elif self.win_streak >= self.max_win_streak:
    return base_size * 1.5
```

## 段階的改善ロードマップ

### フェーズ1：シグナル品質向上（目標：勝率35%、PF1.0）
1. シグナル生成条件をORからANDに変更
2. ボリンジャーバンド幅を1.6から1.8に拡大
3. ボラティリティフィルターに上限を追加

### フェーズ2：リスク・リワード比の最適化（目標：勝率40%、PF1.2）
1. 損切り幅を3.0から2.5に縮小
2. 利確幅を7.5から8.0に拡大
3. ATRベースの乗数を調整

### フェーズ3：時間フィルターの最適化（目標：勝率45%、PF1.4）
1. 2025年データに基づいて時間フィルターを調整
2. 価格アクションパターンを導入

### フェーズ4：ポジション管理の強化（目標：勝率50%、PF1.5）
1. 連続損失時のポジションサイズ削減を強化
2. 連続勝利時のポジションサイズ増加を導入

## 期待される効果

1. **シグナル品質の向上**：取引数は減少するが、勝率とPFが向上
2. **リスク・リワード比の改善**：平均利益が増加し、平均損失が減少
3. **時間フィルターの最適化**：高勝率の時間帯に集中することで全体の勝率が向上
4. **ポジション管理の強化**：連続損失のリスクを軽減し、連続勝利の利益を最大化

## 次のステップ

1. 各フェーズごとにバックテストを実行し、効果を検証
2. 最も効果的な最適化を特定し、組み合わせて最終的な最適化を実施
3. 2023年、2024年、2025年の全期間でバックテストを実行し、一貫したパフォーマンス向上を確認
