#!/usr/bin/env python3
"""
自動データ収集・処理システム
必要な時間足データを自動的に収集・生成して以後のテストで使用可能にする
"""

import pandas as pd
import numpy as np
import os
import zipfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from ..utils.logger import Logger

class AutoDataCollector:
    """
    自動データ収集・処理システム
    
    機能:
    1. 不足している時間足データの自動生成
    2. rawデータからprocessedデータへの変換
    3. 戦略テストに必要なデータセットの準備
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
            
        self.raw_data_dir = os.path.join(self.base_dir, 'data', 'raw')
        self.processed_data_dir = os.path.join(self.base_dir, 'data', 'processed')
        
        # サポートする時間足とその変換ルール
        self.supported_timeframes = {
            '1min': '1T',      # 1分足（ベース）
            '5min': '5T',      # 5分足
            '15min': '15T',    # 15分足
            '30min': '30T',    # 30分足
            '1H': '1H',        # 1時間足
            '4H': '4H',        # 4時間足
            '1D': '1D'         # 日足
        }
        
        # ログ設定
        log_dir = os.path.join(self.base_dir, 'logs', 'data_collection')
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        
    def get_available_years(self) -> List[int]:
        """利用可能な年のリストを取得"""
        years = []
        for filename in os.listdir(self.raw_data_dir):
            if filename.startswith('HISTDATA_COM_MT_USDJPY_M1') and filename.endswith('.zip'):
                # HISTDATA_COM_MT_USDJPY_M12022.zip -> 2022
                year_str = filename.replace('HISTDATA_COM_MT_USDJPY_M1', '').replace('.zip', '')
                if len(year_str) == 4 and year_str.isdigit():
                    years.append(int(year_str))
                elif len(year_str) == 6:  # 202501形式
                    year = int(year_str[:4])
                    if year not in years:
                        years.append(year)
        return sorted(years)
    
    def extract_and_process_raw_data(self, year: int) -> pd.DataFrame:
        """
        RAWデータを解凍・処理して1分足データを作成
        
        Parameters
        ----------
        year : int
            処理対象年
            
        Returns
        -------
        pd.DataFrame
            1分足データ
        """
        self.logger.log_info(f"Processing raw data for year {year}")
        
        # ZIP形式の場合
        zip_file = os.path.join(self.raw_data_dir, f'HISTDATA_COM_MT_USDJPY_M1{year}.zip')
        if not os.path.exists(zip_file):
            # 月別ファイルを探す（2025年の場合）
            monthly_files = []
            for month in range(1, 13):
                monthly_zip = os.path.join(self.raw_data_dir, f'HISTDATA_COM_MT_USDJPY_M1{year}{month:02d}.zip')
                if os.path.exists(monthly_zip):
                    monthly_files.append(monthly_zip)
            
            if not monthly_files:
                raise FileNotFoundError(f"No raw data found for year {year}")
            
            # 月別データを統合
            year_data = []
            for monthly_zip in monthly_files:
                with zipfile.ZipFile(monthly_zip, 'r') as zip_ref:
                    csv_name = None
                    for name in zip_ref.namelist():
                        if name.endswith('.csv'):
                            csv_name = name
                            break
                    
                    if csv_name:
                        with zip_ref.open(csv_name) as csv_file:
                            monthly_data = pd.read_csv(csv_file, 
                                                     names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume'],
                                                     parse_dates=[['Date', 'Time']], 
                                                     date_parser=lambda x: pd.to_datetime(x, format='%Y.%m.%d %H:%M'))
                            year_data.append(monthly_data)
            
            if year_data:
                data = pd.concat(year_data, ignore_index=True)
            else:
                raise ValueError(f"No data extracted for year {year}")
        else:
            # 年間ファイルを処理
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                csv_name = None
                for name in zip_ref.namelist():
                    if name.endswith('.csv'):
                        csv_name = name
                        break
                
                if not csv_name:
                    raise ValueError(f"No CSV file found in {zip_file}")
                
                with zip_ref.open(csv_name) as csv_file:
                    data = pd.read_csv(csv_file, 
                                     names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume'],
                                     parse_dates=[['Date', 'Time']], 
                                     date_parser=lambda x: pd.to_datetime(x, format='%Y.%m.%d %H:%M'))
        
        # インデックス設定
        data.set_index('Date_Time', inplace=True)
        data.sort_index(inplace=True)
        
        self.logger.log_info(f"Processed {len(data)} 1-minute records for year {year}")
        return data
    
    def convert_to_timeframe(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        1分足データを指定時間足に変換
        
        Parameters
        ----------
        data : pd.DataFrame
            1分足データ
        timeframe : str
            変換先時間足
            
        Returns
        -------
        pd.DataFrame
            変換後データ
        """
        if timeframe not in self.supported_timeframes:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        pandas_rule = self.supported_timeframes[timeframe]
        
        resampled = data.resample(pandas_rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        self.logger.log_info(f"Converted to {timeframe}: {len(resampled)} records")
        return resampled
    
    def save_processed_data(self, data: pd.DataFrame, timeframe: str, year: int):
        """
        処理済みデータを保存
        
        Parameters
        ----------
        data : pd.DataFrame
            保存するデータ
        timeframe : str
            時間足
        year : int
            年
        """
        # 保存ディレクトリ作成
        save_dir = os.path.join(self.processed_data_dir, timeframe, str(year))
        os.makedirs(save_dir, exist_ok=True)
        
        # ファイル名統一（大文字小文字の問題を解決）
        filename = f"USDJPY_{timeframe}_{year}.csv"
        filepath = os.path.join(save_dir, filename)
        
        # データ保存
        data.to_csv(filepath)
        self.logger.log_info(f"Saved {timeframe} data for {year}: {filepath}")
    
    def ensure_timeframe_data(self, timeframe: str, years: List[int] = None) -> Dict[int, str]:
        """
        指定時間足のデータが存在することを確認し、不足分を自動生成
        
        Parameters
        ----------
        timeframe : str
            確認する時間足
        years : List[int], optional
            確認する年のリスト（未指定なら全利用可能年）
            
        Returns
        -------
        Dict[int, str]
            {年: ファイルパス} の辞書
        """
        if years is None:
            years = self.get_available_years()
        
        result_files = {}
        
        for year in years:
            # 既存ファイル確認
            year_dir = os.path.join(self.processed_data_dir, timeframe, str(year))
            if os.path.exists(year_dir):
                # 既存ファイル検索（大文字小文字混在対応）
                existing_file = None
                for filename in os.listdir(year_dir):
                    if filename.lower().startswith('usdjpy') and filename.lower().endswith('.csv'):
                        existing_file = os.path.join(year_dir, filename)
                        break
                
                if existing_file and os.path.exists(existing_file):
                    result_files[year] = existing_file
                    self.logger.log_info(f"Found existing {timeframe} data for {year}: {existing_file}")
                    continue
            
            # データが存在しない場合は生成
            self.logger.log_info(f"Generating {timeframe} data for {year}")
            
            try:
                # 1分足データを取得/生成
                minute_data = self.get_or_create_minute_data(year)
                
                # 指定時間足に変換
                timeframe_data = self.convert_to_timeframe(minute_data, timeframe)
                
                # 保存
                self.save_processed_data(timeframe_data, timeframe, year)
                
                # 結果に追加
                filename = f"USDJPY_{timeframe}_{year}.csv"
                filepath = os.path.join(self.processed_data_dir, timeframe, str(year), filename)
                result_files[year] = filepath
                
            except Exception as e:
                self.logger.log_error(f"Failed to generate {timeframe} data for {year}: {str(e)}")
                continue
        
        self.logger.log_info(f"Ensured {timeframe} data for {len(result_files)} years")
        return result_files
    
    def get_or_create_minute_data(self, year: int) -> pd.DataFrame:
        """
        1分足データを取得または生成
        
        Parameters
        ----------
        year : int
            対象年
            
        Returns
        -------
        pd.DataFrame
            1分足データ
        """
        # 既存の1分足データ確認
        minute_dir = os.path.join(self.processed_data_dir, '1min', str(year))
        if os.path.exists(minute_dir):
            for filename in os.listdir(minute_dir):
                if filename.lower().startswith('usdjpy') and filename.lower().endswith('.csv'):
                    filepath = os.path.join(minute_dir, filename)
                    data = pd.read_csv(filepath, index_col=0, parse_dates=True)
                    self.logger.log_info(f"Loaded existing 1min data for {year}")
                    return data
        
        # RAWデータから生成
        minute_data = self.extract_and_process_raw_data(year)
        self.save_processed_data(minute_data, '1min', year)
        return minute_data
    
    def prepare_strategy_data(self, timeframes: List[str], years: List[int] = None) -> Dict[str, Dict[int, str]]:
        """
        戦略テスト用に複数時間足のデータを準備
        
        Parameters
        ----------
        timeframes : List[str]
            必要な時間足のリスト
        years : List[int], optional
            必要な年のリスト
            
        Returns
        -------
        Dict[str, Dict[int, str]]
            {時間足: {年: ファイルパス}} の辞書
        """
        self.logger.log_info(f"Preparing strategy data for timeframes: {timeframes}")
        
        if years is None:
            years = self.get_available_years()
        
        result = {}
        for timeframe in timeframes:
            result[timeframe] = self.ensure_timeframe_data(timeframe, years)
        
        # サマリーログ
        for timeframe, year_files in result.items():
            self.logger.log_info(f"{timeframe}: {len(year_files)} years available")
            
        return result
    
    def get_data_summary(self) -> Dict[str, List[int]]:
        """
        利用可能なデータのサマリーを取得
        
        Returns
        -------
        Dict[str, List[int]]
            {時間足: [利用可能年リスト]} の辞書
        """
        summary = {}
        
        if not os.path.exists(self.processed_data_dir):
            return summary
        
        for timeframe in os.listdir(self.processed_data_dir):
            timeframe_path = os.path.join(self.processed_data_dir, timeframe)
            if os.path.isdir(timeframe_path):
                years = []
                for year_dir in os.listdir(timeframe_path):
                    year_path = os.path.join(timeframe_path, year_dir)
                    if os.path.isdir(year_path) and year_dir.isdigit():
                        # ファイル存在確認
                        has_files = any(f.endswith('.csv') for f in os.listdir(year_path))
                        if has_files:
                            years.append(int(year_dir))
                
                if years:
                    summary[timeframe] = sorted(years)
        
        return summary

# 便利関数
def ensure_required_data(timeframes: List[str] = None, years: List[int] = None) -> Dict[str, Dict[int, str]]:
    """
    戦略テストに必要なデータを確保する便利関数
    
    Parameters
    ----------
    timeframes : List[str], optional
        必要な時間足（デフォルト: ['5min', '15min', '1H', '4H', '1D']）
    years : List[int], optional
        必要な年（デフォルト: 全利用可能年）
        
    Returns
    -------
    Dict[str, Dict[int, str]]
        利用可能なデータファイルパス
    """
    if timeframes is None:
        timeframes = ['5min', '15min', '1H', '4H', '1D']
    
    collector = AutoDataCollector()
    return collector.prepare_strategy_data(timeframes, years)

def get_available_data() -> Dict[str, List[int]]:
    """
    利用可能なデータのサマリーを取得する便利関数
    
    Returns
    -------
    Dict[str, List[int]]
        {時間足: [利用可能年リスト]} の辞書
    """
    collector = AutoDataCollector()
    return collector.get_data_summary()

if __name__ == "__main__":
    # テスト実行
    print("自動データ収集システムのテスト実行")
    
    collector = AutoDataCollector()
    
    # 利用可能年表示
    print("利用可能な年:", collector.get_available_years())
    
    # 現在のデータサマリー
    print("\n現在のデータサマリー:")
    summary = collector.get_data_summary()
    for timeframe, years in summary.items():
        print(f"  {timeframe}: {years}")
    
    # 戦略テスト用データ準備（例）
    print("\n戦略テスト用データ準備中...")
    required_timeframes = ['5min', '15min', '1H', '4H']
    test_years = [2022, 2023, 2024, 2025]
    
    result = collector.prepare_strategy_data(required_timeframes, test_years)
    
    print("\n準備完了:")
    for timeframe, year_files in result.items():
        print(f"  {timeframe}: {len(year_files)} 年分のデータ")