"""
Google Colab Training Script for ApexPricing AI Demand Forecasting & Elasticity Engine
===================================================================================
Run this directly in a Google Colab notebook cell by cell, or execute via:
    !python scripts/train_colab.py
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so modules under src.* are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# 1. Environment & Path Setup
print("=" * 70)
print("1. INITIALIZING ENVIRONMENT & DIRECTORIES")
print("=" * 70)

BASE_DIR = PROJECT_ROOT
MODELS_DIR = BASE_DIR / "models_saved"
DATA_DIR = BASE_DIR / "data" / "synthetic"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"Working Directory: {BASE_DIR}")
print(f"Models Directory : {MODELS_DIR}")

# 2. Dataset Synthesis (or Loading Real Data)
print("\n" + "=" * 70)
print("2. PREPARING TRAINING DATASET")
print("=" * 70)

try:
    from src.data.data_pipeline import DataPipeline
    dp = DataPipeline()
    df = dp.build_unified_dataset()
    print(f"Successfully loaded unified dataset via local pipeline: {len(df)} records.")
except Exception as e:
    print(f"Loading via pipeline failed ({e}); falling back to direct synthesis...")
    from src.data.generate_synthetic_data import SyntheticDataGenerator
    gen = SyntheticDataGenerator()
    gen.generate_all()
    from src.data.data_pipeline import DataPipeline
    dp = DataPipeline()
    df = dp.build_unified_dataset()
    print(f"Unified dataset generated: {len(df)} records.")

# 3. Feature Engineering & Monotone Demand Constraints
print("\n" + "=" * 70)
print("3. FEATURE ENGINEERING & STRICT LAW OF DEMAND ENFORCEMENT")
print("=" * 70)

from src.data.feature_engineering import FeatureEngineer
fe = FeatureEngineer()
X, y = fe.prepare_training_data(df, target_col="units_sold")

# Time-ordered split (no shuffle) to guarantee zero temporal data leakage
split_idx = int(len(X) * 0.8)
X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

print(f"Training Samples  : {len(X_train)}")
print(f"Validation Samples: {len(X_val)}")
print(f"Features Count    : {X.shape[1]}")

# 4. Training Monotone LightGBM Forecaster
print("\n" + "=" * 70)
print("4. TRAINING MONOTONE GRADIENT-BOOSTED LIGHTGBM MODEL")
print("=" * 70)

monotone_constraints = {
    "price_ratio_mrp": -1,
    "price_ratio_comp": -1,
    "price_delta_comp": -1,
    "price_delta_comp_min": -1,
    "margin_pct": -1,
}
feature_cols = list(X.columns)
monotone_vector = [monotone_constraints.get(col, 0) for col in feature_cols]

model = lgb.LGBMRegressor(
    n_estimators=300,
    learning_rate=0.04,
    max_depth=6,
    num_leaves=31,
    subsample=0.85,
    colsample_bytree=0.85,
    monotone_constraints=monotone_vector,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
)

val_preds = model.predict(X_val)
val_preds = np.clip(val_preds, a_min=0, a_max=None)

mae = float(mean_absolute_error(y_val, val_preds))
rmse = float(np.sqrt(mean_squared_error(y_val, val_preds)))
r2 = float(r2_score(y_val, val_preds))

print(f"Validation MAE : {mae:.3f} units/day")
print(f"Validation RMSE: {rmse:.3f} units/day")
print(f"Validation R^2 : {r2:.4f}")

# 5. Price Elasticity Log-Log Econometric Estimation
print("\n" + "=" * 70)
print("5. FITTING LOG-LOG ECONOMETRIC PRICE ELASTICITY")
print("=" * 70)

from src.models.elasticity_estimator import ElasticityEstimator
elasticity_est = ElasticityEstimator()
elasticities = elasticity_est.fit(df)

sample_skus = list(elasticities.keys())[:5]
for sku in sample_skus:
    el = elasticities[sku]
    el_val = f"{el['elasticity']:.2f}" if el['elasticity'] is not None else "N/A"
    r2_val = f"{el['r_squared']:.3f}" if el['r_squared'] is not None else "N/A"
    print(f"  SKU: {sku:22} | Elasticity: {el_val} ({el['regime']}) | R2: {r2_val}")

# 6. Model Serialization & Export
print("\n" + "=" * 70)
print("6. EXPORTING TRAINED WEIGHTS FOR FASTAPI / FRONTEND")
print("=" * 70)

output_path = MODELS_DIR / "demand_forecaster_lightgbm.joblib"
save_dict = {
    "model": model,
    "feature_names": feature_cols,
    "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
    "feature_engineer": fe
}
joblib.dump(save_dict, output_path)
print(f"Model saved successfully to: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")

# If running in Colab, provide download snippet
try:
    from google.colab import files
    print("\n[Google Colab Detected] Downloading trained model to your machine...")
    files.download(str(output_path))
except ImportError:
    print("\nRun locally or copy to local: models_saved/demand_forecaster_lightgbm.joblib")

print("\nTRAINING COMPLETE - Model ready for production deployment.")
