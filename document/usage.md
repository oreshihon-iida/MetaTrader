# FXトレードシステム 使用方法

## 前提条件

- Python 3.8以上がインストールされていること
- 必要なパッケージがインストールされていること：
  ```
  pip install pandas numpy matplotlib ta
  ```
- USD/JPYの1分足ヒストリカルデータが `data/raw` ディレクトリに配置されていること

## 基本的な使用方法

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/MetaTrader.git
cd MetaTrader
```

### 2. データの準備

HistData.comからダウンロードしたUSD/JPYの1分足データ（ZIPファイルまたはCSVファイル）を `data/raw` ディレクトリに配置します。

```bash
mkdir -p data/raw
# ZIPファイルまたはCSVファイルをdata/rawディレクトリにコピー
```

### 3. バックテストの実行

```bash
python main.py
```

### 4. 結果の確認

バックテスト結果は以下のディレクトリに出力されます：

- **ログとレポート**: `results/logs`
  - `backtest.log`: バックテストログ
  - `trade_history.csv`: トレード履歴
  - `backtest_summary.md`: バックテストサマリーレポート

- **グラフ**: `results/charts`
  - `equity_curve.png`: 資産推移グラフ
  - `monthly_returns.png`: 月別リターングラフ
  - `drawdown.png`: ドローダウングラフ
  - `strategy_comparison.png`: 戦略比較グラフ

## 設定のカスタマイズ

設定をカスタマイズするには、`src/utils/config.py` の `_get_default_config` メソッドを編集するか、JSONファイルを作成して読み込みます。

### JSONファイルによる設定

```json
{
  "data": {
    "raw_dir": "data/raw",
    "processed_dir": "data/processed",
    "timeframe": "15T"
  },
  "backtest": {
    "initial_balance": 500000,
    "lot_size": 0.05,
    "max_positions": 5,
    "spread_pips": 0.3,
    "start_date": "2022-01-01",
    "end_date": "2023-12-31"
  },
  "strategies": {
    "tokyo_london": {
      "sl_pips": 12.0,
      "tp_pips": 18.0
    },
    "bollinger_rsi": {
      "sl_pips": 8.0,
      "tp_pips": 12.0
    }
  },
  "output": {
    "log_dir": "results/logs",
    "chart_dir": "results/charts"
  }
}
```

このJSONファイルを `config.json` として保存し、以下のようにして読み込みます：

```python
config = Config('config.json')
```

## 戦略のカスタマイズ

新しい戦略を追加するには、以下の手順に従います：

1. `src/strategies` ディレクトリに新しい戦略クラスを作成します
2. `generate_signals` メソッドを実装します
3. `main.py` で新しい戦略を初期化し、バックテストエンジンに追加します

### 戦略クラスの例

```python
class MyCustomStrategy:
    def __init__(self, sl_pips=10.0, tp_pips=15.0):
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.name = "カスタム戦略"
    
    def generate_signals(self, df):
        # シグナル生成ロジックを実装
        df['signal'] = 0
        # ...
        return df
```

## トラブルシューティング

### データ読み込みエラー

- ZIPファイルの形式が正しいか確認してください
- CSVファイルのフォーマットがHistData.comの形式と一致しているか確認してください

### メモリエラー

大量のデータを処理する場合、メモリ不足エラーが発生することがあります。その場合は以下の対策を試してください：

- バックテスト期間を短くする
- データをチャンクに分割して処理する
- 不要なカラムを削除してメモリ使用量を減らす

### パフォーマンスの最適化

バックテストの実行速度を向上させるには：

- 必要な期間のデータのみを読み込む
- 不要なテクニカル指標の計算を省略する
- NumPyの配列操作を活用してPandasの操作を最小限に抑える
