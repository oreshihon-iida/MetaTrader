"""
改良版ニュース収集システム
複数の信頼性の高いソースから情報を収集し、CSVファイルを生成
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import csv
import json
import time
import os

class EnhancedNewsCollector:
    """複数ソースからFXニュースを収集"""
    
    def __init__(self):
        # ブラウザヘッダー（Investing.com対策）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
        }
        
        # 複数のRSSソース（動作確認済みのみ有効化）
        self.rss_sources = {
            # 日本語ソース（正常動作）
            'investing_fx': 'https://jp.investing.com/rss/news_14.rss',
            'investing_econ': 'https://jp.investing.com/rss/news_95.rss',
            
            # 英語ソース（正常動作）
            'fxstreet': 'https://www.fxstreet.com/rss/news',
            
            # 中央銀行（正常動作）
            'fed': 'https://www.federalreserve.gov/feeds/press_all.xml',
            
            # エラーになるソース（一時的に無効化）
            # 'dailyfx': 'https://www.dailyfx.com/feeds/market-news',  # 403 Forbidden
            # 'forexlive': 'https://www.forexlive.com/feed/rss',       # 404 Not Found
        }
        
        # 重要イベントキーワード
        self.high_importance_keywords = [
            'fomc', 'fed', 'ecb', 'boj', '日銀', '中央銀行',
            'interest rate', '金利', '利上げ', '利下げ',
            'nfp', 'non-farm', '雇用統計', 'employment',
            'gdp', 'cpi', '消費者物価指数', 'inflation'
        ]
        
        # ニュース履歴（重複防止）
        self.history_file = 'news_history.json'
        self.load_history()
    
    def load_history(self):
        """過去のニュース履歴を読み込み"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    # 必要なキーが存在しない場合は追加
                    if 'processed_ids' not in self.history:
                        self.history['processed_ids'] = []
                    if 'last_update' not in self.history:
                        self.history['last_update'] = None
            except:
                # ファイルが壊れている場合は初期化
                self.history = {'processed_ids': [], 'last_update': None}
        else:
            self.history = {'processed_ids': [], 'last_update': None}
    
    def save_history(self):
        """ニュース履歴を保存"""
        self.history['last_update'] = datetime.now().isoformat()
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def fetch_rss(self, url, source_name):
        """RSSフィードを取得"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                
                # gzip解凍が必要な場合
                if response.headers.get('Content-Encoding') == 'gzip':
                    import gzip
                    content = gzip.decompress(content)
                
                return content
        except Exception as e:
            print(f"[{source_name}] 取得エラー: {str(e)[:50]}")
            return None
    
    def parse_rss(self, content, source_name):
        """RSSをパースしてニュースアイテムを抽出"""
        items = []
        
        try:
            root = ET.fromstring(content)
            channel = root.find('.//channel')
            
            if channel is None:
                return items
            
            for item in channel.findall('item'):
                news_item = {
                    'source': source_name,
                    'title': item.findtext('title', ''),
                    'description': item.findtext('description', ''),
                    'link': item.findtext('link', ''),
                    'pubDate': item.findtext('pubDate', ''),
                    'guid': item.findtext('guid', ''),
                    'timestamp': datetime.now().isoformat()
                }
                
                # 重要度を判定
                news_item['importance'] = self.determine_importance(news_item)
                
                # FX関連度を判定
                news_item['fx_relevance'] = self.calculate_fx_relevance(news_item)
                
                items.append(news_item)
                
        except Exception as e:
            print(f"[{source_name}] パースエラー: {str(e)[:50]}")
        
        return items
    
    def determine_importance(self, item):
        """ニュースの重要度を判定（HIGH/MEDIUM/LOW）"""
        text = (item['title'] + ' ' + item['description']).lower()
        
        # HIGH: 中央銀行関連
        if any(kw in text for kw in self.high_importance_keywords):
            return 'HIGH'
        
        # MEDIUM: 一般的な経済指標
        medium_keywords = ['trade', '貿易', 'retail', '小売', 'manufacturing', '製造業']
        if any(kw in text for kw in medium_keywords):
            return 'MEDIUM'
        
        return 'LOW'
    
    def calculate_fx_relevance(self, item):
        """FX関連度をスコア化（0.0-1.0）"""
        text = (item['title'] + ' ' + item['description']).lower()
        
        fx_keywords = [
            'usd', 'jpy', 'eur', 'gbp', 'ドル', '円', 'ユーロ', 'ポンド',
            'forex', 'fx', '為替', 'currency', 'exchange rate'
        ]
        
        matches = sum(1 for kw in fx_keywords if kw in text)
        score = min(1.0, matches * 0.2)  # 5個以上で1.0
        
        return score
    
    def analyze_sentiment(self, item):
        """簡易センチメント分析（bullish/bearish/neutral）"""
        text = (item['title'] + ' ' + item['description']).lower()
        
        bullish_words = ['上昇', 'rise', 'up', 'higher', 'gain', '利上げ', 'hawkish', '強い', 'strong']
        bearish_words = ['下落', 'fall', 'down', 'lower', 'loss', '利下げ', 'dovish', '弱い', 'weak']
        
        bullish_count = sum(1 for word in bullish_words if word in text)
        bearish_count = sum(1 for word in bearish_words if word in text)
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def collect_all_news(self):
        """全ソースからニュースを収集"""
        all_news = []
        
        for source_name, url in self.rss_sources.items():
            print(f"\n[{source_name}] 収集中...")
            
            # フィード取得
            content = self.fetch_rss(url, source_name)
            if not content:
                continue
            
            # パース
            items = self.parse_rss(content, source_name)
            
            # 重複チェック
            new_items = []
            for item in items:
                if item['guid'] not in self.history['processed_ids']:
                    new_items.append(item)
                    self.history['processed_ids'].append(item['guid'])
            
            print(f"  新規: {len(new_items)}件 / 全体: {len(items)}件")
            all_news.extend(new_items)
            
            # レート制限対策
            time.sleep(1)
        
        return all_news
    
    def generate_trading_signals(self, news_items):
        """ニュースから取引シグナルを生成"""
        signals = []
        
        for item in news_items:
            # FX関連度が高く、重要度が高いもののみ
            if item['fx_relevance'] >= 0.4 and item['importance'] in ['HIGH', 'MEDIUM']:
                
                sentiment = self.analyze_sentiment(item)
                
                signal = {
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'event_date': item['pubDate'],
                    'event_time': '',
                    'event_type': item['title'][:50],
                    'importance': item['importance'],
                    'actual': '',
                    'forecast': '',
                    'previous': '',
                    'expected_direction': sentiment,
                    'confidence': item['fx_relevance'],
                    'ml_confidence': 0.5,  # 簡易版なので固定
                    'priced_in_factor': 0.3,  # 簡易版なので固定
                    'enhanced_confidence': item['fx_relevance'] * 0.8,
                    'trade_signal': item['fx_relevance'] >= 0.6 and item['importance'] == 'HIGH',
                    'recommended_tp_pips': 50 if item['importance'] == 'HIGH' else 30,
                    'recommended_sl_pips': 20 if item['importance'] == 'HIGH' else 15,
                    'news_importance': item['importance']  # v3用
                }
                
                signals.append(signal)
        
        return signals
    
    def save_to_csv(self, signals, filename='longterm_news_signals.csv'):
        """シグナルをCSVファイルに保存（MT5 EA用）"""
        
        if not signals:
            print("保存するシグナルがありません")
            return
        
        # CSVヘッダー（EA読み込み用）
        headers = [
            'analysis_date', 'event_date', 'event_time', 'event_type',
            'importance', 'actual', 'forecast', 'previous',
            'expected_direction', 'confidence', 'ml_confidence',
            'priced_in_factor', 'enhanced_confidence', 'trade_signal',
            'recommended_tp_pips', 'recommended_sl_pips'
        ]
        
        # MT5のFilesフォルダパス
        mt5_files_path = r'C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files'
        mt5_csv_path = os.path.join(mt5_files_path, filename)
        
        # 1. MT5のFilesフォルダに保存（EA読み込み用）
        try:
            os.makedirs(mt5_files_path, exist_ok=True)  # フォルダがなければ作成
            with open(mt5_csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for signal in signals:
                    # news_importance は v3用なので除外
                    row = {k: v for k, v in signal.items() if k != 'news_importance'}
                    writer.writerow(row)
            
            print(f"\n[MT5] CSVファイル生成: {mt5_csv_path}")
            print(f"シグナル数: {len(signals)}件")
        except Exception as e:
            print(f"[ERROR] MT5フォルダへの保存失敗: {e}")
        
        # 2. ローカルフォルダにもバックアップ保存
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for signal in signals:
                # news_importance は v3用なので除外
                row = {k: v for k, v in signal.items() if k != 'news_importance'}
                writer.writerow(row)
        
        print(f"[バックアップ] CSVファイル生成: {filename}")
        print(f"シグナル数: {len(signals)}件")

def main():
    """メイン処理"""
    print("="*60)
    print("Enhanced News Collector v2")
    print("複数ソースからのFXニュース収集システム")
    print("="*60)
    
    collector = EnhancedNewsCollector()
    
    # ニュース収集
    print("\n[Phase 1] ニュース収集")
    all_news = collector.collect_all_news()
    
    print(f"\n合計 {len(all_news)} 件の新規ニュースを収集")
    
    # シグナル生成
    print("\n[Phase 2] シグナル生成")
    signals = collector.generate_trading_signals(all_news)
    
    print(f"生成されたシグナル: {len(signals)}件")
    
    # 高重要度シグナルを表示
    high_signals = [s for s in signals if s['importance'] == 'HIGH']
    if high_signals:
        print("\n[HIGH重要度シグナル]")
        for i, sig in enumerate(high_signals[:5]):
            # ASCII文字のみ表示
            event_type = sig['event_type'].encode('ascii', 'ignore').decode('ascii')
            print(f"{i+1}. {event_type[:50]}")
            print(f"   方向: {sig['expected_direction']}, 信頼度: {sig['enhanced_confidence']:.2f}")
    
    # CSV保存
    print("\n[Phase 3] CSV保存")
    collector.save_to_csv(signals)
    
    # 履歴保存
    collector.save_history()
    
    print("\n完了！NewsBasedTradingSystem v3で使用可能です。")

if __name__ == "__main__":
    main()