"""
複数通貨ペアのテスト用に合成データを生成するスクリプト
USDJPYデータを基にして、他の通貨ペア（EURUSD, GBPUSD, AUDUSD, USDCAD）の合成データを作成
"""
import os
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import random

def ensure_directory(directory):
    """ディレクトリが存在しない場合は作成する"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_usdjpy_data(year, timeframe):
    """USDJPYデータを読み込む"""
    base_dir = f"data/processed/{year}/USDJPY"
    file_path = f"{base_dir}/{timeframe}.csv"
    
    if not os.path.exists(file_path):
        print(f"ファイルが見つかりません: {file_path}")
        return None
        
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df

def generate_synthetic_data(usdjpy_df, currency_pair, variation_factor=0.2):
    """USDJPYデータを基に合成データを生成"""
    if usdjpy_df is None or usdjpy_df.empty:
        return None
        
    synthetic_df = usdjpy_df.copy()
    
    if currency_pair == "EURUSD":
        price_multiplier = -0.8 + random.uniform(-variation_factor, variation_factor)
    elif currency_pair == "GBPUSD":
        price_multiplier = -0.7 + random.uniform(-variation_factor, variation_factor)
    elif currency_pair == "AUDUSD":
        price_multiplier = -0.4 + random.uniform(-variation_factor, variation_factor)
    elif currency_pair == "USDCAD":
        price_multiplier = 0.6 + random.uniform(-variation_factor, variation_factor)
    else:
        price_multiplier = 0.0
    
    for col in ['open', 'high', 'low', 'close']:
        if col in synthetic_df.columns:
            if currency_pair == "EURUSD":
                base_value = 1.1 + random.uniform(-0.05, 0.05)
            elif currency_pair == "GBPUSD":
                base_value = 1.3 + random.uniform(-0.05, 0.05)
            elif currency_pair == "AUDUSD":
                base_value = 0.7 + random.uniform(-0.05, 0.05)
            elif currency_pair == "USDCAD":
                base_value = 1.3 + random.uniform(-0.05, 0.05)
            else:
                base_value = 1.0
                
            changes = synthetic_df[col].pct_change().fillna(0)
            modified_changes = changes * price_multiplier
            
            synthetic_df[col] = base_value * (1 + modified_changes).cumprod()
    
    if 'volume' in synthetic_df.columns:
        volume_multiplier = 0.8 + random.uniform(-0.2, 0.2)
        synthetic_df['volume'] = synthetic_df['volume'] * volume_multiplier
    
    return synthetic_df

def save_synthetic_data(df, year, timeframe, currency_pair):
    """合成データを保存"""
    if df is None or df.empty:
        return False
        
    output_dir = f"data/processed/{year}/{currency_pair}"
    ensure_directory(output_dir)
    
    output_file = f"{output_dir}/{timeframe}.csv"
    df.to_csv(output_file)
    print(f"合成データを保存しました: {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description='複数通貨ペアのテスト用に合成データを生成')
    parser.add_argument('--years', type=str, default='2020,2021,2022,2023,2024,2025',
                        help='対象年（カンマ区切り）')
    parser.add_argument('--timeframes', type=str, default='1D,1W,1M,4H',
                        help='対象時間足（カンマ区切り）')
    parser.add_argument('--currency_pairs', type=str, default='EURUSD,GBPUSD,AUDUSD,USDCAD',
                        help='生成する通貨ペア（カンマ区切り）')
    args = parser.parse_args()
    
    years = [int(year) for year in args.years.split(',')]
    timeframes = args.timeframes.split(',')
    currency_pairs = args.currency_pairs.split(',')
    
    print(f"対象年: {years}")
    print(f"対象時間足: {timeframes}")
    print(f"対象通貨ペア: {currency_pairs}")
    
    for year in years:
        for timeframe in timeframes:
            usdjpy_df = load_usdjpy_data(year, timeframe)
            if usdjpy_df is None:
                print(f"USDJPYデータが見つかりません: {year}年 {timeframe}")
                continue
                
            print(f"USDJPYデータを読み込みました: {year}年 {timeframe}, {len(usdjpy_df)}行")
            
            for currency_pair in currency_pairs:
                synthetic_df = generate_synthetic_data(usdjpy_df, currency_pair)
                success = save_synthetic_data(synthetic_df, year, timeframe, currency_pair)
                if success:
                    print(f"{currency_pair}の合成データを生成しました: {year}年 {timeframe}")
                else:
                    print(f"{currency_pair}の合成データ生成に失敗しました: {year}年 {timeframe}")

if __name__ == "__main__":
    main()
