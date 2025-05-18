import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from ..data.data_processor_enhanced import DataProcessor
from .short_term_bollinger_rsi_strategy import ShortTermBollingerRsiStrategy
from .long_term_bollinger_rsi_strategy import LongTermBollingerRsiStrategy

class EnhancedDualStrategyManager:
    """
    拡張デュアル戦略マネージャー
    
    短期戦略と長期戦略を組み合わせたデュアル戦略マネージャー
    同時ポジション数5に対応し、勝率に応じたロットサイズ調整機能を持つ
    """
    
    def __init__(self, 
                short_term_strategy_params: Dict = None,
                long_term_strategy_params: Dict = None,
                max_short_term_positions: int = 3,
                max_long_term_positions: int = 2,
                short_term_capital_ratio: float = 0.4,
                long_term_capital_ratio: float = 0.6):
        """
        初期化
        
        Parameters
        ----------
        short_term_strategy_params : Dict, default None
            短期戦略のパラメータ
        long_term_strategy_params : Dict, default None
            長期戦略のパラメータ
        max_short_term_positions : int, default 3
            短期戦略の最大ポジション数
        max_long_term_positions : int, default 2
            長期戦略の最大ポジション数
        short_term_capital_ratio : float, default 0.4
            短期戦略に割り当てる資金の割合
        long_term_capital_ratio : float, default 0.6
            長期戦略に割り当てる資金の割合
        """
        self.short_term_strategy = ShortTermBollingerRsiStrategy(**(short_term_strategy_params or {}))
        self.long_term_strategy = LongTermBollingerRsiStrategy(**(long_term_strategy_params or {}))
        
        self.max_short_term_positions = max_short_term_positions
        self.max_long_term_positions = max_long_term_positions
        
        self.short_term_capital_ratio = short_term_capital_ratio
        self.long_term_capital_ratio = long_term_capital_ratio
        
        self.name = "拡張デュアル戦略マネージャー"
    
    def generate_signals(self, df_15min: pd.DataFrame, df_1h: pd.DataFrame, year: int, 
                       processed_dir: str = 'data/processed') -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        短期戦略と長期戦略のシグナルを生成する
        
        Parameters
        ----------
        df_15min : pd.DataFrame
            15分足のデータ
        df_1h : pd.DataFrame
            1時間足のデータ
        year : int
            対象年
        processed_dir : str, default 'data/processed'
            処理済みデータのディレクトリ
            
        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame]
            (短期戦略のシグナル, 長期戦略のシグナル)
        """
        short_term_signals = self.short_term_strategy.generate_signals(df_15min, year, processed_dir)
        
        long_term_signals = self.long_term_strategy.generate_signals(df_1h, year, processed_dir)
        
        short_term_signals['position_size'] = np.where(
            short_term_signals['signal'] != 0, 
            0.01 * self.short_term_capital_ratio, 
            np.nan
        )
        
        long_term_signals['position_size'] = np.where(
            long_term_signals['signal'] != 0, 
            0.01 * self.long_term_capital_ratio, 
            np.nan
        )
        
        return short_term_signals, long_term_signals
