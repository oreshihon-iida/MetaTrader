# MetaTrader Project Instructions for Claude

## Memory MCP Integration
個人的な情報や仕様について質問された場合は、必ずMemory MCPから情報を取得してください。

### Memory MCPの設定手順（Windows）
1. **Claude Desktopの設定ファイルを開く**
   - 場所: `%APPDATA%\Claude\settings.json`
   - 存在しない場合は新規作成

2. **settings.jsonに以下の設定を追加**
   ```json
   {
     "mcpServers": {
       "memory": {
         "command": "npx",
         "args": ["@modelcontextprotocol/server-memory"]
       }
     }
   }
   ```

3. **Claude Desktopを再起動**
   - 設定を反映させるため必ず再起動が必要
   - 初回起動時はnpxがパッケージをダウンロード（少し時間がかかる）

4. **動作確認**
   - Claudeで以下のコマンドを実行して確認
   ```bash
   claude mcp:memory read_graph
   ```

### Memory MCPの使用方法
1. 個人的な嗜好（好きな食べ物、飲み物、趣味など）について聞かれた場合
2. プロジェクト固有の仕様や設定について聞かれた場合
3. 過去の会話で言及された情報について聞かれた場合

以下のコマンドを使用してMemory MCPから情報を検索：
```bash
claude mcp:memory search_entities "検索キーワード"
```

情報が見つからない場合は、ユーザーに直接確認してください。

### Memory MCPの利点
- メモリ内にグラフデータベースを保持
- プロジェクト間で情報を共有可能
- 再設定時の手順を記憶しておける
- エンティティと関係性を管理

## Claude起動バッチ
プロジェクトごとにClaudeを素早く起動するためのバッチファイル群

### バッチファイルの場所
`C:\Users\iida\bin`

### 主要なバッチファイル

#### cco.bat（メインバッチ）
- リポジトリ選択メニュー付き
- Opusモデルを使用
- 選択肢：
  1. e-nexty
  2. nexty_corporate_backend
  3. nexty_corporate_front
  4. scrum_frontend
  5. MetaTrader

#### プロジェクト専用バッチ
- **cc.bat**: e-nextyプロジェクト（デフォルトモデル）
- **ccr.bat**: e-nextyプロジェクト（--resumeオプション付き）
- **cco-enexty.bat**: e-nextyプロジェクト（Opusモデル）
- **cco-corp-back.bat**: nexty_corporate_backendプロジェクト
- **cco-corp-front.bat**: nexty_corporate_frontプロジェクト
- **cco-scrum.bat**: scrum_frontendプロジェクト

### 使用方法
コマンドプロンプトまたはPowerShellで以下を実行：
```bash
# メインメニューから選択
cco

# e-nextyプロジェクトを直接起動
cc

# 前回のセッションを継続
ccr
```

## Project Overview
This is a MetaTrader forex trading strategy development project focused on USD/JPY trading.

## Testing Commands
When implementing or modifying code, always run the following tests if applicable:
- Python syntax check: `python -m py_compile <filename.py>`
- Run specific test files when modifying strategies

## Code Style Guidelines
- Follow existing code conventions in the project
- Use type hints where applicable
- Maintain clear documentation for strategy implementations

## Strategy Development Status & Lessons Learned

### 戦略開発履歴
1. **ProfitTargetStrategyV2**: 初期成功戦略 (+88,080円、41.08%勝率)
   - RSI(25/75) + BolingerBand(2.2σ) + 時間帯 + トレンドフィルター
   - 現在のテスト環境では0シグナル問題あり（フィルター過度）

2. **IntegratedStrategyV1**: V2ベース統合戦略 (Phase 1完了)
   - 固定R/R比2.8:1 + 市況適応TP/SL
   - テスト結果: 83取引、-302,950円、26.51%勝率
   - シグナル生成問題解決（トレンドフィルター緩和）

3. **MacroBasedLongTermStrategy**: develop分岐戦略（否定）
   - 当初746,200円/5年の利益を主張
   - 詳細検証で強制シグナル生成（10日毎買い、20日毎売り）判明
   - 実際は0円、0取引で市場分析機能なし

### 重要な技術的発見
- **現代FX市場**: アルゴリズム取引が80%以上を支配
- **効果的戦略**: トレンドフォロー、統計アービトラージ、AI/ML
- **データの重要性**: 25年分HistData.com実データで検証
- **微調整の限界**: 根本的戦略変更が必要

### システム構築成果
- **自動データ収集**: 2000-2025年、複数時間軸完備
- **包括的テスト**: AutoTestRunner + TradeExecutor
- **完全シミュレーション**: TP/SL自動、月別分析、リスク管理

### 完成済み戦略（2025年8月時点）

#### 1. Modern Trend Following Strategy（狙撃手型）- 完成済み
- **性能**: 238万円利益/3年間、勝率75%（4取引中3勝）
- **特徴**: 超選択的・超高品質・極低頻度（年1.3回）
- **技術**: マルチタイムフレーム(15分,1H,4H,日足)解析 + 厳格フィルター
- **フィルター通過率**: 11%（36シグナル中4取引のみ実行）
- **用途**: サブ戦略として他戦略と併用推奨
- **改善試行**: 頻度向上を3回試みたが品質劣化で狙撃手型として完成

#### 2. Lightweight ML Predictor Strategy（機械学習版）- 完成済み
- **技術**: RandomForest/XGBoostベースの軽量機械学習
- **特徴**: 15分〜1時間先の短期予測特化、TensorFlow不要
- **学習**: 週次自動再学習、テクニカル指標特徴量
- **目標**: 高頻度取引（日5-10回）
- **相補性**: 狙撃手型戦略との組み合わせでポートフォリオバランス向上
- **処理最適化**: 11個厳選特徴量、キャッシュ機能、200本間隔処理

### 現在の開発状況（2025年8月）

#### 実行中テスト結果
- **最適化ML戦略**: 2年分学習版、9秒で完了、取引0件（方向精度47-56%）
- **問題**: 信頼度スコア0.28-0.36と低く、取引条件未達
- **対策**: 特徴量エンジニアリング改善、予測ホライゾン調整が必要

#### 高性能マシン移行計画
- **現在**: 2年分データを9秒で処理（最適化済み）
- **期待**: 高性能マシンで3-5倍高速化（2-3秒）
- **利点**: 複雑な特徴量・深層学習・精度向上と高速化の両立

#### 環境構築要件（別マシン用）
以下のセクションに詳細記載

## 高性能マシン環境構築手順

### システム要件
```
推奨スペック:
- CPU: 8コア以上（Intel i7/i9またはAMD Ryzen 7/9）
- メモリ: 16GB以上
- ストレージ: NVMe SSD 500GB以上
- OS: Windows 10/11 または Ubuntu 20.04/22.04
```

### 基本環境セットアップ

#### 1. Python環境
```bash
# Python 3.9-3.11推奨
python --version
pip install --upgrade pip

# 仮想環境作成
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

#### 2. 必要パッケージ
```bash
# 基本パッケージ
pip install pandas numpy matplotlib seaborn
pip install scikit-learn xgboost lightgbm
pip install talib-binary  # Windows用
# または
pip install TA-Lib  # Linux/Mac用

# オプション（深層学習用）
pip install tensorflow tensorflow-gpu  # GPU版
pip install torch torchvision  # PyTorch

# データ処理・可視化
pip install jupyter plotly dash
pip install requests zipfile36
```

#### 3. プロジェクトクローン
```bash
git clone <プロジェクトURL>
cd MetaTrader

# データディレクトリ作成
mkdir -p data/{raw,processed}/{1min,15min,1H,4H,1D}
mkdir -p results/yearly
mkdir -p models/{optimized_ml,lightweight_ml}
mkdir -p logs/{auto_test,data_collection}
```

### Claude Code環境

#### 1. Claude Code インストール
```bash
# Node.js インストール（必要な場合）
# Windows: https://nodejs.org からダウンロード
# Linux: sudo apt install nodejs npm

# Claude Code インストール
npm install -g @anthropic/claude-code
# または
curl -fsSL https://claude.ai/install.sh | sh
```

#### 2. Memory MCP設定
```json
# %APPDATA%\Claude\settings.json (Windows)
# ~/.claude/settings.json (Linux/Mac)
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-memory"]
    }
  }
}
```

#### 3. 起動スクリプト（Windows用）
```batch
@echo off
cd /d "C:\path\to\MetaTrader"
call venv\Scripts\activate
claude --model sonnet
pause
```

### データ収集セットアップ

#### 1. 自動データ収集実行
```bash
# 初回データ収集（25年分）
python src/data/auto_data_collector.py

# 定期更新（日次）
# crontab -e
0 6 * * * cd /path/to/MetaTrader && python src/data/auto_data_collector.py
```

#### 2. データ品質確認
```bash
# データ統計表示
python -c "import pandas as pd; df=pd.read_csv('data/processed/15min/2024/USDJPY_15min_2024.csv'); print(df.info())"
```

### テスト実行手順

#### 1. 基本動作確認
```bash
# 構文チェック
python -m py_compile src/strategies/optimized_ml_predictor_strategy.py

# 簡単なテスト
python test_optimized_ml.py
```

#### 2. 高速テスト
```bash
# 1ヶ月のみテスト（超高速）
python test_ml_quick.py

# バックグラウンド実行
nohup python test_optimized_ml.py > test_result.log 2>&1 &
```

### 高性能化設定

#### 1. マルチコア活用
```python
# scikit-learn
RandomForestRegressor(n_jobs=-1)  # 全コア使用

# pandas
kimport os
os.environ['NUMEXPR_MAX_THREADS'] = '16'  # CPU数に合わせて調整
```

#### 2. GPU活用（オプション）
```python
# XGBoost GPU版
import xgboost as xgb
xgb.XGBRegressor(tree_method='gpu_hist')

# TensorFlow GPU確認
import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))
```

## トラブルシューティング

### よくある問題

#### 1. タイムアウト問題
```bash
# バックグラウンド実行で回避
python test_script.py &

# 処理間隔調整
# 200本間隔 → 500本間隔で高速化
```

#### 2. メモリ不足
```python
# データを分割処理
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    process_chunk(chunk)
```

#### 3. パッケージエラー
```bash
# TA-Lib インストール問題
# Windows
pip install talib-binary

# Linux
sudo apt-get install libta-lib-dev
pip install TA-Lib
```

### パフォーマンス監視
```bash
# CPU/メモリ使用率
top
htop

# プロセス監視
ps aux | grep python
```

### 最新戦略移行チェックリスト
- [ ] 基本環境構築完了
- [ ] データ収集システム稼働
- [ ] Memory MCP設定完了
- [ ] 狙撃手型戦略テスト成功
- [ ] 機械学習戦略テスト成功
- [ ] 最適化ML戦略改善着手
- [ ] 高性能マシン性能測定
- [ ] 月20万円目標達成戦略確立