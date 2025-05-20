import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from src.utils.logger import Logger

class MacroEconomicDataProcessor:
    """
    マクロ経済データの取得、処理、保存を行うクラス
    
    特徴:
    - カレンシースコアカード方式による指標評価
    - 複数のデータソース（Trading Economics, FRED等）に対応
    - 手動データ入力と半自動データ取得をサポート
    - 異なる更新頻度のデータを管理
    """
    
    def __init__(self, data_dir: str = "data/macro_economic"):
        """
        初期化
        
        Parameters
        ----------
        data_dir : str
            マクロ経済データを保存するディレクトリ
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)
        
        self.currency_pair = "USDJPY"
        self.base_currency = "USD"
        self.quote_currency = "JPY"
        
        self.high_importance_indicators = [
            "interest_rate", "gdp_growth", "inflation_rate", "unemployment_rate"
        ]
        
        self.medium_importance_indicators = [
            "trade_balance", "industrial_production", "retail_sales", "consumer_confidence"
        ]
        
        self.indicator_weights = {
            "gdp_growth": 0.30,      # GDP成長率: 30%
            "interest_rate": 0.25,    # 政策金利: 25%
            "inflation_rate": 0.20,   # インフレ率: 20%
            "unemployment_rate": 0.15, # 雇用統計: 15%
            "trade_balance": 0.10     # 貿易収支: 10%
        }
        
        self.trend_market_weights = {
            "gdp_growth": 0.35,      # トレンド市場ではGDP成長率と金利を重視
            "interest_rate": 0.30,
            "inflation_rate": 0.15,
            "unemployment_rate": 0.10,
            "trade_balance": 0.10
        }
        
        self.range_market_weights = {
            "gdp_growth": 0.25,      # レンジ市場ではインフレと雇用を重視
            "interest_rate": 0.20,
            "inflation_rate": 0.25,
            "unemployment_rate": 0.20,
            "trade_balance": 0.10
        }
        
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """
        保存されているマクロ経済データを読み込む
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            指標ごとのデータを格納した辞書
        """
        data = {}
        
        for indicator_type in ["high_importance", "medium_importance"]:
            indicators = getattr(self, f"{indicator_type}_indicators", [])
            for indicator in indicators:
                file_path = os.path.join(self.data_dir, f"{indicator}.json")
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            data[indicator] = json.load(f)
                        self.logger.log_info(f"{indicator}データを読み込みました")
                    except Exception as e:
                        self.logger.log_error(f"{indicator}データの読み込み中にエラーが発生しました: {e}")
                        data[indicator] = {}
                else:
                    data[indicator] = {}
                    self.logger.log_warning(f"{indicator}データが見つかりません")
        
        return data
    
    def save_data(self) -> None:
        """
        マクロ経済データを保存する
        """
        for indicator, indicator_data in self.data.items():
            file_path = os.path.join(self.data_dir, f"{indicator}.json")
            try:
                with open(file_path, 'w') as f:
                    json.dump(indicator_data, f, indent=4)
                self.logger.log_info(f"{indicator}データを保存しました")
            except Exception as e:
                self.logger.log_error(f"{indicator}データの保存中にエラーが発生しました: {e}")
    
    def update_data_manually(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        マクロ経済データを手動で更新する
        
        Parameters
        ----------
        data : Dict[str, Dict[str, Any]]
            更新するデータ
            {
                "indicator": {
                    "date": "YYYY-MM-DD",
                    "value": 0.0,
                    "previous": 0.0,
                    "forecast": 0.0,
                    "country": "country_code"
                }
            }
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for indicator, values in data.items():
            if indicator in self.data:
                self.data[indicator]["last_update"] = timestamp
                self.data[indicator]["values"] = values
            else:
                self.data[indicator] = {
                    "last_update": timestamp,
                    "values": values
                }
        
        self.save_data()
        self.logger.log_info(f"マクロ経済データを手動で更新しました: {', '.join(data.keys())}")
    
    def calculate_currency_score(self, countries: List[str] = ["US", "JP"], market_regime: str = "normal") -> Dict[str, float]:
        """
        通貨ごとのスコアを計算する（カレンシースコアカード方式）
        
        Parameters
        ----------
        countries : List[str]
            スコアを計算する国のリスト（デフォルト: ["US", "JP"]）
        market_regime : str
            市場レジーム（"normal", "trend", "range"のいずれか）
            
        Returns
        -------
        Dict[str, float]
            通貨ごとのスコアを格納した辞書
        """
        currency_scores = {country: 0.0 for country in countries}
        
        if market_regime == "trend":
            weights = self.trend_market_weights
        elif market_regime == "range":
            weights = self.range_market_weights
        else:
            weights = self.indicator_weights
        
        for indicator, weight in weights.items():
            if indicator in self.data and "values" in self.data[indicator]:
                for country in countries:
                    if country in self.data[indicator]["values"]:
                        indicator_value = self.data[indicator]["values"][country]["value"]
                        indicator_score = self._score_indicator(indicator, indicator_value, country)
                        currency_scores[country] += indicator_score * weight
        
        return currency_scores
    
    def _score_indicator(self, indicator: str, value: float, country: str) -> float:
        """
        指標の値に基づいてスコアを計算する（-5〜+5のスケール）
        
        Parameters
        ----------
        indicator : str
            指標名
        value : float
            指標値
        country : str
            国コード
            
        Returns
        -------
        float
            スコア（-5〜+5）
        """
        if indicator == "gdp_growth":
            return min(5, max(-5, value * 2.5))
        
        elif indicator == "interest_rate":
            return min(5, max(-5, value * 1.0))
        
        elif indicator == "inflation_rate":
            target = 2.0  # 中央銀行の目標インフレ率
            deviation = abs(value - target)
            
            if deviation <= 0.5:  # 目標±0.5%以内
                return 5
            elif deviation <= 1.0:  # 目標±1.0%以内
                return 3
            elif deviation <= 2.0:  # 目標±2.0%以内
                return 0
            elif deviation <= 4.0:  # 目標±4.0%以内
                return -3
            else:  # 目標から大きく乖離
                return -5
        
        elif indicator == "unemployment_rate":
            if value <= 3.0:
                return 5
            elif value <= 5.0:
                return 3
            elif value <= 7.0:
                return 0
            elif value <= 10.0:
                return -3
            else:
                return -5
        
        elif indicator == "trade_balance":
            if value >= 3.0:  # GDP比3%以上の黒字
                return 5
            elif value >= 1.0:  # GDP比1-3%の黒字
                return 3
            elif value >= -1.0:  # GDP比±1%（ほぼ均衡）
                return 0
            elif value >= -3.0:  # GDP比1-3%の赤字
                return -3
            else:  # GDP比3%以上の赤字
                return -5
        
        else:
            return 0.0
    
    def calculate_differentials(self, countries: List[str] = ["US", "JP"], market_regime: str = "normal") -> Dict[str, float]:
        """
        通貨ペア間の経済指標差分と総合スコアを計算する
        
        Parameters
        ----------
        countries : List[str]
            差分を計算する国のリスト（デフォルト: ["US", "JP"]）
        market_regime : str
            市場レジーム
            
        Returns
        -------
        Dict[str, float]
            指標ごとの差分とスコア差を格納した辞書
        """
        if len(countries) != 2:
            self.logger.log_error("差分計算には2つの国が必要です")
            return {}
            
        country_a, country_b = countries
        differentials = {}
        
        all_indicators = self.high_importance_indicators + self.medium_importance_indicators
        
        for indicator in all_indicators:
            if indicator in self.data and "values" in self.data[indicator]:
                if all(c in self.data[indicator]["values"] for c in countries):
                    value_a = self.data[indicator]["values"][country_a]["value"]
                    value_b = self.data[indicator]["values"][country_b]["value"]
                    
                    diff_key = f"{indicator}_diff"
                    differentials[diff_key] = value_a - value_b
        
        currency_scores = self.calculate_currency_score(countries, market_regime)
        
        if country_a in currency_scores and country_b in currency_scores:
            differentials["currency_score_diff"] = currency_scores[country_a] - currency_scores[country_b]
        
        return differentials
    
    def get_update_frequency(self, indicator: str) -> str:
        """
        指標の更新頻度を取得する
        
        Parameters
        ----------
        indicator : str
            指標名
            
        Returns
        -------
        str
            更新頻度（daily, weekly, monthly, quarterly）
        """
        high_freq_indicators = ["interest_rate"]
        monthly_indicators = ["inflation_rate", "unemployment_rate", "trade_balance", 
                             "industrial_production", "retail_sales", "consumer_confidence"]
        quarterly_indicators = ["gdp_growth"]
        
        if indicator in high_freq_indicators:
            return "event_based"
        elif indicator in monthly_indicators:
            return "monthly"
        elif indicator in quarterly_indicators:
            return "quarterly"
        else:
            return "unknown"
    
    def should_update(self, indicator: str) -> bool:
        """
        指標が更新されるべきかを判断する
        
        Parameters
        ----------
        indicator : str
            指標名
            
        Returns
        -------
        bool
            更新が必要な場合True
        """
        if indicator not in self.data:
            return True
            
        if "last_update" not in self.data[indicator]:
            return True
            
        last_update = datetime.strptime(self.data[indicator]["last_update"], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        frequency = self.get_update_frequency(indicator)
        
        if frequency == "event_based":
            return False
        elif frequency == "monthly":
            return (now - last_update) > timedelta(days=30)
        elif frequency == "quarterly":
            return (now - last_update) > timedelta(days=90)
        else:
            return (now - last_update) > timedelta(days=7)
    
    def update_data_automatically(self) -> bool:
        """
        マクロ経済データを自動的に更新する（FRED APIを使用）
        
        Returns
        -------
        bool
            更新が成功した場合True
        """
        updated = False
        try:
            import fredapi
            from datetime import datetime, timedelta
            
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                self.logger.log_warning(".envファイルの読み込みに失敗しました。python-dotenvがインストールされていることを確認してください。")
            
            api_key = os.environ.get('FRED_API_KEY', '')
            
            if not api_key:
                config_file = os.path.join("config", "api_settings.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        api_key = config.get('fred', {}).get('api_key', '')
            
            if not api_key:
                self.logger.log_error("FRED API Keyが設定されていません")
                return False
                
            fred = fredapi.Fred(api_key=api_key)
            
            fred_series_mapping = {
                "interest_rate": {
                    "US": "FEDFUNDS",  # 米国FRB政策金利
                    "JP": "INTDSRJPM193N"  # 日本政策金利
                },
                "gdp_growth": {
                    "US": "A191RL1Q225SBEA",  # 米国実質GDP成長率
                    "JP": "JPNRGDPEXP"  # 日本実質GDP成長率
                },
                "inflation_rate": {
                    "US": "CPIAUCSL",  # 米国CPI
                    "JP": "JPNCPIALLMINMEI"  # 日本CPI
                },
                "unemployment_rate": {
                    "US": "UNRATE",  # 米国失業率
                    "JP": "LRUNTTTTJPM156S"  # 日本失業率
                },
                "trade_balance": {
                    "US": "BOPGSTB",  # 米国貿易収支
                    "JP": "JPTBALE"  # 日本貿易収支
                }
            }
            
            now = datetime.now()
            
            for indicator in self.high_importance_indicators + self.medium_importance_indicators:
                if self.should_update(indicator) and indicator in fred_series_mapping:
                    try:
                        values = {}
                        for country, series_id in fred_series_mapping[indicator].items():
                            series_data = fred.get_series(series_id)
                            if not series_data.empty:
                                latest_date = series_data.index[-1]
                                latest_value = series_data.iloc[-1]
                                prev_value = series_data.iloc[-2] if len(series_data) > 1 else None
                                
                                values[country] = {
                                    "value": float(latest_value),
                                    "previous": float(prev_value) if prev_value is not None else None,
                                    "forecast": None,
                                    "date": latest_date.strftime("%Y-%m-%d")
                                }
                        
                        if values:
                            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                            
                            if indicator in self.data:
                                self.data[indicator]["last_update"] = timestamp
                                self.data[indicator]["values"] = values
                            else:
                                self.data[indicator] = {
                                    "last_update": timestamp,
                                    "values": values
                                }
                            
                            self.logger.log_info(f"{indicator}データを自動更新しました")
                            updated = True
                    except Exception as e:
                        self.logger.log_error(f"{indicator}データの自動更新中にエラーが発生しました: {str(e)}")
            
            if updated:
                self.save_data()
                self.logger.log_info("マクロ経済データを保存しました")
                
            return updated
        except Exception as e:
            self.logger.log_error(f"マクロ経済データの自動更新中にエラーが発生しました: {str(e)}")
            return False
    
    def get_sample_data(self) -> Dict[str, Dict[str, Any]]:
        """
        サンプルデータを生成する（テスト・デモ用）
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            サンプルデータ
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        us_data = {
            "interest_rate": {
                "values": {
                    "US": {"value": 5.25, "previous": 5.0, "forecast": 5.25, "date": date_str},
                    "JP": {"value": 0.1, "previous": 0.0, "forecast": 0.1, "date": date_str}
                },
                "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
            },
            "gdp_growth": {
                "values": {
                    "US": {"value": 2.1, "previous": 1.9, "forecast": 2.0, "date": date_str},
                    "JP": {"value": 0.9, "previous": 0.8, "forecast": 1.0, "date": date_str}
                },
                "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
            },
            "inflation_rate": {
                "values": {
                    "US": {"value": 3.7, "previous": 3.5, "forecast": 3.6, "date": date_str},
                    "JP": {"value": 2.6, "previous": 2.8, "forecast": 2.5, "date": date_str}
                },
                "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
            },
            "unemployment_rate": {
                "values": {
                    "US": {"value": 3.8, "previous": 3.7, "forecast": 3.8, "date": date_str},
                    "JP": {"value": 2.6, "previous": 2.7, "forecast": 2.7, "date": date_str}
                },
                "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
            },
            "trade_balance": {
                "values": {
                    "US": {"value": -3.2, "previous": -3.4, "forecast": -3.3, "date": date_str},
                    "JP": {"value": 1.8, "previous": 1.7, "forecast": 1.8, "date": date_str}
                },
                "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        return us_data
