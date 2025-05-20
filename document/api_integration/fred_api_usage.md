# FRED API 統合ガイド

## 概要
このドキュメントでは、MetaTraderシステムにおけるFRED API（Federal Reserve Economic Data）の統合と使用方法について説明します。FRED APIは、米国セントルイス連邦準備銀行が提供する経済データAPIで、GDP成長率、インフレ率、金利、失業率などの経済指標データを取得するために使用されます。

## APIキーの取得と設定

### APIキーの取得
1. [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)のウェブサイトにアクセス
2. アカウント登録を行い、APIキーを取得

### APIキーの設定方法
セキュリティ上の理由から、APIキーはリポジトリにコミットせず、以下のいずれかの方法で設定してください：

1. **.envファイルを使用する方法（推奨）**
   プロジェクトのルートディレクトリに`.env`ファイルを作成し、以下の内容を記述します：
   ```
   FRED_API_KEY=your_api_key
   ```
   
   このファイルは`.gitignore`に追加して、gitリポジトリにコミットされないようにしてください。
   アプリケーションの起動時に自動的に読み込まれます。

2. **環境変数を使用する方法**
   ```bash
   export FRED_API_KEY=your_api_key
   ```

3. **設定ファイルを使用する方法**
   `config/api_settings.json`ファイルにAPIキーを設定します：
   ```json
   {
       "fred": {
           "api_key": "your_api_key"
       },
       "update_schedule": {
           "interest_rate": "event_based",
           "gdp_growth": "quarterly",
           "inflation_rate": "monthly",
           "unemployment_rate": "monthly",
           "trade_balance": "monthly"
       }
   }
   ```

**重要**: APIキーは機密情報です。いずれの方法でも、APIキーがgitリポジトリにコミットされないようにしてください。

## 使用方法

### マクロ経済データの手動更新

```python
from src.data.macro_economic_data_processor import MacroEconomicDataProcessor

# プロセッサの初期化
processor = MacroEconomicDataProcessor()

# データの自動更新
updated = processor.update_data_automatically()

if updated:
    print("マクロ経済データが更新されました")
else:
    print("更新するデータがないか、エラーが発生しました")
```

### 自動更新スケジューラの使用

```python
from src.utils.economic_update_scheduler import EconomicUpdateScheduler

# スケジューラの初期化（デフォルトでは1時間ごとにチェック）
scheduler = EconomicUpdateScheduler(update_interval=3600)

# スケジューラの開始（毎朝9時に更新）
scheduler.start()

# アプリケーション終了時にスケジューラを停止
# scheduler.stop()
```

## 取得可能な経済指標

FRED APIを通じて以下の経済指標データを取得できます：

1. **金利 (interest_rate)**
   - 米国: FEDFUNDS（FRB政策金利）
   - 日本: INTDSRJPM193N（日本政策金利）

2. **GDP成長率 (gdp_growth)**
   - 米国: A191RL1Q225SBEA（実質GDP成長率）
   - 日本: JPNRGDPEXP（実質GDP成長率）

3. **インフレ率 (inflation_rate)**
   - 米国: CPIAUCSL（消費者物価指数）
   - 日本: JPNCPIALLMINMEI（消費者物価指数）

4. **失業率 (unemployment_rate)**
   - 米国: UNRATE（失業率）
   - 日本: LRUNTTTTJPM156S（失業率）

5. **貿易収支 (trade_balance)**
   - 米国: BOPGSTB（貿易収支）
   - 日本: JPTBALE（貿易収支）

## 更新頻度の設定

`config/api_settings.json`ファイルの`update_schedule`セクションで、各経済指標の更新頻度を設定できます：

- `"event_based"`: イベント発生時（金利変更など）
- `"daily"`: 毎日
- `"weekly"`: 毎週
- `"monthly"`: 毎月
- `"quarterly"`: 四半期ごと

## エラー処理

APIリクエストが失敗した場合、システムは自動的にログを記録し、次回の更新時に再試行します。エラーログは`logs`ディレクトリに保存されます。

## 制限事項

- FRED APIの利用制限は1日あたり約1,000リクエストです
- 一部の経済指標は更新頻度が低い場合があります（四半期データなど）
- 予測値は提供されないため、現在値と過去の値のみが利用可能です

## トラブルシューティング

1. **APIキーが認識されない場合**
   - 環境変数が正しく設定されているか確認
   - `config/api_settings.json`ファイルが正しく作成されているか確認

2. **データが更新されない場合**
   - ログファイルでエラーメッセージを確認
   - インターネット接続を確認
   - FRED APIのステータスを[公式サイト](https://fred.stlouisfed.org/)で確認
