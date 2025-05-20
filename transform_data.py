import os
import pandas as pd
import logging
import time
from multiprocessing import Pool, cpu_count
from src.data.data_loader import DataLoader
from src.data.data_processor_enhanced import DataProcessor
from src.utils.config import Config

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('transform_data')

def process_year(args):
    """
    指定された年のデータを処理する（並列処理用）
    """
    year, timeframes, raw_dir, processed_dir, currency_pair = args
    logger = logging.getLogger(f'transform_data.year_{year}_{currency_pair}')
    
    try:
        filename = f"HISTDATA_COM_MT_{currency_pair}_M1{year}.zip"
        file_path = os.path.join(raw_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return year, currency_pair, False
        
        logger.info(f"Loading data for year {year} and currency pair {currency_pair}...")
        data_loader = DataLoader(raw_dir, currency_pair)
        data = data_loader.load_year_data(year)
        
        if data.empty:
            logger.warning(f"No data found for year {year} and currency pair {currency_pair}")
            return year, currency_pair, False
        
        data_processor = DataProcessor(data)
        
        currency_processed_dir = os.path.join(processed_dir, str(year), currency_pair)
        os.makedirs(currency_processed_dir, exist_ok=True)
        
        result = {}
        for timeframe in timeframes:
            logger.info(f"Processing {timeframe} data for year {year} and currency pair {currency_pair}...")
            
            resampled = data_processor.resample(timeframe)
            
            with_indicators = data_processor.add_technical_indicators(resampled)
            
            processed_data = data_processor.get_tokyo_session_range(with_indicators)
            
            processed_data = data_processor.detect_support_resistance_levels(processed_data)
            
            file_path = os.path.join(currency_processed_dir, f"{timeframe}.csv")
            processed_data.to_csv(file_path)
            
            result[timeframe] = file_path
            logger.info(f"Saved {timeframe} data for year {year} and currency pair {currency_pair} to {file_path}")
            
            print(f"✅ {year}年の{currency_pair} {timeframe}データ変換が完了しました")
        
        return year, currency_pair, True
    except Exception as e:
        logger.error(f"Error processing year {year} and currency pair {currency_pair}: {str(e)}")
        return year, currency_pair, False

def main():
    start_time = time.time()
    logger = setup_logging()
    
    import argparse
    parser = argparse.ArgumentParser(description='FXデータ変換・拡張ツール')
    parser.add_argument('--years', type=str, default='2000-2026', 
                        help='処理対象年（例: 2020,2021 or 2020-2022）')
    parser.add_argument('--timeframes', type=str, default='5min,15min,30min,1H,4H,1D,1W,1M', 
                        help='生成する時間足（例: 5min,15min,1H）')
    parser.add_argument('--currency_pairs', type=str, default='USDJPY', 
                        help='処理する通貨ペア（例: USDJPY,EURUSD,GBPUSD）')
    args = parser.parse_args()
    
    config = Config()
    raw_dir = config.get('data', 'raw_dir')
    processed_dir = config.get('data', 'processed_dir')
    
    timeframes = args.timeframes.split(',')
    
    years = []
    if '-' in args.years:
        start_year, end_year = args.years.split('-')
        years = list(range(int(start_year), int(end_year) + 1))
    else:
        years = [int(year) for year in args.years.split(',')]
    
    currency_pairs = args.currency_pairs.split(',')
    
    tasks = []
    for currency_pair in currency_pairs:
        for year in years:
            tasks.append((year, timeframes, raw_dir, processed_dir, currency_pair))
    
    logger.info(f"Starting parallel processing with {min(cpu_count(), len(tasks))} processes")
    with Pool(processes=min(cpu_count(), len(tasks))) as pool:
        results = pool.map(process_year, tasks)
    
    success_count = sum(1 for _, _, success in results if success)
    logger.info(f"Processing completed. {success_count}/{len(tasks)} tasks processed successfully.")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Total processing time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
