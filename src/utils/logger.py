import pandas as pd
import logging
import os
from typing import Optional

class Logger:
    """
    ログ出力クラス
    """
    
    def __init__(self, log_dir: str, log_level: int = logging.INFO):
        """
        初期化
        
        Parameters
        ----------
        log_dir : str
            ログファイルを保存するディレクトリ
        log_level : int, default logging.INFO
            ログレベル
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger = logging.getLogger('fx_trading')
        self.logger.setLevel(log_level)
        
        log_file = os.path.join(log_dir, 'backtest.log')
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(log_level)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def log_info(self, message: str):
        """
        情報ログを出力する
        
        Parameters
        ----------
        message : str
            ログメッセージ
        """
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """
        警告ログを出力する
        
        Parameters
        ----------
        message : str
            ログメッセージ
        """
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """
        エラーログを出力する
        
        Parameters
        ----------
        message : str
            ログメッセージ
        """
        self.logger.error(message)
    
    def log_trade_history(self, trade_history: pd.DataFrame):
        """
        トレード履歴をCSVファイルに出力する
        
        Parameters
        ----------
        trade_history : pd.DataFrame
            トレード履歴のDataFrame
        """
        csv_file = os.path.join(self.log_dir, 'trade_history.csv')
        trade_history.to_csv(csv_file)
        self.log_info(f"トレード履歴を {csv_file} に保存しました")
    
    def log_performance_metrics(self, metrics: dict):
        """
        パフォーマンス指標をログに出力する
        
        Parameters
        ----------
        metrics : dict
            パフォーマンス指標の辞書
        """
        self.log_info("===== パフォーマンス指標 =====")
        for key, value in metrics.items():
            self.log_info(f"{key}: {value}")
