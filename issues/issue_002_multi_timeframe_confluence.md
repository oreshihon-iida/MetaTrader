# Issue #002: マルチタイムフレーム・コンフルエンス戦略実装

## 概要
4時間足と日足の複数時間軸を組み合わせた高精度トレンドフォロー戦略の実装

## 背景
単一時間軸では誤シグナルが多発。複数時間軸の確認により、より確実性の高いエントリーポイントを特定し、勝率向上を図る。

## 目的
- 複数時間軸の合流点での高確率取引
- 月間10-15回の質の高い取引
- 勝率70%以上の実現

## 詳細仕様

### 1. 時間軸の定義と役割
```python
# 時間軸設定
PRIMARY_TIMEFRAME = "4H"    # メイン判断軸
HIGHER_TIMEFRAME = "D1"     # トレンド確認軸
CONFIRMATION_TF = "1H"      # エントリータイミング軸（オプション）

# 各時間軸の役割
timeframe_roles = {
    "D1": "overall_trend",      # 大局トレンド
    "4H": "trade_direction",    # 取引方向
    "1H": "entry_timing"        # エントリータイミング
}
```

### 2. トレンド判定ロジック
```python
def analyze_trend(timeframe):
    # 移動平均線ベース
    ema_20 = EMA(close, 20)
    ema_50 = EMA(close, 50)
    sma_200 = SMA(close, 200)
    
    # トレンドスコア計算（-100 to +100）
    trend_score = 0
    
    # 価格位置
    if close > sma_200:
        trend_score += 25
    else:
        trend_score -= 25
    
    # EMAクロス
    if ema_20 > ema_50:
        trend_score += 25
    else:
        trend_score -= 25
    
    # 傾き
    ema_slope = (ema_50[-1] - ema_50[-10]) / 10
    trend_score += min(50, max(-50, ema_slope * 100))
    
    # ADX強度
    adx_value = ADX(14)
    if adx_value > 25:
        trend_score = trend_score * 1.2
    
    return trend_score
```

### 3. コンフルエンス（合流）判定
```python
def check_confluence():
    # 各時間軸のトレンドスコア取得
    daily_trend = analyze_trend("D1")
    h4_trend = analyze_trend("4H")
    h1_trend = analyze_trend("1H")
    
    # 重み付け平均
    weights = {"D1": 0.4, "4H": 0.4, "1H": 0.2}
    weighted_score = (
        daily_trend * weights["D1"] +
        h4_trend * weights["4H"] +
        h1_trend * weights["1H"]
    )
    
    # コンフルエンス条件
    strong_bullish = weighted_score > 60
    strong_bearish = weighted_score < -60
    
    # 方向性の一致確認
    all_bullish = daily_trend > 0 and h4_trend > 0
    all_bearish = daily_trend < 0 and h4_trend < 0
    
    # 最終判定
    if strong_bullish and all_bullish:
        return "STRONG_BUY"
    elif strong_bearish and all_bearish:
        return "STRONG_SELL"
    else:
        return "NO_TRADE"
```

### 4. エントリー条件
```python
# プライマリ条件（4時間足）
def primary_entry_signal():
    # RSIダイバージェンス
    rsi = RSI(14)
    price_higher = high[-1] > high[-5]
    rsi_lower = rsi[-1] < rsi[-5]
    bearish_divergence = price_higher and rsi_lower
    
    # MACD確認
    macd, signal, histogram = MACD(12, 26, 9)
    macd_bullish = macd > signal and histogram > 0
    macd_bearish = macd < signal and histogram < 0
    
    # ボリューム確認
    volume_surge = volume > SMA(volume, 20) * 1.5
    
    return {
        "divergence": bearish_divergence,
        "macd": macd_bullish or macd_bearish,
        "volume": volume_surge
    }

# 最終エントリー判定
def final_entry_decision():
    confluence = check_confluence()
    primary_signals = primary_entry_signal()
    
    # 必須条件
    if confluence == "NO_TRADE":
        return None
    
    # 確認条件（3つ中2つ以上）
    signal_count = sum([
        primary_signals["divergence"],
        primary_signals["macd"],
        primary_signals["volume"]
    ])
    
    if signal_count >= 2:
        return confluence
    
    return None
```

### 5. ポジション管理
```python
# ポジションサイジング
def calculate_position_size():
    # コンフルエンススコアに基づく動的調整
    base_risk = 0.02  # 基本リスク2%
    confluence_multiplier = min(1.5, max(0.5, weighted_score / 50))
    adjusted_risk = base_risk * confluence_multiplier
    
    # ATRベースのストップロス
    atr_4h = get_atr("4H", 14)
    stop_distance = atr_4h * 2.5
    
    position_size = (account_balance * adjusted_risk) / stop_distance
    return position_size

# 利確・損切り
def set_exit_levels():
    # 日足レジスタンス/サポートを考慮
    daily_levels = get_support_resistance("D1")
    
    # 動的TP設定
    if confluence == "STRONG_BUY":
        tp1 = entry_price + (atr_4h * 2)  # 第1目標
        tp2 = min(daily_levels["resistance"], entry_price + (atr_4h * 4))  # 第2目標
        tp3 = entry_price + (atr_4h * 6)  # 第3目標
    
    # 分割決済
    exit_strategy = {
        "tp1": {"price": tp1, "percent": 40},
        "tp2": {"price": tp2, "percent": 40},
        "tp3": {"price": tp3, "percent": 20}
    }
    
    return exit_strategy
```

### 6. リスク管理
```python
# 時間軸矛盾時の処理
conflict_resolution = {
    "priority": "D1 > 4H > 1H",  # 優先順位
    "min_agreement": 2,          # 最低2つの時間軸が一致
    "veto_power": "D1"           # 日足が逆なら取引なし
}

# 最大ポジション制限
max_positions = {
    "total": 3,
    "per_direction": 2,  # 同一方向は最大2つ
    "correlation_check": True  # 相関チェック実施
}

# ドローダウン管理
drawdown_limits = {
    "daily": 0.03,    # 3%
    "weekly": 0.08,   # 8%
    "monthly": 0.15   # 15%
}
```

## 実装要件

### 技術要件
- マルチタイムフレームデータ同期処理
- 効率的なデータキャッシング
- リアルタイム更新対応

### データ要件
- 1時間足、4時間足、日足データ（3年分）
- データ整合性チェック機能
- 欠損データ補完処理

## テスト計画

### ユニットテスト
- [ ] トレンドスコア計算の正確性
- [ ] コンフルエンス判定ロジック
- [ ] 時間軸同期処理
- [ ] 矛盾解決アルゴリズム

### 統合テスト
- [ ] 複数時間軸データの整合性
- [ ] シグナル生成タイミング
- [ ] パフォーマンス（処理速度）
- [ ] メモリ使用量

### 受入基準
- [ ] 勝率: 70%以上
- [ ] 月間取引: 10-15回
- [ ] プロフィットファクター: 1.5以上
- [ ] 平均保有期間: 2-5日
- [ ] 最大連敗: 3回以内

## 実装ステップ

1. **ブランチ作成**
```bash
git checkout -b feature/issue-002-multi-timeframe-confluence
```

2. **データ処理層実装**
- マルチタイムフレームローダー
- データ同期メカニズム
- キャッシング実装

3. **分析エンジン実装**
- トレンド分析モジュール
- コンフルエンス計算
- シグナル生成

4. **取引ロジック実装**
- エントリー/エグジット
- ポジション管理
- リスク管理

5. **最適化と検証**
- パラメータチューニング
- バックテスト実行
- 結果分析

## 成功指標

### 必須達成項目
- ✅ 勝率 70%以上
- ✅ 月間利益 5-8万円
- ✅ シャープレシオ 1.2以上

### 追加評価項目
- 取引あたり平均利益 5,000円以上
- 最大ドローダウン期間 10日以内
- 時間軸一致率 80%以上

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| 時間軸の矛盾 | 高 | 中 | 優先順位ルール、最小一致数設定 |
| シグナル遅延 | 中 | 高 | 早期警戒シグナル、部分エントリー |
| 過度の複雑化 | 中 | 中 | スコアリングシステムで簡略化 |
| データ同期エラー | 高 | 低 | 冗長性確保、エラーハンドリング |

## 依存関係
- Issue #001の基本フレームワーク
- 既存のDataLoaderクラス
- テクニカル指標ライブラリ（TA-Lib）

## 作業見積もり
- データ処理層: 6時間
- 分析エンジン: 8時間
- 取引ロジック: 6時間
- テスト作成: 6時間
- 最適化: 8時間
- ドキュメント: 2時間
- **合計: 36時間**

## 関連Issue
- #001: ダイナミックレンジ戦略（統合可能性）
- #003: ファンダメンタルズ戦略（フィルター利用）
- #004: ボリンジャー戦略（確認指標として）

---
*Issue作成日: 2025年8月17日*
*目標完了日: 2025年9月7日*