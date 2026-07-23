import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import *

class FeatureEngineer:
    """Performs feature engineering for ML models."""
    
    def _get_days_to_next_festival(self, dates: pd.Series) -> pd.Series:
        """Calculates days until the next festival for each date."""
        fest_path = Path(__file__).resolve().parent.parent.parent / "data" / "external" / "indian_festivals.json"
        try:
            with open(fest_path, 'r') as f:
                fest_data = json.load(f)
                festival_dates = sorted([pd.to_datetime(item['date']) for item in fest_data])
        except FileNotFoundError:
            festival_dates = []
            
        def find_next(current_date):
            if not festival_dates:
                return 365
            future_fests = [d for d in festival_dates if d >= current_date]
            if future_fests:
                return (future_fests[0] - current_date).days
            return 365
            
        return dates.apply(find_next)
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adds engineered features to the DataFrame."""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by=['product_id', 'date']).reset_index(drop=True)
        
        # Ratios
        df['price_to_cost_ratio'] = df['selling_price'] / df['cost_price']
        df['price_vs_competitor'] = df['selling_price'] / df['competitor_price']
        
        # Log transformations
        df['log_price'] = np.log(df['selling_price'] + 1e-8)
        df['log_demand'] = np.log(df['units_sold'] + 1)
        df['log_competitor_price'] = np.log(df['competitor_price'] + 1e-8)
        
        # Grouped lag features
        df['sales_lag_7d'] = df.groupby('product_id')['units_sold'].shift(7)
        df['sales_lag_14d'] = df.groupby('product_id')['units_sold'].shift(14)
        df['sales_lag_30d'] = df.groupby('product_id')['units_sold'].shift(30)
        
        # Grouped rolling means
        df['sales_rolling_7d_mean'] = df.groupby('product_id')['units_sold'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        df['sales_rolling_14d_mean'] = df.groupby('product_id')['units_sold'].transform(lambda x: x.rolling(14, min_periods=1).mean())
        df['sales_rolling_30d_mean'] = df.groupby('product_id')['units_sold'].transform(lambda x: x.rolling(30, min_periods=1).mean())
        df['price_rolling_7d_mean'] = df.groupby('product_id')['selling_price'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        
        # Price change pct
        df['price_change_pct'] = df.groupby('product_id')['selling_price'].pct_change().fillna(0)
        
        # Days to next festival
        df['days_to_next_festival'] = self._get_days_to_next_festival(df['date'])
        
        # Fill NaNs in lag features with column median
        lag_cols = ['sales_lag_7d', 'sales_lag_14d', 'sales_lag_30d']
        for col in lag_cols:
            df[col] = df[col].fillna(df[col].median())
            
        return df
        
    def prepare_ml_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """Prepares features and target for ML training."""
        # Drop any remaining rows with NaNs after feature engineering
        df = df.dropna().reset_index(drop=True)
        
        try:
            features = ALL_FEATURES
            target = TARGET_COLUMN
        except NameError:
            features = [
                'price_to_cost_ratio', 'price_vs_competitor', 'log_price', 'log_competitor_price',
                'sales_lag_7d', 'sales_lag_14d', 'sales_lag_30d',
                'sales_rolling_7d_mean', 'sales_rolling_14d_mean', 'sales_rolling_30d_mean',
                'price_rolling_7d_mean', 'days_to_next_festival', 'price_change_pct',
                'is_weekend', 'is_festival', 'discount_pct', 'rating', 'num_reviews', 'ad_spend'
            ]
            target = 'log_demand'
            
        available_features = [f for f in features if f in df.columns]
        X = df[available_features]
        y = df[target] if target in df.columns else df['units_sold']
        
        return X, y
