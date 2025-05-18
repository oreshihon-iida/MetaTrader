import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import datetime
from src.backtest.position import Position, PositionStatus

class CustomBacktestEngine:
    """
    カスタムバックテストエンジン
    
    特定の戦略のみをテストするための簡易バックテストエンジン
    """

    def __init__(self, data: pd.DataFrame, initial_balance: float = 200000,
                 lot_size: float = 0.01, max_positions: int = 3,
                 spread_pips: float = 0.2, strategy_instance=None):
        """
        初期化

        Parameters
        ----------
        data : pd.DataFrame
            バックテスト対象のデータ（15分足）
        initial_balance : float, default 200000
            初期資金（円）
        lot_size : float, default 0.01
            1トレードあたりのロットサイズ
        max_positions : int, default 3
            同時に保有できる最大ポジション数
        spread_pips : float, default 0.2
            スプレッド（pips）
        strategy_instance : object, default None
            戦略インスタンス（パターン統計更新用）
        """
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.lot_size = lot_size
        self.max_positions = max_positions
        self.spread_pips = spread_pips
        self.strategy_instance = strategy_instance

        self.open_positions = []
        self.closed_positions = []

        self.equity_curve = []
        self.trade_history = []

    def run(self) -> Dict:
        """
        バックテストを実行する

        Returns
        -------
        Dict
            バックテスト結果の要約
        """
        
        for i in range(len(self.data)):
            current_time = self.data.index[i]
            current_bar = self.data.iloc[i]

            self._check_positions_for_exit(current_time, current_bar)

            if current_bar['signal'] != 0 and len(self.open_positions) < self.max_positions:
                self._open_new_position(current_time, current_bar)

            self._record_equity(current_time)

        total_trades = len(self.closed_positions)
        wins = sum(1 for pos in self.closed_positions if pos.profit_pips > 0)
        losses = total_trades - wins
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        gross_profit = sum(pos.profit_jpy for pos in self.closed_positions if pos.profit_jpy > 0)
        gross_loss = abs(sum(pos.profit_jpy for pos in self.closed_positions if pos.profit_jpy < 0))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        net_profit = sum(pos.profit_jpy for pos in self.closed_positions)
        
        monthly_performance = {}
        for pos in self.closed_positions:
            month_key = pos.exit_time.strftime('%Y-%m')
            if month_key not in monthly_performance:
                monthly_performance[month_key] = {
                    'trades': 0,
                    'wins': 0,
                    'profit': 0
                }
            
            monthly_performance[month_key]['trades'] += 1
            if pos.profit_pips > 0:
                monthly_performance[month_key]['wins'] += 1
            monthly_performance[month_key]['profit'] += pos.profit_jpy
        
        results = {
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'net_profit': net_profit,
            'final_balance': self.balance,
            'monthly_performance': monthly_performance,
            'equity_curve': self.get_equity_curve(),
            'trade_history': self.closed_positions
        }
        
        return results

    def _check_positions_for_exit(self, current_time: pd.Timestamp, current_bar: pd.Series):
        """
        ポジションの決済条件を確認する

        Parameters
        ----------
        current_time : pd.Timestamp
            現在の時間
        current_bar : pd.Series
            現在の価格データ
        """
        bid = current_bar['Close'] - self.spread_pips * 0.01 / 2
        ask = current_bar['Close'] + self.spread_pips * 0.01 / 2

        positions_to_remove = []

        for position in self.open_positions:
            if position.direction == 1:
                if current_bar['High'] >= position.tp_price:
                    position.close_position(current_time, position.tp_price, PositionStatus.CLOSED_TAKE_PROFIT)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy
                elif current_bar['Low'] <= position.sl_price:
                    position.close_position(current_time, position.sl_price, PositionStatus.CLOSED_STOP_LOSS)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy

            else:
                if current_bar['Low'] <= position.tp_price:
                    position.close_position(current_time, position.tp_price, PositionStatus.CLOSED_TAKE_PROFIT)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy
                elif current_bar['High'] >= position.sl_price:
                    position.close_position(current_time, position.sl_price, PositionStatus.CLOSED_STOP_LOSS)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy

        for position in positions_to_remove:
            self.closed_positions.append(position)
            self.open_positions.remove(position)
            self.trade_history.append(self._create_trade_log(position))
            
            if hasattr(position, 'strategy') and hasattr(position, 'entry_time'):
                strategy_instance = self._get_strategy_instance(position.strategy)
                if strategy_instance and hasattr(strategy_instance, 'update_consecutive_stats'):
                    entry_time = position.entry_time
                    pattern_types = None
                    
                    if hasattr(strategy_instance, 'active_trade_patterns') and entry_time in strategy_instance.active_trade_patterns:
                        pattern_types = strategy_instance.active_trade_patterns.pop(entry_time)
                        
                    strategy_instance.update_consecutive_stats(position.profit_pips > 0, pattern_types)

    def _open_new_position(self, current_time: pd.Timestamp, current_bar: pd.Series):
        """
        新規ポジションを開く

        Parameters
        ----------
        current_time : pd.Timestamp
            現在の時間
        current_bar : pd.Series
            現在の価格データ
        """
        entry_price = current_bar['entry_price']
        if current_bar['signal'] == 1:  # 買いの場合はaskを使用
            entry_price += self.spread_pips * 0.01 / 2
        else:  # 売りの場合はbidを使用
            entry_price -= self.spread_pips * 0.01 / 2

        position = Position(
            entry_time=current_time,
            direction=current_bar['signal'],
            entry_price=entry_price,
            sl_price=current_bar['sl_price'],
            tp_price=current_bar['tp_price'],
            strategy=current_bar['strategy'],
            lot_size=self.lot_size if 'position_size' not in current_bar else current_bar['position_size']
        )

        self.open_positions.append(position)

    def _record_equity(self, current_time: pd.Timestamp):
        """
        資産推移を記録する

        Parameters
        ----------
        current_time : pd.Timestamp
            現在の時間
        """
        unrealized_profit = sum([pos.calculate_profit(self.data.loc[current_time, 'Close']) for pos in self.open_positions])

        equity = self.balance + unrealized_profit

        self.equity_curve.append({
            'time': current_time,
            'balance': self.balance,
            'equity': equity,
            'open_positions': len(self.open_positions)
        })

    def _create_trade_log(self, position: Position) -> Dict:
        """
        トレードログを作成する

        Parameters
        ----------
        position : Position
            ポジション情報

        Returns
        -------
        Dict
            トレードログ
        """
        direction_str = "買い" if position.direction == 1 else "売り"
        status_str = position.status.value if position.status else "不明"

        log = {
            'timestamp': position.exit_time,
            'message': f"【{status_str}】{position.strategy}戦略 {direction_str}ポジション決済: "
                      f"エントリー: {position.entry_time.strftime('%Y-%m-%d %H:%M')} "
                      f"@ {position.entry_price:.3f}, "
                      f"決済: {position.exit_time.strftime('%Y-%m-%d %H:%M')} "
                      f"@ {position.exit_price:.3f}, "
                      f"損益: {position.profit_pips:.1f}pips ({position.profit_jpy:.0f}円)"
        }

        return log

    def get_equity_curve(self) -> pd.DataFrame:
        """
        資産推移を取得する
        
        Returns
        -------
        pd.DataFrame
            資産推移のDataFrame
        """
        df = pd.DataFrame(self.equity_curve)
        if len(df) > 0:
            if 'time' in df.columns:
                return df.set_index('time')
            else:
                return df
        return pd.DataFrame(columns=['balance', 'equity', 'open_positions'])
        
    def _get_strategy_instance(self, strategy_name: str) -> Optional[object]:
        """
        戦略名から戦略インスタンスを取得する
        
        Parameters
        ----------
        strategy_name : str
            戦略名
            
        Returns
        -------
        Optional[object]
            戦略インスタンス。見つからない場合はNone
        """
        
        if hasattr(self, 'strategy_instance'):
            return self.strategy_instance
            
        return None
