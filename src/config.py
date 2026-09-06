"""
Configuration settings and constants for AI-Powered Dynamic Pricing & Inventory Optimization
Focused on Indian Offline Electronics Retail (Smartphones & Tech Hardware)
"""
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
MODELS_DIR = PROJECT_ROOT / "models_saved"

# Create necessary directories
for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, SYNTHETIC_DATA_DIR, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Project Metadata
PROJECT_NAME = "AI-Powered Dynamic Pricing and Inventory Optimization"
PROJECT_VERTICAL = "Indian Electronics Retail (Smartphones Focus)"
CURRENCY_SYMBOL = "₹"

# Economic & Cost Parameters
DEFAULT_DAILY_HOLDING_COST_RATE = 0.0005   # 0.05% of inventory value per day
DEFAULT_ANNUAL_FINANCING_RATE = 0.12       # 12% annual working capital cost
DEFAULT_POST_SUCCESSOR_DEPRECIATION = 0.30 # 30% value erosion post-successor launch
DEFAULT_MAX_LOSS_TOLERANCE = 0.00          # 0% selling below acquisition cost strictly forbidden by default
INTER_STORE_TRANSFER_COST_PER_UNIT = 250   # ₹250 logistics cost to transfer unit between physical stores

# Indian Legal Metrology Rules (Packaged Commodities)
ENFORCE_MRP_CEILING = True                 # Mandatory legal constraint: Selling Price <= MRP

# Benchmark Baselines
BASELINE_STATUS_QUO = "Status Quo (Maintain Current Price)"
BASELINE_COMPETITOR_MATCH = "Match Lowest Online Competitor"
BASELINE_FIXED_MARKDOWN = "Fixed 15% Clearance Markdown"

# Competitors
ONLINE_COMPETITORS = ["Amazon India", "Flipkart"]
OFFLINE_COMPETITORS = ["Croma", "Vijay Sales", "Reliance Digital"]
ALL_COMPETITORS = ONLINE_COMPETITORS + OFFLINE_COMPETITORS

# Stores Definition (Indian Metro / Tier-1 / Tier-2 Offline Hubs)
STORES_MASTER = [
    {
        "store_id": "STORE_MUM_01",
        "store_name": "Phoenix Palladium Flagship",
        "city": "Mumbai",
        "state": "Maharashtra",
        "tier": "Tier 1",
        "footfall_index": 1.35,
        "store_type": "Multi-Brand Flagship"
    },
    {
        "store_id": "STORE_DEL_02",
        "store_name": "Select Citywalk Mega Store",
        "city": "Delhi NCR",
        "state": "Delhi",
        "tier": "Tier 1",
        "footfall_index": 1.25,
        "store_type": "Multi-Brand Flagship"
    },
    {
        "store_id": "STORE_BLR_03",
        "store_name": "Indiranagar Tech Hub",
        "city": "Bengaluru",
        "state": "Karnataka",
        "tier": "Tier 1",
        "footfall_index": 1.20,
        "store_type": "Multi-Brand Outlet"
    },
    {
        "store_id": "STORE_HYD_04",
        "store_name": "Banjara Hills Premium",
        "city": "Hyderabad",
        "state": "Telangana",
        "tier": "Tier 1",
        "footfall_index": 1.10,
        "store_type": "Multi-Brand Outlet"
    },
    {
        "store_id": "STORE_PUN_05",
        "store_name": "FC Road Retail Hub",
        "city": "Pune",
        "state": "Maharashtra",
        "tier": "Tier 2",
        "footfall_index": 0.95,
        "store_type": "Multi-Brand Outlet"
    }
]

# Flagship Specification Showcase Scenario (from Spec Section 1 & Section 27)
SHOWCASE_SCENARIO = {
    "product_id": "SKU_IPHONE_17_256",
    "product_name": "iPhone 17 256GB (Midnight)",
    "current_inventory": 800,
    "unit_cost": 68000.0,
    "current_price": 79999.0,
    "competitor_avg_price": 77999.0,
    "competitor_min_price": 76999.0,
    "mrp": 84999.0,
    "days_to_successor": 60,
    "baseline_velocity": 10.0, # units per day at 79,999
    "holding_cost_rate": DEFAULT_DAILY_HOLDING_COST_RATE,
    "post_successor_depreciation": DEFAULT_POST_SUCCESSOR_DEPRECIATION
}
