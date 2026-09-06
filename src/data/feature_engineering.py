"""
Feature Engineering Module for Retail Demand and Pricing Models
Constructs competitive price ratios, inventory turnover signals, lifecycle urgency, and temporal features.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple

class FeatureEngineer:
    def __init__(self):
        self.feature_columns: List[str] = [
            "price_ratio_mrp",
            "price_ratio_comp",
            "price_delta_comp",
            "price_delta_comp_min",
            "margin_pct",
            "opening_inventory",
            "inventory_age_days",
            "days_to_successor",
            "is_aging_model",
            "is_clearance_urgency",
            "competitor_stockout_flag",
            "footfall_index",
            "is_weekend",
            "is_festive_season",
            "day_of_week",
            "month"
        ]

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all engineered features to the unified dataframe."""
        data = df.copy()
        data["date"] = pd.to_datetime(data["date"])

        # 1. Price Ratios & Competitor Deltas
        data["price_ratio_mrp"] = data["selling_price"] / (data["mrp"] + 1e-5)
        data["price_ratio_comp"] = data["selling_price"] / (data["competitor_avg_price"] + 1e-5)
        data["price_delta_comp"] = data["selling_price"] - data["competitor_avg_price"]
        data["price_delta_comp_min"] = data["selling_price"] - data["competitor_min_price"]
        
        # 2. Margins
        data["margin_amount"] = data["selling_price"] - data["unit_cost"]
        data["margin_pct"] = (data["margin_amount"]) / (data["selling_price"] + 1e-5)

        # 3. Product Lifecycle Features
        # Ensure days_to_successor is integer
        data["days_to_successor"] = data["days_to_successor"].fillna(180).astype(int)
        data["is_aging_model"] = (data["days_to_successor"] <= 60).astype(int)
        data["is_clearance_urgency"] = (data["days_to_successor"] <= 30).astype(int)

        # 4. Temporal & Calendar Signals
        data["day_of_week"] = data["date"].dt.dayofweek
        data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
        data["month"] = data["date"].dt.month

        # Indian festive calendar identification
        # Oct/Nov (Diwali / Festive Sale) or Jan (Republic Day Sale)
        is_diwali = (data["month"].isin([10, 11])) & (data["date"].dt.day.between(14, 30))
        is_rep_day = (data["month"] == 1) & (data["date"].dt.day.between(20, 27))
        data["is_festive_season"] = (is_diwali | is_rep_day).astype(int)

        # 5. Fill any lingering NaNs in critical features
        for col in self.feature_columns:
            if col in data.columns:
                data[col] = data[col].fillna(0)

        return data

    def prepare_training_data(
        self, df: pd.DataFrame, target_col: str = "units_sold"
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Transform dataframe into feature matrix X and target y."""
        featured = self.engineer_features(df)
        X = featured[self.feature_columns]
        y = featured[target_col]
        return X, y

if __name__ == "__main__":
    from src.data.data_pipeline import DataPipeline
    dp = DataPipeline()
    raw = dp.build_unified_dataset()
    fe = FeatureEngineer()
    X, y = fe.prepare_training_data(raw)
    print(f"Features prepared: X shape {X.shape}, y shape {y.shape}")
