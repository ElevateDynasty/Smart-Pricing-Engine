import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import statsmodels.api as sm
import joblib
from typing import Dict, Any, Union, Optional, Tuple

try:
    from src.utils.config import *
except ImportError:
    pass


class ElasticityEstimator:
    """Estimates price elasticity using log-log OLS regression."""
    
    def __init__(self):
        """Uses statsmodels OLS for interpretable regression."""
        self.model = None
        self.results = None
        self.category_models = {}
        
    def _prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare dataframe for log-log regression."""
        X = pd.DataFrame()
        X['log_price'] = np.log(df['selling_price'].clip(lower=0.01))
        
        if 'is_weekend' in df.columns:
            X['is_weekend'] = df['is_weekend'].astype(int)
        else:
            X['is_weekend'] = 0
            
        if 'is_festival' in df.columns:
            X['is_festival'] = df['is_festival'].astype(int)
        else:
            X['is_festival'] = 0
            
        if 'competitor_price' in df.columns:
            X['log_competitor_price'] = np.log(df['competitor_price'].clip(lower=0.01))
        else:
            X['log_competitor_price'] = 0
            
        X = sm.add_constant(X)
        y = np.log(df['units_sold'].clip(lower=0) + 1)
        
        return X, y
        
    def fit(self, df: pd.DataFrame) -> None:
        """Fit log-log model: log(units_sold+1) = α - β·log(price) + γ₁·is_weekend + γ₂·is_festival + γ₃·log(competitor_price) + ε
        Store the fitted model, coefficients, R², p-values."""
        X, y = self._prepare_data(df)
        
        self.model = sm.OLS(y, X)
        self.results = self.model.fit()
        
    def fit_by_category(self, df: pd.DataFrame) -> Dict[str, float]:
        """Fit separate elasticity models per product_category. Returns dict {category: β}."""
        if 'product_category' not in df.columns:
            raise ValueError("Dataframe must contain 'product_category' column")
            
        elasticities = {}
        for category, group in df.groupby('product_category'):
            if len(group) < 10: 
                continue
                
            X, y = self._prepare_data(group)
            model = sm.OLS(y, X)
            results = model.fit()
            
            self.category_models[category] = results
            
            if 'log_price' in results.params:
                elasticities[category] = results.params['log_price']
                
        return elasticities
        
    def get_elasticity(self, category: Optional[str] = None) -> float:
        """Return the price elasticity coefficient β.
        If category specified, return category-specific elasticity."""
        if category is not None and category in self.category_models:
            return self.category_models[category].params.get('log_price', 0.0)
            
        if self.results is not None:
            return self.results.params.get('log_price', 0.0)
            
        raise ValueError("Model not fitted yet.")
        
    def get_summary(self) -> str:
        """Return the statsmodels OLS summary as string."""
        if self.results is not None:
            return self.results.summary().as_text()
        return "Model not fitted."
        
    def predict_demand_at_price(self, price: float, base_demand_log: float, 
                                is_weekend: bool = False, is_festival: bool = False, 
                                competitor_price: Optional[float] = None) -> float:
        """Using the fitted log-log model, predict demand at a given price."""
        if self.results is None:
            raise ValueError("Model not fitted.")
            
        log_price = np.log(max(price, 0.01))
        log_comp_price = np.log(max(competitor_price, 0.01)) if competitor_price else 0.0
        
        params = self.results.params
        pred_log_demand = (params.get('const', 0) + 
                           params.get('log_price', 0) * log_price + 
                           params.get('is_weekend', 0) * int(is_weekend) + 
                           params.get('is_festival', 0) * int(is_festival) + 
                           params.get('log_competitor_price', 0) * log_comp_price)
                           
        return max(np.exp(pred_log_demand) - 1, 0)
        
    def calculate_point_elasticity(self, demand_model, features: Dict[str, Any], 
                                   price: float, cost_price: float, 
                                   competitor_price: float, delta_pct: float = 0.01) -> float:
        """Calculate numerical point elasticity using the LightGBM model:
        ε = (ΔQ/Q) / (ΔP/P) using finite differences around current price.
        This is more accurate than the constant elasticity from log-log regression."""
        
        price_up = price * (1 + delta_pct)
        price_down = price * (1 - delta_pct)
        
        q_up = demand_model.predict_at_price(features, price_up, cost_price, competitor_price)
        q_down = demand_model.predict_at_price(features, price_down, cost_price, competitor_price)
        
        delta_q = q_up - q_down
        delta_p = price_up - price_down
        
        q_current = (q_up + q_down) / 2
        
        if q_current <= 0 or price <= 0:
            return 0.0
            
        elasticity = (delta_q / delta_p) * (price / q_current)
        return elasticity
        
    def save(self, filepath: Union[str, Path]) -> None:
        """Save to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({'results': self.results, 'category_models': self.category_models}, filepath)
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "ElasticityEstimator":
        """Load from disk."""
        instance = cls()
        data = joblib.load(filepath)
        instance.results = data.get('results')
        instance.category_models = data.get('category_models', {})
        return instance
