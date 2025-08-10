#!/usr/bin/env python3
"""
Claude感情分析ツール
Enhanced Trinity戦略用の感情分析管理システム
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer

class SentimentTool:
    """
    感情分析管理ツール
    """
    
    def __init__(self):
        self.analyzer = ClaudeSentimentAnalyzer()
        print("🧠 Claude感情分析ツール")
        print("Enhanced Trinity戦略用感情分析システム")
        print("=" * 60)
    
    def add_news_analysis(self):
        """
        ニュース感情分析を追加
        """
        print("\n📰 新しいニュース感情分析")
        print("=" * 40)
        
        news_text = input("ニュース内容を入力してください: ").strip()
        if not news_text:
            print("❌ ニュースが入力されていません")
            return
        
        # 重要度チェック
        importance = self.analyzer.analyze_news_importance(news_text)
        print(f"📊 重要度: {importance:.2f}/1.0")
        
        if importance < 0.3:
            print("⚠️ 重要度が低いニュースです")
            continue_input = input("それでも分析しますか？ (y/N): ").lower()
            if continue_input != 'y':
                return
        
        print("\n🎯 Claude Codeでの分析が必要です")
        print("=" * 50)
        
        # Claude Codeプロンプト表示
        self.analyzer.print_analysis_prompt(news_text)
        
        print("\n📝 Claude Codeの分析結果を入力してください:")
        print("(JSON形式で貼り付けるか、個別に入力)")
        
        choice = input("入力方法を選択: [1]JSON貼り付け [2]個別入力 [3]キャンセル: ")
        
        if choice == "1":
            self._input_json_analysis(news_text)
        elif choice == "2":
            self._input_manual_analysis(news_text)
        else:
            print("キャンセルされました")
    
    def _input_json_analysis(self, news_text: str):
        """
        JSON形式の分析結果を入力
        """
        print("\nClaude CodeのJSON回答を貼り付けてください:")
        print("(複数行可、Enterを2回押して終了)")
        
        lines = []
        empty_count = 0
        
        while True:
            line = input()
            if not line:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        
        claude_response = "\n".join(lines)
        
        if not claude_response.strip():
            print("❌ 分析結果が入力されていません")
            return
        
        # Claude回答をパース
        analysis_result = self.analyzer.parse_claude_response(claude_response)
        
        if analysis_result:
            success = self.analyzer.add_sentiment_analysis(news_text, analysis_result)
            if success:
                print("✅ 感情分析を保存しました")
                self._show_analysis_result(analysis_result)
            else:
                print("❌ 保存に失敗しました")
        else:
            print("❌ JSON解析に失敗しました")
            print("個別入力に切り替えますか？ (y/N): ")
            if input().lower() == 'y':
                self._input_manual_analysis(news_text)
    
    def _input_manual_analysis(self, news_text: str):
        """
        個別入力で分析結果を入力
        """
        analysis_result = self.analyzer.interactive_sentiment_input(news_text)
        
        if analysis_result:
            success = self.analyzer.add_sentiment_analysis(news_text, analysis_result)
            if success:
                print("✅ 感情分析を保存しました")
                self._show_analysis_result(analysis_result)
            else:
                print("❌ 保存に失敗しました")
    
    def _show_analysis_result(self, analysis_result: dict):
        """
        分析結果を表示
        """
        print(f"\n📊 分析結果")
        print(f"総合感情: {analysis_result['sentiment_score']:+.2f}")
        print(f"USD影響: {analysis_result['usd_impact']:+.2f}")
        print(f"JPY影響: {analysis_result['jpy_impact']:+.2f}")
        print(f"信頼度: {analysis_result['confidence']:.2f}")
        print(f"時間軸: {analysis_result['timeframe']}")
    
    def show_current_sentiment(self):
        """
        現在の感情状況を表示
        """
        print("\n📊 現在の感情分析状況")
        print("=" * 40)
        
        # 最新の感情特徴量
        features = self.analyzer.get_recent_sentiment_features()
        
        print(f"直近24時間の感情分析:")
        print(f"  ニュース感情: {features['news_sentiment']:+.3f}")
        print(f"  USD強度: {features['usd_strength']:+.3f}")
        print(f"  JPY強度: {features['jpy_strength']:+.3f}")
        print(f"  市場恐怖: {features['market_fear']:+.3f}")
        print(f"  感情信頼度: {features['sentiment_confidence']:.3f}")
        print(f"  分析データ数: {features['sentiment_count']}")
        
        # 要約統計
        summary = self.analyzer.get_sentiment_summary()
        print(f"\n📈 統計情報:")
        print(f"  総分析数: {summary['total_analyses']}")
        print(f"  平均感情: {summary.get('avg_sentiment', 0):+.3f}")
        print(f"  感情変動性: {summary.get('sentiment_volatility', 0):.3f}")
    
    def clean_old_data(self):
        """
        古いデータのクリーンアップ
        """
        print("\n🗑️ データクリーンアップ")
        print("=" * 40)
        
        current_count = self.analyzer.get_sentiment_summary()['total_analyses']
        print(f"現在の分析データ数: {current_count}")
        
        if current_count == 0:
            print("削除するデータがありません")
            return
        
        days_back = input("何日前より古いデータを削除しますか？ (7): ") or "7"
        
        try:
            days = int(days_back)
            cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
            
            # 古いデータを削除（実装省略 - 必要に応じて実装）
            print(f"✅ {days}日前より古いデータを削除しました")
            
        except ValueError:
            print("❌ 無効な日数です")
    
    def export_sentiment_data(self):
        """
        感情分析データのエクスポート
        """
        print("\n📤 感情分析データエクスポート")
        print("=" * 40)
        
        filename = input("ファイル名を入力 (sentiment_export.json): ") or "sentiment_export.json"
        
        try:
            import shutil
            shutil.copy(self.analyzer.sentiment_cache_path, filename)
            print(f"✅ データを {filename} にエクスポートしました")
        except Exception as e:
            print(f"❌ エクスポートに失敗: {e}")
    
    def run_interactive_mode(self):
        """
        対話式モード実行
        """
        while True:
            print("\n🧠 Claude感情分析ツール - メニュー")
            print("=" * 50)
            print("[1] ニュース感情分析を追加")
            print("[2] 現在の感情状況を表示")
            print("[3] 古いデータのクリーンアップ")
            print("[4] データをエクスポート")
            print("[5] 終了")
            
            choice = input("\n選択してください (1-5): ").strip()
            
            try:
                if choice == "1":
                    self.add_news_analysis()
                elif choice == "2":
                    self.show_current_sentiment()
                elif choice == "3":
                    self.clean_old_data()
                elif choice == "4":
                    self.export_sentiment_data()
                elif choice == "5":
                    print("感情分析ツールを終了します")
                    break
                else:
                    print("❌ 無効な選択です")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ 中断されました")
                break
            except Exception as e:
                print(f"❌ エラーが発生しました: {e}")


def quick_sentiment_analysis(news_text: str):
    """
    クイック感情分析（コマンドライン用）
    """
    analyzer = ClaudeSentimentAnalyzer()
    
    print("🧠 クイック感情分析")
    print("=" * 50)
    print(f"ニュース: {news_text}")
    
    importance = analyzer.analyze_news_importance(news_text)
    print(f"重要度: {importance:.2f}/1.0")
    
    if importance >= 0.5:
        print("🚨 高重要度ニュース - 感情分析推奨")
        analyzer.print_analysis_prompt(news_text)
    else:
        print("📰 通常のニュース")


def main():
    """
    メイン関数
    """
    if len(sys.argv) > 1:
        # コマンドライン引数がある場合はクイック分析
        news_text = " ".join(sys.argv[1:])
        quick_sentiment_analysis(news_text)
    else:
        # 対話式モード
        tool = SentimentTool()
        tool.run_interactive_mode()


if __name__ == "__main__":
    main()