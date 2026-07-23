import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
from typing import Dict, Any, Union, Optional

try:
    from src.utils.config import LGBM_PARAMS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
except ImportError:
    LGBM_PARAMS = {
        'objective': 'regression',
        'metric': 'rmse',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'max_depth': 6,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_samples': 20,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'n_estimators': 500,
        'verbose': -1,
        'random_state': 42,
    }

    NUMERICAL_FEATURES = [
        'selling_price', 'cost_price', 'competitor_price',
        'discount_pct', 'rating', 'num_reviews', 'ad_spend',
        'price_to_cost_ratio', 'price_vs_competitor',
        'sales_lag_7d', 'sales_lag_14d', 'sales_lag_30d',
        'sales_rolling_7d_mean', 'sales_rolling_14d_mean',
        'sales_rolling_30d_mean', 'price_rolling_7d_mean',
        'days_to_next_festival',
    ]
    CATEGORICAL_FEATURES = [
        'product_category', 'day_of_week', 'month',
        'season', 'is_weekend', 'is_festival',
    ]

ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES


class DemandForecaster:
    """LightGBM based model for demand forecasting."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize with LightGBM params. Default from config.LGBM_PARAMS."""
        self.params = params if params is not None else LGBM_PARAMS
        self.model = lgb.LGBMRegressor(**self.params)
        self.evals_result_ = {}
        
    def train(self, X_train: pd.DataFrame, y_train: Union[pd.Series, np.ndarray], 
              X_val: Optional[pd.DataFrame] = None, y_val: Optional[Union[pd.Series, np.ndarray]] = None) -> None:
        """Train the model. Use early stopping if validation data provided."""
        
        callbacks = []
        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))
            callbacks.append(lgb.early_stopping(stopping_rounds=50, verbose=False))
            callbacks.append(lgb.record_evaluation(self.evals_result_))
            
        # Ensure categorical features are explicitly set
        cat_features_idx = [X_train.columns.get_loc(col) for col in CATEGORICAL_FEATURES if col in X_train.columns]
            
        self.model.fit(
            X_train, 
            y_train,
            eval_set=eval_set if eval_set else None,
            categorical_feature=cat_features_idx if cat_features_idx else 'auto',
            callbacks=callbacks if callbacks else None
        )
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict demand. Clip predictions to >= 0."""
        preds = self.model.predict(X)
        return np.clip(preds, a_min=0, a_max=None)
        
    def predict_at_price(self, base_features: Union[Dict[str, Any], pd.Series], 
                         price: float, cost_price: float, competitor_price: Optional[float] = None) -> float:
        """Predict demand at a specific price point.
        Takes a dict or Series of base features and overrides the price-related features.
        Updates: selling_price, price_to_cost_ratio, price_vs_competitor, log_price
        Returns predicted units_sold (float)."""
        
        if isinstance(base_features, pd.Series):
            features_dict = base_features.to_dict()
        else:
            features_dict = dict(base_features)
            
        # Override price features
        features_dict['selling_price'] = price
        features_dict['cost_price'] = cost_price
        features_dict['price_to_cost_ratio'] = price / cost_price if cost_price > 0 else 0
        
        if competitor_price is not None and competitor_price > 0:
            features_dict['competitor_price'] = competitor_price
            features_dict['price_vs_competitor'] = price / competitor_price
        else:
            features_dict['price_vs_competitor'] = features_dict.get('price_vs_competitor', 1.0)
            
        features_dict['log_price'] = np.log(price) if price > 0 else 0
        
        # Create a single-row DataFrame
        df_row = pd.DataFrame([features_dict])
        
        # Ensure all features exist
        for col in ALL_FEATURES:
            if col not in df_row.columns:
                df_row[col] = 0
                
        # Handle categorical dtypes
        for col in CATEGORICAL_FEATURES:
            if col in df_row.columns:
                df_row[col] = df_row[col].astype('category')
                
        # Reorder to match ALL_FEATURES exactly
        cols_to_use = [c for c in ALL_FEATURES if c in df_row.columns]
        pred = self.predict(df_row[cols_to_use])[0]
        return float(pred)
        
    def get_feature_importance(self) -> pd.DataFrame:
        """Return DataFrame with feature names and importance scores, sorted descending."""
        importance = self.model.feature_importances_
        features = self.model.feature_name_
        
        df_imp = pd.DataFrame({
            'feature': features,
            'importance': importance
        })
        return df_imp.sort_values(by='importance', ascending=False).reset_index(drop=True)
        
    def save(self, filepath: Union[str, Path]) -> None:
        """Save model to disk using joblib."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, filepath)
        
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "DemandForecaster":
        """Load model from disk."""
        instance = cls()
        instance.model = joblib.load(filepath)
        return instance
