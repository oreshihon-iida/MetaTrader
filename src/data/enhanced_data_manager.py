#!/usr/bin/env python3
"""
強化データマネージャー
戦略テスト用の統合データ管理システム
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging
from .auto_data_collector import AutoDataCollector, ensure_required_data
from .data_processor_enhanced import DataProcessor

class EnhancedDataManager:
    """
    戦略テスト用の統合データ管理システム
    
    機能:
    1. 複数時間足データの自動収集・管理
    2. 戦略テスト用データセットの準備
    3. テクニカル指標の自動追加
    4. データ品質チェック
    """
    
    def __init__(self, base_dir: str = None):
        """
        初期化
        
        Parameters
        ----------
        base_dir : str, optional
            プロジェクトのベースディレクトリパス
        """
        if base_dir is None:
            # 現在のファイルから3階層上がプロジェクトルート
            current_file = os.path.abspath(__file__)
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        else:
            self.base_dir = base_dir
        
        self.auto_collector = AutoDataCollector(base_dir)
        
        # キャッシュ
        self._data_cache = {}
        
    def get_strategy_data(self, 
                         primary_timeframe: str, 
                         years: List[int], 
                         additional_timeframes: List[str] = None,
                         add_indicators: bool = True) -> pd.DataFrame:
        """
        戦略テスト用のデータセットを取得
        
        Parameters
        ----------
        primary_timeframe : str
            メイン時間足
        years : List[int]
            データ年
        additional_timeframes : List[str], optional
            追加で必要な時間足
        add_indicators : bool, default True
            テクニカル指標を自動追加するか
            
        Returns
        -------
        pd.DataFrame
            戦略テスト用データセット
        """
        cache_key = f"{primary_timeframe}_{sorted(years)}_{additional_timeframes}_{add_indicators}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key].copy()
        
        # 必要なデータを確保
        required_timeframes = [primary_timeframe]
        if additional_timeframes:
            required_timeframes.extend(additional_timeframes)
        
        data_files = ensure_required_data(required_timeframes, years)
        
        # プライマリ時間足データを読み込み
        primary_data = self._load_multi_year_data(primary_timeframe, years, data_files)
        
        if add_indicators:
            # テクニカル指標を追加
            primary_data = self._add_technical_indicators(primary_data)
        
        # 追加時間足データがある場合は統合
        if additional_timeframes:
            for timeframe in additional_timeframes:
                tf_data = self._load_multi_year_data(timeframe, years, data_files)
                primary_data = self._merge_timeframe_data(primary_data, tf_data, timeframe)
        
        # データ品質チェック
        primary_data = self._validate_data_quality(primary_data)
        
        # キャッシュに保存
        self._data_cache[cache_key] = primary_data.copy()
        
        return primary_data
    
    def _load_multi_year_data(self, 
                             timeframe: str, 
                             years: List[int], 
                             data_files: Dict[str, Dict[int, str]]) -> pd.DataFrame:
        """
        複数年のデータを読み込み統合
        
        Parameters
        ----------
        timeframe : str
            時間足
        years : List[int]
            年リスト
        data_files : Dict[str, Dict[int, str]]
            データファイルパス辞書
            
        Returns
        -------
        pd.DataFrame
            統合データ
        """
        all_data = []
        
        if timeframe not in data_files:
            raise ValueError(f"No data available for timeframe: {timeframe}")
        
        for year in years:
            if year in data_files[timeframe]:
                filepath = data_files[timeframe][year]
                yearly_data = pd.read_csv(filepath, index_col=0, parse_dates=True)
                
                # カラム名を統一
                yearly_data = self._standardize_columns(yearly_data)
                
                all_data.append(yearly_data)
                print(f"  {year}年 ({timeframe}): {len(yearly_data)} 行")
        
        if not all_data:
            raise ValueError(f"No data loaded for {timeframe} in years {years}")
        
        # データ統合
        combined_data = pd.concat(all_data, sort=True)
        combined_data.sort_index(inplace=True)
        
        # 重複削除
        combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
        
        return combined_data
    
    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        カラム名を標準化
        
        Parameters
        ----------
        data : pd.DataFrame
            データ
            
        Returns
        -------
        pd.DataFrame
            標準化されたデータ
        """
        # カラム名のマッピング
        column_mapping = {
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        # 小文字を大文字に変換
        data.columns = [column_mapping.get(col.lower(), col) for col in data.columns]
        
        # 必須カラムの確認
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        return data
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        基本的なテクニカル指標を追加
        
        Parameters
        ----------
        data : pd.DataFrame
            価格データ
            
        Returns
        -------
        pd.DataFrame
            指標付きデータ
        """
        # DataProcessorを使用してテクニカル指標を追加
        processor = DataProcessor(data)
        enhanced_data = processor.add_technical_indicators(data)
        return enhanced_data
    
    def _merge_timeframe_data(self, 
                             primary_data: pd.DataFrame, 
                             secondary_data: pd.DataFrame, 
                             secondary_timeframe: str) -> pd.DataFrame:
        """
        異なる時間足のデータをマージ
        
        Parameters
        ----------
        primary_data : pd.DataFrame
            メインデータ
        secondary_data : pd.DataFrame
            追加データ
        secondary_timeframe : str
            追加データの時間足
            
        Returns
        -------
        pd.DataFrame
            マージされたデータ
        """
        # セカンダリデータのカラム名にプレフィックスを追加
        prefix = secondary_timeframe + '_'
        secondary_renamed = secondary_data.add_prefix(prefix)
        
        # 前方補完でマージ（高時間足データを低時間足に合わせる）
        merged_data = pd.merge_asof(
            primary_data.sort_index(),
            secondary_renamed.sort_index(),
            left_index=True,
            right_index=True,
            direction='backward'
        )
        
        return merged_data
    
    def _validate_data_quality(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        データ品質チェックと修正
        
        Parameters
        ----------
        data : pd.DataFrame
            データ
            
        Returns
        -------
        pd.DataFrame
            品質チェック済みデータ
        """
        original_len = len(data)
        
        # 1. NaN値の処理
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        # 2. 異常値の検出・除去（価格が0以下、異常な価格変動）
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in data.columns:
                # 0以下の値を除去
                data = data[data[col] > 0]
                
                # 異常な価格変動（前日比±50%以上）を除去
                pct_change = data[col].pct_change()
                data = data[abs(pct_change) < 0.5]
        
        # 3. OHLC整合性チェック
        valid_ohlc = (
            (data['Low'] <= data['Open']) &
            (data['Low'] <= data['Close']) &
            (data['High'] >= data['Open']) &
            (data['High'] >= data['Close'])
        )
        data = data[valid_ohlc]
        
        # 4. 時系列の整合性チェック（重複時刻の除去）
        data = data[~data.index.duplicated(keep='first')]
        
        # 結果ログ
        removed_count = original_len - len(data)
        if removed_count > 0:
            removal_rate = (removed_count / original_len) * 100
            print(f"Data quality check: Removed {removed_count} records ({removal_rate:.2f}%)")
        
        return data
    
    def get_available_data_summary(self) -> Dict[str, Dict[str, List[int]]]:
        """
        利用可能なデータのサマリーを取得
        
        Returns
        -------
        Dict[str, Dict[str, List[int]]]
            データサマリー情報
        """
        summary = self.auto_collector.get_data_summary()
        
        # 統計情報を追加
        detailed_summary = {}
        for timeframe, years in summary.items():
            detailed_summary[timeframe] = {
                'years': years,
                'year_count': len(years),
                'year_range': f"{min(years)}-{max(years)}" if years else "N/A"
            }
        
        return detailed_summary
    
    def prepare_backtest_environment(self, 
                                   primary_timeframe: str = '15min',
                                   years: List[int] = None,
                                   additional_timeframes: List[str] = None) -> Dict[str, any]:
        """
        バックテスト環境を準備
        
        Parameters
        ----------
        primary_timeframe : str, default '15min'
            メイン時間足
        years : List[int], optional
            テスト年（デフォルトは直近3年）
        additional_timeframes : List[str], optional
            追加時間足
            
        Returns
        -------
        Dict[str, any]
            バックテスト用データとメタデータ
        """
        if years is None:
            # デフォルトは直近3年
            available_years = self.auto_collector.get_available_years()
            years = sorted(available_years)[-3:] if len(available_years) >= 3 else available_years
        
        print(f"\nバックテスト環境準備中...")
        print(f"メイン時間足: {primary_timeframe}")
        print(f"対象年: {years}")
        if additional_timeframes:
            print(f"追加時間足: {additional_timeframes}")
        
        # データ取得
        data = self.get_strategy_data(
            primary_timeframe=primary_timeframe,
            years=years,
            additional_timeframes=additional_timeframes,
            add_indicators=True
        )
        
        # 期間設定（最初と最後の年の特定期間を使用）
        if len(years) >= 3:
            start_date = pd.Timestamp(f'{min(years)}-08-09')  # 8月9日から
            end_date = pd.Timestamp(f'{max(years)}-08-09')    # 翌年8月9日まで
        else:
            start_date = data.index.min()
            end_date = data.index.max()
        
        # 期間でフィルタリング
        filtered_data = data[start_date:end_date]
        
        # メタデータ
        metadata = {
            'timeframe': primary_timeframe,
            'years': years,
            'start_date': start_date,
            'end_date': end_date,
            'total_records': len(filtered_data),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
            'additional_timeframes': additional_timeframes or []
        }
        
        print(f"データ準備完了: {len(filtered_data)} レコード")
        print(f"期間: {metadata['date_range']}")
        
        return {
            'data': filtered_data,
            'metadata': metadata
        }
    
    def clear_cache(self):
        """データキャッシュをクリア"""
        self._data_cache.clear()
        print("Data cache cleared")

# 便利関数
def get_backtest_data(timeframe: str = '15min', 
                     years: List[int] = None,
                     additional_timeframes: List[str] = None) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    バックテスト用データを取得する便利関数
    
    Parameters
    ----------
    timeframe : str, default '15min'
        メイン時間足
    years : List[int], optional
        テスト年
    additional_timeframes : List[str], optional
        追加時間足
        
    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, any]]
        (データ, メタデータ) のタプル
    """
    manager = EnhancedDataManager()
    result = manager.prepare_backtest_environment(timeframe, years, additional_timeframes)
    return result['data'], result['metadata']

if __name__ == "__main__":
    # テスト実行
    print("Enhanced Data Manager テスト実行")
    
    manager = EnhancedDataManager()
    
    # 利用可能データ表示
    print("\n利用可能なデータ:")
    summary = manager.get_available_data_summary()
    for timeframe, info in summary.items():
        print(f"  {timeframe}: {info['year_count']}年分 ({info['year_range']})")
    
    # バックテスト環境準備テスト
    try:
        backtest_env = manager.prepare_backtest_environment(
            primary_timeframe='15min',
            years=[2022, 2023, 2024, 2025],
            additional_timeframes=['1H', '4H']
        )
        
        data = backtest_env['data']
        metadata = backtest_env['metadata']
        
        print(f"\nテスト成功:")
        print(f"  データサイズ: {len(data)} レコード")
        print(f"  カラム数: {len(data.columns)}")
        print(f"  期間: {metadata['date_range']}")
        print(f"  サンプルデータ:")
        print(data.head(3))
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")