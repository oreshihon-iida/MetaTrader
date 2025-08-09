#!/usr/bin/env python3
"""
クイックテスト用ヘルパー
戦略テストを簡単に実行するための便利関数
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.enhanced_data_manager import EnhancedDataManager, get_backtest_data
from src.backtest.trade_executor import TradeExecutor
from src.utils.logger import Logger

class QuickTestHelper:
    """
    戦略テストを簡単に実行するためのヘルパークラス
    """
    
    def __init__(self):
        """初期化"""
        self.data_manager = EnhancedDataManager()
        
        # デフォルト設定
        self.default_config = {
            'initial_balance': 3000000,
            'timeframe': '15min',
            'years': [2022, 2023, 2024, 2025],
            'start_date': '2022-08-09',
            'end_date': '2025-08-09',
            'spread_pips': 0.2,
            'commission_per_lot': 0,
            'max_positions': 10
        }
    
    def get_test_data(self, 
                     timeframe: str = '15min',
                     years: List[int] = None,
                     additional_timeframes: List[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        テスト用データを簡単取得
        
        Parameters
        ----------
        timeframe : str, default '15min'
            メイン時間足
        years : List[int], optional
            テスト年（デフォルトは2022-2025）
        additional_timeframes : List[str], optional
            追加時間足
            
        Returns
        -------
        Tuple[pd.DataFrame, Dict]
            (データ, メタデータ) のタプル
        """
        if years is None:
            years = self.default_config['years']
        
        return get_backtest_data(timeframe, years, additional_timeframes)
    
    def setup_basic_backtest(self, 
                            initial_balance: float = 3000000,
                            max_positions: int = 10) -> Tuple[pd.DataFrame, TradeExecutor, Dict]:
        """
        基本的なバックテスト環境をセットアップ
        
        Parameters
        ----------
        initial_balance : float, default 3000000
            初期資金
        max_positions : int, default 10
            最大ポジション数
            
        Returns
        -------
        Tuple[pd.DataFrame, TradeExecutor, Dict]
            (データ, エグゼキューター, メタデータ) のタプル
        """
        # データ取得
        data, metadata = self.get_test_data()
        
        # 期間フィルタリング
        start_date = pd.Timestamp(self.default_config['start_date'])
        end_date = pd.Timestamp(self.default_config['end_date'])
        filtered_data = data[start_date:end_date]
        
        # エグゼキューター初期化
        executor = TradeExecutor(
            initial_balance=initial_balance,
            spread_pips=self.default_config['spread_pips'],
            commission_per_lot=self.default_config['commission_per_lot'],
            max_positions=max_positions
        )
        
        print(f"バックテスト環境セットアップ完了:")
        print(f"  データ期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        print(f"  データサイズ: {len(filtered_data)} レコード")
        print(f"  初期資金: {initial_balance:,.0f}円")
        print(f"  最大ポジション: {max_positions}")
        
        return filtered_data, executor, metadata
    
    def setup_enhanced_backtest(self,
                               timeframe: str = '15min',
                               additional_timeframes: List[str] = None,
                               initial_balance: float = 3000000,
                               max_positions: int = 12) -> Tuple[pd.DataFrame, TradeExecutor, Dict]:
        """
        拡張バックテスト環境をセットアップ（複数時間足対応）
        
        Parameters
        ----------
        timeframe : str, default '15min'
            メイン時間足
        additional_timeframes : List[str], optional
            追加時間足（例: ['1H', '4H']）
        initial_balance : float, default 3000000
            初期資金
        max_positions : int, default 12
            最大ポジション数
            
        Returns
        -------
        Tuple[pd.DataFrame, TradeExecutor, Dict]
            (データ, エグゼキューター, メタデータ) のタプル
        """
        # データ取得
        data, metadata = self.get_test_data(timeframe, None, additional_timeframes)
        
        # 期間フィルタリング
        start_date = pd.Timestamp(self.default_config['start_date'])
        end_date = pd.Timestamp(self.default_config['end_date'])
        filtered_data = data[start_date:end_date]
        
        # エグゼキューター初期化
        executor = TradeExecutor(
            initial_balance=initial_balance,
            spread_pips=self.default_config['spread_pips'],
            commission_per_lot=self.default_config['commission_per_lot'],
            max_positions=max_positions
        )
        
        print(f"拡張バックテスト環境セットアップ完了:")
        print(f"  メイン時間足: {timeframe}")
        if additional_timeframes:
            print(f"  追加時間足: {additional_timeframes}")
        print(f"  データ期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        print(f"  データサイズ: {len(filtered_data)} レコード")
        print(f"  カラム数: {len(filtered_data.columns)} (指標含む)")
        print(f"  初期資金: {initial_balance:,.0f}円")
        
        return filtered_data, executor, metadata
    
    def quick_performance_summary(self, executor: TradeExecutor) -> Dict:
        """
        クイックパフォーマンスサマリー表示
        
        Parameters
        ----------
        executor : TradeExecutor
            実行済みのトレードエグゼキューター
            
        Returns
        -------
        Dict
            パフォーマンス統計
        """
        stats = executor.get_statistics()
        
        print(f"\n" + "=" * 40)
        print("クイック結果サマリー")
        print("=" * 40)
        
        print(f"総損益: {stats['total_pnl']:,.0f}円 ({stats['total_return']:+.2f}%)")
        print(f"最大ドローダウン: {stats['max_drawdown']:.2f}%")
        print(f"取引数: {stats['total_trades']} (勝率: {stats['win_rate']:.1f}%)")
        print(f"プロフィットファクター: {stats['profit_factor']:.2f}")
        
        # 月別パフォーマンス
        monthly_perf = executor.get_monthly_performance()
        if not monthly_perf.empty:
            avg_monthly = monthly_perf['profit'].mean()
            target_months = len(monthly_perf[monthly_perf['profit'] >= 200000])
            print(f"月平均損益: {avg_monthly:,.0f}円")
            print(f"月20万円達成: {target_months}/{len(monthly_perf)}月")
        
        print("=" * 40)
        
        return stats
    
    def create_output_dirs(self, test_name: str) -> Dict[str, str]:
        """
        テスト結果出力用ディレクトリ作成
        
        Parameters
        ----------
        test_name : str
            テスト名
            
        Returns
        -------
        Dict[str, str]
            出力ディレクトリパス辞書
        """
        base_output = f"results/{test_name}"
        dirs = {
            'base': base_output,
            'logs': f"{base_output}/logs",
            'charts': f"{base_output}/charts"
        }
        
        for dir_path in dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        return dirs
    
    def save_quick_results(self, 
                          executor: TradeExecutor,
                          test_name: str,
                          strategy_config: Dict = None) -> str:
        """
        テスト結果を素早く保存
        
        Parameters
        ----------
        executor : TradeExecutor
            実行済みのトレードエグゼキューター
        test_name : str
            テスト名
        strategy_config : Dict, optional
            戦略設定情報
            
        Returns
        -------
        str
            保存先ディレクトリパス
        """
        # 出力ディレクトリ作成
        dirs = self.create_output_dirs(test_name)
        
        # 統計保存
        stats = executor.get_statistics()
        
        # 基本情報追加
        stats['test_name'] = test_name
        stats['test_date'] = datetime.now().isoformat()
        if strategy_config:
            stats['strategy_config'] = strategy_config
        
        # JSON保存
        import json
        with open(f"{dirs['base']}/statistics.json", 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        # 取引履歴CSV保存
        if executor.trade_history:
            trade_df = pd.DataFrame(executor.trade_history)
            trade_df.to_csv(f"{dirs['base']}/trade_history.csv", index=False)
        
        print(f"結果保存完了: {dirs['base']}")
        return dirs['base']

# 便利関数群
def quick_test_setup() -> Tuple[pd.DataFrame, TradeExecutor, Dict]:
    """
    最も簡単なテストセットアップ
    
    Returns
    -------
    Tuple[pd.DataFrame, TradeExecutor, Dict]
        (データ, エグゼキューター, メタデータ)
    """
    helper = QuickTestHelper()
    return helper.setup_basic_backtest()

def enhanced_test_setup(additional_timeframes: List[str] = None) -> Tuple[pd.DataFrame, TradeExecutor, Dict]:
    """
    複数時間足対応テストセットアップ
    
    Parameters
    ----------
    additional_timeframes : List[str], optional
        追加時間足（例: ['1H', '4H']）
    
    Returns
    -------
    Tuple[pd.DataFrame, TradeExecutor, Dict]
        (データ, エグゼキューター, メタデータ)
    """
    helper = QuickTestHelper()
    return helper.setup_enhanced_backtest(additional_timeframes=additional_timeframes)

def show_results(executor: TradeExecutor):
    """
    結果を素早く表示
    
    Parameters
    ----------
    executor : TradeExecutor
        実行済みのトレードエグゼキューター
    """
    helper = QuickTestHelper()
    helper.quick_performance_summary(executor)

def save_test_results(executor: TradeExecutor, test_name: str, config: Dict = None) -> str:
    """
    テスト結果を保存
    
    Parameters
    ----------
    executor : TradeExecutor
        実行済みのトレードエグゼキューター
    test_name : str
        テスト名
    config : Dict, optional
        設定情報
        
    Returns
    -------
    str
        保存先パス
    """
    helper = QuickTestHelper()
    return helper.save_quick_results(executor, test_name, config)

if __name__ == "__main__":
    # テスト実行例
    print("Quick Test Helper デモ")
    
    # 基本セットアップ
    data, executor, metadata = quick_test_setup()
    
    print(f"\nデータサンプル:")
    print(data[['Close', 'rsi', 'bb_upper', 'bb_lower']].head(3))
    
    # 拡張セットアップテスト
    print(f"\n" + "-" * 50)
    print("拡張セットアップテスト")
    
    enhanced_data, enhanced_executor, enhanced_metadata = enhanced_test_setup(['1H', '4H'])
    
    print(f"\n拡張データサンプル:")
    available_cols = [col for col in ['Close', 'rsi', '1H_Close', '4H_Close'] if col in enhanced_data.columns]
    print(enhanced_data[available_cols].head(3))