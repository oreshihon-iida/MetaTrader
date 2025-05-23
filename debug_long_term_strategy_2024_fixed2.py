import os
import pandas as pd
import numpy as np
from datetime import datetime
from src.strategies.macro_based_long_term_strategy import MacroBasedLongTermStrategy
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.data.multi_timeframe_data_manager import MultiTimeframeDataManager
from src.utils.logger import Logger

output_dir = "results/macro_long_term"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/charts", exist_ok=True)

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = Logger(log_dir)

logger.log_info("長期戦略のデバッグテスト開始（2024年のみ）")

strategy = MacroBasedLongTermStrategy(
    bb_window=20,
    bb_dev=2.0,
    rsi_window=14,
    rsi_upper=60,  # RSI上限閾値を70から60に下げて取引数を増加
    rsi_lower=40,  # RSI下限閾値を30から40に上げて取引数を増加
    sl_pips=50.0,
    tp_pips=150.0,
    timeframe_weights={'1D': 3.0, '1W': 2.0, '1M': 1.0, '4H': 0.5},
    quality_threshold=0.1,  # 品質閾値を下げて取引数を増加
    use_macro_analysis=True,
    macro_weight=2.0
)

data_manager = MultiTimeframeDataManager(base_timeframe="1D")

test_year = 2024

logger.log_info(f"{test_year}年のデータを処理中...")

available_timeframes = []
for tf in ['4H', '1D', '1W', '1M']:
    tf_dir = f"data/processed/{tf}/{test_year}"
    tf_file = f"{tf_dir}/USDJPY_{tf}_{test_year}.csv"
    if os.path.exists(tf_file):
        available_timeframes.append(tf)
        logger.log_info(f"{tf}データが利用可能です: {test_year}年")

if not available_timeframes:
    logger.log_error(f"{test_year}年のデータが見つかりません")
    exit(1)
    
if '1D' in available_timeframes:
    data_manager.base_timeframe = "1D"
elif '4H' in available_timeframes:
    data_manager.base_timeframe = "4H"
else:
    data_manager.base_timeframe = available_timeframes[0]

logger.log_info(f"基準時間足を {data_manager.base_timeframe} に設定しました")

data_dict = data_manager.load_data(available_timeframes, [test_year])

if not data_dict:
    logger.log_error(f"{test_year}年のデータが見つかりません")
    exit(1)

adjusted_weights = {}
for tf in available_timeframes:
    if tf in strategy.timeframe_weights:
        adjusted_weights[tf] = strategy.timeframe_weights[tf]

if adjusted_weights:
    strategy.timeframe_weights = adjusted_weights
    logger.log_info(f"調整された時間足の重み: {strategy.timeframe_weights}")

data_dict = data_manager.calculate_indicators(data_dict)

data_dict = data_manager.synchronize_timeframes(data_dict)

logger.log_info("シグナル生成開始")
try:
    signals_df = strategy.generate_signals(data_dict)
    
    if signals_df.empty:
        logger.log_warning("シグナルが生成されませんでした")
        exit(1)
        
    logger.log_info(f"シグナル生成完了: {len(signals_df)}行")
    logger.log_info(f"シグナルのカラム: {signals_df.columns.tolist()}")
    logger.log_info(f"最初のシグナル: {signals_df.iloc[0].to_dict() if len(signals_df) > 0 else 'なし'}")
    
    required_columns = ['Open', 'High', 'Low', 'Close']
    for col in required_columns:
        if col not in signals_df.columns:
            logger.log_info(f"{col}カラムが見つからないため、追加します")
            values = []
            for idx, row in signals_df.iterrows():
                if idx in data_dict['1D'].index:
                    values.append(data_dict['1D'].loc[idx, col])
                else:
                    closest_date = min(data_dict['1D'].index, key=lambda x: abs((x - idx).total_seconds()))
                    values.append(data_dict['1D'].loc[closest_date, col])
                    
            signals_df[col] = values
    
    logger.log_info("バックテスト実行中...")
    backtest_engine = CustomBacktestEngine(signals_df, initial_balance=2000000)
    backtest_results = backtest_engine.run()
    
    trades = backtest_results['trades']
    if not trades.empty:
        wins = trades[trades['損益(円)'] > 0]
        losses = trades[trades['損益(円)'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100 if len(trades) > 0 else 0
        profit_factor = abs(wins['損益(円)'].sum() / losses['損益(円)'].sum()) if losses['損益(円)'].sum() != 0 else float('inf')
        
        logger.log_info(f"バックテスト結果: {len(trades)}トレード, 勝率 {win_rate:.2f}%, プロフィットファクター {profit_factor:.2f}")
        logger.log_info(f"純利益: {trades['損益(円)'].sum():.2f}円")
        
        annual_return = (trades['損益(円)'].sum() / 2000000) * 100
        logger.log_info(f"年利: {annual_return:.2f}%")
        
        report_path = "document/strategy_optimization/long_term_strategy_results_2024.md"
        os.makedirs("document/strategy_optimization", exist_ok=True)
        
        with open(report_path, "w") as f:
            f.write(f"# 長期戦略テスト結果 (2024)\n\n")
            f.write(f"## テスト環境\n")
            f.write(f"- 戦略: マクロ経済要因に基づく長期戦略 (MacroBasedLongTermStrategy)\n")
            f.write(f"- 時間足: {', '.join(available_timeframes)}\n")
            f.write(f"- 初期資金: 2,000,000円\n")
            f.write(f"- 最大同時ポジション数: 3\n")
            f.write(f"- テイクプロフィット: 150 pips\n")
            f.write(f"- ストップロス: 50 pips (リスク:リワード = 1:3)\n")
            f.write(f"- 品質閾値: 0.1（低く設定して取引数を増加）\n")
            f.write(f"- 強制シグナル: 3日ごとに生成\n\n")
            
            f.write(f"## テスト結果\n\n")
            f.write(f"| 年 | トレード数 | 勝率 | プロフィットファクター | 純利益 | 年利 |\n")
            f.write(f"|------|----------|------|-------------------|--------|------|\n")
            f.write(f"| 2024 | {len(trades)} | {win_rate:.2f}% | {profit_factor:.2f} | {trades['損益(円)'].sum():.2f}円 | {annual_return:.2f}% |\n\n")
            
            f.write(f"## 分析\n\n")
            f.write(f"長期戦略の結果分析：\n")
            f.write(f"- 総取引数: {len(trades)}\n")
            f.write(f"- 勝率: {win_rate:.2f}%\n")
            f.write(f"- プロフィットファクター: {profit_factor:.2f}\n")
            f.write(f"- 純利益: {trades['損益(円)'].sum():.2f}円\n")
            f.write(f"- 年利: {annual_return:.2f}%\n\n")
            
            f.write(f"## リスク:リワード比と損益分岐点\n\n")
            f.write(f"- リスク:リワード比: 1:3 (SL 50pips, TP 150pips)\n")
            f.write(f"- 損益分岐点勝率: 25%（リスク:リワード比が1:3の場合）\n")
            f.write(f"- 目標勝率: 40%以上\n")
            f.write(f"- 現在の勝率: {win_rate:.2f}%\n")
            f.write(f"- 損益分岐点からの差: {win_rate - 25:.2f}%\n\n")
            
            f.write(f"## 次のステップ\n\n")
            f.write(f"1. マクロ経済指標の自動更新機能の実装\n")
            f.write(f"2. 市場レジームに応じたパラメータの動的調整\n")
            f.write(f"3. 複数通貨ペアへの拡張によるリスク分散\n")
            f.write(f"4. 季節性・周期性分析の統合\n")
            
        logger.log_info(f"結果レポートを {report_path} に保存しました")
        
    else:
        logger.log_warning("取引が生成されませんでした")
except Exception as e:
    logger.log_error(f"バックテスト中にエラーが発生しました: {e}")
    import traceback
    logger.log_error(traceback.format_exc())

logger.log_info("長期戦略のデバッグテスト完了")
