"""
Data caching and optimization helper for the Streamlit dashboard
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Tuple
from src.config import SYNTHETIC_DATA_DIR, MODELS_DIR, STORES_MASTER
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.optimization.lifecycle_optimizer import LifecycleOptimizer, OptimizationResult
from src.data.data_pipeline import DataPipeline

@st.cache_resource
def load_models_and_pipeline() -> Tuple[DemandForecaster, ElasticityEstimator, LifecycleOptimizer]:
    """Loads or initializes models and optimizer."""
    forecaster = DemandForecaster(model_type="lightgbm")
    try:
        forecaster.load()
    except Exception:
        dp = DataPipeline()
        df = dp.build_unified_dataset()
        forecaster.fit(df)

    elasticity_est = ElasticityEstimator()
    try:
        dp = DataPipeline()
        df = dp.build_unified_dataset()
        elasticity_est.fit(df)
    except Exception:
        pass

    optimizer = LifecycleOptimizer(forecaster)
    return forecaster, elasticity_est, optimizer

@st.cache_data
def load_catalog_and_meta() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads product master, costs, and latest competitor prices."""
    products_df = pd.read_csv(SYNTHETIC_DATA_DIR / "products.csv")
    costs_df = pd.read_csv(SYNTHETIC_DATA_DIR / "costs.csv")
    competitors_df = pd.read_csv(SYNTHETIC_DATA_DIR / "competitors.csv")
    return products_df, costs_df, competitors_df

def compute_all_sku_optimizations(optimizer: LifecycleOptimizer) -> List[OptimizationResult]:
    """Computes lifecycle optimization for every SKU in catalog."""
    products_df, costs_df, competitors_df = load_catalog_and_meta()
    
    # Latest competitor summary per product
    latest_date = competitors_df["date"].max()
    latest_comp = competitors_df[competitors_df["date"] == latest_date].groupby("product_id").agg(
        competitor_avg_price=("competitor_price", "mean"),
        competitor_min_price=("competitor_price", "min"),
        competitor_stockouts=("availability", lambda s: (s == "Out of Stock").sum())
    ).reset_index()

    merged = products_df.merge(costs_df, on="product_id", how="left")
    merged = merged.merge(latest_comp, on="product_id", how="left")

    results = []
    for _, row in merged.iterrows():
        # Inventory allocation simulation across catalog
        if row["product_id"] == "SKU_IPHONE_17_256":
            curr_inv = 800
            curr_price = 79999.0
        elif row["product_id"] == "SKU_IPHONE_16_128":
            curr_inv = 320
            curr_price = 62999.0
        elif row["product_id"] == "SKU_PIXEL_10_PRO":
            curr_inv = 95
            curr_price = 104999.0
        else:
            curr_inv = 220
            curr_price = round(row["competitor_avg_price"] * 1.015, -2)

        stockout_flag = 1 if row["competitor_stockouts"] > 0 else 0

        res = optimizer.optimize_sku(
            product_id=row["product_id"],
            product_name=f"{row['brand']} {row['model']} ({row['variant']})",
            current_price=curr_price,
            mrp=row["mrp"],
            unit_cost=row["unit_cost"],
            current_inventory=curr_inv,
            competitor_avg_price=row["competitor_avg_price"],
            competitor_min_price=row["competitor_min_price"],
            days_to_successor=row["days_to_successor"],
            competitor_stockout_flag=stockout_flag
        )
        results.append(res)

    return results
