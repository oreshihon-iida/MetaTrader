# FXトレードシステム

USD/JPYの1分足ヒストリカルデータを使用して、2つの異なる取引戦略をバックテストするためのPythonベースのシステムです。

## 機能

- **データ処理**: HistData.comから提供される1分足データを15分足にリサンプリング
- **戦略実装**: 
  - 東京レンジ・ロンドンブレイクアウト戦略
  - ボリンジャーバンド＋RSI逆張り戦略
- **バックテスト**: ポジション管理、詳細なログ出力、パフォーマンス分析
- **可視化**: 資産推移、月別リターン、ドローダウン、戦略比較などのグラフ生成

## 必要条件

- Python 3.8以上
- 必要なパッケージ:
  ```
  pip install pandas numpy matplotlib ta
  ```

## セットアップ

1. リポジトリをクローン:
   ```
   git clone https://github.com/oreshihon-iida/MetaTrader.git
   cd MetaTrader
   ```

2. 必要なディレクトリを作成:
   ```
   mkdir -p data/raw data/processed results/logs results/charts
   ```

3. データの準備:
   - HistData.comからダウンロードしたUSD/JPYの1分足データ（ZIPファイルまたはCSVファイル）を `data/raw` ディレクトリに配置
   - データ形式: CSVファイルは `Date,Time,Open,High,Low,Close,Volume` の形式である必要があります
   - 例: `20200101,000000,109.456,109.458,109.453,109.455,42`

## 使用方法

```
python main.py
```

バックテスト結果は以下のディレクトリに出力されます:

- **ログとレポート**: `results/logs`
  - `backtest.log`: バックテストログ
  - `trade_history.csv`: トレード履歴
  - `backtest_summary.md`: バックテストサマリーレポート

- **グラフ**: `results/charts`
  - `equity_curve.png`: 資産推移グラフ
  - `monthly_returns.png`: 月別リターングラフ
  - `drawdown.png`: ドローダウングラフ
  - `strategy_comparison.png`: 戦略比較グラフ

## 詳細情報

詳細な情報は以下のドキュメントを参照してください:

- [システム概要](document/system_overview.md)
- [設計書](document/system_design.md)
- [使用方法](document/usage.md)
