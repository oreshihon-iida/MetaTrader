import pandas as pd
import numpy as np
import itertools
from typing import Dict, List, Tuple, Any, Callable
from ..backtest.backtest_engine import BacktestEngine
from ..utils.logger import Logger

class ParameterOptimizer:
    """
    戦略のパラメータを最適化するためのクラス
    """
    
    def __init__(self, data: pd.DataFrame, logger: Logger = None):
        """
        初期化
        
        Parameters
        ----------
        data : pd.DataFrame
            最適化に使用するデータ
        logger : Logger, optional
            ログ出力用のロガー
        """
        self.data = data
        self.logger = logger
        
    def grid_search(self, 
                   strategy_class: Any,
                   param_grid: Dict[str, List[Any]],
                   eval_metric: str = 'win_rate',
                   initial_balance: float = 200000,
                   lot_size: float = 0.01,
                   max_positions: int = 1,
                   spread_pips: float = 0.2) -> Tuple[Dict[str, Any], pd.DataFrame]:
        """
        グリッドサーチによるパラメータ最適化を実行する
        
        Parameters
        ----------
        strategy_class : Any
            最適化対象の戦略クラス
        param_grid : Dict[str, List[Any]]
            パラメータとその候補値のディクショナリ
        eval_metric : str, default 'win_rate'
            評価指標（'win_rate', 'profit_factor', 'total_profit'のいずれか）
        initial_balance : float, default 200000
            初期資金
        lot_size : float, default 0.01
            1トレードあたりのロットサイズ
        max_positions : int, default 1
            同時に保有できる最大ポジション数
        spread_pips : float, default 0.2
            スプレッド（pips）
            
        Returns
        -------
        Tuple[Dict[str, Any], pd.DataFrame]
            最適なパラメータと、すべての組み合わせの結果
        """
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        results = []
        
        if self.logger:
            self.logger.log_info(f"パラメータ最適化開始: {len(combinations)}通りの組み合わせ")
        
        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            
            strategy = strategy_class(**params)
            
            signals_df = strategy.generate_signals(self.data.copy())
            
            backtest_engine = BacktestEngine(
                data=signals_df,
                initial_balance=initial_balance,
                lot_size=lot_size,
                max_positions=max_positions,
                spread_pips=spread_pips
            )
            
            trade_history = backtest_engine.run(['bollinger_rsi_enhanced'])
            
            if len(trade_history) > 0:
                wins = sum(trade_history['損益(円)'] > 0)
                win_rate = wins / len(trade_history) * 100
                
                winning_trades = trade_history[trade_history['損益(円)'] > 0]['損益(円)'].sum()
                losing_trades = abs(trade_history[trade_history['損益(円)'] < 0]['損益(円)'].sum())
                profit_factor = winning_trades / losing_trades if losing_trades > 0 else float('inf')
                
                total_profit = trade_history['損益(円)'].sum()
                
                result = {
                    'combination_id': i,
                    'trades': len(trade_history),
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'total_profit': total_profit,
                    **params
                }
                
                results.append(result)
                
                if self.logger and (i+1) % 10 == 0:
                    self.logger.log_info(f"進捗: {i+1}/{len(combinations)} 組み合わせ完了")
            
        results_df = pd.DataFrame(results)
        
        if len(results_df) > 0:
            if eval_metric == 'win_rate':
                best_idx = results_df['win_rate'].idxmax()
            elif eval_metric == 'profit_factor':
                best_idx = results_df['profit_factor'].idxmax()
            else:  # eval_metric == 'total_profit'
                best_idx = results_df['total_profit'].idxmax()
            
            best_params = {k: results_df.loc[best_idx, k] for k in param_names}
            
            if self.logger:
                self.logger.log_info(f"最適化完了。最適なパラメータ: {best_params}")
                self.logger.log_info(f"最適パラメータの結果: トレード数={results_df.loc[best_idx, 'trades']}, "
                                    f"勝率={results_df.loc[best_idx, 'win_rate']:.2f}%, "
                                    f"プロフィットファクター={results_df.loc[best_idx, 'profit_factor']:.2f}, "
                                    f"総利益={results_df.loc[best_idx, 'total_profit']:.0f}円")
        else:
            best_params = {}
            if self.logger:
                self.logger.log_warning("最適化結果なし。有効なトレードが生成されませんでした。")
        
        return best_params, results_df
