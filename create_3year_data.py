#!/usr/bin/env python3
"""
過去3年間（2022-2025）のデータを生成するスクリプト
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from src.data.data_loader import DataLoader
from src.data.data_processor_enhanced import DataProcessor

def create_year_data(year):
    """
    指定年のデータを処理して保存
    """
    print(f"\n{year}年のデータを処理中...")
    
    # 生データの読み込み
    data_loader = DataLoader('data/raw')
    
    # ZIPファイルから直接読み込み
    zip_file = f'data/raw/HISTDATA_COM_MT_USDJPY_M1{year}.zip'
    if not os.path.exists(zip_file):
        print(f"  警告: {zip_file} が見つかりません")
        return False
    
    # データの読み込みと処理
    try:
        # DataLoaderを使って年別データを読み込み
        raw_data = data_loader.load_year_data(year)
        
        if raw_data.empty:
            print(f"  {year}年のデータが空です")
            return False
        
        print(f"  読み込み完了: {len(raw_data)} 行")
        
        # データプロセッサーで処理
        processor = DataProcessor(raw_data)
        
        # 各時間足のデータを生成
        timeframes = ['5min', '15min', '30min', '1h', '4h', '1D']
        
        for tf in timeframes:
            print(f"  {tf}データを生成中...")
            
            # リサンプリング
            resampled = processor.resample(tf)
            
            # テクニカル指標を追加
            processed = processor.add_technical_indicators(resampled)
            
            # 保存
            output_dir = f'data/processed/{tf}/{year}'
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = f'{output_dir}/USDJPY_{tf}_{year}.csv'
            processed.to_csv(output_file)
            print(f"    保存完了: {output_file} ({len(processed)} 行)")
        
        return True
        
    except Exception as e:
        print(f"  エラー: {str(e)}")
        return False

def main():
    """
    メイン処理
    """
    print("=" * 50)
    print("3年間のバックテスト用データ生成")
    print("対象期間: 2022年8月 - 2025年8月")
    print("=" * 50)
    
    # 処理する年のリスト
    years = [2022, 2023, 2024, 2025]
    
    success_count = 0
    for year in years:
        # 既に処理済みかチェック
        check_file = f'data/processed/15min/{year}/USDJPY_15min_{year}.csv'
        if os.path.exists(check_file):
            print(f"\n{year}年のデータは既に存在します（スキップ）")
            success_count += 1
            continue
        
        # データ生成
        if create_year_data(year):
            success_count += 1
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("データ生成完了")
    print(f"成功: {success_count}/{len(years)} 年")
    
    if success_count == len(years):
        print("\nすべてのデータが準備できました")
        print("バックテストを実行できます")
    else:
        print("\n一部のデータ生成に失敗しました")
        print("エラーを確認してください")

if __name__ == "__main__":
    main()