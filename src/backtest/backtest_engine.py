import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import datetime
from ..strategies.tokyo_london import TokyoLondonStrategy
from ..strategies.bollinger_rsi import BollingerRsiStrategy
from ..strategies.trend_following import TrendFollowingStrategy
from ..strategies.range_trading import RangeTradingStrategy
from .position import Position, PositionStatus

class BacktestEngine:
    """
    バックテストエンジン
    """

    def __init__(self, data: pd.DataFrame, initial_balance: float = 200000,
                 lot_size: float = 0.01, max_positions: int = 3,
                 spread_pips: float = 0.2):
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
        """
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.lot_size = lot_size
        self.max_positions = max_positions
        self.spread_pips = spread_pips

        self.open_positions = []
        self.closed_positions = []

        self.equity_curve = []
        self.trade_history = []

    def run(self) -> pd.DataFrame:
        """
        バックテストを実行する

        Returns
        -------
        pd.DataFrame
            トレード履歴のDataFrame
        """
        tokyo_london = TokyoLondonStrategy(
            sl_pips=10.0,
            tp_pips=15.0,
            atr_multiplier=1.5,
            min_adx=25.0
        )
        
        bollinger_rsi = BollingerRsiStrategy(
            sl_pips=7.0,
            tp_pips=10.0,
            atr_multiplier=1.2,
            max_adx=20.0
        )
        
        trend_following = TrendFollowingStrategy(
            short_ma=5,
            long_ma=20,
            min_adx=25.0,
            atr_multiplier=2.0
        )
        
        range_trading = RangeTradingStrategy(
            max_adx=20.0,
            stoch_k=14,
            stoch_d=3,
            atr_multiplier=1.0
        )
        
        self.data = tokyo_london.generate_signals(self.data)
        self.data = bollinger_rsi.generate_signals(self.data)
        self.data = trend_following.generate_signals(self.data)
        self.data = range_trading.generate_signals(self.data)

        for i in range(len(self.data)):
            current_time = self.data.index[i]
            current_bar = self.data.iloc[i]

            self._check_positions_for_exit(current_time, current_bar)

            if current_bar['signal'] != 0 and len(self.open_positions) < self.max_positions:
                self._open_new_position(current_time, current_bar)

            self._record_equity(current_time)

        history_df = pd.DataFrame([pos.to_dict() for pos in self.closed_positions])
        return history_df

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
            if position.trailing_stop:
                if position.direction == 1:  # 買いポジション
                    if current_bar['High'] > position.trailing_price:
                        if 'atr' in current_bar:
                            atr_value = current_bar['atr']
                            new_sl = current_bar['High'] - atr_value
                            
                            if new_sl > position.sl_price:
                                position.sl_price = new_sl
                                position.trailing_price = current_bar['High']
                    
                else:  # 売りポジション
                    if current_bar['Low'] < position.trailing_price:
                        if 'atr' in current_bar:
                            atr_value = current_bar['atr']
                            new_sl = current_bar['Low'] + atr_value
                            
                            if new_sl < position.sl_price:
                                position.sl_price = new_sl
                                position.trailing_price = current_bar['Low']
            
            if position.direction == 1:  # 買いポジション
                if current_bar['High'] >= position.tp_price:
                    position.close_position(current_time, position.tp_price, PositionStatus.CLOSED_TAKE_PROFIT)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy
                elif current_bar['Low'] <= position.sl_price:
                    position.close_position(current_time, position.sl_price, PositionStatus.CLOSED_STOP_LOSS)
                    positions_to_remove.append(position)
                    self.balance += position.profit_jpy

            else:  # 売りポジション
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

        trailing_stop = False
        if 'trailing_stop' in current_bar:
            trailing_stop = current_bar['trailing_stop']

        position = Position(
            entry_time=current_time,
            direction=current_bar['signal'],
            entry_price=entry_price,
            sl_price=current_bar['sl_price'],
            tp_price=current_bar['tp_price'],
            strategy=current_bar['strategy'],
            lot_size=self.lot_size,
            trailing_stop=trailing_stop
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
        current_idx = self.data.index.get_loc(current_time)
        current_close = self.data.iloc[current_idx]['Close']
        
        unrealized_profit = sum([pos.direction * (current_close - pos.entry_price) * 100 * 0.01 * 1000 * pos.lot_size for pos in self.open_positions])

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
        
        def format_time(timestamp):
            return timestamp.strftime('%Y-%m-%d %H:%M') if timestamp is not None else "N/A"
        
        entry_time_str = format_time(position.entry_time)
        exit_time_str = format_time(position.exit_time)

        log = {
            'timestamp': position.exit_time,
            'message': f"【{status_str}】{position.strategy}戦略 {direction_str}ポジション決済: "
                      f"エントリー: {entry_time_str} "
                      f"@ {position.entry_price:.3f}, "
                      f"決済: {exit_time_str} "
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

    def get_trade_log(self) -> pd.DataFrame:
        """
        トレードログを取得する

        Returns
        -------
        pd.DataFrame
            トレードログのDataFrame
        """
        df = pd.DataFrame(self.trade_history)
        if len(df) > 0 and 'timestamp' in df.columns:
            return df.set_index('timestamp')
        return df
