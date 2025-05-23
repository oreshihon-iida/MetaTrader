import pandas as pd
import matplotlib.pyplot as plt
import os
from src.data.data_processor_enhanced import DataProcessor
from src.utils.config import Config

def main():
    config = Config()
    processed_dir = config.get('data', 'processed_dir')
    
    timeframes = ['15min', '1H']
    test_year = 2020  # テスト対象の年
    
    data_processor = DataProcessor(None)
    
    for timeframe in timeframes:
        print(f"\n====== Testing {timeframe} data for {test_year} ======")
        
        data = data_processor.load_processed_data(timeframe, test_year, processed_dir)
        
        if data.empty:
            print(f"No processed data found for {timeframe} in {test_year}")
            continue
        
        print(f"Data shape: {data.shape}")
        print(f"Date range: {data.index.min()} to {data.index.max()}")
        print(f"Columns: {list(data.columns)}")
        
        if 'support_level_1' in data.columns and 'resistance_level_1' in data.columns:
            support_count = data['support_level_1'].notna().sum()
            resistance_count = data['resistance_level_1'].notna().sum()
            print(f"Support levels detected: {support_count}")
            print(f"Resistance levels detected: {resistance_count}")
            
            print("\nSample data with support/resistance levels:")
            sample = data[data['support_level_1'].notna() | data['resistance_level_1'].notna()].head(3)
            print(sample[['Open', 'High', 'Low', 'Close', 'support_level_1', 'resistance_level_1']])
            
            plot_dir = 'results/test_plots'
            os.makedirs(plot_dir, exist_ok=True)
            
            month_data = data.loc[f"{test_year}-01-01":f"{test_year}-01-31"]
            if not month_data.empty:
                plt.figure(figsize=(12, 6))
                plt.plot(month_data.index, month_data['Close'], label='Close Price')
                
                support = month_data['support_level_1'].dropna()
                if not support.empty:
                    plt.scatter(support.index, support.values, color='green', marker='^', label='Support Level')
                
                resistance = month_data['resistance_level_1'].dropna()
                if not resistance.empty:
                    plt.scatter(resistance.index, resistance.values, color='red', marker='v', label='Resistance Level')
                
                plt.title(f'USDJPY {timeframe} with Support/Resistance Levels - Jan {test_year}')
                plt.xlabel('Date')
                plt.ylabel('Price')
                plt.legend()
                plt.grid(True)
                
                plot_path = os.path.join(plot_dir, f'support_resistance_{timeframe}_{test_year}_01.png')
                plt.savefig(plot_path)
                plt.close()
                print(f"Plot saved to {plot_path}")
        else:
            print("Support/resistance levels not found in the data")

if __name__ == "__main__":
    main()
