import sys
import os
import pandas as pd
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.config import *
from src.optimization.price_optimizer import PriceOptimizer

class ScenarioEngine:
    def __init__(self, optimizer: PriceOptimizer):
        """Takes a configured PriceOptimizer instance."""
        self.optimizer = optimizer
        
    def festival_scenario(self, base_features: Dict[str, Any], festival_name: str = None) -> Dict[str, Any]:
        """What-if: festival period pricing.
        Sets is_festival=1 in features, re-optimizes.
        Returns comparison dict (normal vs festival optimal)."""
        normal_opt = self.optimizer.optimize(base_features)
        
        fest_features = base_features.copy()
        fest_features['is_festival'] = 1
        if festival_name is not None and 'festival_name' in fest_features:
            fest_features['festival_name'] = festival_name
            
        fest_opt = self.optimizer.optimize(fest_features)
        
        return {
            'normal_scenario': normal_opt,
            'festival_scenario': fest_opt,
            'profit_diff': fest_opt['daily_profit'] - normal_opt['daily_profit']
        }
        
    def competitor_undercut_scenario(self, base_features: Dict[str, Any], competitor_prices: List[float]) -> List[Dict[str, Any]]:
        """What-if: competitor changes price.
        Takes list of competitor prices, returns optimal price for each.
        Returns list of dicts."""
        results = []
        for comp_price in competitor_prices:
            opt = self.optimizer.optimize(base_features, competitor_price=comp_price)
            opt['competitor_price'] = comp_price
            results.append(opt)
        return results
        
    def weekend_scenario(self, base_features: Dict[str, Any]) -> Dict[str, Any]:
        """Compare weekday vs weekend optimal pricing."""
        weekday_features = base_features.copy()
        weekday_features['is_weekend'] = 0
        weekday_opt = self.optimizer.optimize(weekday_features)
        
        weekend_features = base_features.copy()
        weekend_features['is_weekend'] = 1
        weekend_opt = self.optimizer.optimize(weekend_features)
        
        return {
            'weekday_scenario': weekday_opt,
            'weekend_scenario': weekend_opt,
            'profit_diff': weekend_opt['daily_profit'] - weekday_opt['daily_profit']
        }
        
    def sensitivity_analysis(self, base_features: Dict[str, Any], competitor_price: float = None, price_range_pct: float = 0.3, n_points: int = 50) -> pd.DataFrame:
        """Analyze how small price changes around optimal affect profit.
        Returns DataFrame with columns: price, demand, profit, pct_from_optimal."""
        opt = self.optimizer.optimize(base_features, competitor_price)
        optimal_price = opt['optimal_price']
        
        min_p = max(self.optimizer.min_price, optimal_price * (1 - price_range_pct))
        max_p = min(self.optimizer.max_price, optimal_price * (1 + price_range_pct))
        
        import numpy as np
        test_prices = np.linspace(min_p, max_p, n_points)
        
        data = []
        for p in test_prices:
            d = self.optimizer.demand_model.predict_at_price(base_features, p, self.optimizer.cost_price, competitor_price)
            prof = (p - self.optimizer.cost_price) * d
            pct_diff = ((p - optimal_price) / optimal_price) * 100
            data.append({
                'price': p,
                'demand': d,
                'profit': prof,
                'pct_from_optimal': pct_diff
            })
            
        return pd.DataFrame(data)
        
    def run_all_scenarios(self, base_features: Dict[str, Any], competitor_price: float = None) -> Dict[str, Any]:
        """Run all scenarios and return a comprehensive report dict."""
        return {
            'baseline': self.optimizer.optimize(base_features, competitor_price),
            'festival': self.festival_scenario(base_features),
            'weekend': self.weekend_scenario(base_features)
        }
