#!/usr/bin/env python3
"""
Strategy Comparison Runner - ASCII only for encoding safety
"""

import pandas as pd
import numpy as np
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_test_runner import AutoTestRunner
from src.strategies.profit_target_strategy_v2 import ProfitTargetStrategyV2

class SimplifiedMacroStrategy:
    """Simplified version of macro long-term strategy"""
    
    def __init__(self):
        self.sl_pips = 50.0
        self.tp_pips = 150.0  # 3:1 R/R ratio
        
    def generate_signals(self, data):
        """Generate long-term signals"""
        signals_df = data.copy()
        signals_df['signal'] = 0.0
        signals_df['signal_quality'] = 0.8
        signals_df['sl_pips'] = self.sl_pips  
        signals_df['tp_pips'] = self.tp_pips
        signals_df['strategy'] = 'macro_long_term'
        
        close_col = 'Close' if 'Close' in data.columns else 'close'
        
        # Technical indicators
        signals_df['bb_middle'] = data[close_col].rolling(20).mean()
        bb_std = data[close_col].rolling(20).std()
        signals_df['bb_upper'] = signals_df['bb_middle'] + 2.0 * bb_std
        signals_df['bb_lower'] = signals_df['bb_middle'] - 2.0 * bb_std
        
        # RSI
        delta = data[close_col].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        signals_df['rsi'] = 100 - (100 / (1 + rs))
        
        # Long-term moving averages
        signals_df['sma_50'] = data[close_col].rolling(50).mean()
        signals_df['sma_200'] = data[close_col].rolling(200).mean()
        
        # Generate signals (low frequency for long-term strategy)
        for i in range(200, len(data), 240):  # Every 10 days (240 = 10*24 15min bars)
            if i >= len(data):
                break
                
            current_price = data[close_col].iloc[i]
            rsi = signals_df['rsi'].iloc[i]
            
            if pd.isna(rsi):
                continue
            
            # RSI signals
            rsi_signal = 0
            if rsi < 30:
                rsi_signal = 1
            elif rsi > 70:
                rsi_signal = -1
            
            # Bollinger Band signals
            bb_signal = 0
            if current_price < signals_df['bb_lower'].iloc[i]:
                bb_signal = 1
            elif current_price > signals_df['bb_upper'].iloc[i]:
                bb_signal = -1
            
            # Moving average trend
            ma_signal = 0
            if (pd.notna(signals_df['sma_50'].iloc[i]) and 
                pd.notna(signals_df['sma_200'].iloc[i])):
                if signals_df['sma_50'].iloc[i] > signals_df['sma_200'].iloc[i]:
                    ma_signal = 0.5
                else:
                    ma_signal = -0.5
            
            # Combined signal
            total_signal = (rsi_signal * 1.0 + bb_signal * 0.8 + ma_signal * 1.5) / 3.3
            
            if total_signal > 0.3:
                signals_df.loc[signals_df.index[i], 'signal'] = 1.0
            elif total_signal < -0.3:
                signals_df.loc[signals_df.index[i], 'signal'] = -1.0
        
        return signals_df

def macro_wrapper(data):
    """Macro strategy wrapper"""
    strategy = SimplifiedMacroStrategy()
    return strategy.generate_signals(data)

def v2_wrapper(data):
    """V2 strategy wrapper"""
    strategy = ProfitTargetStrategyV2(
        initial_balance=3000000,
        monthly_profit_target=200000,
        scaling_phase='growth'
    )
    
    result_df = data.copy()
    result_df['signal'] = 0.0
    result_df['signal_quality'] = 0.0
    result_df['sl_pips'] = 0.0
    result_df['tp_pips'] = 0.0
    result_df['strategy'] = 'V2'
    
    # Generate V2 signals
    for i in range(200, len(data)):
        if i % 5 == 0:  # Every 5 bars
            window_data = data.iloc[:i+1]
            current_time = window_data.index[-1]
            
            if strategy.is_good_trading_time(current_time):
                trend = strategy.check_trend_alignment(window_data)
                if trend != 0:
                    signal = strategy.generate_core_signal(window_data)
                    if signal != 0:
                        tp_pips, sl_pips = strategy.calculate_dynamic_tp_sl(window_data)
                        
                        result_df.loc[result_df.index[i], 'signal'] = signal
                        result_df.loc[result_df.index[i], 'signal_quality'] = 0.8
                        result_df.loc[result_df.index[i], 'sl_pips'] = sl_pips
                        result_df.loc[result_df.index[i], 'tp_pips'] = tp_pips
    
    return result_df

def run_comparison():
    """Run the strategy comparison"""
    print("\n" + "=" * 50)
    print("STRATEGY COMPARISON TEST")
    print("Macro Long-term vs V2 Strategy")
    print("=" * 50)
    
    auto_tester = AutoTestRunner()
    
    print("\n[1] Testing Macro Long-term Strategy...")
    print("Characteristics: SL 50pips, TP 150pips, Low frequency")
    
    try:
        macro_executor, macro_stats = auto_tester.run_strategy_test(
            macro_wrapper, "SimplifiedMacroLongTerm"
        )
        
        print("\nMacro Strategy Results:")
        print(f"  Final Balance: {macro_stats['final_balance']:,.0f} JPY")
        print(f"  Total P&L: {macro_stats['total_pnl']:,.0f} JPY ({macro_stats['total_return']:.2f}%)")
        print(f"  Trades: {macro_stats['total_trades']}")
        print(f"  Win Rate: {macro_stats['win_rate']:.2f}%")
        print(f"  Profit Factor: {macro_stats['profit_factor']:.2f}")
        print(f"  Max DD: {macro_stats['max_drawdown']:.2f}%")
        
        macro_monthly = macro_executor.get_monthly_performance()
        if not macro_monthly.empty:
            avg_monthly = macro_monthly['profit'].mean()
            print(f"  Monthly Avg: {avg_monthly:,.0f} JPY")
            
    except Exception as e:
        print(f"ERROR in Macro strategy test: {e}")
        macro_executor = None
        macro_stats = None
    
    print("\n[2] Testing V2 Strategy...")
    print("Characteristics: Dynamic TP/SL, Time/Trend filters")
    
    try:
        v2_executor, v2_stats = auto_tester.run_strategy_test(
            v2_wrapper, "V2_Comparison"
        )
        
        print("\nV2 Strategy Results:")
        print(f"  Final Balance: {v2_stats['final_balance']:,.0f} JPY")
        print(f"  Total P&L: {v2_stats['total_pnl']:,.0f} JPY ({v2_stats['total_return']:.2f}%)")
        print(f"  Trades: {v2_stats['total_trades']}")
        print(f"  Win Rate: {v2_stats['win_rate']:.2f}%")
        print(f"  Profit Factor: {v2_stats['profit_factor']:.2f}")
        print(f"  Max DD: {v2_stats['max_drawdown']:.2f}%")
        
        v2_monthly = v2_executor.get_monthly_performance()
        if not v2_monthly.empty:
            avg_monthly = v2_monthly['profit'].mean()
            print(f"  Monthly Avg: {avg_monthly:,.0f} JPY")
            
    except Exception as e:
        print(f"ERROR in V2 strategy test: {e}")
        v2_executor = None
        v2_stats = None
    
    # Comparison
    if macro_stats and v2_stats:
        print("\n" + "=" * 50)
        print("COMPARISON SUMMARY")
        print("=" * 50)
        
        print(f"\nProfitability:")
        print(f"  Macro: {macro_stats['total_pnl']:,.0f} JPY ({macro_stats['total_return']:.2f}%)")
        print(f"  V2:    {v2_stats['total_pnl']:,.0f} JPY ({v2_stats['total_return']:.2f}%)")
        
        print(f"\nStability:")
        print(f"  Macro DD: {macro_stats['max_drawdown']:.2f}%")
        print(f"  V2 DD:    {v2_stats['max_drawdown']:.2f}%")
        
        print(f"\nEfficiency:")
        print(f"  Macro: {macro_stats['total_trades']} trades, {macro_stats['win_rate']:.1f}% win rate")
        print(f"  V2:    {v2_stats['total_trades']} trades, {v2_stats['win_rate']:.1f}% win rate")
        
        # Winner determination
        macro_score = 0
        v2_score = 0
        
        if macro_stats['total_pnl'] > v2_stats['total_pnl']:
            macro_score += 1
            print("\nProfitability Winner: Macro Strategy")
        else:
            v2_score += 1
            print("\nProfitability Winner: V2 Strategy")
            
        if macro_stats['max_drawdown'] < v2_stats['max_drawdown']:
            macro_score += 1
            print("Stability Winner: Macro Strategy")
        else:
            v2_score += 1
            print("Stability Winner: V2 Strategy")
            
        if macro_stats['win_rate'] > v2_stats['win_rate']:
            macro_score += 1
            print("Win Rate Winner: Macro Strategy")
        else:
            v2_score += 1
            print("Win Rate Winner: V2 Strategy")
        
        print(f"\nOVERALL SCORE: Macro {macro_score} - {v2_score} V2")
        
        if macro_score > v2_score:
            print("RECOMMENDATION: Adopt Macro Long-term Strategy as primary")
        elif v2_score > macro_score:
            print("RECOMMENDATION: Keep V2 Strategy as primary")
        else:
            print("RECOMMENDATION: Consider hybrid approach")
        
        # Save results
        save_results(macro_stats, v2_stats)
    
    return macro_executor, macro_stats, v2_executor, v2_stats

def save_results(macro_stats, v2_stats):
    """Save comparison results"""
    output_dir = "results/strategy_comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        'comparison_date': datetime.now().isoformat(),
        'macro_strategy': macro_stats,
        'v2_strategy': v2_stats
    }
    
    with open(f'{output_dir}/comparison_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Simple report
    report = f"""# Strategy Comparison Results

Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Results Summary

### Macro Long-term Strategy
- Final Balance: {macro_stats['final_balance']:,.0f} JPY
- Total P&L: {macro_stats['total_pnl']:,.0f} JPY ({macro_stats['total_return']:.2f}%)
- Trades: {macro_stats['total_trades']}
- Win Rate: {macro_stats['win_rate']:.2f}%
- Profit Factor: {macro_stats['profit_factor']:.2f}
- Max Drawdown: {macro_stats['max_drawdown']:.2f}%

### V2 Strategy
- Final Balance: {v2_stats['final_balance']:,.0f} JPY
- Total P&L: {v2_stats['total_pnl']:,.0f} JPY ({v2_stats['total_return']:.2f}%)
- Trades: {v2_stats['total_trades']}
- Win Rate: {v2_stats['win_rate']:.2f}%
- Profit Factor: {v2_stats['profit_factor']:.2f}
- Max Drawdown: {v2_stats['max_drawdown']:.2f}%

Generated with Claude Code
"""
    
    with open(f'{output_dir}/comparison_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nResults saved to: {output_dir}/")

if __name__ == "__main__":
    print("Starting Strategy Comparison System...")
    
    run_comparison()
    
    print("\nComparison completed successfully!")