"""
Main Entry Point for AI-Powered Dynamic Pricing and Inventory Optimization
Supports data generation, model training, baseline benchmarking, and the showcase demonstration.
"""
import argparse
import sys
from pathlib import Path
import pandas as pd

# Ensure UTF-8 stdout encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import SHOWCASE_SCENARIO
CURRENCY_STR = "₹"

from src.data.generate_synthetic_data import SyntheticDataGenerator
from src.data.data_pipeline import DataPipeline
from src.data.kaggle_pipeline import KaggleRetailPipeline
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.optimization.lifecycle_optimizer import LifecycleOptimizer
from src.explainability.reason_generator import ReasonGenerator
from src.evaluation.baseline_benchmarking import BaselineBenchmarking

def run_kaggle():
    print("=" * 70)
    print("EXECUTING KAGGLE RETAIL PRICE DATASET PIPELINE")
    print("=" * 70)
    kaggle_pipe = KaggleRetailPipeline()
    return kaggle_pipe.run_kaggle_pipeline()

def run_data_generation():
    print("=" * 70)
    print("STEP 1: GENERATING SYNTHETIC RETAIL DATA (INDIAN ELECTRONICS MARKET)")
    print("=" * 70)
    gen = SyntheticDataGenerator()
    gen.generate_all()

def run_training():
    print("=" * 70)
    print("STEP 2: ASSEMBLING DATA PIPELINE & TRAINING MODELS")
    print("=" * 70)
    dp = DataPipeline()
    unified_df = dp.build_unified_dataset()
    print(f"Unified dataset built: {len(unified_df)} daily store-SKU records.")

    print("\nTraining Demand Forecaster (LightGBM)...")
    forecaster = DemandForecaster(model_type="lightgbm")
    metrics = forecaster.fit(unified_df)
    print(f"Demand Forecaster Trained | MAE: {metrics['mae']} units | RMSE: {metrics['rmse']} | R2: {metrics['r2']}")

    print("\nEstimating Price Elasticity across Catalog...")
    elasticity_est = ElasticityEstimator()
    elasticities = elasticity_est.fit(unified_df)
    for pid, el in list(elasticities.items())[:6]:
        print(f"  SKU: {pid:22} | Elasticity: {el['elasticity']} ({el['regime']}) | R2: {el['r_squared']}")

    return forecaster, elasticity_est, unified_df

def run_showcase_demo(forecaster: DemandForecaster):
    print("\n" + "=" * 70)
    print("STEP 3: EXECUTING FLAGSHIP DEMO (SPEC SECTION 1 & SECTION 27)")
    print("=" * 70)
    sc = SHOWCASE_SCENARIO
    print(f"Target Product       : {sc['product_name']} ({sc['product_id']})")
    print(f"Current Inventory    : {sc['current_inventory']} units across stores")
    print(f"Acquisition Cost     : {CURRENCY_STR}{sc['unit_cost']:,.0f} per unit")
    print(f"Current Selling Price: {CURRENCY_STR}{sc['current_price']:,.0f}")
    print(f"Competitor Average   : {CURRENCY_STR}{sc['competitor_avg_price']:,.0f}")
    print(f"Competitor Lowest    : {CURRENCY_STR}{sc['competitor_min_price']:,.0f}")
    print(f"MRP (Legal Ceiling)  : {CURRENCY_STR}{sc['mrp']:,.0f}")
    print(f"Successor Launch     : In {sc['days_to_successor']} days")

    optimizer = LifecycleOptimizer(forecaster)
    result = optimizer.optimize_sku(
        product_id=sc["product_id"],
        product_name=sc["product_name"],
        current_price=sc["current_price"],
        mrp=sc["mrp"],
        unit_cost=sc["unit_cost"],
        current_inventory=sc["current_inventory"],
        competitor_avg_price=sc["competitor_avg_price"],
        competitor_min_price=sc["competitor_min_price"],
        days_to_successor=sc["days_to_successor"]
    )

    print("\n" + "-" * 70)
    print("DEMAND CURVE SIMULATION ACROSS CANDIDATE PRICES:")
    print("-" * 70)
    test_sample_prices = [79999.0, 78999.0, 77999.0, 77499.0, 76999.0, 75999.0]
    for p in test_sample_prices:
        d = forecaster.predict_point(
            selling_price=p,
            mrp=sc["mrp"],
            competitor_avg_price=sc["competitor_avg_price"],
            competitor_min_price=sc["competitor_min_price"],
            unit_cost=sc["unit_cost"],
            opening_inventory=sc["current_inventory"],
            days_to_successor=sc["days_to_successor"]
        )
        total_sales = min(sc["current_inventory"], d * 60)
        leftover = max(0, sc["current_inventory"] - total_sales)
        print(f"  Price: {CURRENCY_STR}{p:,.0f} -> Daily Demand: {d:.1f} units/day | 60-Day Sales: {int(total_sales)} | Leftover: {int(leftover)}")

    print("\n" + "=" * 70)
    print("AI LIFECYCLE OPTIMIZATION RECOMMENDATION")
    print("=" * 70)
    print(f"Action               : {result.price_action.upper()}")
    print(f"Recommended Price    : {CURRENCY_STR}{result.recommended_price:,.0f} (Change: {CURRENCY_STR}{result.price_change:,.0f} / {result.price_change_pct}%)")
    print(f"Expected Daily Sales : {result.expected_daily_demand:.1f} units/day (Status Quo: {result.status_quo_daily_demand:.1f})")
    print(f"Clearance Time       : {result.projected_clearance_days:.0f} days (Status Quo: {result.status_quo_clearance_days:.0f} days)")
    print(f"Clearance Probability: {result.clearance_probability * 100:.1f}%")
    print(f"Leftover Inventory   : {int(result.expected_leftover_inventory)} units (Status Quo: {int(result.status_quo_leftover)} units)")
    print(f"Expected Total Profit: {CURRENCY_STR}{result.expected_lifecycle_profit:,.0f}")
    print(f"Status Quo Profit    : {CURRENCY_STR}{result.status_quo_profit:,.0f}")
    print(f"Net Profit Lift      : +{CURRENCY_STR}{result.profit_lift_amount:,.0f} (+{result.profit_lift_pct}%)")

    # Natural language memo
    memo = ReasonGenerator.generate_retailer_memo(result)
    print("\nRETAILER EXPLANATION MEMO:")
    print(f"  Headline : {memo['headline']}")
    print(f"  Rationale: {memo['key_rationale']}")
    print(f"  Advantage: {memo['offline_advantage']}")

    # Benchmark vs baselines
    benchmarker = BaselineBenchmarking(optimizer)
    bench_df = benchmarker.benchmark_sku(
        product_id=sc["product_id"],
        product_name=sc["product_name"],
        current_price=sc["current_price"],
        mrp=sc["mrp"],
        unit_cost=sc["unit_cost"],
        current_inventory=sc["current_inventory"],
        competitor_avg_price=sc["competitor_avg_price"],
        competitor_min_price=sc["competitor_min_price"],
        days_to_successor=sc["days_to_successor"]
    )
    print("\nBENCHMARKING VS HEURISTIC STRATEGIES:")
    cols_to_show = ["Strategy", "Selling Price (₹)", "Clearance (%)", "Leftover Stock (Units)", "Expected Net Profit (₹)", "Profit Lift vs Status Quo (₹)"]
    print(bench_df[cols_to_show].to_string(index=False))

    return result

def main():
    parser = argparse.ArgumentParser(description="AI-Powered Dynamic Pricing & Inventory Optimization Engine")
    parser.add_argument("--generate-data", action="store_true", help="Generate synthetic retail dataset")
    parser.add_argument("--train", action="store_true", help="Train forecasting and elasticity models")
    parser.add_argument("--demo", action="store_true", help="Run flagship showcase demonstration")
    parser.add_argument("--kaggle", action="store_true", help="Download Kaggle dataset & train demand/elasticity models on it")
    parser.add_argument("--all", action="store_true", help="Execute complete pipeline")

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.all:
        run_data_generation()
        forecaster, _, _ = run_training()
        run_showcase_demo(forecaster)
    else:
        if args.generate_data:
            run_data_generation()
        if args.train:
            run_training()
        if args.kaggle:
            run_kaggle()
        if args.demo:
            forecaster = DemandForecaster()
            run_showcase_demo(forecaster)

if __name__ == "__main__":
    main()
