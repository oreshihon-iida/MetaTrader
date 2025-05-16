import os
import json
from typing import Dict, Any

class Config:
    """
    設定管理クラス
    """
    
    def __init__(self, config_file: str = None):
        """
        初期化
        
        Parameters
        ----------
        config_file : str, optional
            設定ファイルのパス
        """
        self.config = self._get_default_config()
        
        if config_file and os.path.exists(config_file):
            self._load_config(config_file)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を取得する
        
        Returns
        -------
        Dict[str, Any]
            デフォルト設定の辞書
        """
        return {
            'data': {
                'raw_dir': 'data/raw',
                'processed_dir': 'data/processed',
                'timeframe': '15min',  # 15分足
            },
            
            'backtest': {
                'initial_balance': 450000,  # 初期資金（円）
                'lot_size': 0.01,  # 1トレードあたりのロットサイズ
                'max_positions': 2,  # 同時に保有できる最大ポジション数
                'spread_pips': 0.2,  # スプレッド（pips）
                'start_date': '2000-06-01',  # バックテスト開始日
                'end_date': '2000-12-29',  # バックテスト終了日
            },
            
            'strategies': {
                'tokyo_london': {
                    'sl_pips': 10.0,  # 損切り幅（pips）
                    'tp_pips': 15.0,  # 利確幅（pips）
                },
                'bollinger_rsi': {
                    'sl_pips': 7.0,  # 損切り幅（pips）
                    'tp_pips': 10.0,  # 利確幅（pips）
                }
            },
            
            'output': {
                'log_dir': 'results/logs',
                'chart_dir': 'results/charts',
            }
        }
    
    def _load_config(self, config_file: str):
        """
        設定ファイルを読み込む
        
        Parameters
        ----------
        config_file : str
            設定ファイルのパス
        """
        with open(config_file, 'r') as f:
            user_config = json.load(f)
            
            for section, values in user_config.items():
                if section in self.config:
                    self.config[section].update(values)
                else:
                    self.config[section] = values
    
    def get(self, section: str, key: str = None):
        """
        設定値を取得する
        
        Parameters
        ----------
        section : str
            セクション名
        key : str, optional
            キー名
            
        Returns
        -------
        Any
            設定値
        """
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)
    
    def save(self, config_file: str):
        """
        設定をファイルに保存する
        
        Parameters
        ----------
        config_file : str
            設定ファイルのパス
        """
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
