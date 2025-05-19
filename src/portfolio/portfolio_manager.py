import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from src.strategies.base_strategy import BaseStrategy
from src.utils.logger import Logger

class PortfolioManager:
    """
    複数の取引戦略を組み合わせたポートフォリオ管理クラス
    
    特徴:
    - 長期・中期・短期戦略の組み合わせ
    - リスクパリティアプローチによる資金配分
    - 戦略間の相関を考慮した最適化
    - 総合リスク管理
    """
    
    def __init__(self, strategies: Dict[str, Dict[str, Any]], initial_balance: float = 2000000.0):
        """
        初期化
        
        Parameters
        ----------
        strategies : Dict[str, Dict[str, Any]]
            戦略名と設定を格納した辞書
            {
                "strategy_name": {
                    "strategy": BaseStrategy,
                    "allocation": float,  # 資金配分比率（0.0-1.0）
                    "max_positions": int,  # 最大同時ポジション数
                    "volatility": float,   # ボラティリティ（標準偏差）
                    "max_drawdown": float  # 最大ドローダウン
                }
            }
        initial_balance : float
            初期口座残高
        """
        self.strategies = strategies
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.logger = Logger()
        
        self._calculate_allocations()
        
        self.strategy_performance = {name: {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "max_drawdown": 0.0
        } for name in strategies.keys()}
        
        self.portfolio_performance = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "max_drawdown": 0.0,
            "correlation": {}
        }
    
    def _calculate_allocations(self):
        """
        戦略ごとの資金配分を計算（リスクパリティアプローチ）
        """
        total_allocation = sum(s["allocation"] for s in self.strategies.values())
        
        if total_allocation <= 0:
            self.logger.log_error("総資金配分が0以下です")
            return
            
        if total_allocation != 1.0:
            for name, strategy_info in self.strategies.items():
                strategy_info["allocation"] = strategy_info["allocation"] / total_allocation
                self.logger.log_info(f"{name}の資金配分を{strategy_info['allocation']:.2f}に調整しました")
        
        if all("volatility" in s for s in self.strategies.values()):
            inv_volatilities = {name: 1.0 / max(0.001, s["volatility"]) for name, s in self.strategies.items()}
            
            total_inv_vol = sum(inv_volatilities.values())
            
            risk_parity_allocations = {name: inv_vol / total_inv_vol for name, inv_vol in inv_volatilities.items()}
            
            for name, strategy_info in self.strategies.items():
                current_allocation = strategy_info["allocation"]
                risk_parity_allocation = risk_parity_allocations[name]
                
                strategy_info["allocation"] = 0.7 * current_allocation + 0.3 * risk_parity_allocation
                self.logger.log_info(f"{name}の資金配分をリスクパリティに基づき{strategy_info['allocation']:.2f}に調整しました")
        
        for name, strategy_info in self.strategies.items():
            strategy_info["balance"] = self.initial_balance * strategy_info["allocation"]
            self.logger.log_info(f"{name}の初期資金: {strategy_info['balance']:.2f}円")
    
    def generate_portfolio_signals(self, data_dict: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, pd.DataFrame]:
        """
        ポートフォリオ全体のシグナルを生成
        
        Parameters
        ----------
        data_dict : Dict[str, Dict[str, pd.DataFrame]]
            戦略名ごとの時間足データ辞書
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            戦略名ごとのシグナルデータフレーム
        """
        signals = {}
        
        for name, strategy_info in self.strategies.items():
            strategy = strategy_info["strategy"]
            
            if name in data_dict:
                try:
                    signals_df = strategy.generate_signals(data_dict[name])
                    signals[name] = signals_df
                    self.logger.log_info(f"{name}のシグナル生成完了: {len(signals_df)}行")
                except Exception as e:
                    self.logger.log_error(f"{name}のシグナル生成中にエラーが発生しました: {e}")
            else:
                self.logger.log_warning(f"{name}のデータが見つかりません")
        
        return signals
    
    def calculate_position_sizes(self, signals: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        ポートフォリオ全体のポジションサイズを計算
        
        Parameters
        ----------
        signals : Dict[str, pd.DataFrame]
            戦略名ごとのシグナルデータフレーム
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            ポジションサイズが追加されたデータフレーム
        """
        for name, signals_df in signals.items():
            if name in self.strategies:
                strategy = self.strategies[name]["strategy"]
                balance = self.strategies[name]["balance"]
                
                signals_df['position_size'] = 0.0
                
                for i in range(len(signals_df)):
                    signal = signals_df['signal'].iloc[i]
                    if signal != 0:
                        position_size = strategy.calculate_position_size(signal, balance)
                        signals_df.loc[signals_df.index[i], 'position_size'] = position_size
        
        return signals
    
    def calculate_correlation(self, signals: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        戦略間のシグナル相関を計算
        
        Parameters
        ----------
        signals : Dict[str, pd.DataFrame]
            戦略名ごとのシグナルデータフレーム
            
        Returns
        -------
        Dict[str, Dict[str, float]]
            戦略間の相関係数を格納した辞書
        """
        correlation = {}
        strategy_names = list(signals.keys())
        
        for i, name1 in enumerate(strategy_names):
            correlation[name1] = {}
            
            for name2 in strategy_names[i:]:
                if name1 == name2:
                    correlation[name1][name2] = 1.0
                    continue
                    
                df1 = signals[name1]
                df2 = signals[name2]
                
                if isinstance(df1.index, pd.DatetimeIndex) and isinstance(df2.index, pd.DatetimeIndex):
                    common_dates = df1.index.intersection(df2.index)
                    
                    if not common_dates.empty:
                        signals1 = df1.loc[common_dates, 'signal']
                        signals2 = df2.loc[common_dates, 'signal']
                        
                        corr = signals1.corr(signals2)
                        correlation[name1][name2] = corr
                        
                        if name2 not in correlation:
                            correlation[name2] = {}
                        correlation[name2][name1] = corr
                
        return correlation
    
    def rebalance_portfolio(self, performance: Dict[str, Dict[str, Any]]):
        """
        パフォーマンスに基づいてポートフォリオをリバランス
        
        Parameters
        ----------
        performance : Dict[str, Dict[str, Any]]
            戦略ごとのパフォーマンス指標
        """
        total_profit = sum(p["profit"] for p in performance.values())
        
        if total_profit <= 0:
            self.logger.log_warning("総利益が0以下のため、リバランスをスキップします")
            return
            
        for name, perf in performance.items():
            if "equity_curve" in perf and not perf["equity_curve"].empty:
                equity = perf["equity_curve"]["equity"]
                daily_returns = equity.pct_change().dropna()
                volatility = daily_returns.std()
                
                self.strategies[name]["volatility"] = volatility
                
                equity_max = equity.cummax()
                drawdown = (equity_max - equity) / equity_max
                max_drawdown = drawdown.max()
                
                self.strategies[name]["max_drawdown"] = max_drawdown
        
        inv_volatilities = {name: 1.0 / max(0.001, s["volatility"]) for name, s in self.strategies.items() if "volatility" in s}
        total_inv_vol = sum(inv_volatilities.values())
        risk_parity_allocations = {name: inv_vol / total_inv_vol for name, inv_vol in inv_volatilities.items()}
        
        profit_contributions = {name: max(0, perf["profit"]) / max(0.001, total_profit) for name, perf in performance.items()}
        
        new_allocations = {}
        for name in self.strategies.keys():
            if name in risk_parity_allocations and name in profit_contributions:
                current_allocation = self.strategies[name]["allocation"]
                risk_parity_allocation = risk_parity_allocations[name]
                profit_allocation = profit_contributions[name]
                
                new_allocations[name] = (
                    0.5 * risk_parity_allocation +
                    0.3 * profit_allocation +
                    0.2 * current_allocation
                )
        
        total_new_allocation = sum(new_allocations.values())
        for name in new_allocations:
            new_allocations[name] /= total_new_allocation
            
            old_allocation = self.strategies[name]["allocation"]
            self.strategies[name]["allocation"] = new_allocations[name]
            self.logger.log_info(f"{name}の資金配分: {old_allocation:.2f} → {new_allocations[name]:.2f}")
        
        self.current_balance = self.initial_balance + total_profit
        for name, strategy_info in self.strategies.items():
            strategy_info["balance"] = self.current_balance * strategy_info["allocation"]
            self.logger.log_info(f"{name}の資金: {strategy_info['balance']:.2f}円")
