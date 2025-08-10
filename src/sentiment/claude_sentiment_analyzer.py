#!/usr/bin/env python3
"""
Claude Sentiment Analyzer for Forex Trading
Claude Codeベースの無料感情分析システム
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
import re

class ClaudeSentimentAnalyzer:
    """
    Claude Code感情分析システム
    """
    
    def __init__(self, sentiment_cache_path: str = "sentiment_cache.json"):
        self.sentiment_cache_path = sentiment_cache_path
        self.sentiment_cache = self._load_sentiment_cache()
        
        # 感情分析スコアの範囲
        self.score_range = (-1.0, 1.0)
        
        # 重要イベントキーワード
        self.important_keywords = {
            'fed_keywords': ['FRB', 'FOMC', '利上げ', '利下げ', 'パウエル', '金融政策'],
            'boj_keywords': ['日銀', '黒田', '植田', '金融緩和', 'YCC', '金融政策決定会合'],
            'economic_keywords': ['雇用統計', 'GDP', 'CPI', 'インフレ', 'PCE', 'ISM'],
            'geopolitical_keywords': ['ウクライナ', 'ロシア', '中東', '台湾', '中国', '地政学'],
            'market_keywords': ['株価', 'VIX', 'リスクオン', 'リスクオフ', '円安', '円高']
        }
    
    def _load_sentiment_cache(self) -> Dict:
        """感情分析キャッシュの読み込み"""
        if os.path.exists(self.sentiment_cache_path):
            try:
                with open(self.sentiment_cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"キャッシュ読み込みエラー: {e}")
        return {}
    
    def _save_sentiment_cache(self):
        """感情分析キャッシュの保存"""
        try:
            with open(self.sentiment_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.sentiment_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")
    
    def analyze_news_importance(self, news_text: str) -> float:
        """
        ニュースの重要度を自動判定
        """
        importance_score = 0.0
        news_lower = news_text.lower()
        
        # カテゴリ別重要度
        category_weights = {
            'fed_keywords': 0.9,      # FRB関連は最重要
            'boj_keywords': 0.8,      # 日銀関連も重要
            'economic_keywords': 0.7,  # 経済指標
            'geopolitical_keywords': 0.6,  # 地政学
            'market_keywords': 0.5     # 市場関連
        }
        
        for category, keywords in self.important_keywords.items():
            for keyword in keywords:
                if keyword.lower() in news_lower:
                    importance_score = max(importance_score, category_weights[category])
        
        return min(importance_score, 1.0)
    
    def generate_claude_analysis_prompt(self, news_text: str, forex_pair: str = "USDJPY") -> str:
        """
        Claude Code用の感情分析プロンプト生成
        """
        prompt = f"""
以下のニュースが{forex_pair}通貨ペアに与える影響を専門的に分析してください：

【ニュース】
{news_text}

【分析項目】
1. 総合感情スコア: -1.0〜+1.0 （強いネガティブ〜強いポジティブ）
2. USD影響度: -1.0〜+1.0 （USD弱い〜USD強い）
3. JPY影響度: -1.0〜+1.0 （JPY弱い〜JPY強い）
4. 時間軸: short/medium/long （影響の持続期間）
5. 信頼度: 0.0〜1.0 （分析の確信度）
6. 主要要因: このニュースの核心的要素

【回答形式】
```json
{{
    "sentiment_score": 0.0,
    "usd_impact": 0.0, 
    "jpy_impact": 0.0,
    "timeframe": "short",
    "confidence": 0.0,
    "key_factors": ["要因1", "要因2"]
}}
```

FXトレーダーの視点で、実際の取引判断に使える分析をお願いします。
"""
        return prompt
    
    def parse_claude_response(self, claude_response: str) -> Optional[Dict]:
        """
        Claude Codeの回答をパース
        """
        try:
            # JSON部分を抽出
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, claude_response, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                sentiment_data = json.loads(json_str)
                
                # 必要なフィールドの検証
                required_fields = ['sentiment_score', 'usd_impact', 'jpy_impact', 
                                 'timeframe', 'confidence']
                
                for field in required_fields:
                    if field not in sentiment_data:
                        print(f"必須フィールドが不足: {field}")
                        return None
                
                # 数値の範囲チェック
                for score_field in ['sentiment_score', 'usd_impact', 'jpy_impact']:
                    value = sentiment_data[score_field]
                    if not (-1.0 <= value <= 1.0):
                        print(f"スコア範囲エラー {score_field}: {value}")
                        return None
                
                if not (0.0 <= sentiment_data['confidence'] <= 1.0):
                    print(f"信頼度範囲エラー: {sentiment_data['confidence']}")
                    return None
                
                # タイムスタンプ追加
                sentiment_data['timestamp'] = datetime.now().isoformat()
                
                return sentiment_data
            
            else:
                print("JSON形式が見つかりません")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return None
        except Exception as e:
            print(f"パースエラー: {e}")
            return None
    
    def add_sentiment_analysis(self, news_text: str, analysis_result: Dict) -> bool:
        """
        感情分析結果をキャッシュに追加
        """
        try:
            news_hash = str(hash(news_text.strip()))
            analysis_result['news_text'] = news_text[:200]  # 最初の200文字のみ保存
            analysis_result['added_timestamp'] = datetime.now().isoformat()
            
            self.sentiment_cache[news_hash] = analysis_result
            self._save_sentiment_cache()
            
            print(f"感情分析結果を保存: {analysis_result['sentiment_score']:.2f}")
            return True
            
        except Exception as e:
            print(f"感情分析保存エラー: {e}")
            return False
    
    def get_recent_sentiment_features(self, hours_back: int = 24) -> Dict[str, float]:
        """
        直近の感情分析特徴量を取得
        """
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=hours_back)
        
        recent_sentiments = []
        
        # 直近のデータをフィルタリング
        for news_hash, analysis in self.sentiment_cache.items():
            try:
                timestamp = datetime.fromisoformat(analysis['timestamp'])
                if timestamp >= cutoff_time:
                    recent_sentiments.append(analysis)
            except (KeyError, ValueError):
                continue
        
        if not recent_sentiments:
            # デフォルト値（ニュートラル）
            return {
                'news_sentiment': 0.0,
                'usd_strength': 0.0,
                'jpy_strength': 0.0,
                'market_fear': 0.0,
                'sentiment_confidence': 0.5,
                'sentiment_count': 0
            }
        
        # 重み付き平均計算（新しいニュースほど重要）
        total_weight = 0
        weighted_sentiment = 0
        weighted_usd = 0
        weighted_jpy = 0
        weighted_confidence = 0
        
        for analysis in recent_sentiments:
            # 時間による重み（新しいほど重い）
            timestamp = datetime.fromisoformat(analysis['timestamp'])
            hours_ago = (current_time - timestamp).total_seconds() / 3600
            time_weight = max(0.1, 1.0 - (hours_ago / hours_back))
            
            # 信頼度による重み
            confidence_weight = analysis.get('confidence', 0.5)
            
            # 総合重み
            weight = time_weight * confidence_weight
            
            weighted_sentiment += analysis['sentiment_score'] * weight
            weighted_usd += analysis['usd_impact'] * weight
            weighted_jpy += analysis['jpy_impact'] * weight
            weighted_confidence += analysis['confidence'] * weight
            total_weight += weight
        
        if total_weight == 0:
            return {
                'news_sentiment': 0.0,
                'usd_strength': 0.0,
                'jpy_strength': 0.0,
                'market_fear': 0.0,
                'sentiment_confidence': 0.5,
                'sentiment_count': 0
            }
        
        # 正規化
        features = {
            'news_sentiment': weighted_sentiment / total_weight,
            'usd_strength': weighted_usd / total_weight,
            'jpy_strength': weighted_jpy / total_weight,
            'market_fear': -weighted_sentiment / total_weight,  # センチメントの逆
            'sentiment_confidence': weighted_confidence / total_weight,
            'sentiment_count': len(recent_sentiments)
        }
        
        return features
    
    def print_analysis_prompt(self, news_text: str):
        """
        Claude Code用プロンプトを表示
        """
        importance = self.analyze_news_importance(news_text)
        
        print("=" * 80)
        print("🧠 Claude Code 感情分析リクエスト")
        print("=" * 80)
        print(f"重要度: {importance:.2f}/1.0")
        print()
        print(self.generate_claude_analysis_prompt(news_text))
        print("=" * 80)
        print("👆 上記をClaude Codeで実行して、結果を貼り付けてください")
        print("=" * 80)
    
    def interactive_sentiment_input(self, news_text: str) -> Optional[Dict]:
        """
        対話式感情分析入力
        """
        print(f"\nニュース: {news_text}")
        print("感情分析結果を入力してください（Enter で 0.0）:")
        
        try:
            sentiment_score = float(input("総合感情スコア (-1.0〜1.0): ") or "0.0")
            usd_impact = float(input("USD影響度 (-1.0〜1.0): ") or "0.0")
            jpy_impact = float(input("JPY影響度 (-1.0〜1.0): ") or "0.0")
            timeframe = input("時間軸 (short/medium/long): ") or "short"
            confidence = float(input("信頼度 (0.0〜1.0): ") or "0.5")
            
            analysis_result = {
                'sentiment_score': max(-1.0, min(1.0, sentiment_score)),
                'usd_impact': max(-1.0, min(1.0, usd_impact)),
                'jpy_impact': max(-1.0, min(1.0, jpy_impact)),
                'timeframe': timeframe,
                'confidence': max(0.0, min(1.0, confidence)),
                'key_factors': ['手動入力'],
                'timestamp': datetime.now().isoformat()
            }
            
            return analysis_result
            
        except ValueError as e:
            print(f"入力エラー: {e}")
            return None
    
    def get_sentiment_summary(self) -> Dict:
        """
        感情分析の要約統計
        """
        if not self.sentiment_cache:
            return {"total_analyses": 0}
        
        total_count = len(self.sentiment_cache)
        recent_features = self.get_recent_sentiment_features()
        
        # スコア分布
        all_scores = [analysis.get('sentiment_score', 0) 
                     for analysis in self.sentiment_cache.values()]
        
        summary = {
            'total_analyses': total_count,
            'recent_sentiment': recent_features['news_sentiment'],
            'recent_usd_strength': recent_features['usd_strength'],
            'recent_confidence': recent_features['sentiment_confidence'],
            'avg_sentiment': np.mean(all_scores) if all_scores else 0.0,
            'sentiment_volatility': np.std(all_scores) if all_scores else 0.0
        }
        
        return summary


def demo_sentiment_analyzer():
    """
    感情分析システムのデモ
    """
    analyzer = ClaudeSentimentAnalyzer()
    
    # サンプルニュース
    sample_news = [
        "FRBが0.75%の大幅利上げを決定、インフレ抑制を最優先",
        "日銀総裁、金融緩和政策の継続を表明、円安進行の懸念",
        "米雇用統計が予想を大幅上回る、労働市場の堅調さ示す"
    ]
    
    print("🧠 Claude感情分析システム デモ")
    print("=" * 60)
    
    for news in sample_news:
        importance = analyzer.analyze_news_importance(news)
        print(f"\nニュース: {news}")
        print(f"重要度: {importance:.2f}")
        
        # プロンプト生成
        prompt = analyzer.generate_claude_analysis_prompt(news)
        print("生成されたプロンプト:")
        print(prompt[:200] + "...")
    
    # 感情特徴量取得
    features = analyzer.get_recent_sentiment_features()
    print(f"\n現在の感情特徴量:")
    for key, value in features.items():
        print(f"  {key}: {value:.3f}")


if __name__ == "__main__":
    demo_sentiment_analyzer()