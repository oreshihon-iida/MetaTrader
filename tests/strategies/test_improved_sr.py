import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_loader import DataLoader
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.support_resistance_strategy import SupportResistanceStrategy

def test_improved_support_resistance():
    """
    改善されたサポート/レジスタンスレベル検出アルゴリズムをテストする
    """
    timeframes = ['15min', '1H']
    test_year = 2020
    
    data_processor = DataProcessor(pd.DataFrame())
    
    for timeframe in timeframes:
        print(f"\n====== Testing {timeframe} data for {test_year} ======")
        
        processed_data = data_processor.load_processed_data(timeframe, test_year)
        
        if processed_data is None or processed_data.empty:
            print(f"No processed data found for {timeframe} {test_year}")
            continue
        
        if isinstance(processed_data.index, pd.DatetimeIndex):
            month_data = processed_data[processed_data.index.month == 1]
        else:
            month_data = processed_data[pd.to_datetime(processed_data.index).month == 1]
        
        if month_data.empty:
            print(f"No data for January {test_year}")
            continue
        
        original_support_count = month_data['support_level_1'].notna().sum() if 'support_level_1' in month_data.columns else 0
        original_resistance_count = month_data['resistance_level_1'].notna().sum() if 'resistance_level_1' in month_data.columns else 0
        
        print(f"Original Support Levels: {original_support_count}")
        print(f"Original Resistance Levels: {original_resistance_count}")
        
        improved_data = data_processor.detect_support_resistance_levels(
            month_data, 
            window_size=10, 
            swing_threshold=0.0003, 
            cluster_distance=0.0005,
            adaptive_params=True
        )
        
        improved_support_count = improved_data['support_level_1'].notna().sum() if 'support_level_1' in improved_data.columns else 0
        improved_resistance_count = improved_data['resistance_level_1'].notna().sum() if 'resistance_level_1' in improved_data.columns else 0
        
        print(f"Improved Support Levels: {improved_support_count}")
        print(f"Improved Resistance Levels: {improved_resistance_count}")
        
        print("\nSample data with improved support/resistance levels:")
        print(improved_data[['Close', 'support_level_1', 'resistance_level_1']].head(10) if 'support_level_1' in improved_data.columns and 'resistance_level_1' in improved_data.columns else "No support/resistance levels detected")
        
        plt.figure(figsize=(15, 7))
        plt.plot(month_data.index, month_data['Close'], label='Close Price')
        
        if 'support_level_1' in month_data.columns:
            original_support = month_data['support_level_1'].dropna()
            if not original_support.empty:
                plt.scatter(original_support.index, original_support, 
                           color='green', marker='^', label='Original Support')
        
        if 'resistance_level_1' in month_data.columns:
            original_resistance = month_data['resistance_level_1'].dropna()
            if not original_resistance.empty:
                plt.scatter(original_resistance.index, original_resistance, 
                           color='red', marker='v', label='Original Resistance')
        
        if 'support_level_1' in improved_data.columns:
            improved_support = improved_data['support_level_1'].dropna()
            if not improved_support.empty:
                plt.scatter(improved_support.index, improved_support, 
                           color='blue', marker='s', label='Improved Support')
        
        if 'resistance_level_1' in improved_data.columns:
            improved_resistance = improved_data['resistance_level_1'].dropna()
            if not improved_resistance.empty:
                plt.scatter(improved_resistance.index, improved_resistance, 
                           color='purple', marker='d', label='Improved Resistance')
        
        plt.title(f'USDJPY {timeframe} with Improved Support/Resistance Levels - Jan {test_year}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        os.makedirs('results/improved_sr', exist_ok=True)
        plt.savefig(f'results/improved_sr/improved_sr_{timeframe}_{test_year}_01.png')
        plt.close()
        
        print(f"Plot saved to results/improved_sr/improved_sr_{timeframe}_{test_year}_01.png")
    
    print("\n====== Testing Support/Resistance Strategy ======")
    
    data_15min = data_processor.load_processed_data('15min', test_year)
    data_1h = data_processor.load_processed_data('1H', test_year)
    
    if data_15min is not None and not data_15min.empty and data_1h is not None and not data_1h.empty:
        merged_data = data_processor.merge_multi_timeframe_levels(data_15min, data_1h)
        
        strategy = SupportResistanceStrategy()
        result = strategy.generate_signals(merged_data)
        
        buy_signals = (result['signal'] == 1).sum()
        sell_signals = (result['signal'] == -1).sum()
        
        print(f"Buy Signals: {buy_signals}")
        print(f"Sell Signals: {sell_signals}")
        
        if 'strategy' in result.columns:
            strategy_counts = result[result['signal'] != 0]['strategy'].value_counts()
            print("\nStrategy Breakdown:")
            print(strategy_counts)
        
        if isinstance(result.index, pd.DatetimeIndex):
            month_result = result[result.index.month == 1]
        else:
            month_result = result[pd.to_datetime(result.index).month == 1]
        
        plt.figure(figsize=(15, 7))
        plt.plot(month_result.index, month_result['Close'], label='Close Price')
        
        buy_signals = month_result[month_result['signal'] == 1]
        if not buy_signals.empty:
            plt.scatter(buy_signals.index, buy_signals['Close'], 
                       color='green', marker='^', s=100, label='Buy Signal')
        
        sell_signals = month_result[month_result['signal'] == -1]
        if not sell_signals.empty:
            plt.scatter(sell_signals.index, sell_signals['Close'], 
                       color='red', marker='v', s=100, label='Sell Signal')
        
        if 'support_level_1' in month_result.columns:
            support = month_result['support_level_1'].dropna()
            if not support.empty:
                plt.scatter(support.index, support, 
                           color='blue', marker='_', label='Support Level')
        
        if 'resistance_level_1' in month_result.columns:
            resistance = month_result['resistance_level_1'].dropna()
            if not resistance.empty:
                plt.scatter(resistance.index, resistance, 
                           color='purple', marker='_', label='Resistance Level')
        
        plt.title(f'Support/Resistance Strategy Signals - Jan {test_year}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        plt.savefig(f'results/improved_sr/sr_strategy_signals_{test_year}_01.png')
        plt.close()
        
        print(f"Strategy plot saved to results/improved_sr/sr_strategy_signals_{test_year}_01.png")

if __name__ == "__main__":
    test_improved_support_resistance()
