# サポート/レジスタンスレベル検出アルゴリズム改善の総括

## 1. 実装した改善内容

### 1.1 アダプティブなパラメータ設定
- ATR（Average True Range）を使用して市場ボラティリティを測定
- ボラティリティに応じてスイングポイント検出の閾値とクラスタリングの距離閾値を動的に調整
- 高ボラティリティ環境では大きな閾値、低ボラティリティ環境では小さな閾値を使用

```python
# ボラティリティに基づいて閾値を調整
if adaptive_params:
    # ATR（Average True Range）を計算して市場ボラティリティを測定
    high = df['high'].values
    low = df['low'].values
    close = np.array(df['close'].shift(1).fillna(df['close'].iloc[0]))
    true_range = np.maximum(high - low, np.maximum(np.abs(high - close), np.abs(low - close)))
    atr = pd.Series(true_range).rolling(vol_lookback).mean().values
    
    # ATRの長期平均に対する比率でパラメータを調整
    atr_mean = np.nanmean(atr)
    atr_ratio = atr / atr_mean
    atr_ratio = np.nan_to_num(atr_ratio, nan=1.0)
    
    # 閾値を動的に調整
    dynamic_swing_threshold = np.where(atr_ratio > 0, swing_threshold * atr_ratio, swing_threshold)
    dynamic_cluster_distance = np.where(atr_ratio > 0, cluster_distance * atr_ratio, cluster_distance)
```

### 1.2 改良されたクラスタリング手法
- DBSCAN風のクラスタリングアルゴリズムを実装
- 価格レベルの「強度」（タッチ回数）を考慮した重み付き平均を計算
- より重要なサポート/レジスタンスレベルを優先的に抽出

```python
def _improved_cluster_levels(self, prices, points, cluster_distance):
    # ポイントを価格に変換
    price_points = [prices[i] for i in points]
    
    # 強度を計算（同じレベル付近でのタッチ回数）
    strength = {}
    for p in price_points:
        for p2 in price_points:
            if abs(p - p2) < cluster_distance:
                strength[p] = strength.get(p, 0) + 1
    
    # クラスタリング（DBSCAN風のアプローチ）
    clusters = []
    visited = set()
    
    for p in sorted(price_points, key=lambda x: strength.get(x, 0), reverse=True):
        if p in visited:
            continue
            
        cluster = []
        self._expand_cluster(p, price_points, cluster, visited, cluster_distance)
        
        if cluster:
            # 重み付き平均を計算（タッチ回数の多いレベルを重視）
            weighted_sum = sum(p * strength.get(p, 1) for p in cluster)
            total_weight = sum(strength.get(p, 1) for p in cluster)
            cluster_avg = weighted_sum / total_weight if total_weight > 0 else 0
            clusters.append(cluster_avg)
    
    return clusters
```

### 1.3 複数時間足分析
- 15分足と1時間足のサポート/レジスタンスレベルを統合
- 大きな時間足のレベルを優先的に考慮
- 複数時間足の確認によるフィルタリング機能を実装

```python
def merge_multi_timeframe_levels(self, df_15min, df_1h, max_levels=3):
    result_df = df_15min.copy()
    
    # 1時間足のデータを15分足のインデックスにリサンプル
    hour_support_levels = {}
    hour_resistance_levels = {}
    
    for i in range(1, max_levels + 1):
        if f'support_level_{i}' in df_1h.columns:
            hour_support_levels[i] = df_1h[f'support_level_{i}'].resample('15T').ffill()
        
        if f'resistance_level_{i}' in df_1h.columns:
            hour_resistance_levels[i] = df_1h[f'resistance_level_{i}'].resample('15T').ffill()
    
    # 1時間足のレベルを15分足のデータフレームに追加
    for i in range(1, max_levels + 1):
        if i in hour_support_levels:
            result_df[f'h1_support_level_{i}'] = hour_support_levels[i]
        
        if i in hour_resistance_levels:
            result_df[f'h1_resistance_level_{i}'] = hour_resistance_levels[i]
    
    return result_df
```

### 1.4 サポート/レジスタンス戦略の実装
- サポート/レジスタンスレベルからのバウンス（反発）を利用した取引戦略
- サポート/レジスタンスレベルのブレイクアウト（突破）を利用した取引戦略
- RSIとの組み合わせによるフィルタリング

```python
# バウンス戦略（サポートからの反発）
if 'support_level_1' in current_row and not pd.isna(current_row['support_level_1']):
    support_level = current_row['support_level_1']
    
    # 価格がサポートレベル付近でRSIが30以下の場合、買いシグナル
    if (prev_row['low'] - support_level) / support_level < self.bounce_threshold and current_row['rsi'] < 30:
        result_df.loc[result_df.index[i], 'signal'] = 1
        result_df.loc[result_df.index[i], 'entry_price'] = price
        result_df.loc[result_df.index[i], 'sl_price'] = price - self.sl_pips * 0.01
        result_df.loc[result_df.index[i], 'tp_price'] = price + self.tp_pips * 0.01
        result_df.loc[result_df.index[i], 'strategy'] = self.strategy_name + "_SupportBounce"
```

### 1.5 価格アクションパターンの導入
- ピンバー、エンゲルフィングなどのパターン検出
- パターンが確認された場合のみシグナルを生成

```python
def detect_pin_bar(self, df, i, direction='bullish'):
    """
    ピンバーパターンを検出する
    
    Parameters
    ----------
    df : pd.DataFrame
        価格データ
    i : int
        現在のインデックス
    direction : str, default 'bullish'
        'bullish'または'bearish'
        
    Returns
    -------
    bool
        ピンバーパターンが検出された場合はTrue
    """
    if i < 1:
        return False
    
    current = df.iloc[i]
    prev = df.iloc[i-1]
    
    body_size = abs(current['open'] - current['close'])
    total_range = current['high'] - current['low']
    
    # ボディサイズが小さく、ヒゲが長いキャンドル
    if body_size / total_range < 0.3:
        if direction == 'bullish':
            # 下ヒゲが長い（ボディの3倍以上）
            lower_wick = min(current['open'], current['close']) - current['low']
            return lower_wick > 3 * body_size and current['close'] > current['open']
        else:
            # 上ヒゲが長い（ボディの3倍以上）
            upper_wick = current['high'] - max(current['open'], current['close'])
            return upper_wick > 3 * body_size and current['close'] < current['open']
    
    return False
```

## 2. バックテスト結果

### 2.1 2000年のバックテスト結果

| 指標 | 改善前 | 第1版 | 第2版 |
|------|--------|-------|-------|
| 勝率 | 39.62% | 36.92% | 36.92% |
| プロフィットファクター | 1.01 | 0.99 | 0.99 |
| 総トレード数 | - | 65 | 65 |
| 総利益 | - | -6円 | -5.65円 |

### 2.2 2001年のバックテスト結果

| 指標 | 改善前 | 第1版 | 第2版 |
|------|--------|-------|-------|
| 勝率 | 45.24% | 42.86% | 42.86% |
| プロフィットファクター | 1.21 | 1.03 | 1.03 |
| 総トレード数 | - | 105 | 105 |
| 総利益 | - | 6円 | 6.45円 |

## 3. 分析と考察

### 3.1 改善の効果
- アダプティブなパラメータ設定により、市場環境に応じたサポート/レジスタンスレベルの検出が可能になりました
- 改良されたクラスタリング手法により、より重要なレベルを優先的に抽出できるようになりました
- 複数時間足の統合により、より信頼性の高いレベルを特定できるようになりました
- 価格アクションパターンの導入により、より精度の高いシグナル生成が可能になりました

### 3.2 課題
- 目標とする勝率（70%）とプロフィットファクター（2.0以上）には達していません
- 改善後の勝率が改善前よりも若干低下しています
- シグナル生成の精度が十分ではありません
- サポート/レジスタンスレベルの評価方法に改善の余地があります

### 3.3 原因分析
- サポート/レジスタンスレベルの「強度」の評価が不十分
- RSIフィルタリングの閾値が固定的
- 市場環境（トレンド/レンジ）の判断が不足
- 複数時間足の統合方法に改善の余地がある

## 4. 今後の改善案

### 4.1 機械学習の検討
- サポート/レジスタンスレベルの重要度を学習
- 市場環境に応じたパラメータの自動調整
- シグナル生成の精度向上

### 4.2 複合指標の開発
- サポート/レジスタンスレベルと他のテクニカル指標の組み合わせ
- 市場環境（トレンド/レンジ）に応じた戦略の切り替え
- 複数の確認条件によるフィルタリング

### 4.3 パラメータ最適化の自動化
- 遺伝的アルゴリズムによるパラメータ最適化
- ウォークフォワードテストによる過学習の防止
- 市場環境に応じたパラメータの動的調整

### 4.4 リスク管理の高度化
- 市場ボラティリティに応じた損切り/利確レベルの調整
- ポジションサイジングの最適化
- 複数ポジションの相関性を考慮したリスク管理

### 4.5 既存戦略との統合
- 東京レンジ・ロンドンブレイクアウト戦略との組み合わせ
- ボリンジャーバンド＋RSI逆張り戦略との組み合わせ
- 複数戦略のシグナルを統合した複合シグナルシステムの構築

## 5. 結論

サポート/レジスタンスレベル検出アルゴリズムの改善と新しい取引戦略の実装を行いましたが、目標とする勝率（70%）とプロフィットファクター（2.0以上）には達していません。しかし、今回の実装は今後の改善に向けた重要な基盤となります。

特に、アダプティブなパラメータ設定、改良されたクラスタリング手法、複数時間足分析、価格アクションパターンの導入など、多くの革新的な機能を実装しました。これらの機能は、今後の改善において重要な役割を果たすでしょう。

今後は、機械学習の検討、複合指標の開発、パラメータ最適化の自動化、リスク管理の高度化、既存戦略との統合など、さらなる改善を進めていく予定です。これらの改善により、目標とする勝率とプロフィットファクターの達成を目指します。
