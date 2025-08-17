"""
取引執行シミュレーターとP&L計算機能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

class OrderType(Enum):
    """注文タイプ"""
    BUY = 1
    SELL = -1

class OrderStatus(Enum):
    """注文ステータス"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class Position:
    """ポジションクラス"""
    
    def __init__(self, 
                 position_id: int,
                 symbol: str,
                 order_type: OrderType,
                 entry_price: float,
                 lot_size: float,
                 entry_time: pd.Timestamp,
                 stop_loss: float,
                 take_profit: float,
                 strategy: str = ""):
        """
        ポジションの初期化
        
        Parameters
        ----------
        position_id : int
            ポジションID
        symbol : str
            通貨ペア
        order_type : OrderType
            買い/売り
        entry_price : float
            エントリー価格
        lot_size : float
            ロットサイズ
        entry_time : pd.Timestamp
            エントリー時刻
        stop_loss : float
            ストップロス価格
        take_profit : float
            テイクプロフィット価格
        strategy : str
            戦略名
        """
        self.position_id = position_id
        self.symbol = symbol
        self.order_type = order_type
        self.entry_price = entry_price
        self.lot_size = lot_size
        self.entry_time = entry_time
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy = strategy
        self.status = OrderStatus.OPEN
        
        # 決済情報
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl_pips = 0
        self.pnl_amount = 0
        self.commission = 0
        self.swap = 0
        
    def close(self, exit_price: float, exit_time: pd.Timestamp, reason: str = "manual"):
        """
        ポジションをクローズ
        
        Parameters
        ----------
        exit_price : float
            決済価格
        exit_time : pd.Timestamp
            決済時刻
        reason : str
            決済理由（tp/sl/manual/signal）
        """
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        self.status = OrderStatus.CLOSED
        
        # P&L計算
        if self.order_type == OrderType.BUY:
            self.pnl_pips = (exit_price - self.entry_price) * 100  # pips変換（100倍）
        else:  # SELL
            self.pnl_pips = (self.entry_price - exit_price) * 100
        
        # 金額計算（1ロット = 100,000通貨、1pip = 1,000円）
        self.pnl_amount = self.pnl_pips * self.lot_size * 1000
        
    def is_tp_hit(self, current_price: float) -> bool:
        """TP到達チェック"""
        if self.order_type == OrderType.BUY:
            return current_price >= self.take_profit
        else:
            return current_price <= self.take_profit
    
    def is_sl_hit(self, current_price: float) -> bool:
        """SL到達チェック"""
        if self.order_type == OrderType.BUY:
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """未実現損益を計算"""
        if self.order_type == OrderType.BUY:
            pips = (current_price - self.entry_price) * 100
        else:
            pips = (self.entry_price - current_price) * 100
        return pips * self.lot_size * 1000

class TradeExecutor:
    """取引執行シミュレーター"""
    
    def __init__(self,
                 initial_balance: float = 3000000,
                 spread_pips: float = 0.2,
                 commission_per_lot: float = 0,
                 max_positions: int = 10,
                 margin_rate: float = 1.0):  # レバレッジ1倍 = 証拠金率100%
        """
        初期化
        
        Parameters
        ----------
        initial_balance : float
            初期資金（円）
        spread_pips : float
            スプレッド（pips）
        commission_per_lot : float
            1ロットあたりの手数料（円）
        max_positions : int
            最大同時保有ポジション数
        margin_rate : float
            証拠金率（1.0 = レバレッジ1倍）
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.spread_pips = spread_pips
        self.commission_per_lot = commission_per_lot
        self.max_positions = max_positions
        self.margin_rate = margin_rate
        
        # ポジション管理
        self.positions = {}  # {position_id: Position}
        self.closed_positions = []
        self.next_position_id = 1
        
        # 統計情報
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        self.total_commission = 0
        self.peak_balance = initial_balance
        self.max_drawdown = 0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        
        # 履歴
        self.balance_history = [initial_balance]
        self.equity_history = [initial_balance]
        self.trade_history = []
        
    def can_open_position(self, lot_size: float, price: float = 150.0) -> bool:
        """新規ポジションを開けるかチェック"""
        if len(self.positions) >= self.max_positions:
            return False
        
        # 必要証拠金の計算（実際の価格使用）
        required_margin = self.calculate_required_margin(lot_size, price)
        used_margin = sum(self.calculate_required_margin(pos.lot_size, price) 
                         for pos in self.positions.values())
        
        # 総保有制限チェック（証拠金の80%まで）
        max_total_position = self.initial_balance * 0.80
        total_position_value = used_margin + required_margin
        
        if total_position_value > max_total_position:
            return False
        
        # 利用可能証拠金のチェック
        available_margin = self.balance - used_margin
        return available_margin >= required_margin
    
    def calculate_required_margin(self, lot_size: float, price: float = 150.0) -> float:
        """必要証拠金を計算"""
        # 1ロット = 100,000通貨
        position_value = lot_size * 100000 * price
        return position_value * self.margin_rate
    
    def calculate_max_lot_size(self, price: float = 150.0) -> float:
        """現在の状況で取引可能な最大ロットサイズを計算"""
        # 現在の使用証拠金
        used_margin = sum(self.calculate_required_margin(pos.lot_size, price) 
                         for pos in self.positions.values())
        
        # 80%制限での利用可能証拠金
        max_total_position = self.initial_balance * 0.80
        available_for_new_position = max_total_position - used_margin
        
        if available_for_new_position <= 0:
            return 0.0
        
        # 1ロット = 100,000通貨 × 価格 × 証拠金率
        one_lot_margin = 100000 * price * self.margin_rate
        max_lot_size = available_for_new_position / one_lot_margin
        
        # 最小単位0.01ロットに丸める
        return max(0.0, round(max_lot_size, 2))
    
    def calculate_max_positions(self, lot_size: float, price: float = 150.0) -> int:
        """現在の価格とロットサイズで取引可能な最大ポジション数を計算"""
        # 80%制限での利用可能証拠金
        max_total_margin = self.initial_balance * 0.80
        
        # 1ポジションあたりの必要証拠金
        margin_per_position = self.calculate_required_margin(lot_size, price)
        
        if margin_per_position <= 0:
            return 0
        
        # 理論上の最大ポジション数
        theoretical_max = int(max_total_margin / margin_per_position)
        
        # システムの最大制限と比較して小さい方を採用
        return min(theoretical_max, self.max_positions)
    
    def open_position(self,
                     signal: int,
                     price: float,
                     lot_size: float,
                     stop_loss_pips: float,
                     take_profit_pips: float,
                     timestamp: pd.Timestamp,
                     strategy: str = "") -> Optional[Position]:
        """
        ポジションを開く
        
        Parameters
        ----------
        signal : int
            1: 買い, -1: 売り
        price : float
            現在価格
        lot_size : float
            ロットサイズ
        stop_loss_pips : float
            ストップロス（pips）
        take_profit_pips : float
            テイクプロフィット（pips）
        timestamp : pd.Timestamp
            時刻
        strategy : str
            戦略名
        
        Returns
        -------
        Position or None
            開いたポジション
        """
        if signal == 0 or not self.can_open_position(lot_size, price):
            return None
        
        # スプレッド考慮
        if signal == 1:  # BUY
            entry_price = price + (self.spread_pips / 100)
            order_type = OrderType.BUY
            stop_loss = entry_price - (stop_loss_pips / 100)
            take_profit = entry_price + (take_profit_pips / 100)
        else:  # SELL
            entry_price = price - (self.spread_pips / 100)
            order_type = OrderType.SELL
            stop_loss = entry_price + (stop_loss_pips / 100)
            take_profit = entry_price - (take_profit_pips / 100)
        
        # ポジション作成
        position = Position(
            position_id=self.next_position_id,
            symbol="USDJPY",
            order_type=order_type,
            entry_price=entry_price,
            lot_size=lot_size,
            entry_time=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy
        )
        
        # 手数料
        position.commission = self.commission_per_lot * lot_size
        self.balance -= position.commission
        self.total_commission += position.commission
        
        # ポジション登録
        self.positions[self.next_position_id] = position
        self.next_position_id += 1
        self.total_trades += 1
        
        return position
    
    def check_positions(self, current_price: float, timestamp: pd.Timestamp) -> List[Position]:
        """
        全ポジションのTP/SLをチェックして決済
        
        Parameters
        ----------
        current_price : float
            現在価格
        timestamp : pd.Timestamp
            現在時刻
        
        Returns
        -------
        List[Position]
            決済されたポジションのリスト
        """
        closed = []
        
        for pos_id, position in list(self.positions.items()):
            close_position = False
            reason = ""
            
            # TP/SLチェック
            if position.is_tp_hit(current_price):
                close_position = True
                reason = "tp"
            elif position.is_sl_hit(current_price):
                close_position = True
                reason = "sl"
            
            if close_position:
                # ポジションクローズ
                position.close(current_price, timestamp, reason)
                
                # 残高更新
                self.balance += position.pnl_amount
                self.total_pnl += position.pnl_amount
                
                # 統計更新
                if position.pnl_amount > 0:
                    self.winning_trades += 1
                    self.consecutive_wins += 1
                    self.consecutive_losses = 0
                    self.max_consecutive_wins = max(self.max_consecutive_wins, self.consecutive_wins)
                else:
                    self.losing_trades += 1
                    self.consecutive_losses += 1
                    self.consecutive_wins = 0
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)
                
                # ピーク残高とドローダウン更新
                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance
                drawdown = (self.peak_balance - self.balance) / self.peak_balance
                self.max_drawdown = max(self.max_drawdown, drawdown)
                
                # 履歴に追加
                self.closed_positions.append(position)
                self.trade_history.append({
                    'position_id': position.position_id,
                    'strategy': position.strategy,
                    'order_type': 'BUY' if position.order_type == OrderType.BUY else 'SELL',
                    'entry_time': position.entry_time,
                    'entry_price': position.entry_price,
                    'exit_time': position.exit_time,
                    'exit_price': position.exit_price,
                    'lot_size': position.lot_size,
                    'pnl_pips': position.pnl_pips,
                    'pnl_amount': position.pnl_amount,
                    'exit_reason': position.exit_reason
                })
                
                # ポジション削除
                del self.positions[pos_id]
                closed.append(position)
        
        return closed
    
    def close_position_by_signal(self, position_id: int, current_price: float, 
                                 timestamp: pd.Timestamp) -> Optional[Position]:
        """シグナルによる手動決済"""
        if position_id not in self.positions:
            return None
        
        position = self.positions[position_id]
        position.close(current_price, timestamp, "signal")
        
        # 残高更新
        self.balance += position.pnl_amount
        self.total_pnl += position.pnl_amount
        
        # 履歴に追加
        self.closed_positions.append(position)
        del self.positions[position_id]
        
        return position
    
    def update_equity(self, current_price: float):
        """現在の評価額を更新"""
        unrealized_pnl = sum(pos.get_unrealized_pnl(current_price) 
                            for pos in self.positions.values())
        equity = self.balance + unrealized_pnl
        self.equity_history.append(equity)
        self.balance_history.append(self.balance)
        return equity
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # 平均利益・損失を計算
        winning_pnl = [p.pnl_amount for p in self.closed_positions if p.pnl_amount > 0]
        losing_pnl = [p.pnl_amount for p in self.closed_positions if p.pnl_amount < 0]
        
        avg_win = np.mean(winning_pnl) if winning_pnl else 0
        avg_loss = np.mean(losing_pnl) if losing_pnl else 0
        
        # プロフィットファクター
        total_wins = sum(winning_pnl) if winning_pnl else 0
        total_losses = abs(sum(losing_pnl)) if losing_pnl else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # リターン
        total_return = ((self.balance - self.initial_balance) / self.initial_balance * 100)
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_pnl': self.total_pnl,
            'total_return': total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown * 100,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'total_commission': self.total_commission,
            'peak_balance': self.peak_balance
        }
    
    def get_monthly_performance(self) -> pd.DataFrame:
        """月別パフォーマンスを取得"""
        if not self.trade_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trade_history)
        df['month'] = pd.to_datetime(df['exit_time']).dt.to_period('M')
        
        monthly = df.groupby('month').agg({
            'pnl_amount': 'sum',
            'position_id': 'count',
            'pnl_pips': 'sum'
        }).rename(columns={
            'position_id': 'trades',
            'pnl_amount': 'profit',
            'pnl_pips': 'total_pips'
        })
        
        # 勝率を計算
        monthly['wins'] = df[df['pnl_amount'] > 0].groupby('month').size()
        monthly['win_rate'] = (monthly['wins'] / monthly['trades'] * 100).fillna(0)
        
        return monthly