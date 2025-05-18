import pandas as pd
import numpy as np
import logging
import os
from src.data.data_processor_enhanced import DataProcessor
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from custom_backtest_engine import CustomBacktestEngine
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_2010_simplified.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_2010_simplified'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_year = 2010

simplified_params = {
    'bb_window': 20,
    'bb_dev': 1.5,        # 標準偏差をさらに小さくしてバンド幅を狭める
    'rsi_window': 14,
    'rsi_upper': 80,      # RSIの閾値をさらに上げて売りシグナルを増やす
    'rsi_lower': 20,      # RSIの閾値をさらに下げて買いシグナルを増やす
    'sl_pips': 5.0,       # 損切り幅を小さくする
    'tp_pips': 10.0,      # 利確幅はそのまま
    'atr_window': 14,
    'atr_sl_multiplier': 1.0,  # ATRベースの損切り乗数をさらに小さくする
    'atr_tp_multiplier': 2.0,
    'use_adaptive_params': True,
    'trend_filter': False,      # トレンドフィルターを無効化
    'vol_filter': False,        # ボラティリティフィルターを無効化
    'time_filter': False,       # 時間フィルターも無効化
    'use_multi_timeframe': True,
    'timeframe_weights': {'15min': 2.0, '1H': 1.0},  # 15分足の重みを増やし、4時間足を除外
    'use_seasonal_filter': False,  # 季節性フィルターを無効化
    'use_price_action': False,     # 価格アクションパターンを無効化
    'consecutive_limit': 5,        # 連続シグナル制限を大幅に緩和
}

logger.info(f"2010年データでの大幅に緩和されたパラメータによるテスト開始")

try:
    data_processor = DataProcessor(pd.DataFrame())
    df_15min = data_processor.load_processed_data('15min', test_year)
    
    if df_15min.empty:
        logger.error(f"データが見つかりません: {test_year}年")
        exit(1)
    
    logger.info(f"データ読み込み成功: {len(df_15min)}行")
    
    strategy = BollingerRsiEnhancedMTStrategy(**simplified_params)
    
    logger.info("シグナル生成開始")
    signals_df = strategy.generate_signals(df_15min, test_year)
    
    logger.info(f"シグナル生成完了: {len(signals_df)}行")
    signal_count = (signals_df['signal'] != 0).sum()
    logger.info(f"シグナル数: {signal_count}")
    
    if signal_count == 0:
        logger.warning(f"シグナルが生成されませんでした。パラメータを調整してください。")
        exit(1)
    
    logger.info("バックテスト実行開始")
    backtest_engine = CustomBacktestEngine(signals_df, spread_pips=0.03)
    backtest_results = backtest_engine.run()
    
    trades = backtest_results['trades']
    wins = backtest_results['wins']
    losses = backtest_results['losses']
    win_rate = backtest_results['win_rate']
    profit_factor = backtest_results['profit_factor']
    net_profit = backtest_results['net_profit']
    
    logger.info(f"2010年のバックテスト結果:")
    logger.info(f"総トレード数: {trades}")
    logger.info(f"勝率: {win_rate:.2f}%")
    logger.info(f"プロフィットファクター: {profit_factor:.2f}")
    logger.info(f"純利益: {net_profit:.2f}")
    
    if trades > 0:
        equity_curve = backtest_results['equity_curve']
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve['equity'])
        plt.title(f'Equity Curve - {test_year}')
        plt.xlabel('Date')
        plt.ylabel('Equity (JPY)')
        plt.grid(True)
        plt.savefig(f'{output_dir}/charts/equity_curve_{test_year}.png')
        plt.close()
        
        equity_curve['drawdown'] = equity_curve['equity'].cummax() - equity_curve['equity']
        equity_curve['drawdown_pct'] = equity_curve['drawdown'] / equity_curve['equity'].cummax() * 100
        
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve['drawdown_pct'])
        plt.title(f'Drawdown - {test_year}')
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.grid(True)
        plt.savefig(f'{output_dir}/charts/drawdown_{test_year}.png')
        plt.close()
        
        monthly_perf = backtest_results['monthly_performance']
        months = list(monthly_perf.keys())
        profits = [monthly_perf[m]['profit'] for m in months]
        
        plt.figure(figsize=(12, 6))
        plt.bar(months, profits)
        plt.title(f'Monthly Performance - {test_year}')
        plt.xlabel('Month')
        plt.ylabel('Profit (JPY)')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/charts/monthly_performance_{test_year}.png')
        plt.close()
    
    with open(f'{output_dir}/reports/test_2010_simplified_results.md', 'w') as f:
        f.write(f"# 2010年データでの大幅に緩和されたパラメータによるテスト結果\n\n")
        f.write(f"## 概要\n\n")
        f.write(f"2010年のデータを使用して、シグナル生成条件を大幅に緩和したボリンジャーバンド＋RSI戦略のバックテスト結果です。\n\n")
        f.write(f"## 総合結果\n\n")
        f.write(f"| 項目 | 値 |\n")
        f.write(f"| --- | --- |\n")
        f.write(f"| 総トレード数 | {trades} |\n")
        f.write(f"| 勝率 | {win_rate:.2f}% |\n")
        f.write(f"| プロフィットファクター | {profit_factor:.2f} |\n")
        f.write(f"| 純利益 | {net_profit:.2f} |\n\n")
        
        f.write(f"## 大幅に緩和されたパラメータ\n\n")
        f.write(f"| パラメータ | 値 | 変更点 |\n")
        f.write(f"| --- | --- | --- |\n")
        f.write(f"| bb_dev | 1.5 | 標準偏差を小さくしてバンド幅を狭める |\n")
        f.write(f"| rsi_upper | 80 | RSIの閾値を上げて売りシグナルを増やす |\n")
        f.write(f"| rsi_lower | 20 | RSIの閾値を下げて買いシグナルを増やす |\n")
        f.write(f"| sl_pips | 5.0 | 損切り幅を小さくする |\n")
        f.write(f"| atr_sl_multiplier | 1.0 | ATRベースの損切り乗数を小さくする |\n")
        f.write(f"| trend_filter | False | トレンドフィルターを無効化 |\n")
        f.write(f"| vol_filter | False | ボラティリティフィルターを無効化 |\n")
        f.write(f"| time_filter | False | 時間フィルターを無効化 |\n")
        f.write(f"| timeframe_weights | {{'15min': 2.0, '1H': 1.0}} | 15分足の重みを増やし、4時間足を除外 |\n")
        f.write(f"| use_seasonal_filter | False | 季節性フィルターを無効化 |\n")
        f.write(f"| use_price_action | False | 価格アクションパターンを無効化 |\n")
        f.write(f"| consecutive_limit | 5 | 連続シグナル制限を大幅に緩和 |\n")
        
        f.write(f"\n## 結論\n\n")
        
        if win_rate >= 70 and profit_factor >= 2.0:
            f.write(f"2010年のデータでは、大幅に緩和されたパラメータにより、目標の勝率70%以上とプロフィットファクター2.0以上を達成しました。\n")
            f.write(f"これは、過去の市場環境では戦略が効果的に機能していたことを示しています。\n")
            f.write(f"2024-2025年の市場環境に適応するためには、これらのパラメータを基に、現在の市場環境に合わせた調整が必要です。\n")
        else:
            f.write(f"2010年のデータでも、大幅に緩和されたパラメータでは目標の勝率70%以上とプロフィットファクター2.0以上を達成できませんでした。\n")
            f.write(f"これは、戦略自体の見直しが必要であることを示唆しています。以下の点を検討してください：\n\n")
            f.write(f"1. 異なる指標の組み合わせの検討（例：MACD、ストキャスティクスなど）\n")
            f.write(f"2. エントリー・イグジット条件の根本的な見直し\n")
            f.write(f"3. 完全に異なる戦略アプローチの検討（例：トレンドフォロー型戦略）\n")
    
    logger.info(f"テスト完了: 結果は {output_dir}/reports/test_2010_simplified_results.md に保存されました")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
