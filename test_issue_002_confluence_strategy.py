"""
Issue #002: Multi-Timeframe Confluence Strategy バックテストシステム
100回煮詰め完了版の包括的検証

Issue #001教訓統合:
1. 現実的な評価基準設定
2. 詳細な取引分析機能
3. CSV出力による検証可能性
4. 月別・年別パフォーマンス分析
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import json
import logging

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.strategies.multi_timeframe_confluence_strategy import MultiTimeframeConfluenceStrategy
from src.data.data_loader import DataLoader
from src.backtest.enhanced_trade_executor import EnhancedTradeExecutor

class Issue002ConfluenceBacktester:
    def __init__(self):
        self.strategy = MultiTimeframeConfluenceStrategy()
        self.data_loader = DataLoader("data/raw")
        self.trade_executor = EnhancedTradeExecutor()
        
        # Issue #001教訓: 現実的評価基準
        self.evaluation_criteria = {
            "min_trades": 20,  # V11.3月2.6回 × 12ヶ月 = 年31回を参考
            "target_win_rate": 0.45,  # V10.2実績37.5%を保守的向上
            "target_profit_factor": 1.2,  # V10.2実績1.23を維持
            "max_drawdown": 0.15,  # 15%上限
            "min_monthly_profit": 10000,  # 月1万円最低ライン
            "target_monthly_profit": 50000  # 月5万円目標
        }
        
        self.results = {
            "trades": [],
            "monthly_stats": {},
            "yearly_stats": {},
            "confluence_analysis": {},
            "timeframe_contribution": {}
        }
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("Issue002_Backtester")
        
    def load_multi_timeframe_data(self, start_date: str, end_date: str) -> dict:
        """
        マルチタイムフレームデータの同期読み込み
        Issue #001教訓: データ整合性重視
        """
        self.logger.info(f"Loading multi-timeframe data: {start_date} to {end_date}")
        
        try:
            # 各時間軸データ読み込み
            d1_data = self.data_loader.load_historical_data("USDJPY", "1D", start_date, end_date)
            h4_data = self.data_loader.load_historical_data("USDJPY", "4H", start_date, end_date)
            h1_data = self.data_loader.load_historical_data("USDJPY", "1H", start_date, end_date)
            
            self.logger.info(f"Data loaded - D1: {len(d1_data)}, 4H: {len(h4_data)}, 1H: {len(h1_data)}")
            
            return {
                "D1": d1_data,
                "4H": h4_data,
                "1H": h1_data
            }
            
        except Exception as e:
            self.logger.error(f"Data loading error: {e}")
            return None
    
    def synchronize_timeframes(self, data_dict: dict, reference_timeframe: str = "4H") -> list:
        """
        時間軸データの同期処理
        基準時間軸に合わせて他の時間軸データを同期
        """
        reference_data = data_dict[reference_timeframe].copy()
        reference_data.reset_index(inplace=True)
        
        synchronized_bars = []
        
        for i, row in reference_data.iterrows():
            current_time = row['Date'] if 'Date' in row else row.name
            
            try:
                # 各時間軸の対応するデータを取得
                sync_data = {}
                
                for tf, data in data_dict.items():
                    if tf == reference_timeframe:
                        # 十分な履歴データがあるかチェック
                        if i >= 250:  # 200SMA計算に必要
                            sync_data[tf] = data.iloc[max(0, i-250):i+1].copy()
                        else:
                            sync_data[tf] = None
                    else:
                        # 他の時間軸データの対応する時刻を見つける
                        tf_data = self.find_corresponding_data(data, current_time, tf)
                        sync_data[tf] = tf_data
                
                # 全時間軸のデータが揃っている場合のみ追加
                if all(d is not None and len(d) >= 200 for d in sync_data.values()):
                    synchronized_bars.append({
                        "timestamp": current_time,
                        "data": sync_data,
                        "reference_bar": row
                    })
                    
            except Exception as e:
                self.logger.warning(f"Synchronization error at {current_time}: {e}")
                continue
        
        self.logger.info(f"Synchronized {len(synchronized_bars)} bars for analysis")
        return synchronized_bars
    
    def find_corresponding_data(self, data: pd.DataFrame, target_time, timeframe: str) -> pd.DataFrame:
        """指定時刻に対応する時間軸データを取得"""
        try:
            # タイムスタンプでソート
            data_sorted = data.sort_index()
            
            # 指定時刻以前の最新データを取得
            mask = data_sorted.index <= target_time
            corresponding_data = data_sorted[mask]
            
            if len(corresponding_data) >= 200:  # 最低限の履歴確保
                return corresponding_data.iloc[-250:].copy()  # 250本分取得
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Error finding corresponding data for {timeframe}: {e}")
            return None
    
    def analyze_confluence_distribution(self, signals: list):
        """コンフルエンススコア分布の分析"""
        scores = [s["confluence_score"] for s in signals if s["action"] != "NO_TRADE"]
        
        if not scores:
            return {}
        
        return {
            "total_signals": len(scores),
            "mean_score": np.mean(scores),
            "std_score": np.std(scores),
            "score_ranges": {
                "strong_70+": len([s for s in scores if abs(s) >= 70]),
                "medium_50-69": len([s for s in scores if 50 <= abs(s) < 70]),
                "weak_30-49": len([s for s in scores if 30 <= abs(s) < 50])
            }
        }
    
    def run_comprehensive_backtest(self, start_date: str = "2022-01-01", end_date: str = "2024-12-31"):
        """
        包括的バックテスト実行
        Issue #001教訓: 詳細分析重視
        """
        self.logger.info("=" * 60)
        self.logger.info("🚀 Issue #002 Multi-Timeframe Confluence Strategy Backtest")
        self.logger.info("=" * 60)
        
        # データ読み込み
        data_dict = self.load_multi_timeframe_data(start_date, end_date)
        if not data_dict:
            self.logger.error("Failed to load data")
            return None
        
        # データ同期
        synchronized_bars = self.synchronize_timeframes(data_dict)
        if len(synchronized_bars) < 100:
            self.logger.error("Insufficient synchronized data")
            return None
        
        self.logger.info(f"Starting backtest with {len(synchronized_bars)} synchronized bars")
        
        # バックテスト実行
        signals = []
        trades = []
        account_balance = 3000000  # 300万円
        
        for i, bar_data in enumerate(synchronized_bars):
            try:
                # シグナル生成
                signal = self.strategy.generate_signal(
                    bar_data["data"]["D1"],
                    bar_data["data"]["4H"], 
                    bar_data["data"]["1H"]
                )
                
                signal["timestamp"] = bar_data["timestamp"]
                signal["bar_index"] = i
                signals.append(signal)
                
                # 取引実行
                if signal["action"] in ["BUY", "SELL"]:
                    trade_result = self.trade_executor.execute_trade(
                        signal, bar_data["reference_bar"], account_balance
                    )
                    
                    if trade_result:
                        trades.append(trade_result)
                        account_balance = trade_result.get("new_balance", account_balance)
                        
                        self.logger.info(
                            f"Trade {len(trades)}: {signal['action']} at {bar_data['timestamp']} "
                            f"(Confluence: {signal['confluence_score']:.1f}, "
                            f"Confidence: {signal['confidence']:.2f})"
                        )
                
                # 進捗表示
                if (i + 1) % 100 == 0:
                    self.logger.info(f"Processed {i+1}/{len(synchronized_bars)} bars")
                    
            except Exception as e:
                self.logger.error(f"Error processing bar {i}: {e}")
                continue
        
        # 結果分析
        self.results["trades"] = trades
        self.results["signals"] = signals
        self.results["total_signals"] = len([s for s in signals if s["action"] != "NO_TRADE"])
        self.results["confluence_analysis"] = self.analyze_confluence_distribution(signals)
        
        # 統計計算
        if trades:
            self.calculate_performance_stats(trades, account_balance)
            self.analyze_monthly_performance(trades)
            self.analyze_timeframe_contribution(signals)
        
        # 結果出力
        self.save_detailed_results()
        self.print_summary_report()
        
        return self.results
    
    def calculate_performance_stats(self, trades: list, final_balance: float):
        """Issue #001教訓を基にした詳細パフォーマンス統計"""
        if not trades:
            return
        
        profits = [t.get("profit", 0) for t in trades]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        total_profit = sum(profits)
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # プロフィットファクター計算
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # シャープレシオ計算
        monthly_returns = self.calculate_monthly_returns(trades)
        sharpe_ratio = (np.mean(monthly_returns) / np.std(monthly_returns)) if len(monthly_returns) > 1 and np.std(monthly_returns) > 0 else 0
        
        self.results["performance"] = {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_profit": total_profit,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "average_win": np.mean(winning_trades) if winning_trades else 0,
            "average_loss": np.mean(losing_trades) if losing_trades else 0,
            "largest_win": max(winning_trades) if winning_trades else 0,
            "largest_loss": min(losing_trades) if losing_trades else 0,
            "sharpe_ratio": sharpe_ratio,
            "final_balance": final_balance,
            "roi": ((final_balance - 3000000) / 3000000) * 100
        }
    
    def calculate_monthly_returns(self, trades: list) -> list:
        """月別リターン計算"""
        monthly_profits = {}
        
        for trade in trades:
            try:
                trade_date = pd.to_datetime(trade.get("exit_time", trade.get("timestamp")))
                month_key = trade_date.strftime("%Y-%m")
                
                if month_key not in monthly_profits:
                    monthly_profits[month_key] = 0
                monthly_profits[month_key] += trade.get("profit", 0)
                
            except Exception:
                continue
        
        return list(monthly_profits.values())
    
    def analyze_monthly_performance(self, trades: list):
        """月別パフォーマンス分析"""
        monthly_stats = {}
        
        for trade in trades:
            try:
                trade_date = pd.to_datetime(trade.get("exit_time", trade.get("timestamp")))
                month_key = trade_date.strftime("%Y-%m")
                
                if month_key not in monthly_stats:
                    monthly_stats[month_key] = {
                        "trades": 0,
                        "profit": 0,
                        "wins": 0,
                        "losses": 0
                    }
                
                monthly_stats[month_key]["trades"] += 1
                monthly_stats[month_key]["profit"] += trade.get("profit", 0)
                
                if trade.get("profit", 0) > 0:
                    monthly_stats[month_key]["wins"] += 1
                else:
                    monthly_stats[month_key]["losses"] += 1
                    
            except Exception:
                continue
        
        # 月別統計計算
        for month, stats in monthly_stats.items():
            if stats["trades"] > 0:
                stats["win_rate"] = stats["wins"] / stats["trades"]
                stats["avg_profit_per_trade"] = stats["profit"] / stats["trades"]
        
        self.results["monthly_stats"] = monthly_stats
    
    def analyze_timeframe_contribution(self, signals: list):
        """時間軸寄与度分析"""
        timeframe_stats = {
            "D1": {"positive": 0, "negative": 0, "total": 0},
            "4H": {"positive": 0, "negative": 0, "total": 0},
            "1H": {"positive": 0, "negative": 0, "total": 0}
        }
        
        for signal in signals:
            if signal["action"] != "NO_TRADE" and "timeframe_scores" in signal:
                tf_scores = signal["timeframe_scores"]
                
                for tf, score in tf_scores.items():
                    if tf in timeframe_stats:
                        timeframe_stats[tf]["total"] += 1
                        if score > 0:
                            timeframe_stats[tf]["positive"] += 1
                        else:
                            timeframe_stats[tf]["negative"] += 1
        
        self.results["timeframe_contribution"] = timeframe_stats
    
    def evaluate_against_criteria(self) -> dict:
        """Issue #001教訓: 現実的基準による評価"""
        performance = self.results.get("performance", {})
        
        evaluation = {
            "total_score": 0,
            "max_score": 6,
            "details": {}
        }
        
        # 取引数評価
        total_trades = performance.get("total_trades", 0)
        if total_trades >= self.evaluation_criteria["min_trades"]:
            evaluation["details"]["trades_sufficient"] = True
            evaluation["total_score"] += 1
        else:
            evaluation["details"]["trades_sufficient"] = False
        
        # 勝率評価
        win_rate = performance.get("win_rate", 0)
        if win_rate >= self.evaluation_criteria["target_win_rate"]:
            evaluation["details"]["win_rate_achieved"] = True
            evaluation["total_score"] += 1
        else:
            evaluation["details"]["win_rate_achieved"] = False
        
        # プロフィットファクター評価
        pf = performance.get("profit_factor", 0)
        if pf >= self.evaluation_criteria["target_profit_factor"]:
            evaluation["details"]["profit_factor_achieved"] = True
            evaluation["total_score"] += 1
        else:
            evaluation["details"]["profit_factor_achieved"] = False
        
        # 月平均利益評価
        monthly_stats = self.results.get("monthly_stats", {})
        if monthly_stats:
            avg_monthly_profit = np.mean([stats["profit"] for stats in monthly_stats.values()])
            if avg_monthly_profit >= self.evaluation_criteria["min_monthly_profit"]:
                evaluation["details"]["monthly_profit_min"] = True
                evaluation["total_score"] += 1
            else:
                evaluation["details"]["monthly_profit_min"] = False
            
            if avg_monthly_profit >= self.evaluation_criteria["target_monthly_profit"]:
                evaluation["details"]["monthly_profit_target"] = True
                evaluation["total_score"] += 1
            else:
                evaluation["details"]["monthly_profit_target"] = False
        
        # 総合評価
        score_ratio = evaluation["total_score"] / evaluation["max_score"]
        if score_ratio >= 0.8:
            evaluation["overall_rating"] = "EXCELLENT"
        elif score_ratio >= 0.6:
            evaluation["overall_rating"] = "GOOD"
        elif score_ratio >= 0.4:
            evaluation["overall_rating"] = "ACCEPTABLE"
        else:
            evaluation["overall_rating"] = "NEEDS_IMPROVEMENT"
        
        return evaluation
    
    def save_detailed_results(self):
        """詳細結果の保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON結果保存
        results_file = f"issue_002_confluence_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str, ensure_ascii=False)
        
        # CSV取引ログ保存
        if self.results.get("trades"):
            trades_df = pd.DataFrame(self.results["trades"])
            trades_csv = f"issue_002_trades_{timestamp}.csv"
            trades_df.to_csv(trades_csv, index=False, encoding='utf-8-sig')
        
        self.logger.info(f"Results saved: {results_file}")
    
    def print_summary_report(self):
        """要約レポート出力"""
        print("\n" + "=" * 80)
        print("🎯 Issue #002: Multi-Timeframe Confluence Strategy - 結果レポート")
        print("=" * 80)
        
        performance = self.results.get("performance", {})
        
        print(f"📊 基本統計:")
        print(f"   総取引数: {performance.get('total_trades', 0)}")
        print(f"   勝率: {performance.get('win_rate', 0)*100:.1f}%")
        print(f"   プロフィットファクター: {performance.get('profit_factor', 0):.2f}")
        print(f"   総利益: {performance.get('total_profit', 0):,.0f}円")
        print(f"   ROI: {performance.get('roi', 0):.1f}%")
        
        print(f"\n📈 月間パフォーマンス:")
        monthly_stats = self.results.get("monthly_stats", {})
        if monthly_stats:
            avg_monthly_profit = np.mean([stats["profit"] for stats in monthly_stats.values()])
            avg_monthly_trades = np.mean([stats["trades"] for stats in monthly_stats.values()])
            print(f"   月平均利益: {avg_monthly_profit:,.0f}円")
            print(f"   月平均取引数: {avg_monthly_trades:.1f}回")
        
        print(f"\n🎯 コンフルエンス分析:")
        confluence = self.results.get("confluence_analysis", {})
        if confluence:
            print(f"   総シグナル数: {confluence.get('total_signals', 0)}")
            print(f"   平均スコア: {confluence.get('mean_score', 0):.1f}")
            score_ranges = confluence.get('score_ranges', {})
            print(f"   強シグナル(70+): {score_ranges.get('strong_70+', 0)}")
            print(f"   中シグナル(50-69): {score_ranges.get('medium_50-69', 0)}")
        
        # 評価結果
        evaluation = self.evaluate_against_criteria()
        print(f"\n⭐ 総合評価: {evaluation['overall_rating']}")
        print(f"   スコア: {evaluation['total_score']}/{evaluation['max_score']}")
        
        print("=" * 80)


if __name__ == "__main__":
    # バックテスト実行
    backtester = Issue002ConfluenceBacktester()
    results = backtester.run_comprehensive_backtest()
    
    if results:
        print("\n🎉 Issue #002バックテスト完了 - 100回煮詰め戦略の検証完了")
    else:
        print("\n❌ バックテスト失敗 - データまたは設定を確認してください")