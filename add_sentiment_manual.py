#!/usr/bin/env python3
"""
手動感情分析データ追加
Claude分析結果を直接システムに追加
"""

import json
import os
from datetime import datetime

# Claude分析結果
analysis_result = {
    "sentiment_score": 0.3,
    "usd_impact": 0.4,
    "jpy_impact": -0.2,
    "timeframe": "medium",
    "confidence": 0.7,
    "key_factors": ["FRB人事変更", "金融政策方向性", "トランプ政策期待"],
    "timestamp": datetime.now().isoformat()
}

news_text = "3 things you need to know about Trump's nominee for the Fed"

def add_sentiment_to_cache():
    """感情分析結果をキャッシュに追加"""
    cache_file = "sentiment_cache.json"
    
    # 既存キャッシュ読み込み
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    else:
        cache = {}
    
    # ニュースハッシュ生成
    news_hash = str(hash(news_text.strip()))
    
    # 分析結果追加
    analysis_result['news_text'] = news_text
    analysis_result['added_timestamp'] = datetime.now().isoformat()
    
    cache[news_hash] = analysis_result
    
    # 保存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"感情分析データ追加完了:")
    print(f"  ニュース: {news_text}")
    print(f"  感情スコア: {analysis_result['sentiment_score']:+.1f}")
    print(f"  USD影響: {analysis_result['usd_impact']:+.1f}")
    print(f"  JPY影響: {analysis_result['jpy_impact']:+.1f}")
    print(f"  信頼度: {analysis_result['confidence']:.1f}")
    print(f"  総キャッシュ数: {len(cache)}件")

if __name__ == "__main__":
    add_sentiment_to_cache()