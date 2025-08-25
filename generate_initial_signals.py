"""
初期シグナルデータを生成してEAをテスト可能にする
"""

import csv
import os
from datetime import datetime, timedelta

def generate_test_signals():
    """テスト用の初期シグナルを生成"""
    
    # MT5のFilesフォルダパス
    mt5_files_path = r'C:\Users\iida\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files'
    csv_path = os.path.join(mt5_files_path, 'longterm_news_signals.csv')
    
    # CSVヘッダー
    headers = [
        'analysis_date', 'event_date', 'event_time', 'event_type',
        'importance', 'actual', 'forecast', 'previous',
        'expected_direction', 'confidence', 'ml_confidence',
        'priced_in_factor', 'enhanced_confidence', 'trade_signal',
        'recommended_tp_pips', 'recommended_sl_pips'
    ]
    
    # テスト用シグナルデータ（現在時刻から生成）
    now = datetime.now()
    test_signals = []
    
    # 今後24時間のテストシグナルを生成
    for i in range(5):
        signal_time = now + timedelta(hours=i*4)
        
        signal = {
            'analysis_date': now.strftime('%Y-%m-%d %H:%M:%S'),
            'event_date': signal_time.strftime('%Y-%m-%d'),
            'event_time': signal_time.strftime('%H:%M'),
            'event_type': f'Test Signal {i+1} - Economic Data',
            'importance': 'HIGH' if i % 2 == 0 else 'MEDIUM',
            'actual': '',
            'forecast': '0.5',
            'previous': '0.3',
            'expected_direction': 'bullish' if i % 2 == 0 else 'bearish',
            'confidence': '0.65',
            'ml_confidence': '0.60',
            'priced_in_factor': '0.3',
            'enhanced_confidence': '0.62',
            'trade_signal': 'true' if i < 2 else 'false',  # 最初の2つだけ取引
            'recommended_tp_pips': '50',
            'recommended_sl_pips': '20'
        }
        test_signals.append(signal)
    
    # CSVファイルに書き込み
    print(f"Generating test signals to: {csv_path}")
    
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_signals)
    
    print(f"Generated {len(test_signals)} test signals")
    
    # バックアップも作成
    local_path = 'longterm_news_signals.csv'
    with open(local_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_signals)
    
    print(f"Backup saved to: {local_path}")
    
    return test_signals

def main():
    print("="*60)
    print("Test Signal Generator for NewsBasedTradingSystem v3")
    print("="*60)
    
    signals = generate_test_signals()
    
    print("\n[Generated Signals]")
    for i, sig in enumerate(signals):
        print(f"{i+1}. {sig['event_type']}")
        print(f"   Time: {sig['event_date']} {sig['event_time']}")
        print(f"   Direction: {sig['expected_direction']}, Confidence: {sig['enhanced_confidence']}")
        print(f"   Trade: {sig['trade_signal']}")
    
    print("\n✅ CSV file generated successfully!")
    print("You can now use the EA without errors.")

if __name__ == "__main__":
    main()