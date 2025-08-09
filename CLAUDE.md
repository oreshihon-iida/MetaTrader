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

### 次期開発方針
現在のV1/V2微調整では月20万円目標達成困難。以下を検討:
1. 現代的トレンドフォロー戦略実装
2. 統計アービトラージベース開発  
3. 機械学習要素統合
4. マルチ戦略アプローチ採用