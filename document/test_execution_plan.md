# FX取引戦略テスト実行計画（2020-2025年）

## 1. 概要

本文書では、以下のFX取引戦略の2020-2025年データに対するバックテスト実行計画を詳述します：

- 東京レンジ・ロンドンブレイクアウト戦略
- ボリンジャーバンド＋RSI逆張り戦略
- サポート/レジスタンス戦略
- 改良版サポート/レジスタンス戦略
- サポート/レジスタンスV2戦略

## 2. テスト実行状況マトリクス

| 戦略 / 年度 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|------------|------|------|------|------|------|------|
| 東京レンジ・ロンドン | ✅ | ✅ | ✅ | ⏳ | ⏳ | ⏳ |
| ボリンジャーバンド＋RSI | ✅ | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| サポート/レジスタンス | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ |
| 改良版サポート/レジスタンス | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ |
| サポート/レジスタンスV2 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

✅：完了　⏳：未完了/実行中

## 3. テスト実行コマンド

各戦略の各年のテストを実行するためのコマンドは以下の通りです：

```bash
# 東京レンジ・ロンドンブレイクアウト戦略
python yearly_backtest.py --year 2020 --strategies tokyo_london
python yearly_backtest.py --year 2021 --strategies tokyo_london
python yearly_backtest.py --year 2022 --strategies tokyo_london
python yearly_backtest.py --year 2023 --strategies tokyo_london
python yearly_backtest.py --year 2024 --strategies tokyo_london
python yearly_backtest.py --year 2025 --strategies tokyo_london

# ボリンジャーバンド＋RSI戦略
python yearly_backtest.py --year 2020 --strategies bollinger_rsi
python yearly_backtest.py --year 2021 --strategies bollinger_rsi
python yearly_backtest.py --year 2022 --strategies bollinger_rsi
python yearly_backtest.py --year 2023 --strategies bollinger_rsi
python yearly_backtest.py --year 2024 --strategies bollinger_rsi
python yearly_backtest.py --year 2025 --strategies bollinger_rsi

# サポート/レジスタンス戦略
python yearly_backtest.py --year 2020 --strategies support_resistance
python yearly_backtest.py --year 2021 --strategies support_resistance
python yearly_backtest.py --year 2022 --strategies support_resistance
python yearly_backtest.py --year 2023 --strategies support_resistance
python yearly_backtest.py --year 2024 --strategies support_resistance
python yearly_backtest.py --year 2025 --strategies support_resistance

# 改良版サポート/レジスタンス戦略
python yearly_backtest.py --year 2020 --strategies support_resistance_improved
python yearly_backtest.py --year 2021 --strategies support_resistance_improved
python yearly_backtest.py --year 2022 --strategies support_resistance_improved
python yearly_backtest.py --year 2023 --strategies support_resistance_improved
python yearly_backtest.py --year 2024 --strategies support_resistance_improved
python yearly_backtest.py --year 2025 --strategies support_resistance_improved

# サポート/レジスタンスV2戦略
python yearly_backtest.py --year 2020 --strategies support_resistance_v2
python yearly_backtest.py --year 2021 --strategies support_resistance_v2
python yearly_backtest.py --year 2022 --strategies support_resistance_v2
python yearly_backtest.py --year 2023 --strategies support_resistance_v2
python yearly_backtest.py --year 2024 --strategies support_resistance_v2
python yearly_backtest.py --year 2025 --strategies support_resistance_v2
```

## 4. テスト実行時間の見積もり

各戦略の1年分のテストにかかる時間の見積もりは以下の通りです：

| 戦略 | 1年あたりの実行時間 | 6年分の合計時間 |
|------|-------------------|---------------|
| 東京レンジ・ロンドン | 約5分 | 約30分 |
| ボリンジャーバンド＋RSI | 約5分 | 約30分 |
| サポート/レジスタンス | 約5分 | 約30分 |
| 改良版サポート/レジスタンス | 約5分 | 約30分 |
| サポート/レジスタンスV2 | 約10分 | 約60分 |
| **合計** | - | **約3時間** |

## 5. 効率的なテスト実行計画

テスト実行時間を短縮するために、以下の方針でテストを実行します：

1. **優先順位付け**：
   - 2020年のテストは全戦略で完了済み
   - 2021-2023年の主要戦略（ボリンジャーバンド＋RSI、サポート/レジスタンス）を優先的にテスト
   - 2024-2025年は最後にテスト

2. **並列実行**：
   - 複数のシェルを使用して並列にテストを実行
   - 例：tokyo_london（2021年）とbollinger_rsi（2021年）を別々のシェルで同時に実行

3. **段階的な結果収集**：
   - 各テスト完了後に結果を収集し、strategy_performance_analysis.mdを随時更新
   - 特に重要な指標（勝率、プロフィットファクター）を優先的に収集

## 6. 結果収集方法

各テスト完了後、以下のコマンドで結果を収集します：

```bash
# 勝率とプロフィットファクターの収集
cat results/yearly/[年]/logs/backtest_summary.md | grep "勝率\|プロフィットファクター" -A 1
```

## 7. 次のステップ

1. 2021年の各戦略のテストを実行
2. 結果を収集し、strategy_performance_analysis.mdを更新
3. 2022年以降の各戦略のテストを順次実行
4. 全テスト完了後、総合的な分析と改善案を作成
