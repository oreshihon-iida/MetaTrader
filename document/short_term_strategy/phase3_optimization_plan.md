# 短期版戦略最適化 - フェーズ3: 時間フィルターの最適化計画

## フェーズ2の結果
| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |
| --- | --- | --- | --- | --- |
| 2023 | 479 | 24.01 | 1.00 | -1.65 |
| 2024 | 554 | 24.73 | 1.18 | 97.39 |
| 2025 | 172 | 23.84 | 1.07 | 14.89 |
| **合計** | **1,205** | **24.32** | **1.08** | **110.63** |

## フェーズ3の目標
- 勝率: 24.32% → 35%
- プロフィットファクター: 1.08 → 1.3
- 純利益: さらなる向上

## 変更内容

### 1. リスク・リワード比パラメータの復元
- 損切り幅: 2.5 → 3.0（フェーズ1の値に戻す）
- 利確幅: 8.0 → 7.5（フェーズ1の値に戻す）
- ATR乗数の調整:
  - ATR損切り乗数: 0.7 → 0.8（フェーズ1の値に戻す）
  - ATR利確乗数: 2.2 → 2.0（フェーズ1の値に戻す）

### 2. 時間フィルターの最適化
- 現在の時間フィルター: 0-2時、8-10時、13-15時
- 新しい時間フィルター:
  - アジアセッション: 0-3時（JST 9-12時）
  - ロンドンセッション開始: 8-11時（JST 17-20時）
  - NYセッション開始: 13-16時（JST 22-25時）
  - 重要な時間帯の拡大（各セッション開始時間の前後1時間を含む）

### 3. 曜日フィルターの導入
- 月曜日と金曜日は市場の不安定性が高いため、取引条件を厳格化
- 火曜日から木曜日は通常の取引条件を適用
- 週末（土日）は取引なし（デフォルト）

### 4. 市場環境適応型パラメータの基盤導入
- 市場環境の分類（トレンド/レンジ/高ボラティリティ）
- 環境に応じたRSI閾値の動的調整:
  - レンジ相場: RSI 65/35
  - トレンド相場: RSI 55/45
  - 高ボラティリティ: RSI 70/30

## 実装箇所
```python
# src/strategies/improved_short_term_strategy.py
default_params = {
    'bb_window': 20,
    'bb_dev': 1.8,          # フェーズ1で1.6から1.8に調整済み
    'rsi_window': 14,
    'rsi_upper': 60,        # フェーズ1で55から60に調整済み
    'rsi_lower': 40,        # フェーズ1で45から40に調整済み
    'sl_pips': 3.0,         # フェーズ2の2.5からフェーズ1の3.0に戻す
    'tp_pips': 7.5,         # フェーズ2の8.0からフェーズ1の7.5に戻す
    'atr_window': 14,
    'atr_sl_multiplier': 0.8,  # フェーズ2の0.7からフェーズ1の0.8に戻す
    'atr_tp_multiplier': 2.0,  # フェーズ2の2.2からフェーズ1の2.0に戻す
    'use_atr_for_sl_tp': True,
    'vol_filter': True,
    'time_filter': True,
    'day_filter': True,     # 曜日フィルターを有効化
    'use_adaptive_params': True,  # 市場環境適応型パラメータを有効化
}

# 時間フィルターの最適化
def _apply_filters(self, df: pd.DataFrame, i: int) -> bool:
    # 時間フィルター
    if self.time_filter:
        hour = df.index[i].hour
        # アジアセッション、ロンドンセッション開始、NYセッション開始の時間帯に集中
        if not ((0 <= hour < 3) or (8 <= hour < 11) or (13 <= hour < 16)):
            return False
            
    # 曜日フィルター
    if self.day_filter:
        weekday = df.index[i].weekday()
        # 月曜日(0)と金曜日(4)は条件を厳格化
        if weekday in [0, 4]:
            # RSIの条件を厳格化
            rsi = df['rsi'].iloc[i]
            if signal > 0 and rsi > self.rsi_upper * 0.9:  # 買いシグナルの場合
                return False
            if signal < 0 and rsi < self.rsi_lower * 1.1:  # 売りシグナルの場合
                return False
                
    # 市場環境適応型パラメータ
    if self.use_adaptive_params:
        # トレンド強度の計算
        trend_strength = self._calculate_trend_strength(df, i)
        # ボラティリティの計算
        volatility = df['atr'].iloc[i] / df['atr'].rolling(window=20).mean().iloc[i]
        
        # 市場環境の分類
        if volatility > 1.5:  # 高ボラティリティ
            self.adaptive_rsi_upper = 70
            self.adaptive_rsi_lower = 30
        elif abs(trend_strength) > 0.7:  # トレンド相場
            self.adaptive_rsi_upper = 55
            self.adaptive_rsi_lower = 45
        else:  # レンジ相場
            self.adaptive_rsi_upper = 65
            self.adaptive_rsi_lower = 35
```

## 期待される効果
1. **勝率の向上**: 高勝率時間帯への集中と曜日フィルターにより、低品質シグナルを除外
2. **プロフィットファクターの向上**: 市場環境に応じたパラメータ調整により、各環境での最適なトレードを実現
3. **年別パフォーマンスの安定化**: 2023年と2025年のパフォーマンス改善

## 検証方法
1. パラメータ変更前後の以下の指標を比較:
   - 勝率
   - プロフィットファクター
   - 時間帯別・曜日別の勝率
   - 市場環境別の勝率
   - 純利益

2. 年別パフォーマンスの変化を分析:
   - 2023年、2024年、2025年それぞれの改善度合い
   - 特に2023年の赤字からの回復に注目
