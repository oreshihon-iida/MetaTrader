"""
FRED APIキーのテストスクリプト
.envファイルからAPIキーを読み込み、マクロ経済データの更新をテストします
"""
from src.data.macro_economic_data_processor import MacroEconomicDataProcessor

def test_fred_api():
    """FREDのAPIキーを使用してマクロ経済データの更新をテストする"""
    processor = MacroEconomicDataProcessor()
    result = processor.update_data_automatically()
    print(f'マクロ経済データの更新結果: {result}')
    return result

if __name__ == "__main__":
    test_fred_api()
