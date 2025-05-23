import os
import pandas as pd
import numpy as np
from src.data.data_processor_enhanced import DataProcessor
from src.utils.logger import Logger
import zipfile
import io
import argparse

parser = argparse.ArgumentParser(description='指定した年のデータを処理します')
parser.add_argument('--year', type=int, required=True, help='処理する年（例：2010）')
args = parser.parse_args()

year = args.year

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)
logger.log_info(f"{year}年データ処理開始")

def extract_and_process_histdata(zip_path, year):
    """
    HistData.comのZIPファイルからデータを抽出して処理する
    
    Parameters
    ----------
    zip_path : str
        ZIPファイルのパス
    year : int
        データの年
        
    Returns
    -------
    pd.DataFrame
        処理されたデータフレーム
    """
    logger.log_info(f"{zip_path} からデータを抽出中...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
            
            if not csv_files:
                logger.log_warning(f"{zip_path} にCSVファイルが見つかりません")
                return pd.DataFrame()
            
            csv_file = csv_files[0]
            with zip_ref.open(csv_file) as f:
                content = io.TextIOWrapper(f, encoding='utf-8')
                
                df = pd.read_csv(content, sep=',', names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
                df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y.%m.%d %H:%M', errors='coerce')
                
                invalid_dates = df['Datetime'].isna()
                if invalid_dates.any():
                    logger.log_warning(f"{sum(invalid_dates)}行の無効な日時データを除外しました")
                    df = df[~invalid_dates]
                
                df = df.drop(['Date', 'Time'], axis=1)
                df = df.set_index('Datetime')
                
                if df.index.duplicated().any():
                    logger.log_warning(f"{sum(df.index.duplicated())}行の重複データを除外しました")
                    df = df[~df.index.duplicated()]
                
                df = df.sort_index()
                
                return df
    except Exception as e:
        logger.log_error(f"データ抽出中にエラーが発生しました: {e}")
        return pd.DataFrame()

for timeframe in ['15min', '1H', '4H']:
    os.makedirs(f"data/processed/{timeframe}/{year}", exist_ok=True)

logger.log_info(f"{year}年のデータ処理中...")

zip_files = [f for f in os.listdir("data/raw") if f.endswith('.zip') and f"USDJPY_M1{year}" in f]

if not zip_files:
    logger.log_warning(f"{year}年のデータファイルが見つかりません")
    exit(1)

all_data = []
for zip_file in zip_files:
    zip_path = os.path.join("data/raw", zip_file)
    df = extract_and_process_histdata(zip_path, year)
    if not df.empty:
        all_data.append(df)

if not all_data:
    logger.log_warning(f"{year}年の有効なデータがありません")
    exit(1)

data = pd.concat(all_data)
data = data.sort_index()

for col in ['Open', 'High', 'Low', 'Close']:
    data[col] = pd.to_numeric(data[col], errors='coerce')

invalid_rows = data.isna().any(axis=1)
if invalid_rows.any():
    logger.log_warning(f"{sum(invalid_rows)}行の無効なデータを除外しました")
    data = data[~invalid_rows]

logger.log_info(f"データ読み込み完了: {len(data)} 行")

data_processor = DataProcessor(data)

for timeframe in ['15min', '1H', '4H']:
    logger.log_info(f"{timeframe}へのリサンプリング中...")
    try:
        resampled = data_processor.resample(timeframe)
        if not resampled.empty:
            resampled = data_processor.add_technical_indicators(resampled)
            
            file_path = f"data/processed/{timeframe}/{year}/USDJPY_{timeframe}_{year}.csv"
            resampled.to_csv(file_path)
            logger.log_info(f"{file_path} に保存完了: {len(resampled)} 行")
        else:
            logger.log_warning(f"{timeframe}へのリサンプリング結果が空です")
    except Exception as e:
        logger.log_error(f"{timeframe}へのリサンプリング中にエラーが発生しました: {e}")

logger.log_info(f"{year}年データ処理完了")
