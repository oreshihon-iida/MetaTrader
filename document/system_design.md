# FXトレードシステム 設計書

## システム構成

FXトレードシステムは以下のモジュールで構成されています：

```
fx_trading_system/
├── data/
│   ├── raw/         # 生データ（ZIPファイル、CSVファイル）
│   └── processed/   # 処理済みデータ
├── document/        # ドキュメント
├── results/
│   ├── logs/        # ログファイル、レポート
│   └── charts/      # グラフ
├── src/
│   ├── data/        # データ処理モジュール
│   ├── strategies/  # 戦略モジュール
│   ├── backtest/    # バックテストモジュール
│   ├── utils/       # ユーティリティモジュール
│   └── visualization/ # 可視化モジュール
└── main.py          # メインスクリプト
```

## モジュール詳細

### 1. データ処理モジュール (`src/data/`)

#### 1.1 DataLoader クラス (`data_loader.py`)

- **役割**：HistData.comから提供されるZIPファイルを展開し、CSVデータを読み込む
- **主要メソッド**：
  - `extract_zip_files()`: ZIPファイルを展開
  - `load_csv_to_dataframe()`: CSVファイルをDataFrameとして読み込む
  - `load_all_data()`: すべてのデータを結合

#### 1.2 DataProcessor クラス (`data_processor.py`)

- **役割**：1分足データを15分足にリサンプリングし、テクニカル指標を計算
- **主要メソッド**：
  - `resample()`: 指定された時間足にリサンプリング
  - `add_technical_indicators()`: テクニカル指標を追加
  - `get_tokyo_session_range()`: 東京時間のレンジを計算

### 2. 戦略モジュール (`src/strategies/`)

#### 2.1 TokyoLondonStrategy クラス (`tokyo_london.py`)

- **役割**：東京レンジ・ロンドンブレイクアウト戦略を実装
- **主要メソッド**：
  - `generate_signals()`: トレードシグナルを生成

#### 2.2 BollingerRsiStrategy クラス (`bollinger_rsi.py`)

- **役割**：ボリンジャーバンド＋RSI逆張り戦略を実装
- **主要メソッド**：
  - `generate_signals()`: トレードシグナルを生成

### 3. バックテストモジュール (`src/backtest/`)

#### 3.1 Position クラス (`position.py`)

- **役割**：トレードポジションを管理
- **主要メソッド**：
  - `close_position()`: ポジションを決済
  - `to_dict()`: ポジション情報を辞書形式で返す

#### 3.2 BacktestEngine クラス (`backtest_engine.py`)

- **役割**：バックテストを実行し、結果を記録
- **主要メソッド**：
  - `run()`: バックテストを実行
  - `_check_positions_for_exit()`: 決済条件を確認
  - `_open_new_position()`: 新規ポジションを開く
  - `get_equity_curve()`: 資産推移を取得
  - `get_trade_log()`: トレードログを取得

### 4. ユーティリティモジュール (`src/utils/`)

#### 4.1 Logger クラス (`logger.py`)

- **役割**：ログ出力を管理
- **主要メソッド**：
  - `log_info()`, `log_warning()`, `log_error()`: ログを出力
  - `log_trade_history()`: トレード履歴をCSVに保存
  - `log_performance_metrics()`: パフォーマンス指標をログに出力

#### 4.2 Config クラス (`config.py`)

- **役割**：設定を管理
- **主要メソッド**：
  - `get()`: 設定値を取得
  - `save()`: 設定をファイルに保存

### 5. 可視化モジュール (`src/visualization/`)

#### 5.1 ChartGenerator クラス (`charts.py`)

- **役割**：グラフを生成
- **主要メソッド**：
  - `plot_equity_curve()`: 資産推移グラフを生成
  - `plot_monthly_returns()`: 月別リターングラフを生成
  - `plot_drawdown()`: ドローダウングラフを生成
  - `plot_strategy_comparison()`: 戦略比較グラフを生成

#### 5.2 ReportGenerator クラス (`reports.py`)

- **役割**：レポートを生成
- **主要メソッド**：
  - `calculate_performance_metrics()`: パフォーマンス指標を計算
  - `generate_summary_report()`: サマリーレポートを生成

## データフロー

1. DataLoaderがZIPファイルを展開し、CSVデータを読み込む
2. DataProcessorが1分足データを15分足にリサンプリングし、テクニカル指標を計算
3. 各戦略クラスがトレードシグナルを生成
4. BacktestEngineがシグナルに基づいてトレードを実行し、結果を記録
5. ChartGeneratorとReportGeneratorがバックテスト結果を可視化・レポート化

## 設定パラメータ

主要な設定パラメータは以下の通りです：

- **データ設定**：
  - `raw_dir`: 生データのディレクトリ
  - `processed_dir`: 処理済みデータのディレクトリ
  - `timeframe`: リサンプリングする時間足（デフォルト: '15T'）

- **バックテスト設定**：
  - `initial_balance`: 初期資金（デフォルト: 200,000円）
  - `lot_size`: 1トレードあたりのロットサイズ（デフォルト: 0.01）
  - `max_positions`: 同時に保有できる最大ポジション数（デフォルト: 3）
  - `spread_pips`: スプレッド（デフォルト: 0.2pips）
  - `start_date`: バックテスト開始日
  - `end_date`: バックテスト終了日

- **戦略設定**：
  - 東京レンジ・ロンドンブレイクアウト戦略：
    - `sl_pips`: 損切り幅（デフォルト: 10.0pips）
    - `tp_pips`: 利確幅（デフォルト: 15.0pips）
  - ボリンジャーバンド＋RSI逆張り戦略：
    - `sl_pips`: 損切り幅（デフォルト: 7.0pips）
    - `tp_pips`: 利確幅（デフォルト: 10.0pips）

- **出力設定**：
  - `log_dir`: ログディレクトリ
  - `chart_dir`: チャートディレクトリ
