import sys
import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.config import *

class PriceOptimizer:
    def __init__(self, demand_model, cost_price, min_price=None, max_price=None):
        """Initialize optimizer.
        - demand_model: a trained DemandForecaster with predict_at_price() method
        - cost_price: float, the product's cost
        - min_price: float, minimum allowed price (default: cost × 1.1)
        - max_price: float, maximum allowed price (default: cost × 5.0)
        """
        self.demand_model = demand_model
        self.cost_price = cost_price
        self.min_price = min_price if min_price is not None else cost_price * 1.1
        self.max_price = max_price if max_price is not None else cost_price * 5.0
        
    def _profit_function(self, price, base_features, competitor_price):
        """Calculate profit at a given price:
        profit = (price - cost) × demand_model.predict_at_price(base_features, price, cost, competitor_price)
        Return NEGATIVE profit (because scipy minimizes)."""
        demand = self.demand_model.predict_at_price(base_features, price, self.cost_price, competitor_price)
        profit = (price - self.cost_price) * demand
        return -profit
        
    def optimize(self, base_features, competitor_price=None):
        """Find the optimal price that maximizes profit.
        Uses scipy.optimize.minimize_scalar with method='bounded'.
        
        Returns dict:
        {
            'optimal_price': float,
            'predicted_demand': float,
            'daily_profit': float,
            'daily_revenue': float,
            'monthly_profit': float,
            'margin_pct': float,
        }
        """
        res = minimize_scalar(
            self._profit_function,
            bounds=(self.min_price, self.max_price),
            args=(base_features, competitor_price),
            method='bounded'
        )
        
        optimal_price = res.x
        predicted_demand = self.demand_model.predict_at_price(base_features, optimal_price, self.cost_price, competitor_price)
        daily_profit = (optimal_price - self.cost_price) * predicted_demand
        daily_revenue = optimal_price * predicted_demand
        
        return {
            'optimal_price': float(optimal_price),
            'predicted_demand': float(predicted_demand),
            'daily_profit': float(daily_profit),
            'daily_revenue': float(daily_revenue),
            'monthly_profit': float(daily_profit * 30),
            'margin_pct': float(((optimal_price - self.cost_price) / optimal_price) * 100) if optimal_price > 0 else 0.0,
        }
        
    def generate_profit_curve(self, base_features, competitor_price=None, n_points=200):
        """Generate profit, demand, and revenue at each price point.
        Returns dict with keys: 'prices', 'profits', 'demands', 'revenues', 'margins'
        Each value is a numpy array of length n_points.
        This is used for the profit curve visualization."""
        prices = np.linspace(self.min_price, self.max_price, n_points)
        demands = np.zeros(n_points)
        for i, p in enumerate(prices):
            demands[i] = self.demand_model.predict_at_price(base_features, p, self.cost_price, competitor_price)
            
        profits = (prices - self.cost_price) * demands
        revenues = prices * demands
        margins = np.where(prices > 0, ((prices - self.cost_price) / prices) * 100, 0)
        
        return {
            'prices': prices,
            'profits': profits,
            'demands': demands,
            'revenues': revenues,
            'margins': margins
        }
        
    def compare_with_current(self, current_price, base_features, competitor_price=None):
        """Compare optimal price vs current price.
        Returns dict with:
        {
            'current': {price, demand, daily_profit, monthly_profit},
            'optimal': {price, demand, daily_profit, monthly_profit},
            'improvement': {demand_change_pct, profit_change_pct, monthly_extra_profit},
        }
        """
        current_demand = self.demand_model.predict_at_price(base_features, current_price, self.cost_price, competitor_price)
        current_daily_profit = (current_price - self.cost_price) * current_demand
        
        opt = self.optimize(base_features, competitor_price)
        
        demand_change_pct = ((opt['predicted_demand'] - current_demand) / current_demand) * 100 if current_demand > 0 else 0
        profit_change_pct = ((opt['daily_profit'] - current_daily_profit) / current_daily_profit) * 100 if current_daily_profit > 0 else 0
        monthly_extra_profit = opt['monthly_profit'] - (current_daily_profit * 30)
        
        return {
            'current': {
                'price': current_price,
                'demand': current_demand,
                'daily_profit': current_daily_profit,
                'monthly_profit': current_daily_profit * 30
            },
            'optimal': {
                'price': opt['optimal_price'],
                'demand': opt['predicted_demand'],
                'daily_profit': opt['daily_profit'],
                'monthly_profit': opt['monthly_profit']
            },
            'improvement': {
                'demand_change_pct': demand_change_pct,
                'profit_change_pct': profit_change_pct,
                'monthly_extra_profit': monthly_extra_profit
            }
        }
