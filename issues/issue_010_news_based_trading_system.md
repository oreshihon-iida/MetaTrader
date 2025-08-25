# Issue #010: News-Based Trading System - ニュース駆動型自動取引戦略

## 📋 プロジェクト概要
**開発期間**: 2025年8月24日  
**開発目標**: ニュースフィードを活用した自動取引システムの構築  
**最終バージョン**: v3  
**ステータス**: ✅ **デモ口座稼働中**

## 🎯 開発背景
- バックテストで54万円の利益を確認（2024年データ）
- テクニカル分析のみの戦略から、ファンダメンタルズ要素を統合
- リアルタイムニュース分析による取引判断の自動化

## 🚀 システム構成

### 1. ニュース収集システム（Python）
**ファイル**: `enhanced_news_collector_v2.py`

#### 機能
- RSS フィードからリアルタイムニュース収集
- Yahoo Finance、Reuters等の主要ソースをカバー
- 60秒間隔での自動更新
- 重複ニュース防止機能

#### データソース
```python
rss_sources = {
    'Yahoo Finance': 'https://finance.yahoo.com/news/rss',
    'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
    'Reuters Markets': 'https://feeds.reuters.com/reuters/markets',
    'MarketWatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse',
    'CNBC Top News': 'https://www.cnbc.com/id/100003114/device/rss/rss.html'
}
```

### 2. 感情分析システム（現在：簡易版）

#### 現在の実装
- 単語ベースの簡易センチメント分析
- bullish/bearish/neutral の3分類
- FX関連度スコアリング（0.0-1.0）

#### 判定ロジック
```python
# FX関連度 >= 0.6 かつ 重要度 == HIGH で取引シグナル生成
trade_signal = fx_relevance >= 0.6 and importance == 'HIGH'
```

### 3. Expert Advisor（MQL5）
**ファイル**: `NewsBasedTradingSystem_v3.mq5`

#### 主要機能
- CSVファイルからシグナル読み込み（60秒間隔）
- 自動ポジション管理（エントリー/決済）
- リスク管理（証拠金1%/取引）
- 動的ロットサイズ計算

#### パラメータ
```mql5
input double RiskPercent = 1.0;          // リスク比率
input int MaxPositions = 3;              // 最大同時ポジション
input double MaxMarginUsage = 70.0;      // 最大証拠金使用率
input int SignalCheckInterval = 60;      // シグナルチェック間隔（秒）
input string CSVFile = "longterm_news_signals.csv";  // CSVファイル名
```

## 📊 技術的成果

### 解決した課題
1. **CSVファイルパス問題**
   - 問題: `Files\Files\longterm_news_signals.csv` の二重パス
   - 原因: FileOpen関数が既にMQL5\Files内で動作
   - 解決: パスプレフィックス削除

2. **文字エンコーディング問題**
   - 問題: 日本語Windowsでのバッチファイル実行エラー
   - 解決: 英語のみのバッチファイルに書き換え

3. **RSS フィードアクセス問題**
   - DailyFX: 403 Forbidden → 無効化
   - ForexLive: 404 Not Found → 無効化

### システムアーキテクチャ
```
[RSS Feeds] → [Python Collector] → [CSV File] → [MT5 EA] → [Auto Trading]
     ↓              ↓                    ↑            ↓
[60秒間隔]    [簡易分析]         [60秒間隔]    [TP/SL管理]
```

## 🔮 将来の発展計画

### Phase 1: Claude感情分析統合（計画中）
```python
# 将来実装予定
def analyze_with_claude(self, news_text):
    """
    Claude APIを使用した高度な感情分析
    - 文脈理解
    - 複雑な因果関係分析
    - 市場影響度の定量評価
    """
    pass
```

### Phase 2: 機械学習統合
- ニュースと価格変動の相関学習
- 取引成功パターンの自動抽出
- 動的パラメータ最適化

### Phase 3: マルチ通貨対応
- USD/JPY以外の通貨ペアサポート
- 通貨相関を考慮した総合判断
- ポートフォリオ最適化

## 📈 運用実績

### バックテスト結果（2024年）
- **初期資金**: 300万円
- **最終資金**: 354万円
- **純利益**: +54万円
- **月平均**: +4.5万円

### デモ口座運用（2025年8月24日〜）
- **状態**: 稼働中
- **監視項目**: 
  - リアルタイムニュース反応速度
  - シグナル生成精度
  - 実際の約定状況

## 🛠️ 関連ファイル

### コアシステム
- `enhanced_news_collector_v2.py` - ニュース収集・分析
- `NewsBasedTradingSystem_v3.mq5` - MT5 EA
- `auto_news_collector.bat` - 自動収集バッチ
- `generate_initial_signals.py` - テストシグナル生成

### 設定・データ
- `longterm_news_signals.csv` - 取引シグナルデータ
- `news_history.json` - 処理済みニュース履歴

## 💡 重要な学習事項

1. **MT5ファイルシステムの理解**
   - サンドボックス環境での動作
   - FileOpen関数の基準ディレクトリ
   - セキュリティ制限の影響

2. **リアルタイム処理の課題**
   - ニュースフィードの信頼性
   - レート制限への対応
   - 重複処理の防止

3. **自動取引の実装**
   - 24時間稼働の要件（VPS推奨）
   - エラーハンドリングの重要性
   - リスク管理の多層防御

## 🎯 達成状況

### 完了項目
- ✅ RSS フィード統合
- ✅ 簡易感情分析実装
- ✅ MT5 EA開発・デプロイ
- ✅ デモ口座での稼働開始
- ✅ 自動化システム構築

### 保留項目
- ⏸️ Claude感情分析統合
- ⏸️ VPS環境への移行
- ⏸️ 本番口座での運用

## 📝 結論

NewsBasedTradingSystem v3は、ニュース駆動型の自動取引システムとして基本機能を完成させ、デモ口座での稼働を開始した。現在は簡易的な感情分析を使用しているが、将来的にClaude APIを統合することで、より高度な市場分析が可能になる見込み。

バックテストでの54万円の利益実績を基に、リアルタイムでの検証を継続中。システムの安定性と収益性を確認後、段階的に機能拡張を進める予定。

---

**開発完了日**: 2025年8月24日  
**Issue作成日**: 2025年8月24日  
**最終更新**: 2025年8月24日