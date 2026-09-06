"""
Demand Forecasting Module
Trains gradient-boosted and tree models to forecast product demand as a function of
price, competitor context, inventory levels, lifecycle stage, and market temporal factors.
"""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
from src.config import MODELS_DIR
from src.data.feature_engineering import FeatureEngineer

class DemandForecaster:
    def __init__(self, model_type: str = "lightgbm"):
        self.model_type = model_type
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.feature_names = self.feature_engineer.feature_columns
        self.metrics: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> Dict[str, float]:
        """Train the demand forecaster on historical sales data."""
        X, y = self.feature_engineer.prepare_training_data(df, target_col="units_sold")
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        if self.model_type == "lightgbm":
            self.model = lgb.LGBMRegressor(
                n_estimators=150,
                learning_rate=0.05,
                num_leaves=31,
                random_state=42,
                verbosity=-1
            )
        elif self.model_type == "gradient_boosting":
            self.model = GradientBoostingRegressor(
                n_estimators=120,
                learning_rate=0.05,
                max_depth=4,
                random_state=42
            )
        else:
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=6,
                random_state=42
            )

        self.model.fit(X_train, y_train)

        # Evaluate on validation
        preds = np.maximum(0, self.model.predict(X_val))
        mae = float(mean_absolute_error(y_val, preds))
        rmse = float(np.sqrt(mean_squared_error(y_val, preds)))
        r2 = float(r2_score(y_val, preds))

        self.metrics = {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 3),
            "val_samples": len(y_val)
        }

        # Save model
        self.save()
        return self.metrics

    def predict_point(
        self,
        selling_price: float,
        mrp: float,
        competitor_avg_price: float,
        competitor_min_price: float,
        unit_cost: float,
        opening_inventory: int,
        inventory_age_days: int = 45,
        days_to_successor: int = 60,
        competitor_stockout_flag: int = 0,
        footfall_index: float = 1.2,
        is_weekend: int = 0,
        is_festive_season: int = 0,
        day_of_week: int = 2,
        month: int = 9
    ) -> float:
        """Predict expected daily demand for a specific price & context point."""
        if self.model is None:
            self.load()

        # Build single-row feature dataframe
        price_ratio_mrp = selling_price / (mrp + 1e-5)
        price_ratio_comp = selling_price / (competitor_avg_price + 1e-5)
        price_delta_comp = selling_price - competitor_avg_price
        price_delta_comp_min = selling_price - competitor_min_price
        margin_pct = (selling_price - unit_cost) / (selling_price + 1e-5)

        is_aging_model = 1 if days_to_successor <= 60 else 0
        is_clearance_urgency = 1 if days_to_successor <= 30 else 0

        row = pd.DataFrame([{
            "price_ratio_mrp": price_ratio_mrp,
            "price_ratio_comp": price_ratio_comp,
            "price_delta_comp": price_delta_comp,
            "price_delta_comp_min": price_delta_comp_min,
            "margin_pct": margin_pct,
            "opening_inventory": opening_inventory,
            "inventory_age_days": inventory_age_days,
            "days_to_successor": days_to_successor,
            "is_aging_model": is_aging_model,
            "is_clearance_urgency": is_clearance_urgency,
            "competitor_stockout_flag": competitor_stockout_flag,
            "footfall_index": footfall_index,
            "is_weekend": is_weekend,
            "is_festive_season": is_festive_season,
            "day_of_week": day_of_week,
            "month": month
        }])[self.feature_names]

        pred = float(self.model.predict(row)[0])
        return max(0.0, pred)

    def predict_demand_curve(
        self,
        candidate_prices: np.ndarray,
        mrp: float,
        competitor_avg_price: float,
        competitor_min_price: float,
        unit_cost: float,
        opening_inventory: int,
        days_to_successor: int = 60,
        competitor_stockout_flag: int = 0,
        footfall_index: float = 1.2
    ) -> np.ndarray:
        """Evaluate demand across an array of candidate prices."""
        if self.model is None:
            self.load()

        rows = []
        for p in candidate_prices:
            rows.append({
                "price_ratio_mrp": p / (mrp + 1e-5),
                "price_ratio_comp": p / (competitor_avg_price + 1e-5),
                "price_delta_comp": p - competitor_avg_price,
                "price_delta_comp_min": p - competitor_min_price,
                "margin_pct": (p - unit_cost) / (p + 1e-5),
                "opening_inventory": opening_inventory,
                "inventory_age_days": 45,
                "days_to_successor": days_to_successor,
                "is_aging_model": 1 if days_to_successor <= 60 else 0,
                "is_clearance_urgency": 1 if days_to_successor <= 30 else 0,
                "competitor_stockout_flag": competitor_stockout_flag,
                "footfall_index": footfall_index,
                "is_weekend": 0,
                "is_festive_season": 0,
                "day_of_week": 2,
                "month": 9
            })

        features_df = pd.DataFrame(rows)[self.feature_names]
        preds = self.model.predict(features_df)
        return np.maximum(0.0, preds)

    def save(self, filepath: Optional[Path] = None):
        """Persist model and metadata to disk."""
        target = filepath or (MODELS_DIR / f"demand_forecaster_{self.model_type}.joblib")
        joblib.dump({
            "model": self.model,
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "metrics": self.metrics
        }, target)

    def load(self, filepath: Optional[Path] = None):
        """Load model and metadata from disk."""
        target = filepath or (MODELS_DIR / f"demand_forecaster_{self.model_type}.joblib")
        if not target.exists():
            raise FileNotFoundError(f"Model file not found at {target}. Fit model first.")
        bundle = joblib.load(target)
        self.model = bundle["model"]
        self.model_type = bundle["model_type"]
        self.feature_names = bundle["feature_names"]
        self.metrics = bundle["metrics"]
