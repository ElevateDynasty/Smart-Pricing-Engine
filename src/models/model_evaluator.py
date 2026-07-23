import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

try:
    from src.utils.config import *
except ImportError:
    pass


class ModelEvaluator:
    """Class for evaluating and comparing model performance."""
    
    def __init__(self):
        self.results = {}  # {model_name: {metric: value}}
    
    def evaluate(self, model_name: str, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate RMSE, MAE, MAPE, R² and store results."""
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        
        if len(y_true) == 0 or len(y_pred) == 0:
            raise ValueError("Arrays cannot be empty.")
            
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        mask = y_true != 0
        if np.any(mask):
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = np.nan
            
        metrics = {
            'RMSE': rmse,
            'MAE': mae,
            'MAPE (%)': mape,
            'R²': r2
        }
        
        self.results[model_name] = metrics
        return metrics
        
    def compare_models(self) -> pd.DataFrame:
        """Return a DataFrame comparing all evaluated models."""
        if not self.results:
            return pd.DataFrame()
            
        df = pd.DataFrame.from_dict(self.results, orient='index')
        return df.sort_values(by='RMSE', ascending=True)
        
    def get_residuals(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
        """Return residuals array."""
        return np.asarray(y_true) - np.asarray(y_pred)
        
    def print_report(self) -> None:
        """Pretty-print comparison table."""
        df = self.compare_models()
        if df.empty:
            print("No models evaluated yet.")
            return
            
        print("=" * 50)
        print("MODEL EVALUATION REPORT")
        print("=" * 50)
        print(df.to_string())
        print("=" * 50)
