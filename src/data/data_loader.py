import os
import zipfile
import pandas as pd
from typing import List, Optional

class DataLoader:
    """HistData.comから提供されるFXデータを読み込むクラス"""
    
    def __init__(self, data_dir: str):
        """
        初期化
        
        Parameters
        ----------
        data_dir : str
            生データが格納されているディレクトリパス
        """
        self.data_dir = data_dir
        self.processed_dir = os.path.join(os.path.dirname(data_dir), 'processed')
        os.makedirs(self.processed_dir, exist_ok=True)
    
    def extract_zip_files(self) -> List[str]:
        """
        ZIPファイルを展開し、CSVファイルのリストを返す
        
        Returns
        -------
        List[str]
            展開されたCSVファイルのパスのリスト
        """
        csv_files = []
        zip_files = [f for f in os.listdir(self.data_dir) if f.endswith('.zip')]
        
        for zip_file in zip_files:
            zip_path = os.path.join(self.data_dir, zip_file)
            extract_dir = os.path.join(self.processed_dir, os.path.splitext(zip_file)[0])
            
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.csv'):
                        csv_files.append(os.path.join(root, file))
        
        for file in os.listdir(self.data_dir):
            if file.endswith('.csv') or file.endswith('.txt'):
                if file.endswith('.csv'):  # .txtファイルはメタデータなので除外
                    csv_files.append(os.path.join(self.data_dir, file))
        
        return csv_files
    
    def load_csv_to_dataframe(self, csv_path: str) -> pd.DataFrame:
        """
        CSVファイルをDataFrameとして読み込む
        
        Parameters
        ----------
        csv_path : str
            CSVファイルのパス
            
        Returns
        -------
        pd.DataFrame
            読み込まれたデータ
        """
        try:
            df = pd.read_csv(csv_path, header=None, 
                            names=['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'])
            
            df['Datetime'] = pd.to_datetime(df['DateTime'], format='%Y.%m.%d,%H:%M')
            
            df = df.drop(['DateTime'], axis=1)
            
            df.set_index('Datetime', inplace=True)
            
            return df
        except Exception as e:
            print(f"Error in standard format, trying alternative format: {e}")
            try:
                df = pd.read_csv(csv_path, header=None, 
                                names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
                df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
                
                df = df.drop(['Date', 'Time'], axis=1)
                
                df.set_index('Datetime', inplace=True)
                
                return df
            except Exception as e2:
                print(f"Error in alternative format: {e2}")
                return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    
    def load_all_data(self) -> pd.DataFrame:
        """
        すべてのCSVファイルを読み込み、1つのDataFrameに結合する
        
        Returns
        -------
        pd.DataFrame
            すべてのデータが結合されたDataFrame
        """
        csv_files = self.extract_zip_files()
        
        all_data = pd.DataFrame()
        
        for csv_file in csv_files:
            try:
                df = self.load_csv_to_dataframe(csv_file)
                all_data = pd.concat([all_data, df])
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")
        
        all_data = all_data.loc[~all_data.index.duplicated(keep='first')]
        all_data = all_data.sort_index()
        
        return all_data
