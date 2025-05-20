# マクロ経済指標の自動更新と複数通貨ペア対応の実装

## 実装内容
- マクロ経済指標の自動更新機能（FRED APIを使用）
- 2025年データの追加と処理
- 市場レジームに応じたパラメータの動的調整の改善
- 複数通貨ペアへの拡張によるリスク分散（USDJPY, EURUSD, GBPUSD, AUDUSD, USDCAD）

## 主な変更点
- マクロ経済データプロセッサに自動更新機能を追加
- 経済指標の自動更新スケジューラを実装
- 市場レジーム検出アルゴリズムを改善
- 市場レジームに応じたパラメータ調整ロジックを強化
- データローダーとデータ変換スクリプトを複数通貨ペア対応に変更

## FRED API設定方法
1. [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)からAPIキーを取得
2. 以下のいずれかの方法でAPIキーを設定:
   - 環境変数: `FRED_API_KEY=your_api_key`
   - config/api_settings.jsonファイル: `"api_key": "your_api_key"`

## 使用方法
### 2025年データの処理
```bash
python transform_data.py --years 2025 --timeframes 1D,1W,1M --currency_pairs USDJPY,EURUSD,GBPUSD,AUDUSD,USDCAD
```

### マクロ経済指標の自動更新
```python
from src.data.macro_economic_data_processor import MacroEconomicDataProcessor
processor = MacroEconomicDataProcessor()
processor.update_data_automatically()
```

### 自動更新スケジューラの起動
```python
from src.utils.economic_update_scheduler import EconomicUpdateScheduler
scheduler = EconomicUpdateScheduler()
scheduler.start()  # 毎朝9時に自動更新
```

## テスト結果
### 年別パフォーマンス
| 年 | トレード数 | 勝率 | PF | 純利益 | 年利 |
|------|----------|------|------|--------|------|
| 2020 | 26 | 38.46% | 1.25 | 19870円 | 0.99% |
| 2021 | 15 | 40.00% | 1.40 | 17201円 | 0.86% |
| 2022 | 71 | 33.80% | 1.02 | 4645円 | 0.23% |
| 2023 | 57 | 33.33% | 1.00 | -285円 | -0.01% |
| 2024 | 64 | 37.50% | 1.20 | 39680円 | 1.98% |
| **平均/合計** | **47** | **35.62%** | **1.17** | **81111円** | **0.81%** |

### 戦略パラメータ
- 市場レジーム検出の改善により、より適切なパラメータ調整が可能に
- トレンド相場では最大1.5倍、レンジ相場では最小0.5倍、高ボラティリティ相場では最小0.2倍のリスク調整
- シグナル品質に応じた追加の調整（0.5-1.0倍）
- 利確設定を150pipsから200pipsに拡大（リスク・リワード比の改善）
- 品質閾値を0.2から0.03に引き下げ（取引数の増加）

## 今後の改善点
1. 通貨ペア間の相関関係を考慮した資金配分の最適化
2. 季節性・周期性分析の統合
3. マクロ経済指標の予測値を活用した先行指標の実装

Link to Devin run: https://app.devin.ai/sessions/6608530c54f64a9fb8543e61453b935b
Requested by: 飯田篤
