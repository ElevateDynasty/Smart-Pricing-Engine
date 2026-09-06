"""
Model Evaluator for Pricing & Demand Forecasts
Calculates statistical and economic evaluation metrics across SKU segments and price bands.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class ModelEvaluator:
    @staticmethod
    def calculate_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute standard regression accuracy indicators."""
        y_true = np.array(y_true, dtype=float)
        y_pred = np.maximum(0.0, np.array(y_pred, dtype=float))

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        
        # Mean Absolute Percentage Error (handling zero sales with epsilon)
        nonzero_mask = y_true > 0
        if nonzero_mask.sum() > 0:
            mape = float(np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]))) * 100.0
        else:
            mape = 0.0

        return {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 3),
            "mape_pct": round(mape, 2)
        }

    @staticmethod
    def evaluate_price_curve_monotonicity(
        candidate_prices: np.ndarray, predicted_demands: np.ndarray
    ) -> Dict[str, Any]:
        """
        Economic sanity check:
        Ensures that as price increases, predicted demand generally decreases (Law of Demand).
        """
        diffs = np.diff(predicted_demands)
        # Violations occur where demand strictly increases with price
        violations = (diffs > 0.05).sum()
        monotonicity_score = 1.0 - (violations / max(1, len(diffs)))
        
        return {
            "is_predominantly_monotonic": bool(monotonicity_score >= 0.85),
            "monotonicity_score": round(float(monotonicity_score), 3),
            "monotonic_violations": int(violations)
        }
