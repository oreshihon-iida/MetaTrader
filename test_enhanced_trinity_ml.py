#!/usr/bin/env python3
"""
Enhanced Trinity ML Strategy Test Script
Claude感情分析統合版Trinity戦略テスト
"""

import pandas as pd
import sys
import os
from datetime import datetime
import time

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.enhanced_trinity_ml_strategy import enhanced_trinity_ml_wrapper
from src.backtest.trade_executor import TradeExecutor

def load_data():
    """データ読み込み"""
    print("データ読み込み中...")
    
    data_files = []
    for year in [2023, 2024]:
        file_path = f'data/processed/15min/{year}/USDJPY_15min_{year}.csv'
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
            data_files.append(df)
            print(f"{year}年データ読み込み完了: {len(df)}行レコード")
    
    if not data_files:
        print("データファイルが見つかりません")
        return None
    
    # 全データを結合
    all_data = pd.concat(data_files)
    print(f"\n全データ: {len(all_data)}行レコード")
    print(f"期間: {all_data.index.min()} - {all_data.index.max()}")
    
    return all_data

def main():
    print("=" * 80)
    print("Enhanced Trinity ML Strategy Test")
    print("Claude感情分析統合版Trinity戦略テスト")
    print("=" * 80)
    
    start_time = datetime.now()
    print(f"開始時刻: {start_time}")
    
    # データ読み込み
    data = load_data()
    if data is None:
        return
    
    print("\nEnhanced Trinity ML戦略実行開始...")
    print("特徴: Trinity ML v3 + Claude感情分析 + Enhanced信頼度計算")
    print("目標: v3成功(93取引, 983,407円)を上回る性能")
    
    # Trade Executor初期化
    executor = TradeExecutor(initial_balance=1000000)
    
    try:
        start_strategy_time = time.time()
        
        # Enhanced Trinity戦略実行
        result = enhanced_trinity_ml_wrapper(data, executor)
        
        end_time = datetime.now()
        strategy_duration = time.time() - start_strategy_time
        
        # 比較基準データ
        trinity_v3_trades = 93
        trinity_v3_profit = 983407
        trinity_v3_winrate = 55.9
        
        # 結果比較
        current_trades = result.get('total_trades', 0)
        current_profit = result.get('total_pnl', 0)
        current_winrate = result.get('win_rate', 0)
        
        improvement_trades = (current_trades / trinity_v3_trades - 1) * 100 if trinity_v3_trades > 0 else 0
        improvement_profit = (current_profit / trinity_v3_profit - 1) * 100 if trinity_v3_profit > 0 else 0
        
        # 最終結果表示
        print("\n" + "=" * 80)
        print("Enhanced Trinity ML Strategy テスト結果")
        print("=" * 80)
        
        print(f"\n[実行時間] {end_time - start_time}")
        print(f"[取引数] {current_trades}")
        print(f"  Trinity v3比較: {improvement_trades:+.1f}% (v3: {trinity_v3_trades}取引)")
        
        print(f"\n[総損益] {current_profit:,.0f}円 ({result.get('total_return', 0):.2f}%)")
        print(f"  Trinity v3比較: {improvement_profit:+.1f}% (v3: {trinity_v3_profit:,}円)")
        
        print(f"[勝率] {current_winrate:.1f}%")
        print(f"  Trinity v3比較: {current_winrate - trinity_v3_winrate:+.1f}% (v3: {trinity_v3_winrate}%)")
        
        print(f"[最大DD] {result.get('max_drawdown', 0):.2f}%")
        print(f"[PF] {result.get('profit_factor', 0):.2f}")
        
        # 月平均利益計算
        months = len(data) / (30 * 24 * 4)  # 15分足換算
        monthly_avg = current_profit / months if months > 0 else 0
        v3_monthly = trinity_v3_profit / months if months > 0 else 0
        
        print(f"\n[収益性評価]")
        print(f"  データ期間: {months:.1f}ヶ月")
        print(f"  月平均利益: {monthly_avg:,.0f}円")
        print(f"  Trinity v3比較: {((monthly_avg / v3_monthly - 1) * 100):+.1f}% (v3: {v3_monthly:,.0f}円)")
        
        # Enhanced Trinity効果分析
        print(f"\n[Enhanced Trinity分析]")
        if current_trades >= trinity_v3_trades and current_profit > trinity_v3_profit:
            print("  評価: ✅ Trinity v3を上回る性能達成！")
        elif current_trades >= trinity_v3_trades * 0.8 and current_profit > trinity_v3_profit * 0.8:
            print("  評価: ⭕ Trinity v3に近い性能（80%以上）")
        elif current_trades >= 50 and current_profit > 500000:
            print("  評価: 🔄 良好だが改善余地あり")
        else:
            print("  評価: ⚠️ 感情分析統合の調整が必要")
        
        # 感情分析統合効果
        print(f"\n[感情分析統合効果]")
        if current_profit > trinity_v3_profit:
            sentiment_boost = current_profit - trinity_v3_profit
            print(f"  感情分析による利益向上: +{sentiment_boost:,.0f}円 ({sentiment_boost/trinity_v3_profit*100:.1f}%)")
        else:
            sentiment_impact = current_profit - trinity_v3_profit
            print(f"  感情分析による影響: {sentiment_impact:,.0f}円 ({sentiment_impact/trinity_v3_profit*100:.1f}%)")
        
        # 目標達成評価
        print(f"\n[目標達成度評価]")
        if monthly_avg >= 200000:
            print("  🎯 月20万円目標: 達成可能性あり！")
        elif monthly_avg >= 150000:
            print("  📈 月15万円レベル: 達成")
        elif monthly_avg >= 100000:
            print("  📊 月10万円レベル: 達成")
        else:
            print("  🔧 さらなる最適化が必要")
        
        # 技術仕様
        print(f"\n[Enhanced Trinity技術仕様]")
        print(f"  ベース戦略: Trinity ML v3 (93取引, 98万円)")
        print(f"  感情分析: Claude Code統合（無料）")
        print(f"  信頼度計算: Enhanced式 (0.3×精度 + 0.3×学習 + 0.15×強度 + 0.25×感情)")
        print(f"  処理速度: {strategy_duration/60:.1f}分 (24コア並列)")
        print(f"  感情重み: 25%")
        print(f"  感情時間範囲: 24時間")
        
        print(f"\n[完了時刻] {end_time}")
        
        # 結果保存
        with open('enhanced_trinity_ml_result.txt', 'w', encoding='utf-8') as f:
            f.write("Enhanced Trinity ML Strategy テスト結果\n")
            f.write("=" * 50 + "\n")
            f.write(f"開始時刻: {start_time}\n")
            f.write(f"完了時刻: {end_time}\n")
            f.write(f"データ期間: {data.index.min()} - {data.index.max()}\n\n")
            
            f.write("戦略概要:\n")
            f.write("- Trinity ML v3をベースとした感情分析統合版\n")
            f.write("- Claude Code感情分析システム（無料）\n")
            f.write("- Enhanced信頼度計算式\n")
            f.write("- 感情重み25%、24時間時間範囲\n\n")
            
            f.write("=== 結果 ===\n")
            f.write(f"取引数: {current_trades}\n")
            f.write(f"Trinity v3比較: {improvement_trades:+.1f}% (v3: {trinity_v3_trades})\n")
            f.write(f"総損益: {current_profit:,.0f}円\n")
            f.write(f"Trinity v3比較: {improvement_profit:+.1f}% (v3: {trinity_v3_profit:,}円)\n")
            f.write(f"勝率: {current_winrate:.1f}%\n")
            f.write(f"PF: {result.get('profit_factor', 0):.2f}\n")
            f.write(f"月平均: {monthly_avg:,.0f}円\n")
            f.write(f"実行時間: {strategy_duration/60:.1f}分\n")
            
            # 感情分析詳細
            f.write(f"\n=== 感情分析統合詳細 ===\n")
            if current_profit > trinity_v3_profit:
                f.write(f"感情分析効果: +{current_profit - trinity_v3_profit:,.0f}円向上\n")
            else:
                f.write(f"感情分析影響: {current_profit - trinity_v3_profit:,.0f}円\n")
            
            f.write(f"Enhanced信頼度式: 0.3×精度 + 0.3×学習 + 0.15×強度 + 0.25×感情\n")
        
        print("\n結果は 'enhanced_trinity_ml_result.txt' に保存されました")
        
        # 感情分析データ状況表示
        print(f"\n[感情分析データ状況]")
        if os.path.exists('sentiment_cache.json'):
            import json
            try:
                with open('sentiment_cache.json', 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                print(f"  保存された感情分析数: {len(sentiment_data)}件")
                if sentiment_data:
                    latest_key = max(sentiment_data.keys(), 
                                   key=lambda k: sentiment_data[k].get('timestamp', ''))
                    latest_analysis = sentiment_data[latest_key]
                    print(f"  最新分析: {latest_analysis.get('sentiment_score', 0):.2f}")
                else:
                    print("  ⚠️ 感情分析データなし - sentiment_tool.pyで分析追加推奨")
            except:
                print("  ⚠️ 感情分析データ読み込みエラー")
        else:
            print("  ⚠️ sentiment_cache.jsonなし - 初回実行または未分析")
            print("  💡 sentiment_tool.pyを実行してニュース感情分析を追加してください")
        
    except KeyboardInterrupt:
        print("\nテストが中断されました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def quick_test():
    """
    クイックテスト（デバッグ用）
    """
    print("Enhanced Trinity ML - クイックテスト")
    print("=" * 50)
    
    # 感情分析システムの動作確認
    from src.sentiment.claude_sentiment_analyzer import ClaudeSentimentAnalyzer
    
    analyzer = ClaudeSentimentAnalyzer()
    features = analyzer.get_recent_sentiment_features()
    
    print("感情分析特徴量:")
    for key, value in features.items():
        print(f"  {key}: {value:.3f}")
    
    print(f"\n感情分析データ数: {features['sentiment_count']}")
    
    if features['sentiment_count'] == 0:
        print("\n⚠️ 感情分析データがありません")
        print("sentiment_tool.pyを実行してニュース分析を追加してください")
        
        # サンプルプロンプト表示
        sample_news = "FRBが0.5%の利上げを決定、市場は円安ドル高を予想"
        analyzer.print_analysis_prompt(sample_news)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test()
    else:
        main()