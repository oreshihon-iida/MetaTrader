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
        logging.FileHandler('logs/test_simplified_2024_2025_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

output_dir = 'results/test_simplified_2024_2025_optimized'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/charts', exist_ok=True)
os.makedirs(f'{output_dir}/reports', exist_ok=True)

test_years = [2024, 2025]

optimized_params = {
    'bb_window': 20,
    'bb_dev': 1.5,        # 標準偏差を小さくしてバンド幅を狭める
    'rsi_window': 14,
    'rsi_upper': 80,      # RSIの閾値を上げて売りシグナルを増やす
    'rsi_lower': 20,      # RSIの閾値を下げて買いシグナルを増やす
    'sl_pips': 5.0,       # 損切り幅を小さくする
    'tp_pips': 10.0,      # 利確幅はそのまま
    'atr_window': 14,
    'atr_sl_multiplier': 1.0,  # ATRベースの損切り乗数を小さくする
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

logger.info(f"2024-2025年データでの最適化されたパラメータによるテスト開始")

all_results = []
total_trades = 0
total_wins = 0
total_profit = 0.0

try:
    for test_year in test_years:
        logger.info(f"テスト年: {test_year}")
        
        data_processor = DataProcessor(pd.DataFrame())
        df_15min = data_processor.load_processed_data('15min', test_year)
        
        if df_15min.empty:
            logger.error(f"データが見つかりません: {test_year}年")
            continue
        
        logger.info(f"データ読み込み成功: {len(df_15min)}行")
        
        strategy = BollingerRsiEnhancedMTStrategy(**optimized_params)
        
        logger.info("シグナル生成開始")
        signals_df = strategy.generate_signals(df_15min, test_year)
        
        logger.info(f"シグナル生成完了: {len(signals_df)}行")
        signal_count = (signals_df['signal'] != 0).sum()
        logger.info(f"シグナル数: {signal_count}")
        
        if signal_count == 0:
            logger.warning(f"{test_year}年のシグナルが生成されませんでした。パラメータを調整してください。")
            continue
        
        logger.info("バックテスト実行開始")
        backtest_engine = CustomBacktestEngine(signals_df, spread_pips=0.03)
        backtest_results = backtest_engine.run()
        
        trades = backtest_results['trades']
        wins = backtest_results['wins']
        losses = backtest_results['losses']
        win_rate = backtest_results['win_rate']
        profit_factor = backtest_results['profit_factor']
        net_profit = backtest_results['net_profit']
        
        logger.info(f"{test_year}年のバックテスト結果:")
        logger.info(f"総トレード数: {trades}")
        logger.info(f"勝率: {win_rate:.2f}%")
        logger.info(f"プロフィットファクター: {profit_factor:.2f}")
        logger.info(f"純利益: {net_profit:.2f}")
        
        all_results.append({
            'year': test_year,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_profit': net_profit
        })
        
        total_trades += trades
        total_wins += wins
        total_profit += net_profit
        
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
    
    if total_trades > 0:
        total_win_rate = (total_wins / total_trades) * 100
        logger.info(f"2024-2025年の総合結果:")
        logger.info(f"総トレード数: {total_trades}")
        logger.info(f"総勝率: {total_win_rate:.2f}%")
        logger.info(f"総純利益: {total_profit:.2f}")
        
        with open(f'{output_dir}/reports/test_simplified_2024_2025_optimized_results.md', 'w') as f:
            f.write(f"# 2024-2025年データでの最適化されたパラメータによるテスト結果\n\n")
            f.write(f"## 概要\n\n")
            f.write(f"2010年のデータで良好な結果を示したパラメータを使用して、2024-2025年のデータでボリンジャーバンド＋RSI戦略のバックテストを実行した結果です。\n\n")
            f.write(f"## 総合結果\n\n")
            f.write(f"| 項目 | 値 |\n")
            f.write(f"| --- | --- |\n")
            f.write(f"| 総トレード数 | {total_trades} |\n")
            f.write(f"| 勝率 | {total_win_rate:.2f}% |\n")
            f.write(f"| 純利益 | {total_profit:.2f} |\n\n")
            
            f.write(f"## 年別結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 (%) | プロフィットファクター | 純利益 |\n")
            f.write(f"| --- | --- | --- | --- | --- |\n")
            
            for result in all_results:
                f.write(f"| {result['year']} | {result['trades']} | {result['win_rate']:.2f} | {result['profit_factor']:.2f} | {result['net_profit']:.2f} |\n")
            
            f.write(f"\n## 最適化されたパラメータ\n\n")
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
            
            if total_win_rate >= 70 and any(r['profit_factor'] >= 2.0 for r in all_results):
                f.write(f"2024-2025年のデータでも、2010年で良好な結果を示したパラメータにより、目標の勝率70%以上とプロフィットファクター2.0以上を達成しました。\n")
                f.write(f"これは、過去の市場環境で効果的だったパラメータが現在の市場環境でも有効であることを示しています。\n")
            else:
                f.write(f"2024-2025年のデータでは、2010年で良好な結果を示したパラメータでも目標の勝率70%以上とプロフィットファクター2.0以上を達成できませんでした。\n")
                f.write(f"これは、市場環境の変化により、過去に効果的だったパラメータが現在の市場環境では同様の効果を発揮しないことを示しています。\n\n")
                f.write(f"以下の点を検討してください：\n\n")
                f.write(f"1. 現在の市場環境に特化したパラメータの最適化\n")
                f.write(f"2. 複合指標の導入による信号品質の向上\n")
                f.write(f"3. 高度なリスク管理システムの実装\n")
                f.write(f"4. 市場環境の分類と環境別の最適パラメータの適用\n")
        
        logger.info(f"テスト完了: 結果は {output_dir}/reports/test_simplified_2024_2025_optimized_results.md に保存されました")
    else:
        logger.warning("トレードが生成されませんでした")

except Exception as e:
    logger.error(f"エラーが発生しました: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
