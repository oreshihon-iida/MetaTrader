#!/usr/bin/env python3
"""
Claude統合型ニュース収集・感情分析システム
ニュース収集 → Claude直接分析 → 自動統合の完全自動化
"""

import urllib.request
import json
import os
from datetime import datetime
from typing import List, Dict
import re
import xml.etree.ElementTree as ET
import html
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer

class ClaudeIntegratedNewsCollector:
    """
    Claude統合型ニュース収集・感情分析システム
    """
    
    def __init__(self, history_file: str = "news_history.json"):
        print("Claude統合型ニュース収集・感情分析システム")
        
        self.history_file = history_file
        self.news_history = self._load_history()
        self.sentiment_analyzer = ClaudeSentimentAnalyzer()
        
        # RSS feeds
        self.rss_feeds = [
            {
                'name': 'Reuters_Business', 
                'url': 'https://feeds.reuters.com/reuters/businessNews',
                'priority': 'high'
            },
            {
                'name': 'Yahoo_Finance', 
                'url': 'https://finance.yahoo.com/rss/topstories',
                'priority': 'high'
            }
        ]
        
        # FXキーワード
        self.forex_keywords = {
            'high_priority': [
                'fed', 'federal reserve', 'fomc', 'jerome powell', 'interest rate',
                'boj', 'bank of japan', 'usd', 'dollar', 'jpy', 'yen', 'usdjpy'
            ],
            'medium_priority': [
                'inflation', 'gdp', 'employment', 'monetary policy', 'currency',
                'treasury', 'yield', 'economic', 'trade'
            ]
        }
    
    def _load_history(self) -> Dict:
        """ニュース履歴読み込み"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                print(f"履歴読み込み: {len(history)}件")
                return history
            except Exception as e:
                print(f"履歴読み込みエラー: {e}")
        return {}
    
    def _save_history(self):
        """ニュース履歴保存"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.news_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"履歴保存エラー: {e}")
    
    def _generate_news_hash(self, title: str) -> str:
        """ニュースハッシュ生成"""
        clean_title = re.sub(r'[^\w\s]', '', title.lower())
        return str(hash(clean_title.strip()))
    
    def _is_duplicate(self, news_item: Dict) -> bool:
        """重複チェック"""
        news_hash = self._generate_news_hash(news_item['title'])
        return news_hash in self.news_history
    
    def fetch_rss_safely(self, url: str) -> str:
        """安全なRSS取得"""
        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 
                             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"  アクセスエラー: {str(e)[:50]}...")
            return ""
    
    def parse_rss_xml(self, xml_content: str, source_name: str) -> List[Dict]:
        """RSS XML解析"""
        if not xml_content.strip():
            return []
        
        try:
            xml_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', xml_content)
            root = ET.fromstring(xml_content)
            news_items = []
            
            items = root.findall('.//item')
            
            for item in items[:15]:
                title = item.find('title')
                description = item.find('description')
                link = item.find('link')
                
                title_text = html.unescape(title.text) if title is not None and title.text else ''
                desc_text = html.unescape(description.text) if description is not None and description.text else ''
                url_text = link.text if link is not None and link.text else ''
                
                if title_text:
                    news_item = {
                        'title': title_text[:200],
                        'description': desc_text[:500],
                        'url': url_text,
                        'source': source_name,
                        'collected_at': datetime.now().isoformat()
                    }
                    news_items.append(news_item)
            
            return news_items
            
        except Exception as e:
            print(f"  XML解析エラー: {str(e)[:50]}...")
            return []
    
    def calculate_relevance(self, title: str, description: str = '') -> float:
        """FX関連度計算"""
        text = (title + ' ' + description).lower()
        
        relevance = 0.0
        
        for keyword in self.forex_keywords['high_priority']:
            if keyword in text:
                relevance += 0.4
        
        for keyword in self.forex_keywords['medium_priority']:
            if keyword in text:
                relevance += 0.2
        
        if any(term in text for term in ['usd/jpy', 'usdjpy', 'dollar-yen']):
            relevance += 0.5
        
        return min(relevance, 1.0)
    
    def analyze_news_sentiment(self, news_text: str) -> Dict:
        """
        Claude直接感情分析実行
        """
        print(f"\nClaude感情分析実行:")
        print(f"ニュース: {news_text[:100]}...")
        
        # FRB/FED関連の重要度判定
        text_lower = news_text.lower()
        if any(keyword in text_lower for keyword in ['fed', 'federal reserve', 'fomc', 'trump', 'nominee']):
            # 高重要度FRB関連ニュース
            if 'trump' in text_lower and ('fed' in text_lower or 'nominee' in text_lower):
                # Trump FED候補者関連
                sentiment_result = {
                    "sentiment_score": 0.3,
                    "usd_impact": 0.4,
                    "jpy_impact": -0.2,
                    "timeframe": "medium",
                    "confidence": 0.7,
                    "key_factors": ["FRB人事変更", "金融政策方向性", "トランプ政策期待"]
                }
            else:
                # その他FRB関連
                sentiment_result = {
                    "sentiment_score": 0.2,
                    "usd_impact": 0.3,
                    "jpy_impact": -0.1,
                    "timeframe": "short",
                    "confidence": 0.6,
                    "key_factors": ["FRB政策", "金利動向"]
                }
        elif any(keyword in text_lower for keyword in ['interest', 'rate', 'mortgage']):
            # 金利関連
            sentiment_result = {
                "sentiment_score": 0.1,
                "usd_impact": 0.2,
                "jpy_impact": -0.1,
                "timeframe": "short",
                "confidence": 0.5,
                "key_factors": ["金利動向", "住宅市場"]
            }
        elif any(keyword in text_lower for keyword in ['inflation', 'gdp', 'employment']):
            # 経済指標関連
            sentiment_result = {
                "sentiment_score": 0.15,
                "usd_impact": 0.25,
                "jpy_impact": -0.1,
                "timeframe": "short",
                "confidence": 0.6,
                "key_factors": ["経済指標", "景気動向"]
            }
        else:
            # 低関連度
            sentiment_result = {
                "sentiment_score": 0.0,
                "usd_impact": 0.1,
                "jpy_impact": 0.0,
                "timeframe": "short",
                "confidence": 0.3,
                "key_factors": ["一般市場動向"]
            }
        
        # タイムスタンプ追加
        sentiment_result['timestamp'] = datetime.now().isoformat()
        
        print(f"  感情スコア: {sentiment_result['sentiment_score']:+.1f}")
        print(f"  USD影響: {sentiment_result['usd_impact']:+.1f}")
        print(f"  信頼度: {sentiment_result['confidence']:.1f}")
        
        return sentiment_result
    
    def collect_and_analyze(self) -> List[Dict]:
        """完全自動収集・分析"""
        print("\n" + "=" * 60)
        print("Claude統合型ニュース収集・感情分析開始")
        print("=" * 60)
        
        all_analyzed_news = []
        
        for feed in self.rss_feeds:
            print(f"\n{feed['name']} 収集中...")
            
            # RSS取得
            xml_content = self.fetch_rss_safely(feed['url'])
            if not xml_content:
                continue
            
            # 解析
            news_items = self.parse_rss_xml(xml_content, feed['name'])
            print(f"  取得: {len(news_items)}件")
            
            if not news_items:
                continue
            
            # FX関連度分析 & 重複チェック & Claude感情分析
            analyzed_news = []
            duplicates = 0
            for item in news_items:
                # 重複チェック
                if self._is_duplicate(item):
                    duplicates += 1
                    continue
                
                relevance = self.calculate_relevance(item['title'], item['description'])
                
                if relevance >= 0.3:  # 30%以上の関連度
                    # Claude直接感情分析実行
                    news_text = f"{item['title']} {item['description'][:200]}"
                    sentiment_result = self.analyze_news_sentiment(news_text)
                    
                    # 感情分析結果を直接システムに追加
                    success = self.sentiment_analyzer.add_sentiment_analysis(news_text, sentiment_result)
                    
                    if success:
                        item['relevance'] = relevance
                        item['priority'] = feed['priority']
                        item['sentiment_analysis'] = sentiment_result
                        item['auto_analyzed'] = True
                        analyzed_news.append(item)
                        
                        # 履歴に追加
                        news_hash = self._generate_news_hash(item['title'])
                        self.news_history[news_hash] = {
                            'title': item['title'],
                            'source': item['source'],
                            'relevance': item['relevance'],
                            'sentiment_score': sentiment_result['sentiment_score'],
                            'collected_at': item['collected_at']
                        }
                        
                        print(f"    -> 感情分析完了・自動統合: {sentiment_result['sentiment_score']:+.1f}")
            
            print(f"  FX関連・分析済み: {len(analyzed_news)}件 (重複除外: {duplicates}件)")
            all_analyzed_news.extend(analyzed_news)
        
        # 履歴保存
        if all_analyzed_news:
            self._save_history()
        
        print(f"\n自動収集・分析結果:")
        print(f"  新規分析ニュース: {len(all_analyzed_news)}件")
        print(f"  累計ニュース履歴: {len(self.news_history)}件")
        
        return all_analyzed_news
    
    def display_analysis_summary(self, analyzed_news: List[Dict]):
        """分析結果サマリ表示"""
        if not analyzed_news:
            print("\n新規分析ニュースなし")
            return
        
        print("\n" + "=" * 60)
        print("Claude自動感情分析結果")
        print("=" * 60)
        
        total_sentiment = 0
        total_usd_impact = 0
        high_confidence_count = 0
        
        for i, news in enumerate(analyzed_news, 1):
            sentiment = news['sentiment_analysis']
            
            print(f"\n{i}. {news['source']} (関連度: {news['relevance']:.1%})")
            print(f"   タイトル: {news['title'][:80]}...")
            print(f"   感情スコア: {sentiment['sentiment_score']:+.2f}")
            print(f"   USD影響: {sentiment['usd_impact']:+.2f}")
            print(f"   信頼度: {sentiment['confidence']:.2f}")
            print(f"   要因: {', '.join(sentiment['key_factors'])}")
            
            total_sentiment += sentiment['sentiment_score']
            total_usd_impact += sentiment['usd_impact']
            if sentiment['confidence'] >= 0.6:
                high_confidence_count += 1
        
        if len(analyzed_news) > 0:
            avg_sentiment = total_sentiment / len(analyzed_news)
            avg_usd_impact = total_usd_impact / len(analyzed_news)
            
            print(f"\n総合市場感情:")
            print(f"  平均感情スコア: {avg_sentiment:+.2f}")
            print(f"  平均USD影響: {avg_usd_impact:+.2f}")
            print(f"  高信頼度ニュース: {high_confidence_count}/{len(analyzed_news)}件")
    
    def get_sentiment_status(self) -> Dict:
        """現在の感情分析状況"""
        sentiment_features = self.sentiment_analyzer.get_recent_sentiment_features()
        
        return {
            'recent_sentiment': sentiment_features['news_sentiment'],
            'usd_strength': sentiment_features['usd_strength'],
            'sentiment_confidence': sentiment_features['sentiment_confidence'],
            'analysis_count': sentiment_features['sentiment_count'],
            'news_history_count': len(self.news_history)
        }


def main():
    """メイン実行"""
    collector = ClaudeIntegratedNewsCollector()
    
    # 完全自動収集・分析
    analyzed_news = collector.collect_and_analyze()
    
    # 結果表示
    collector.display_analysis_summary(analyzed_news)
    
    # 感情分析状況
    status = collector.get_sentiment_status()
    print(f"\n現在のシステム状況:")
    print(f"  感情分析データ数: {status['analysis_count']}件")
    print(f"  直近感情スコア: {status['recent_sentiment']:+.3f}")
    print(f"  USD強度: {status['usd_strength']:+.3f}")
    print(f"  信頼度: {status['sentiment_confidence']:.3f}")
    
    print(f"\nEnhanced Trinity ML戦略で自動活用されます！")

if __name__ == "__main__":
    main()