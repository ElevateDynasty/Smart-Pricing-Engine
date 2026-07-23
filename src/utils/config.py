"""
Central Configuration — Single source of truth for paths, constants,
product catalog, model hyperparameters, and optimization constraints.
"""

from pathlib import Path

# ============================================================================
# PROJECT PATHS
# ============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Create directories if they don't exist
for _d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTERNAL_DATA_DIR,
           MODELS_DIR, REPORTS_DIR, FIGURES_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATA SCHEMA — Column Names
# ============================================================================
DATE_COL = "date"
PRODUCT_ID_COL = "product_id"
PRODUCT_NAME_COL = "product_name"
CATEGORY_COL = "product_category"
COST_PRICE_COL = "cost_price"
SELLING_PRICE_COL = "selling_price"
UNITS_SOLD_COL = "units_sold"
COMPETITOR_PRICE_COL = "competitor_price"
REVENUE_COL = "revenue"
PROFIT_COL = "profit"
DISCOUNT_PCT_COL = "discount_pct"
RATING_COL = "rating"
NUM_REVIEWS_COL = "num_reviews"
AD_SPEND_COL = "ad_spend"

TARGET_COLUMN = UNITS_SOLD_COL

# ============================================================================
# FEATURE NAMES (engineered features used by ML models)
# ============================================================================
NUMERICAL_FEATURES = [
    "selling_price", "cost_price", "competitor_price",
    "discount_pct", "rating", "num_reviews", "ad_spend",
    "price_to_cost_ratio", "price_vs_competitor",
    "sales_lag_7d", "sales_lag_14d", "sales_lag_30d",
    "sales_rolling_7d_mean", "sales_rolling_14d_mean",
    "sales_rolling_30d_mean", "price_rolling_7d_mean",
    "days_to_next_festival",
]

CATEGORICAL_FEATURES = [
    "product_category", "day_of_week", "month",
    "season", "is_weekend", "is_festival",
]

ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

# ============================================================================
# PRODUCT CATALOG — 5 diverse products across categories
# ============================================================================
PRODUCT_CATALOG = {
    "PROD_001": {
        "name": "Wireless Earbuds",
        "category": "Electronics",
        "cost_price": 400,
        "base_price": 899,
        "base_demand": 15,
        "elasticity": 2.2,
        "competitor_base_price": 799,
        "rating_mean": 4.1,
        "review_growth_rate": 3,       # new reviews per day avg
    },
    "PROD_002": {
        "name": "Phone Case (Premium)",
        "category": "Electronics",
        "cost_price": 100,
        "base_price": 299,
        "base_demand": 40,
        "elasticity": 2.5,
        "competitor_base_price": 249,
        "rating_mean": 4.3,
        "review_growth_rate": 5,
    },
    "PROD_003": {
        "name": "Cotton T-Shirt",
        "category": "Fashion",
        "cost_price": 200,
        "base_price": 499,
        "base_demand": 25,
        "elasticity": 1.8,
        "competitor_base_price": 449,
        "rating_mean": 3.9,
        "review_growth_rate": 2,
    },
    "PROD_004": {
        "name": "Yoga Mat",
        "category": "Home & Fitness",
        "cost_price": 350,
        "base_price": 799,
        "base_demand": 10,
        "elasticity": 1.5,
        "competitor_base_price": 749,
        "rating_mean": 4.4,
        "review_growth_rate": 1,
    },
    "PROD_005": {
        "name": "Organic Face Wash",
        "category": "Health & Beauty",
        "cost_price": 80,
        "base_price": 249,
        "base_demand": 35,
        "elasticity": 1.2,
        "competitor_base_price": 199,
        "rating_mean": 4.0,
        "review_growth_rate": 4,
    },
}

CATEGORY_ELASTICITIES = {
    "Electronics": 2.2,
    "Fashion": 1.8,
    "Home & Fitness": 1.5,
    "Health & Beauty": 1.2,
    "Grocery": 0.6,
}

# ============================================================================
# SEASON MAPPING
# ============================================================================
MONTH_TO_SEASON = {
    1: "Winter",   2: "Winter",   3: "Spring",
    4: "Spring",   5: "Summer",   6: "Summer",
    7: "Monsoon",  8: "Monsoon",  9: "Monsoon",
    10: "Festival_Season", 11: "Festival_Season", 12: "Winter",
}

# ============================================================================
# MODEL HYPERPARAMETERS
# ============================================================================
LGBM_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_samples": 20,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "n_estimators": 500,
    "verbose": -1,
    "random_state": 42,
}

# ============================================================================
# OPTIMIZATION CONSTRAINTS
# ============================================================================
MIN_MARGIN_PCT = 0.10          # 10% minimum profit margin
MAX_PRICE_MULTIPLIER = 5.0     # Max price = 5× cost
OPTIMIZATION_METHOD = "bounded" # scipy.optimize method
PRICE_GRID_SIZE = 200          # number of points for profit curve

# ============================================================================
# SYNTHETIC DATA PARAMETERS
# ============================================================================
SYNTHETIC_START_DATE = "2023-01-01"
SYNTHETIC_END_DATE = "2024-12-31"
RANDOM_SEED = 42
NOISE_STD = 0.15               # Log-normal noise std

# ============================================================================
# DASHBOARD SETTINGS
# ============================================================================
DASHBOARD_TITLE = "🎯 AI Smart Pricing Engine"
DASHBOARD_ICON = "💰"
CURRENCY = "₹"
