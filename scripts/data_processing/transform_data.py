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
    year, timeframes, raw_dir, processed_dir = args
    logger = logging.getLogger(f'transform_data.year_{year}')
    
    try:
        filename = f"HISTDATA_COM_MT_USDJPY_M1{year}.zip"
        file_path = os.path.join(raw_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return year, False
        
        logger.info(f"Loading data for year {year}...")
        data_loader = DataLoader(raw_dir)
        data = data_loader.load_year_data(year)
        
        if data.empty:
            logger.warning(f"No data found for year {year}")
            return year, False
        
        data_processor = DataProcessor(data)
        
        result = {}
        for timeframe in timeframes:
            logger.info(f"Processing {timeframe} data for year {year}...")
            
            resampled = data_processor.resample(timeframe)
            
            with_indicators = data_processor.add_technical_indicators(resampled)
            
            processed_data = data_processor.get_tokyo_session_range(with_indicators)
            
            processed_data = data_processor.detect_support_resistance_levels(processed_data)
            
            file_path = data_processor.save_processed_data(
                processed_data, 
                timeframe, 
                processed_dir
            )
            
            result[timeframe] = file_path
            logger.info(f"Saved {timeframe} data for year {year} to {file_path}")
            
            print(f"✅ {year}年の{timeframe}データ変換が完了しました")
        
        return year, True
    except Exception as e:
        logger.error(f"Error processing year {year}: {str(e)}")
        return year, False

def main():
    start_time = time.time()
    logger = setup_logging()
    
    config = Config()
    raw_dir = config.get('data', 'raw_dir')
    processed_dir = config.get('data', 'processed_dir')
    
    timeframes = ['5min', '15min', '30min', '1H', '4H', '1D', '1W', '1M']
    
    years = list(range(2000, 2026))
    
    tasks = [(year, timeframes, raw_dir, processed_dir) for year in years]
    
    logger.info(f"Starting parallel processing with {min(cpu_count(), len(years))} processes")
    with Pool(processes=min(cpu_count(), len(years))) as pool:
        results = pool.map(process_year, tasks)
    
    success_count = sum(1 for _, success in results if success)
    logger.info(f"Processing completed. {success_count}/{len(years)} years processed successfully.")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Total processing time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
