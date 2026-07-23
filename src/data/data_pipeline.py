import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import *

class DataPipeline:
    """Pipeline for loading, cleaning, and splitting data."""
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Loads CSV data and parses dates."""
        df = pd.read_csv(filepath, parse_dates=['date'])
        return df
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handles missing values, removes outliers, ensures correct dtypes."""
        # Handle missing values
        if 'festival_name' in df.columns:
            df['festival_name'] = df['festival_name'].fillna('None')
            
        df = df.dropna().copy()
        
        # Remove outliers (units_sold > mean + 3*std)
        mean_units = df['units_sold'].mean()
        std_units = df['units_sold'].std()
        df = df[df['units_sold'] <= (mean_units + 3 * std_units)]
        
        # Ensure correct dtypes
        df['date'] = pd.to_datetime(df['date'])
        df['product_id'] = df['product_id'].astype(str)
        return df.reset_index(drop=True)
        
    def split_data(self, df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Time-based split of the data into train, val, and test sets."""
        df = df.sort_values('date').reset_index(drop=True)
        
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        train = df.iloc[:train_end].copy()
        val = df.iloc[train_end:val_end].copy()
        test = df.iloc[val_end:].copy()
        
        return train, val, test
        
    def run(self, filepath: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Orchestrates load -> clean -> save processed data (and split)."""
        print(f"Loading data from {filepath}...")
        df = self.load_data(filepath)
        
        print("Cleaning data...")
        df_clean = self.clean_data(df)
        
        print("Splitting data...")
        train, val, test = self.split_data(df_clean)
        
        processed_dir = Path(filepath).parent.parent / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        train.to_csv(processed_dir / "train.csv", index=False)
        val.to_csv(processed_dir / "val.csv", index=False)
        test.to_csv(processed_dir / "test.csv", index=False)
        print(f"Processed data saved to {processed_dir}")
        
        return train, val, test
