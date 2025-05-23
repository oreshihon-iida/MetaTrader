import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from src.strategies.bollinger_rsi_enhanced_mt import BollingerRsiEnhancedMTStrategy
from src.data.data_processor_enhanced import DataProcessor
from src.backtest.custom_backtest_engine import CustomBacktestEngine
from src.utils.logger import Logger
from src.visualization.visualizer import Visualizer

log_dir = "results/balanced_strategy_all_years/logs"
chart_dir = "results/balanced_strategy_all_years/charts"
os.makedirs(log_dir, exist_ok=True)
os.makedirs(chart_dir, exist_ok=True)

logger = Logger(log_dir)
logger.log_info("バランス型戦略の全期間テスト開始")

rsi_upper = 75
rsi_lower = 25
bb_dev = 2.0
sl_pips = 10.0
tp_pips = 30.0
consecutive_limit = 2

yearly_results = []

data_dir = 'data/processed'
years = list(range(2000, 2026))  # 2000年から2025年まで
data_processor = DataProcessor(pd.DataFrame())

for year in years:
    logger.log_info(f"{year}年のテスト開始")
    
    df_15min = data_processor.load_processed_data('15min', year, data_dir)
    
    if df_15min.empty:
        logger.log_warning(f"{year}年の15分足データが見つかりません")
        yearly_results.append({
            '年': year,
            'トレード数': 0,
            '勝率': 0.0,
            '純利益': 0.0,
            'プロフィットファクター': 0.0
        })
        continue
    
    logger.log_info(f"{year}年の15分足データ読み込み完了: {len(df_15min)}行")
    
    strategy = BollingerRsiEnhancedMTStrategy(
        use_seasonal_filter=True,
        use_price_action=True,
        timeframe_weights={
            '15min': 1.0,
            '1H': 2.0,
            '4H': 3.0
        },
        rsi_upper=rsi_upper,
        rsi_lower=rsi_lower,
        bb_dev=bb_dev,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        consecutive_limit=consecutive_limit,
        volatility_filter=True
    )
    
    signals_df = strategy.generate_signals(df_15min, year, data_dir)
    
    backtest_engine = CustomBacktestEngine(
        data=signals_df,
        initial_balance=200000,
        lot_size=0.01,
        spread_pips=0.2,
        max_positions=1
    )
    
    results = backtest_engine.run()
    
    if not results.empty:
        results.to_csv(f"{log_dir}/trade_history_{year}.csv")
        
        total_trades = len(results)
        wins = len(results[results['損益(円)'] > 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = results[results['損益(円)'] > 0]['損益(円)'].sum()
        total_loss = abs(results[results['損益(円)'] < 0]['損益(円)'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        net_profit = total_profit - total_loss
        
        yearly_results.append({
            '年': year,
            'トレード数': total_trades,
            '勝率': win_rate,
            '純利益': net_profit,
            'プロフィットファクター': profit_factor
        })
        
        logger.log_info(f"{year}年のテスト結果:")
        logger.log_info(f"トレード数: {total_trades}")
        logger.log_info(f"勝率: {win_rate:.2f}%")
        logger.log_info(f"純利益: {net_profit:.2f}円")
        logger.log_info(f"プロフィットファクター: {profit_factor:.2f}")
        
        visualizer = Visualizer(f"{chart_dir}/{year}")
        visualizer.plot_equity_curve(results)
        visualizer.plot_drawdown(results)
        visualizer.plot_monthly_returns(results)
    else:
        logger.log_warning(f"{year}年の取引履歴がありません")
        yearly_results.append({
            '年': year,
            'トレード数': 0,
            '勝率': 0.0,
            '純利益': 0.0,
            'プロフィットファクター': 0.0
        })

yearly_df = pd.DataFrame(yearly_results)
yearly_df.to_csv(f"{log_dir}/yearly_performance.csv", index=False)

plt.figure(figsize=(14, 7))
plt.bar(yearly_df['年'], yearly_df['勝率'])
plt.title('年別勝率')
plt.xlabel('年')
plt.ylabel('勝率 (%)')
plt.grid(True)
plt.savefig(f"{chart_dir}/yearly_win_rate.png")

plt.figure(figsize=(14, 7))
plt.bar(yearly_df['年'], yearly_df['プロフィットファクター'])
plt.title('年別プロフィットファクター')
plt.xlabel('年')
plt.ylabel('プロフィットファクター')
plt.grid(True)
plt.savefig(f"{chart_dir}/yearly_profit_factor.png")

plt.figure(figsize=(14, 7))
plt.bar(yearly_df['年'], yearly_df['トレード数'])
plt.title('年別トレード数')
plt.xlabel('年')
plt.ylabel('トレード数')
plt.grid(True)
plt.savefig(f"{chart_dir}/yearly_trade_count.png")

with open(f"{log_dir}/all_years_summary.md", "w") as f:
    f.write("# バランス型戦略の全期間（2000-2025年）テスト結果\n\n")
    f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("## 戦略パラメータ\n\n")
    f.write("- 時間足: 15分足 + 1時間足 + 4時間足\n")
    f.write("- 時間足の重み付け: 15min: 1.0, 1H: 2.0, 4H: 3.0\n")
    f.write(f"- RSI上限: {rsi_upper}\n")
    f.write(f"- RSI下限: {rsi_lower}\n")
    f.write(f"- ボリンジャーバンド偏差: {bb_dev}\n")
    f.write(f"- ストップロス: {sl_pips} pips\n")
    f.write(f"- テイクプロフィット: {tp_pips} pips\n")
    f.write(f"- 連続シグナル制限: {consecutive_limit}\n")
    f.write("- 季節性フィルター: 有効\n")
    f.write("- 価格アクションパターン: 有効\n")
    f.write("- ボラティリティフィルター: 有効\n\n")
    
    f.write("## 年別パフォーマンス\n\n")
    f.write("| 年 | トレード数 | 勝率 (%) | 純利益 (円) | プロフィットファクター |\n")
    f.write("| - | - | - | - | - |\n")
    
    for _, row in yearly_df.iterrows():
        f.write(f"| {int(row['年'])} | {int(row['トレード数'])} | {row['勝率']:.2f} | {row['純利益']:.2f} | {row['プロフィットファクター']:.2f} |\n")
    
    valid_years = yearly_df[yearly_df['トレード数'] > 0]
    avg_trades = valid_years['トレード数'].mean()
    avg_win_rate = valid_years['勝率'].mean()
    avg_profit = valid_years['純利益'].mean()
    avg_pf = valid_years['プロフィットファクター'].mean()
    
    f.write(f"| 平均 | {avg_trades:.2f} | {avg_win_rate:.2f} | {avg_profit:.2f} | {avg_pf:.2f} |\n\n")
    
    f.write("## 結論\n\n")
    if avg_win_rate >= 70 and avg_pf >= 2.0:
        f.write("バランス型戦略は目標を達成しました。全期間で平均勝率70%以上、平均プロフィットファクター2.0以上を達成しています。\n")
    else:
        f.write("バランス型戦略は一部の目標を達成していません。\n")
        
        if avg_win_rate < 70:
            f.write("- 平均勝率が目標（70%）を下回っています。\n")
        
        if avg_pf < 2.0:
            f.write("- 平均プロフィットファクターが目標（2.0）を下回っています。\n")
    
    f.write("\n## 元の戦略との比較\n\n")
    f.write("| 指標 | 元の戦略 | バランス型戦略 |\n")
    f.write("| - | - | - |\n")
    f.write(f"| 平均勝率 | 71.08% | {avg_win_rate:.2f}% |\n")
    f.write(f"| 平均トレード数 | 16.77 | {avg_trades:.2f} |\n")
    f.write(f"| 平均純利益 | 19.73円 | {avg_profit:.2f}円 |\n")
    f.write(f"| 平均プロフィットファクター | 不明 | {avg_pf:.2f} |\n\n")
    
    f.write("## 今後の改善点\n\n")
    f.write("1. **パラメータの微調整**：\n")
    f.write("   - 年ごとの最適パラメータの分析\n")
    f.write("   - 市場環境に応じた動的パラメータ調整\n\n")
    
    f.write("2. **機械学習の導入**：\n")
    f.write("   - 特徴量エンジニアリングによる予測モデルの構築\n")
    f.write("   - 過去のパターンに基づく勝率予測\n\n")
    
    f.write("3. **複合指標の開発**：\n")
    f.write("   - 複数の指標を組み合わせた新しい指標の開発\n")
    f.write("   - 市場環境に応じた指標の動的切り替え\n\n")

logger.log_info("バランス型戦略の全期間テスト完了")
