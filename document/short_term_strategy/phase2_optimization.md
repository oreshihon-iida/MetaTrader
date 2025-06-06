# 短期版戦略最適化 - フェーズ2: リスク・リワード比の最適化

## 変更内容

### 1. リスク・リワード比の最適化
- 損切り幅: 3.0 → 2.5（損失を抑制）
- 利確幅: 7.5 → 8.0（利益を拡大）
- ATR乗数の調整:
  - ATR損切り乗数: 0.8 → 0.7（損失を抑制）
  - ATR利確乗数: 2.0 → 2.2（利益を拡大）

## 期待された効果
1. **勝率の向上**: 損切り幅を縮小することで、一時的な価格変動による損切りを減少させる
2. **平均利益の増加**: 利確幅を拡大することで、トレンドが続く場合の利益を最大化する
3. **リスク・リワード比の改善**: 損切り幅と利確幅の比率を最適化することで、少ない勝率でも収益を確保
4. **プロフィットファクターの向上**: 平均勝ちトレード金額の増加と平均負けトレード金額の減少により改善

## フェーズ1の結果（ベースライン）
| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |
| --- | --- | --- | --- | --- |
| 2023 | 478 | 27.82 | 1.06 | 31.44 |
| 2024 | 553 | 28.39 | 1.09 | 50.55 |
| 2025 | 172 | 29.65 | 1.22 | 50.11 |
| **合計** | **1,203** | **28.35** | **1.22** | **132.10** |

## フェーズ2の結果
| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |
| --- | --- | --- | --- | --- |
| 2023 | 479 | 24.01 | 1.00 | -1.65 |
| 2024 | 554 | 24.73 | 1.18 | 97.39 |
| 2025 | 172 | 23.84 | 1.07 | 14.89 |
| **合計** | **1,205** | **24.32** | **1.08** | **110.63** |

## 分析結果

### 1. 勝率の低下
- 全体勝率: 28.35% → 24.32% (-4.03%)
- すべての年で勝率が低下（特に2025年で-5.81%）
- 損切り幅の縮小が逆効果となり、一時的な価格変動で損切りされるケースが増加

### 2. プロフィットファクターの変化
- 全体PF: 1.22 → 1.08 (-0.14)
- 2023年: 1.06 → 1.00 (-0.06)
- 2024年: 1.09 → 1.18 (+0.09)
- 2025年: 1.22 → 1.07 (-0.15)

### 3. 純利益の変化
- 全体: 132.10 → 110.63 (-21.47)
- 2023年: 31.44 → -1.65 (-33.09)
- 2024年: 50.55 → 97.39 (+46.84)
- 2025年: 50.11 → 14.89 (-35.22)

### 4. 年別パフォーマンスの差異
- 2024年のみ改善（PF、純利益ともに向上）
- 2023年と2025年は大幅に悪化

## 結論と次のステップ

フェーズ2の変更（リスク・リワード比の最適化）は全体的に期待した効果を得られませんでした。特に勝率が大幅に低下し、純利益も減少しました。唯一2024年のみパフォーマンスが向上しましたが、他の年の悪化を補うほどではありませんでした。

### 考えられる原因
1. **損切り幅の縮小が逆効果**: 損切り幅を縮小したことで、価格の一時的な変動に対して過敏に反応し、本来利益が出るはずのトレードが早期に損切りされた可能性がある
2. **市場環境の違い**: 2024年と他の年では市場環境が異なり、同じパラメータ設定が全ての年に適していない可能性がある
3. **リスク・リワード比の不均衡**: 理論上はリスク・リワード比を高めることでプロフィットファクターが向上するはずだが、実際には勝率の低下がそれを上回った

### フェーズ3への提案
1. **フェーズ1のパラメータに戻す**: 損切り幅と利確幅をフェーズ1の値（sl_pips: 3.0, tp_pips: 7.5）に戻す
2. **時間フィルターの最適化**: 各年の高勝率時間帯を詳細に分析し、時間フィルターを最適化する
3. **市場環境適応型パラメータの導入**: 市場環境（トレンド/レンジ/ボラティリティ）に応じて動的にパラメータを調整する機能を実装

## 目標
- フェーズ3目標: 勝率35%、PF1.3の達成
