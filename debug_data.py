import pandas as pd
import numpy as np
import os
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategies.tokyo_london import TokyoLondonStrategy
from src.strategies.bollinger_rsi import BollingerRsiStrategy

def main():
    print("Loading data...")
    data_loader = DataLoader('data/raw')
    data = data_loader.load_all_data()
    print(f'Raw data shape: {data.shape}')
    print(f'Raw data date range: {data.index.min()} to {data.index.max()}')

    print("\nProcessing data...")
    data_processor = DataProcessor(data)
    resampled_data = data_processor.resample('15min')
    print(f'Resampled data shape: {resampled_data.shape}')
    print(f'Resampled data date range: {resampled_data.index.min()} to {resampled_data.index.max()}')

    resampled_data = data_processor.add_technical_indicators(resampled_data)
    print(f'Technical indicators added: {list(resampled_data.columns)}')

    resampled_data = data_processor.get_tokyo_session_range(resampled_data)
    print(f'Tokyo session range added: {list(resampled_data.columns)}')

    tokyo_data = resampled_data[resampled_data.tokyo_high.notna()]
    if not tokyo_data.empty:
        print(f'\nTokyo high/low sample (first 3 rows):')
        print(tokyo_data.head(3)[['tokyo_high', 'tokyo_low']])
    else:
        print("\nWARNING: No Tokyo session range data found!")

    backtest_data = resampled_data.loc['2000-06-01':'2000-12-29']
    print(f'\nBacktest data shape: {backtest_data.shape}')
    print(f'Backtest data date range: {backtest_data.index.min()} to {backtest_data.index.max()}')

    print("\nApplying strategies...")
    tokyo_london = TokyoLondonStrategy()
    bollinger_rsi = BollingerRsiStrategy()

    strategy_data = bollinger_rsi.generate_signals(backtest_data.copy())
    signal_count = (strategy_data['signal'] != 0).sum()
    print(f'Bollinger+RSI strategy signals: {signal_count}')
    if signal_count > 0:
        print("Sample signals:")
        print(strategy_data[strategy_data['signal'] != 0].head(3)[['signal', 'entry_price', 'sl_price', 'tp_price', 'strategy']])

    strategy_data = tokyo_london.generate_signals(backtest_data.copy())
    signal_count = (strategy_data['signal'] != 0).sum()
    print(f'Tokyo-London strategy signals: {signal_count}')
    if signal_count > 0:
        print("Sample signals:")
        print(strategy_data[strategy_data['signal'] != 0].head(3)[['signal', 'entry_price', 'sl_price', 'tp_price', 'strategy']])

    print("\nDebugging Tokyo-London strategy...")
    tokyo_range_count = backtest_data.dropna(subset=['tokyo_high', 'tokyo_low']).shape[0]
    print(f'Rows with Tokyo range data: {tokyo_range_count}')
    
    backtest_data['hour_jst'] = (backtest_data.index + pd.Timedelta(hours=9)).hour
    london_session = backtest_data[backtest_data['hour_jst'] >= 16]
    print(f'Rows after 16:00 JST: {london_session.shape[0]}')
    
    if not london_session.empty and tokyo_range_count > 0:
        london_session['prev_close'] = london_session['Close'].shift(1)
        breakout_up = ((london_session['Close'] > london_session['tokyo_high']) & 
                      (london_session['prev_close'] <= london_session['tokyo_high']))
        breakout_down = ((london_session['Close'] < london_session['tokyo_low']) & 
                        (london_session['prev_close'] >= london_session['tokyo_low']))
        print(f'Potential breakout up signals: {breakout_up.sum()}')
        print(f'Potential breakout down signals: {breakout_down.sum()}')
    
    print("\nDebugging Bollinger+RSI strategy...")
    if 'bb_upper' in backtest_data.columns and 'bb_lower' in backtest_data.columns and 'rsi' in backtest_data.columns:
        upper_cross = ((backtest_data['Close'] >= backtest_data['bb_upper']) & 
                      (backtest_data['rsi'] >= 70))
        lower_cross = ((backtest_data['Close'] <= backtest_data['bb_lower']) & 
                      (backtest_data['rsi'] <= 30))
        print(f'Potential Bollinger upper band + RSI>70 signals: {upper_cross.sum()}')
        print(f'Potential Bollinger lower band + RSI<30 signals: {lower_cross.sum()}')
    else:
        print("WARNING: Missing technical indicators!")

if __name__ == "__main__":
    main()
