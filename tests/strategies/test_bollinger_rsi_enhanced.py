import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategies.bollinger_rsi import BollingerRsiStrategy
from src.strategies.bollinger_rsi_enhanced import BollingerRsiEnhancedStrategy
from src.utils.logger import Logger
from src.utils.config import Config

def main():
    """
    拡張版ボリンジャーバンド＋RSI戦略のテスト
    """
    output_dir = "results/bollinger_rsi_enhanced"
    os.makedirs(output_dir, exist_ok=True)
    
    logger = Logger(output_dir)
    logger.log_info("拡張版ボリンジャーバンド＋RSI戦略のテスト開始")
    
    config = Config()
    
    year = 2020
    logger.log_info(f"{year}年の処理済みデータの読み込みを試みています...")
    
    from src.data.data_processor_enhanced import DataProcessor as EnhancedDataProcessor
    data_processor = EnhancedDataProcessor(pd.DataFrame())
    year_data = data_processor.load_processed_data(config.get('data', 'timeframe'), year, config.get('data', 'processed_dir'))
    
    if year_data.empty:
        logger.log_info(f"処理済みデータが見つかりません。{year}年の生データから処理します...")
        data_loader = DataLoader(config.get('data', 'raw_dir'))
        data = data_loader.load_year_data(year)
        
        if data.empty:
            logger.log_warning(f"{year}年のデータがありません")
            return
        
        logger.log_info(f"データ読み込み完了: {len(data)} 行")
        
        logger.log_info("データ処理中...")
        data_processor = DataProcessor(data)
        
        resampled_data = data_processor.resample(config.get('data', 'timeframe'))
        logger.log_info(f"リサンプリング完了: {len(resampled_data)} 行")
        
        resampled_data = data_processor.add_technical_indicators(resampled_data)
        
        resampled_data = data_processor.get_tokyo_session_range(resampled_data)
        logger.log_info("テクニカル指標の計算完了")
        
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        year_data = resampled_data.loc[start_date:end_date]
    else:
        logger.log_info(f"処理済みデータ読み込み完了: {len(year_data)} 行")
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        year_data = year_data.loc[start_date:end_date]
    
    if year_data.empty:
        logger.log_warning(f"{year}年のデータがありません")
        return
    
    logger.log_info("元のボリンジャーバンド＋RSI戦略を適用中...")
    original_strategy = BollingerRsiStrategy()
    original_signals = original_strategy.generate_signals(year_data.copy())
    
    logger.log_info("拡張版ボリンジャーバンド＋RSI戦略を適用中...")
    enhanced_strategy = BollingerRsiEnhancedStrategy(
        bb_window=20,
        bb_dev=2.0,
        rsi_window=14,
        rsi_upper=70,
        rsi_lower=30,
        sl_pips=7.0,
        tp_pips=10.0,
        use_adaptive_params=True,
        trend_filter=True,
        vol_filter=True,
        time_filter=True
    )
    enhanced_signals = enhanced_strategy.generate_signals(year_data.copy())
    
    original_buy_signals = len(original_signals[original_signals['signal'] == 1])
    original_sell_signals = len(original_signals[original_signals['signal'] == -1])
    original_total_signals = original_buy_signals + original_sell_signals
    
    enhanced_buy_signals = len(enhanced_signals[enhanced_signals['signal'] == 1])
    enhanced_sell_signals = len(enhanced_signals[enhanced_signals['signal'] == -1])
    enhanced_total_signals = enhanced_buy_signals + enhanced_sell_signals
    
    logger.log_info(f"元の戦略のシグナル数: 買い={original_buy_signals}, 売り={original_sell_signals}, 合計={original_total_signals}")
    logger.log_info(f"拡張版戦略のシグナル数: 買い={enhanced_buy_signals}, 売り={enhanced_sell_signals}, 合計={enhanced_total_signals}")
    
    jan_data = year_data.loc[f"{year}-01-01":f"{year}-01-31"].copy()
    
    jan_original = original_strategy.generate_signals(jan_data.copy())
    jan_enhanced = enhanced_strategy.generate_signals(jan_data.copy())
    
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 1, 1)
    plt.plot(jan_data.index, jan_data['Close'], label='Close Price')
    plt.plot(jan_data.index, jan_data['bb_upper'], 'r--', label='Upper BB')
    plt.plot(jan_data.index, jan_data['bb_middle'], 'g--', label='Middle BB')
    plt.plot(jan_data.index, jan_data['bb_lower'], 'b--', label='Lower BB')
    
    buy_signals = jan_original[jan_original['signal'] == 1]
    sell_signals = jan_original[jan_original['signal'] == -1]
    
    plt.scatter(buy_signals.index, buy_signals['entry_price'], marker='^', color='g', s=100, label='Original Buy')
    plt.scatter(sell_signals.index, sell_signals['entry_price'], marker='v', color='r', s=100, label='Original Sell')
    
    plt.title(f'{year}年1月 元のボリンジャーバンド＋RSI戦略シグナル')
    plt.legend()
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(jan_data.index, jan_data['Close'], label='Close Price')
    plt.plot(jan_data.index, jan_data['bb_upper'], 'r--', label='Upper BB')
    plt.plot(jan_data.index, jan_data['bb_middle'], 'g--', label='Middle BB')
    plt.plot(jan_data.index, jan_data['bb_lower'], 'b--', label='Lower BB')
    
    buy_signals = jan_enhanced[jan_enhanced['signal'] == 1]
    sell_signals = jan_enhanced[jan_enhanced['signal'] == -1]
    
    plt.scatter(buy_signals.index, buy_signals['entry_price'], marker='^', color='g', s=100, label='Enhanced Buy')
    plt.scatter(sell_signals.index, sell_signals['entry_price'], marker='v', color='r', s=100, label='Enhanced Sell')
    
    plt.title(f'{year}年1月 拡張版ボリンジャーバンド＋RSI戦略シグナル')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/bollinger_rsi_comparison_{year}_01.png", dpi=300)
    
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 1, 1)
    plt.plot(jan_data.index, jan_data['rsi'], label='RSI')
    plt.axhline(y=70, color='r', linestyle='--', label='RSI 70')
    plt.axhline(y=30, color='g', linestyle='--', label='RSI 30')
    
    buy_signals = jan_original[jan_original['signal'] == 1]
    sell_signals = jan_original[jan_original['signal'] == -1]
    
    for idx in buy_signals.index:
        plt.axvline(x=idx, color='g', alpha=0.3)
    
    for idx in sell_signals.index:
        plt.axvline(x=idx, color='r', alpha=0.3)
    
    plt.title(f'{year}年1月 RSIと元の戦略シグナル')
    plt.legend()
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(jan_data.index, jan_data['rsi'], label='RSI')
    plt.axhline(y=70, color='r', linestyle='--', label='RSI 70')
    plt.axhline(y=30, color='g', linestyle='--', label='RSI 30')
    
    buy_signals = jan_enhanced[jan_enhanced['signal'] == 1]
    sell_signals = jan_enhanced[jan_enhanced['signal'] == -1]
    
    for idx in buy_signals.index:
        plt.axvline(x=idx, color='g', alpha=0.3)
    
    for idx in sell_signals.index:
        plt.axvline(x=idx, color='r', alpha=0.3)
    
    plt.title(f'{year}年1月 RSIと拡張版戦略シグナル')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/bollinger_rsi_rsi_comparison_{year}_01.png", dpi=300)
    
    
    logger.log_info("拡張版ボリンジャーバンド＋RSI戦略のテスト完了")
    logger.log_info(f"結果は {output_dir} ディレクトリに保存されました")

if __name__ == "__main__":
    main()
