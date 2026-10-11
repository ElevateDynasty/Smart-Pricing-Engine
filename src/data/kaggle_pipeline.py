"""
Kaggle Retail Price Optimization Pipeline
Loads the Kaggle Retail Price Optimization dataset, engineers competitive pricing features,
trains a LightGBM demand forecaster, and computes econometric price elasticity coefficients.
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import statsmodels.api as sm

from src.config import RAW_DATA_DIR, MODELS_DIR

KAGGLE_DATASET_SLUG = "suddharshan/retail-price-optimization"
KAGGLE_RAW_CSV = RAW_DATA_DIR / "retail_price.csv"
KAGGLE_MODEL_FILE = MODELS_DIR / "demand_forecaster_kaggle.joblib"

class KaggleRetailPipeline:
    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or KAGGLE_RAW_CSV
        self.model = None
        self.metrics: Dict[str, float] = {}
        self.feature_names = [
            "unit_price",
            "competitor_avg_price",
            "competitor_min_price",
            "price_ratio_comp",
            "price_delta_comp",
            "price_delta_comp_min",
            "lag_price",
            "freight_price",
            "product_score",
            "customers",
            "weekday",
            "weekend",
            "holiday",
            "month"
        ]

    def ensure_dataset(self) -> Path:
        """Ensure the Kaggle dataset is present, downloading via Kaggle API if needed."""
        if self.csv_path.exists():
            return self.csv_path

        print(f"Downloading dataset '{KAGGLE_DATASET_SLUG}' from Kaggle...")
        import subprocess
        cmd = [
            "kaggle", "datasets", "download",
            "-d", KAGGLE_DATASET_SLUG,
            "-p", str(RAW_DATA_DIR),
            "--unzip"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to download Kaggle dataset: {res.stderr}")

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Expected file {self.csv_path} not found after Kaggle download.")

        print(f"Successfully downloaded to {self.csv_path}")
        return self.csv_path

    def load_and_preprocess(self) -> pd.DataFrame:
        """Load and engineer features from Kaggle retail_price.csv."""
        self.ensure_dataset()
        df = pd.read_csv(self.csv_path)

        # Calculate competitor price aggregates from comp_1, comp_2, comp_3
        comp_cols = ["comp_1", "comp_2", "comp_3"]
        df["competitor_avg_price"] = df[comp_cols].mean(axis=1)
        df["competitor_min_price"] = df[comp_cols].min(axis=1)
        df["competitor_max_price"] = df[comp_cols].max(axis=1)

        # Fill any missing competitor prices with the item's own unit_price
        df["competitor_avg_price"] = df["competitor_avg_price"].fillna(df["unit_price"])
        df["competitor_min_price"] = df["competitor_min_price"].fillna(df["unit_price"])

        # Price ratios and differentials
        df["price_ratio_comp"] = df["unit_price"] / (df["competitor_avg_price"] + 1e-5)
        df["price_delta_comp"] = df["unit_price"] - df["competitor_avg_price"]
        df["price_delta_comp_min"] = df["unit_price"] - df["competitor_min_price"]

        return df

    def train_demand_forecaster(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train LightGBM regressor to predict sales quantity (qty).

        Uses a TIME-ORDERED 80/20 split on (year, month) — training on earlier
        months, validating on strictly later months — so real-data metrics are
        leakage-free and honest.
        """
        if {"year", "month"}.issubset(df.columns):
            df = df.sort_values(["year", "month"]).reset_index(drop=True)

        X = df[self.feature_names].copy()
        y = df["qty"]

        split_idx = int(len(X) * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        model = lgb.LGBMRegressor(
            n_estimators=160,
            learning_rate=0.04,
            num_leaves=25,
            min_child_samples=5,
            random_state=42,
            verbosity=-1
        )
        model.fit(X_train, y_train)

        preds = np.maximum(0, model.predict(X_val))
        mae = float(mean_absolute_error(y_val, preds))
        rmse = float(np.sqrt(mean_squared_error(y_val, preds)))
        r2 = float(r2_score(y_val, preds))

        self.model = model
        self.metrics = {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 3),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "split_strategy": "time-ordered 80/20 on (year, month) — leakage-free",
            "leakage_free": True
        }

        # Feature importances
        importances = dict(zip(self.feature_names, model.feature_importances_))
        sorted_importance = sorted(importances.items(), key=lambda x: x[1], reverse=True)

        # Save model
        joblib.dump({
            "model": model,
            "feature_names": self.feature_names,
            "metrics": self.metrics,
            "feature_importances": sorted_importance
        }, KAGGLE_MODEL_FILE)

        return {
            "metrics": self.metrics,
            "feature_importances": sorted_importance
        }

    def estimate_elasticity(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Estimate econometric price elasticity by category:
        ln(qty + 1) = alpha - beta * ln(unit_price / competitor_avg_price) + gamma * weekend + holiday + eps
        """
        results = {}
        categories = df["product_category_name"].unique()

        for cat in categories:
            sub = df[df["product_category_name"] == cat].copy()
            if len(sub) < 15:
                continue

            sub = sub[(sub["unit_price"] > 0) & (sub["competitor_avg_price"] > 0)]
            y = np.log(sub["qty"] + 1.0)
            log_price_ratio = np.log(sub["unit_price"] / sub["competitor_avg_price"])
            weekend = sub["weekend"]
            holiday = sub["holiday"]

            X = pd.DataFrame({
                "const": 1.0,
                "log_price_ratio": log_price_ratio,
                "weekend": weekend,
                "holiday": holiday
            })

            try:
                ols = sm.OLS(y, X).fit()
                raw_beta = -float(ols.params.get("log_price_ratio", 1.5))
                beta = max(0.2, min(5.0, raw_beta))
                r2 = float(ols.rsquared)

                if beta > 1.8:
                    regime = "Highly Elastic"
                    recommendation = "Sensitive to pricing. Markdowns drive substantial sales velocity."
                elif beta >= 1.0:
                    regime = "Moderately Elastic"
                    recommendation = "Balanced responsiveness. Stay closely aligned with competitor movements."
                else:
                    regime = "Inelastic"
                    recommendation = "Low price sensitivity. Maintain prices or selectively raise margins."

                results[cat] = {
                    "elasticity": round(beta, 2),
                    "regime": regime,
                    "r_squared": round(r2, 3),
                    "sample_count": len(sub),
                    "avg_price": round(float(sub["unit_price"].mean()), 2),
                    "recommendation": recommendation
                }
            except Exception:
                continue

        return results

    def run_kaggle_pipeline(self) -> Dict[str, Any]:
        """Execute complete Kaggle data ingestion, training, and evaluation workflow."""
        print("=" * 70)
        print("KAGGLE RETAIL DATASET: INGESTION, TRAINING & ELASTICITY")
        print("=" * 70)

        df = self.load_and_preprocess()
        print(f"Loaded {len(df)} records across {df['product_id'].nunique()} SKUs and {df['product_category_name'].nunique()} categories.")
        print(f"Dataset path: {self.csv_path}")

        print("\nTraining LightGBM Demand Forecaster on Kaggle Data...")
        train_res = self.train_demand_forecaster(df)
        m = train_res["metrics"]
        print(f"Model Trained Successfully!")
        print(f"Validation MAE : {m['mae']} units")
        print(f"Validation RMSE: {m['rmse']}")
        print(f"Validation R2  : {m['r2']}")
        print(f"Saved to       : {KAGGLE_MODEL_FILE}")

        print("\nTop 5 Most Influential Predictive Features:")
        for feat, imp in train_res["feature_importances"][:5]:
            print(f"  - {feat:25}: importance {imp}")

        print("\nEconometric Price Elasticity by Retail Category:")
        elasticities = self.estimate_elasticity(df)
        for cat, el in elasticities.items():
            print(f"  Category: {cat:22} | Elasticity: {el['elasticity']:4.2f} ({el['regime']:18}) | R2: {el['r_squared']:4.2f} | Avg Price: ${el['avg_price']}")

        return {
            "dataframe": df,
            "training_results": train_res,
            "elasticities": elasticities
        }

class KaggleDemandAdapter:
    """
    Adapts the real-data Kaggle LightGBM to the DemandForecaster interface
    consumed by LifecycleOptimizer, so the constrained optimizer can run
    end-to-end on products from the real retail dataset.

    IMPORTANT: set 'current_product_id' before calling predict_point /
    predict_demand_curve - per-product covariates (product_score, customers,
    freight_price, calendar context) are selected for that product.

    Documented imputations (real dataset has no MRP/inventory/lifecycle):
      - MRP, unit cost, inventory and successor horizon are supplied by the
        caller (analytics layer) as economic assumptions, not by the model.
    """

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        model_path: Path = KAGGLE_MODEL_FILE
    ):
        self.csv_path = csv_path or KAGGLE_RAW_CSV
        if not model_path.exists():
            raise FileNotFoundError(
                "Kaggle model not found at " + str(model_path) + ". Run 'python main.py --kaggle' first."
            )
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.feature_names = bundle["feature_names"]
        self.metrics = bundle.get("metrics", {})
        self.current_product_id: Optional[str] = None
        self._build_product_stats()

    def _build_product_stats(self):
        df = pd.read_csv(self.csv_path)
        stats = {}
        for pid, sub in df.groupby("product_id"):
            stats[pid] = {
                "product_score": float(sub["product_score"].median()),
                "customers": float(sub["customers"].median()),
                "freight_price": float(sub["freight_price"].median()),
                "weekday": int(sub["weekday"].mode().iloc[0]) if len(sub) else 2,
                "weekend": int(sub["weekend"].mode().iloc[0]) if len(sub) else 0,
                "holiday": int(sub["holiday"].mode().iloc[0]) if len(sub) else 0,
                "month": int(sub["month"].max()),
                "last_unit_price": float(sub["unit_price"].iloc[-1]),
                "max_unit_price": float(sub["unit_price"].max()),
                "median_qty": float(sub["qty"].median()),
                "category": str(sub["product_category_name"].iloc[0])
            }
        self.product_stats = stats

        # Global defaults for unseen product ids
        self.default_stats = {
            "product_score": float(df["product_score"].median()),
            "customers": float(df["customers"].median()),
            "freight_price": float(df["freight_price"].median()),
            "weekday": 2, "weekend": 0, "holiday": 0,
            "month": int(df["month"].max()),
            "last_unit_price": float(df["unit_price"].median()),
            "max_unit_price": float(df["unit_price"].median()),
            "median_qty": float(df["qty"].median()),
            "category": "unknown"
        }

    def _row(self, selling_price: float, competitor_avg_price: float,
             competitor_min_price: float) -> pd.DataFrame:
        stats = self.product_stats.get(self.current_product_id, self.default_stats)
        lag = stats["last_unit_price"]
        row = pd.DataFrame([{
            "unit_price": selling_price,
            "competitor_avg_price": competitor_avg_price,
            "competitor_min_price": competitor_min_price,
            "price_ratio_comp": selling_price / (competitor_avg_price + 1e-5),
            "price_delta_comp": selling_price - competitor_avg_price,
            "price_delta_comp_min": selling_price - competitor_min_price,
            "lag_price": lag,
            "freight_price": stats["freight_price"],
            "product_score": stats["product_score"],
            "customers": stats["customers"],
            "weekday": stats["weekday"],
            "weekend": stats["weekend"],
            "holiday": stats["holiday"],
            "month": stats["month"]
        }])[self.feature_names]
        return row

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
        """Predict expected daily qty for a product from the real dataset.

        mrp / unit_cost / inventory / days_to_successor are accepted for
        interface compatibility but do not exist in the real dataset's feature
        schema; the demand model itself is unaffected by them.
        """
        row = self._row(selling_price, competitor_avg_price, competitor_min_price)
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
        """Evaluate demand across an array of candidate prices (real-data model)."""
        rows = []
        for p in candidate_prices:
            rows.append(self._row(float(p), competitor_avg_price, competitor_min_price))
        features_df = pd.concat(rows, ignore_index=True)[self.feature_names]
        preds = self.model.predict(features_df)
        return np.maximum(0.0, preds)

    def explain_point(
        self,
        selling_price: float,
        competitor_avg_price: float,
        competitor_min_price: float
    ) -> Dict[str, Any]:
        """Native TreeSHAP explanation for the real-data model."""
        row = self._row(selling_price, competitor_avg_price, competitor_min_price)
        contribs = self.model.predict(row, pred_contrib=True)[0]
        bias = float(contribs[-1])
        factors = []
        for name, val in zip(self.feature_names, contribs[:-1]):
            factors.append({
                "feature": name,
                "contribution": round(float(val), 4),
                "direction": "positive" if val > 0 else "negative",
                "abs_contribution": round(abs(float(val)), 4)
            })
        factors.sort(key=lambda f: f["abs_contribution"], reverse=True)
        return {
            "method": "TreeSHAP (LightGBM native pred_contrib)",
            "base_value": round(bias, 4),
            "prediction": round(max(0.0, bias + sum(contribs[:-1])), 4),
            "top_factors": factors[:6]
        }


if __name__ == "__main__":
    pipeline = KaggleRetailPipeline()
    pipeline.run_kaggle_pipeline()
