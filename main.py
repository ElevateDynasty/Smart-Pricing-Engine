"""
main.py — AI Smart Pricing Engine: End-to-End Pipeline Runner
=============================================================

Runs the complete pipeline:
  1. Generate synthetic sales data
  2. Clean & engineer features
  3. Train LightGBM demand forecaster
  4. Estimate price elasticity (log-log regression)
  5. Optimize prices for all products
  6. Print pricing recommendations

Usage:
    python main.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd


def print_header(text: str):
    """Print a styled section header."""
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def print_product_card(product_name: str, result: dict, current: dict = None):
    """Print a nicely formatted product recommendation card."""
    print(f"\n  ┌─────────────────────────────────────────────┐")
    print(f"  │  📦 {product_name:<40}│")
    print(f"  ├─────────────────────────────────────────────┤")
    print(f"  │  🎯 Optimal Price:    ₹{result['optimal_price']:<20,.0f}│")
    print(f"  │  📈 Predicted Demand: {result['predicted_demand']:<21,.1f}│")
    print(f"  │  💰 Daily Profit:     ₹{result['daily_profit']:<20,.0f}│")
    print(f"  │  📊 Monthly Profit:   ₹{result['monthly_profit']:<20,.0f}│")
    print(f"  │  📉 Margin:           {result['margin_pct']:<20,.1%}│")
    if current:
        improvement = current.get("improvement", {})
        profit_change = improvement.get("profit_change_pct", 0)
        extra = improvement.get("monthly_extra_profit", 0)
        arrow = "↑" if profit_change > 0 else "↓"
        print(f"  ├─────────────────────────────────────────────┤")
        print(f"  │  vs Current Price ₹{current['current']['price']:<25,.0f}│")
        print(f"  │  Profit Change:  {arrow} {abs(profit_change):<23,.1f}%│")
        print(f"  │  Monthly Extra:  ₹{extra:<25,.0f}│")
    print(f"  └─────────────────────────────────────────────┘")


def main():
    """Run the complete Smart Pricing Engine pipeline."""

    print("\n" + "🎯 " * 15)
    print("     AI SMART PRICING ENGINE — Full Pipeline")
    print("🎯 " * 15)

    # ── Step 1: Generate Synthetic Data ──────────────────────────
    print_header("STEP 1/5 — Generating Synthetic Sales Data")

    from src.data.generate_synthetic_data import SyntheticDataGenerator
    from src.utils.config import RAW_DATA_DIR, PRODUCT_CATALOG

    generator = SyntheticDataGenerator()
    df_raw = generator.generate()

    output_path = RAW_DATA_DIR / "sales_data.csv"
    df_raw.to_csv(output_path, index=False)
    print(f"  ✅ Generated {len(df_raw):,} rows of sales data")
    print(f"  📁 Saved to: {output_path}")
    print(f"  📦 Products: {df_raw['product_id'].nunique()}")
    print(f"  📅 Date range: {df_raw['date'].min()} → {df_raw['date'].max()}")

    # ── Step 2: Clean Data & Engineer Features ───────────────────
    print_header("STEP 2/5 — Cleaning Data & Engineering Features")

    from src.data.data_pipeline import DataPipeline
    from src.data.feature_engineering import FeatureEngineer

    pipeline = DataPipeline()
    df_clean = pipeline.clean_data(df_raw)
    print(f"  ✅ Cleaned data: {len(df_clean):,} rows")

    engineer = FeatureEngineer()
    df_feat = engineer.create_features(df_clean)
    print(f"  ✅ Engineered features: {df_feat.shape[1]} columns")

    # Time-based split
    train_df, val_df, test_df = pipeline.split_data(df_feat)
    print(f"  📊 Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    # ── Step 3: Train Demand Forecaster ──────────────────────────
    print_header("STEP 3/5 — Training LightGBM Demand Forecaster")

    from src.models.demand_forecaster import DemandForecaster
    from src.models.model_evaluator import ModelEvaluator
    from src.utils.config import ALL_FEATURES, TARGET_COLUMN, MODELS_DIR

    feature_cols = [c for c in ALL_FEATURES if c in train_df.columns]

    # Encode categoricals
    for col in ["product_category", "season"]:
        if col in train_df.columns:
            for _df in [train_df, val_df, test_df]:
                _df[col] = _df[col].astype("category")

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COLUMN]
    X_val = val_df[feature_cols]
    y_val = val_df[TARGET_COLUMN]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COLUMN]

    model = DemandForecaster()
    model.train(X_train, y_train, X_val, y_val)
    print(f"  ✅ LightGBM model trained")

    # Evaluate
    evaluator = ModelEvaluator()
    y_pred_test = model.predict(X_test)
    metrics = evaluator.evaluate("LightGBM", y_test.values, y_pred_test)
    print(f"  📊 Test Metrics:")
    print(f"      RMSE:  {metrics['rmse']:.2f}")
    print(f"      MAE:   {metrics['mae']:.2f}")
    print(f"      MAPE:  {metrics['mape']:.1f}%")
    print(f"      R²:    {metrics['r2']:.4f}")

    # Feature importance
    importance = model.get_feature_importance()
    print(f"\n  🔑 Top 5 Features:")
    for _, row in importance.head(5).iterrows():
        print(f"      {row['feature']:<30s} {row['importance']:.0f}")

    # Save model
    model.save(str(MODELS_DIR / "lgbm_demand_model.pkl"))
    print(f"  💾 Model saved to models/lgbm_demand_model.pkl")

    # ── Step 4: Estimate Price Elasticity ────────────────────────
    print_header("STEP 4/5 — Estimating Price Elasticity")

    from src.models.elasticity_estimator import ElasticityEstimator

    elasticity_model = ElasticityEstimator()
    elasticity_model.fit(df_feat)
    overall_beta = elasticity_model.get_elasticity()
    print(f"  ✅ Overall price elasticity (β): {overall_beta:.3f}")

    cat_elasticities = elasticity_model.fit_by_category(df_feat)
    print(f"\n  📊 Category-Level Elasticities:")
    for cat, beta in sorted(cat_elasticities.items(), key=lambda x: -abs(x[1])):
        bar = "█" * int(abs(beta) * 10)
        label = "Elastic" if abs(beta) > 1 else "Inelastic"
        print(f"      {cat:<20s}  β = {beta:>6.3f}  {bar}  ({label})")

    elasticity_model.save(str(MODELS_DIR / "elasticity_model.pkl"))
    print(f"  💾 Elasticity model saved")

    # ── Step 5: Optimize Prices ──────────────────────────────────
    print_header("STEP 5/5 — Finding Optimal Prices")

    from src.optimization.price_optimizer import PriceOptimizer

    print("\n  🎯 AI PRICING RECOMMENDATIONS")
    print("  " + "─" * 47)

    for prod_id, prod_info in PRODUCT_CATALOG.items():
        cost = prod_info["cost_price"]
        current_price = prod_info["base_price"]
        competitor = prod_info["competitor_base_price"]

        optimizer = PriceOptimizer(
            demand_model=model,
            cost_price=cost,
            min_price=cost * 1.1,
            max_price=cost * 5.0,
        )

        # Build base features from median of training data for this product
        prod_mask = train_df["product_id"] == prod_id if "product_id" in train_df.columns else pd.Series([True] * len(train_df))
        prod_data = train_df[prod_mask]

        if len(prod_data) == 0:
            prod_data = train_df

        base_features = {}
        for col in feature_cols:
            if col in prod_data.columns:
                if prod_data[col].dtype.name == "category":
                    base_features[col] = prod_data[col].mode().iloc[0] if len(prod_data[col].mode()) > 0 else prod_data[col].iloc[0]
                else:
                    base_features[col] = prod_data[col].median()

        # Override with known values
        base_features["cost_price"] = cost
        base_features["competitor_price"] = competitor

        try:
            result = optimizer.optimize(base_features, competitor_price=competitor)
            comparison = optimizer.compare_with_current(
                current_price, base_features, competitor_price=competitor
            )
            print_product_card(prod_info["name"], result, comparison)
        except Exception as e:
            print(f"\n  ⚠️  {prod_info['name']}: Optimization failed — {e}")

    # ── Summary ──────────────────────────────────────────────────
    print_header("PIPELINE COMPLETE ✅")
    print(f"""
  📊 Data:          {len(df_raw):,} rows generated & processed
  🤖 Model:         LightGBM (R² = {metrics['r2']:.3f}, MAPE = {metrics['mape']:.1f}%)
  📈 Elasticity:    {len(cat_elasticities)} categories analyzed
  💰 Optimization:  {len(PRODUCT_CATALOG)} products optimized
  
  Next steps:
    → Run 'streamlit run dashboard/app.py' for the interactive dashboard
    → Check models/ for saved model artifacts
    → Check data/raw/sales_data.csv for the generated data
""")


if __name__ == "__main__":
    main()
