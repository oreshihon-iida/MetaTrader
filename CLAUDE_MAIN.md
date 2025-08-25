# MetaTrader Project Instructions for Claude - MAIN

## 📚 ドキュメント構成

このプロジェクトのドキュメントは以下の5つのファイルに分割されています：

1. **CLAUDE_MAIN.md** （このファイル）
   - 基本設定とインデックス
   - Memory MCP設定
   - 自動承認設定

2. **[CLAUDE_STRATEGIES.md](./CLAUDE_STRATEGIES.md)**
   - 完成済み戦略一覧
   - v21.7シリーズ詳細
   - 戦略開発の教訓

3. **[CLAUDE_TECHNICAL.md](./CLAUDE_TECHNICAL.md)**
   - MT5コマンド集
   - バックテスト設定
   - トラブルシューティング

4. **[CLAUDE_ISSUES.md](./CLAUDE_ISSUES.md)**
   - Issue #001〜#009の詳細記録
   - 各Issueの成果と教訓

5. **[CLAUDE_RESULTS.md](./CLAUDE_RESULTS.md)**
   - 戦略実績データ
   - 市場分析結果

---

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

4. **動作確認**
   ```bash
   claude mcp:memory read_graph
   ```

---

## ⚠️ 最重要原則

### 根本原因分析の重要性（2025年8月21日確立）
**ユーザーからの重要な指摘**: 「強制取引って利益を得るためっていうより『取引を発生させるため』にやってませんか？」

#### 確立された分析原則
1. **症状 vs 根本原因の区別**
   - ❌ 症状: 取引頻度の問題
   - ✅ 根本原因: 本来の取引条件で信号が生成されない理由

2. **常に「なぜ本来の条件で取引できないのか？」を問い続ける**

---

## Autonomous Operation Guidelines

### 自動承認設定（確認不要）
- ファイル作成・編集・削除
- MQL5コンパイル
- MT5バックテスト実行
- Pythonスクリプト実行
- Git操作
- パッケージインストール

### 自動決定方針
- **Yes/No判断**: 開発に関する全ての決定は自動的に"yes"
- **目標達成まで継続**: 月100万円目標まで自律的に作業
- **詳細分析優先**: CSV内容を徹底的に確認

---

## Project Overview

**プロジェクト**: MetaTrader 5 FX自動売買戦略開発
**主要通貨ペア**: USD/JPY, EUR/JPY, GBP/JPY
**現在の状態**: MAXプラン（$200）でターボモード開発中
**最新成果**: v21.7j (+438,552円/年, PF 1.47)
**目標**: 月100万円の安定収益

---

## Claude起動バッチ

### バッチファイルの場所
`C:\Users\iida\bin`

### 主要なバッチファイル
- **cco.bat**: メインバッチ（Opusモデル、プロジェクト選択メニュー）
- **cc.bat**: e-nextyプロジェクト
- **ccr.bat**: 前回セッション継続

### MetaTraderプロジェクト起動
```bash
cco
# メニューから「5. MetaTrader」を選択
```

---

## 開発環境

- **MT5パス**: `C:\Program Files\MetaTrader 5\`
- **データパス**: `C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\`
- **プロジェクトパス**: `C:\Users\iida\Documents\MetaTrader\`

詳細な技術情報は[CLAUDE_TECHNICAL.md](./CLAUDE_TECHNICAL.md)を参照してください。
