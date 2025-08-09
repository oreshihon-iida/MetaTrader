#!/usr/bin/env python3
"""
自動テスト実行システム
最新データの収集→テスト実行→結果保存を自動化
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.auto_data_collector import AutoDataCollector
from src.data.enhanced_data_manager import EnhancedDataManager
from quick_test_helper import QuickTestHelper
from src.backtest.trade_executor import TradeExecutor
from src.utils.logger import Logger

class AutoTestRunner:
    """
    自動テスト実行システム
    
    機能:
    1. 最新データの自動収集・更新
    2. 戦略テストの自動実行
    3. 結果の自動保存・比較
    4. テスト履歴の管理
    """
    
    def __init__(self, base_dir: str = None):
        """初期化"""
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.base_dir = base_dir
            
        self.data_collector = AutoDataCollector(base_dir)
        self.data_manager = EnhancedDataManager(base_dir)
        self.test_helper = QuickTestHelper()
        
        # ログ設定
        log_dir = os.path.join(self.base_dir, 'logs', 'auto_test')
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        
    def ensure_latest_data(self, 
                          required_timeframes: List[str] = None,
                          years: List[int] = None) -> Dict[str, Dict[int, str]]:
        """
        最新データを確保（不足分は自動収集）
        
        Parameters
        ----------
        required_timeframes : List[str], optional
            必要な時間足（デフォルト: ['15min', '1H', '4H']）
        years : List[int], optional
            必要な年（デフォルト: 利用可能な全年）
            
        Returns
        -------
        Dict[str, Dict[int, str]]
            確保されたデータファイルパス
        """
        if required_timeframes is None:
            required_timeframes = ['15min', '1H', '4H']
            
        if years is None:
            years = self.data_collector.get_available_years()
            
        self.logger.log_info("=" * 60)
        self.logger.log_info("最新データ収集開始")
        self.logger.log_info(f"必要時間足: {required_timeframes}")
        self.logger.log_info(f"対象年: {years}")
        self.logger.log_info("=" * 60)
        
        print("最新データ収集中...")
        print(f"   必要時間足: {required_timeframes}")
        print(f"   対象年: {years}")
        
        # データ収集実行
        data_files = self.data_collector.prepare_strategy_data(required_timeframes, years)
        
        # 結果サマリー
        total_files = sum(len(year_files) for year_files in data_files.values())
        self.logger.log_info(f"データ収集完了: {total_files} ファイル準備")
        
        print("[OK] 最新データ収集完了")
        for timeframe, year_files in data_files.items():
            print(f"   {timeframe}: {len(year_files)} 年分")
            
        return data_files
    
    def run_strategy_test(self,
                         strategy_func: Callable,
                         test_name: str,
                         strategy_config: Dict = None,
                         timeframe: str = '15min',
                         additional_timeframes: List[str] = None,
                         years: List[int] = None,
                         auto_save: bool = True) -> Tuple[TradeExecutor, Dict]:
        """
        戦略テストを自動実行
        
        Parameters
        ----------
        strategy_func : Callable
            戦略実行関数（引数: data, executor, metadata）
        test_name : str
            テスト名
        strategy_config : Dict, optional
            戦略設定
        timeframe : str, default '15min'
            メイン時間足
        additional_timeframes : List[str], optional
            追加時間足
        years : List[int], optional
            テスト年
        auto_save : bool, default True
            結果を自動保存するか
            
        Returns
        -------
        Tuple[TradeExecutor, Dict]
            (エグゼキューター, 統計情報) のタプル
        """
        self.logger.log_info("=" * 60)
        self.logger.log_info(f"戦略テスト開始: {test_name}")
        self.logger.log_info(f"実行時刻: {datetime.now().isoformat()}")
        
        # STEP 1: 最新データ収集
        required_timeframes = [timeframe]
        if additional_timeframes:
            required_timeframes.extend(additional_timeframes)
            
        self.ensure_latest_data(required_timeframes, years)
        
        # STEP 2: テスト環境セットアップ
        print(f"\n[TEST] 戦略テスト実行: {test_name}")
        
        if additional_timeframes:
            data, executor, metadata = self.test_helper.setup_enhanced_backtest(
                timeframe=timeframe,
                additional_timeframes=additional_timeframes
            )
        else:
            data, executor, metadata = self.test_helper.setup_basic_backtest()
            
        # STEP 3: 戦略実行
        self.logger.log_info("戦略実行開始")
        print("   戦略実行中...")
        
        try:
            strategy_func(data, executor, metadata)
            self.logger.log_info("戦略実行完了")
        except Exception as e:
            self.logger.log_error(f"戦略実行エラー: {str(e)}")
            print(f"[ERROR] 戦略実行エラー: {str(e)}")
            raise
        
        # STEP 4: 結果取得
        stats = executor.get_statistics()
        self.logger.log_info(f"テスト完了 - 総損益: {stats['total_pnl']:,.0f}円")
        
        # STEP 5: 結果表示
        print("[RESULTS] テスト結果:")
        self.test_helper.quick_performance_summary(executor)
        
        # STEP 6: 自動保存
        if auto_save:
            save_path = self.test_helper.save_quick_results(
                executor, test_name, strategy_config
            )
            self.logger.log_info(f"結果保存完了: {save_path}")
        
        self.logger.log_info("=" * 60)
        
        return executor, stats
    
    def compare_strategy_results(self, test_names: List[str]) -> pd.DataFrame:
        """
        複数戦略の結果を比較
        
        Parameters
        ----------
        test_names : List[str]
            比較するテスト名リスト
            
        Returns
        -------
        pd.DataFrame
            比較結果テーブル
        """
        comparison_data = []
        
        for test_name in test_names:
            result_file = f"results/{test_name}/statistics.json"
            
            if os.path.exists(result_file):
                import json
                with open(result_file, 'r') as f:
                    stats = json.load(f)
                
                comparison_data.append({
                    'Test Name': test_name,
                    'Total PnL (JPY)': stats.get('total_pnl', 0),
                    'Return (%)': stats.get('total_return', 0),
                    'Win Rate (%)': stats.get('win_rate', 0),
                    'Max DD (%)': stats.get('max_drawdown', 0),
                    'Profit Factor': stats.get('profit_factor', 0),
                    'Total Trades': stats.get('total_trades', 0)
                })
        
        if comparison_data:
            df = pd.DataFrame(comparison_data)
            df = df.sort_values('Total PnL (JPY)', ascending=False)
            
            print("\n[COMPARE] 戦略比較結果:")
            print(df.to_string(index=False))
            
            return df
        else:
            print("[WARNING] 比較対象のテスト結果が見つかりません")
            return pd.DataFrame()
    
    def run_test_series(self, 
                       test_series: List[Dict],
                       series_name: str = "test_series") -> Dict[str, Dict]:
        """
        一連のテストを自動実行
        
        Parameters
        ----------
        test_series : List[Dict]
            テスト設定リスト
        series_name : str, default "test_series"
            シリーズ名
            
        Returns
        -------
        Dict[str, Dict]
            {テスト名: 統計情報} の辞書
        """
        self.logger.log_info("=" * 80)
        self.logger.log_info(f"テストシリーズ開始: {series_name}")
        self.logger.log_info(f"テスト数: {len(test_series)}")
        
        print(f"\n[SERIES] テストシリーズ実行: {series_name}")
        print(f"   テスト数: {len(test_series)}")
        
        results = {}
        
        for i, test_config in enumerate(test_series, 1):
            print(f"\n--- テスト {i}/{len(test_series)} ---")
            
            executor, stats = self.run_strategy_test(**test_config)
            results[test_config['test_name']] = stats
        
        # シリーズ結果比較
        print(f"\n{'='*50}")
        print(f"{series_name} 完了")
        print(f"{'='*50}")
        
        self.compare_strategy_results(list(results.keys()))
        
        self.logger.log_info(f"テストシリーズ完了: {series_name}")
        
        return results

# 便利関数
def auto_test(strategy_func: Callable,
              test_name: str,
              strategy_config: Dict = None,
              timeframe: str = '15min',
              additional_timeframes: List[str] = None) -> Tuple[TradeExecutor, Dict]:
    """
    最も簡単な自動テスト実行
    
    Parameters
    ----------
    strategy_func : Callable
        戦略実行関数
    test_name : str
        テスト名
    strategy_config : Dict, optional
        戦略設定
    timeframe : str, default '15min'
        メイン時間足
    additional_timeframes : List[str], optional
        追加時間足
        
    Returns
    -------
    Tuple[TradeExecutor, Dict]
        (エグゼキューター, 統計情報)
    """
    runner = AutoTestRunner()
    return runner.run_strategy_test(
        strategy_func=strategy_func,
        test_name=test_name,
        strategy_config=strategy_config,
        timeframe=timeframe,
        additional_timeframes=additional_timeframes
    )

def compare_tests(test_names: List[str]) -> pd.DataFrame:
    """
    テスト結果を簡単比較
    
    Parameters
    ----------
    test_names : List[str]
        比較するテスト名
        
    Returns
    -------
    pd.DataFrame
        比較結果
    """
    runner = AutoTestRunner()
    return runner.compare_strategy_results(test_names)

if __name__ == "__main__":
    # デモ実行
    print("Auto Test Runner デモ")
    
    runner = AutoTestRunner()
    
    # 最新データ収集テスト
    print("\n最新データ収集テスト:")
    data_files = runner.ensure_latest_data(['15min', '1H'], [2024, 2025])
    
    print("\nテスト準備完了")
    print("今後のテスト実行では、この仕組みで常に最新データが使用されます")