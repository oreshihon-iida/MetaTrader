import time
import threading
import datetime
import os
import json
from typing import Dict, Any, List, Optional
from src.data.macro_economic_data_processor import MacroEconomicDataProcessor
from src.utils.logger import Logger

class EconomicUpdateScheduler:
    """
    マクロ経済データの自動更新をスケジュールするクラス
    """
    
    def __init__(self, update_interval: int = 3600):
        """
        初期化
        
        Parameters
        ----------
        update_interval : int
            更新間隔（秒）、デフォルトは1時間
        """
        self.update_interval = update_interval
        self.stop_flag = False
        self.processor = MacroEconomicDataProcessor()
        
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        
    def start(self):
        """
        スケジューラを開始
        """
        self.stop_flag = False
        threading.Thread(target=self._scheduler_loop).start()
        self.logger.log_info("マクロ経済データ自動更新スケジューラを開始しました")
        
    def stop(self):
        """
        スケジューラを停止
        """
        self.stop_flag = True
        self.logger.log_info("マクロ経済データ自動更新スケジューラを停止しました")
        
    def _scheduler_loop(self):
        """
        スケジューラのメインループ
        """
        while not self.stop_flag:
            now = datetime.datetime.now()
            
            if now.hour == 9 and now.minute < 5:
                self.logger.log_info("マクロ経済データの定期更新を開始します")
                
                updated = self.processor.update_data_automatically()
                
                if updated:
                    self.logger.log_info("マクロ経済データの定期更新が完了しました")
                else:
                    self.logger.log_info("更新するマクロ経済データはありませんでした")
            
            time.sleep(self.update_interval)
