# フェーズ4実装への復帰

## 概要

フェーズ5（パターン検出トラッキング）の実装により戦略のパフォーマンスが低下したため、より高いパフォーマンスを示したフェーズ4の実装に戻すことを決定しました。この文書では、フェーズ4への復帰プロセスと理由を説明します。

## パフォーマンス比較

| 指標 | フェーズ4 | フェーズ5 | フェーズ5修正後 |
| --- | --- | --- | --- |
| 総トレード数 | 1,064 | 1,921 | 1,229 |
| 勝率 | 30.64% | 29.10% | 28.32% |
| プロフィットファクター | 1.15 | 1.07 | 1.27 |
| 純利益 | 163.06 | 115.96 | 94.88 |

## 復帰の理由

1. **パフォーマンスの低下**
   - フェーズ5実装後、純利益が163.06から115.96に減少
   - パターントラッキング修正後も94.88と低いパフォーマンス

2. **シグナル品質と数のバランス崩壊**
   - シグナル条件の変更により取引数が増加（1,064→1,921）
   - 低品質シグナルの混入により勝率低下

3. **複雑性の増加**
   - パターン検出と関連付けロジックの複雑化
   - コード可読性と保守性の低下

## 復帰プロセス

1. **コード変更**
   - `improved_short_term_strategy.py`をフェーズ4実装に戻す
   - `bollinger_rsi_enhanced_mt.py`をフェーズ4実装に戻す
   - パターントラッキング関連のコードを削除

2. **パラメータ復元**
   - ボリンジャーバンド幅: 1.8 → 1.6
   - RSI上限/下限: 60/40 → 55/45
   - ATR乗数: 0.7/2.2 → 0.8/2.0
   - パターン数要件: 2 → 1
   - シグナル条件: AND → OR

3. **テスト検証**
   - フェーズ4実装の復元後、バックテストを実行
   - パフォーマンス指標（純利益、勝率、PF）の確認
   - 年別結果の分析

## 今後の方針

1. **パターントラッキングの代替アプローチ**
   - 戦略本体とは分離したオフライン分析ツールの開発を検討
   - パフォーマンスへの影響を最小化しながらパターン効果を測定する方法を模索

2. **段階的な機能追加**
   - 将来の機能追加は段階的に行い、各ステップでパフォーマンスを検証
   - A/Bテスト方式での比較検証を導入

3. **シンプルさの重視**
   - 複雑な機能追加よりもシンプルで効果的なロジックを優先
   - 「より少ない高品質シグナル」を目指す戦略最適化

この復帰により、フェーズ4の高いパフォーマンス（純利益163.06）を回復しつつ、フェーズ5から得られた教訓を今後の戦略開発に活かします。
