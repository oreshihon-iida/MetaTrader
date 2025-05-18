# 同時ポジション数5、勝率条件付きロットサイズ調整機能の実装

## 概要

本ドキュメントでは、同時ポジション数を3から5に増やし、勝率条件付きロットサイズ調整機能を実装した結果をまとめます。これにより、より多くの取引機会を活用しながら、高い勝率が達成された場合には自動的にリスクを増加させる柔軟な戦略が可能になりました。

## 実装内容

### 1. 拡張バックテストエンジン（EnhancedBacktestEngine）

```python
class EnhancedBacktestEngine:
    def __init__(self, data: pd.DataFrame, initial_balance: float = 1000000,
                 base_lot_size: float = 0.01, max_positions: int = 5,
                 spread_pips: float = 0.2, win_rate_threshold: float = 80.0,
                 increased_lot_size: float = 0.02):
        # ...
        self.position_limit_reached_count = 0  # ポジション制限到達回数のカウンター
        
    def run(self) -> Dict:
        # ...
        if len(self.open_positions) >= self.max_positions:
            self.position_limit_reached_count += 1  # ポジション制限到達時にカウントアップ
        # ...
        
        results = {
            # ...
            'position_limit_reached_count': self.position_limit_reached_count
        }
```

- 同時ポジション数を5に設定
- 初期資金を100万円に設定
- 基本ロットサイズを0.01に設定
- 勝率が80%を超えた場合のロットサイズを0.02に設定
- ポジション制限到達回数を追跡するカウンターを実装

### 2. 拡張デュアル戦略マネージャー（EnhancedDualStrategyManager）

```python
class EnhancedDualStrategyManager:
    def __init__(self, 
                short_term_strategy_params: Dict = None,
                long_term_strategy_params: Dict = None,
                max_short_term_positions: int = 3,
                max_long_term_positions: int = 2,
                short_term_capital_ratio: float = 0.4,
                long_term_capital_ratio: float = 0.6):
        # ...
```

- 短期戦略に3ポジション、長期戦略に2ポジションを割り当て
- 短期戦略に資金の40%、長期戦略に資金の60%を配分
- 各戦略のシグナル生成と資金配分を管理

## テスト結果

### 2025年のバックテスト結果

| 項目 | 短期戦略 | 長期戦略 | 合計 |
| --- | --- | --- | --- |
| トレード数 | 697 | 6 | 703 |
| 勝率 | 34.15% | 33.33% | 34.14% |
| プロフィットファクター | 1.06 | 1.65 | - |
| 純利益 | 20.51 | 8.50 | 29.01 |
| ポジション制限到達回数 | 350 | 8 | 358 |
| 1日あたりの平均取引回数 | - | - | 5.49 |

## ポジション制限の分析

ポジション制限に達した回数は合計358回で、全期間の4.06%を占めています。これは、同時ポジション数を5に増やしたことで、より多くの取引機会を活用できるようになったことを示しています。

- 短期戦略：350回（短期戦略の取引機会の約50%）
- 長期戦略：8回（長期戦略の取引機会の約133%）

長期戦略のポジション制限到達回数が取引数を上回っているのは、同じ日に複数回ポジション制限に達する場合があるためです。

## 勝率条件付きロットサイズ調整の効果

今回のテストでは、勝率が80%の閾値に達することはありませんでした（全体勝率は34.14%）。そのため、ロットサイズが0.01から0.02に自動的に増加することはありませんでした。

この機能は、戦略の改善により勝率が大幅に向上した場合に、自動的にリスクを増加させて利益を最大化するために実装されています。

## 結論と推奨事項

1. **同時ポジション数5の効果**：ポジション制限に達する頻度（4.06%）は比較的低く、現在の最大ポジション数5は適切と考えられます。

2. **勝率条件付きロットサイズ調整**：現在の戦略では勝率80%の閾値に達していないため、この機能の効果は限定的です。戦略の改善により勝率が向上した場合に効果を発揮します。

3. **資金要件**：100万円の資金で同時ポジション数5（ロットサイズ0.01）を運用するのに十分です。

4. **今後の改善点**：
   - 短期戦略と長期戦略のパラメータの最適化
   - 勝率条件の閾値調整（現在は80%）
   - 資金配分比率のさらなる調整

## 技術的な実装詳細

1. **リアルタイム勝率追跡**：
   ```python
   self.total_trades = 0
   self.total_wins = 0
   self.current_win_rate = 0.0
   
   # トレード完了時に更新
   self.total_trades += 1
   if profit > 0:
       self.total_wins += 1
   self.current_win_rate = (self.total_wins / self.total_trades) * 100
   ```

2. **条件付きロットサイズ調整**：
   ```python
   lot_size = self.increased_lot_size if self.current_win_rate >= self.win_rate_threshold else self.base_lot_size
   ```

3. **ポジション制限カウンター**：
   ```python
   if len(self.open_positions) >= self.max_positions:
       self.position_limit_reached_count += 1
   ```

これらの実装により、戦略のパフォーマンスに応じて自動的にリスク管理を調整する柔軟なシステムが実現しました。
