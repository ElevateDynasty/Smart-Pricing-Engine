"""
Synthetic Data Generator for Indian Offline Electronics Retail
Generates realistic historical transactions, inventory movements, competitor prices,
and product masters with embedded showcase scenarios.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from src.config import (
    SYNTHETIC_DATA_DIR,
    STORES_MASTER,
    SHOWCASE_SCENARIO,
    DEFAULT_DAILY_HOLDING_COST_RATE,
    DEFAULT_ANNUAL_FINANCING_RATE,
    DEFAULT_POST_SUCCESSOR_DEPRECIATION
)

class SyntheticDataGenerator:
    def __init__(self, seed: int = 42, days: int = 240):
        self.seed = seed
        self.days = days
        np.random.seed(seed)
        self.end_date = datetime(2026, 9, 1)
        self.start_date = self.end_date - timedelta(days=days)

    def generate_products(self) -> pd.DataFrame:
        """Generate smartphone product catalog with Indian market context."""
        products = [
            # Flagship Showcase Model (Spec Section 1 & 27)
            {
                "product_id": "SKU_IPHONE_17_256",
                "brand": "Apple",
                "model": "iPhone 17",
                "variant": "256GB Midnight Black",
                "category": "Premium Flagship",
                "ram_gb": 8,
                "storage_gb": 256,
                "mrp": 84999.0,
                "launch_date": (self.end_date - timedelta(days=300)).strftime("%Y-%m-%d"),
                "successor_model": "iPhone 18",
                "days_to_successor": 60, # Approaching launch!
                "base_elasticity": 2.4,
                "base_daily_demand": 9.8,
                "target_segment": "Affluent Tech Enthusiasts"
            },
            # Aging Flagship approaching end-of-life
            {
                "product_id": "SKU_IPHONE_16_128",
                "brand": "Apple",
                "model": "iPhone 16",
                "variant": "128GB Blue",
                "category": "Previous-Gen Flagship",
                "ram_gb": 6,
                "storage_gb": 128,
                "mrp": 69999.0,
                "launch_date": (self.end_date - timedelta(days=660)).strftime("%Y-%m-%d"),
                "successor_model": "iPhone 17",
                "days_to_successor": 15,
                "base_elasticity": 2.8,
                "base_daily_demand": 12.0,
                "target_segment": "Value Premium Buyers"
            },
            # Competitor Out of Stock / Inelastic Showcase (Price Increase Candidate)
            {
                "product_id": "SKU_PIXEL_10_PRO",
                "brand": "Google",
                "model": "Pixel 10 Pro",
                "variant": "256GB Hazel",
                "category": "AI Flagship",
                "ram_gb": 16,
                "storage_gb": 256,
                "mrp": 109999.0,
                "launch_date": (self.end_date - timedelta(days=90)).strftime("%Y-%m-%d"),
                "successor_model": "Pixel 11 Pro",
                "days_to_successor": 270,
                "base_elasticity": 0.85, # Inelastic demand
                "base_daily_demand": 7.0,
                "target_segment": "AI Professionals & Photographers"
            },
            # Samsung Multi-Store Balancing Showcase
            {
                "product_id": "SKU_GALAXY_S26_256",
                "brand": "Samsung",
                "model": "Galaxy S26",
                "variant": "256GB Titanium Gray",
                "category": "Flagship",
                "ram_gb": 12,
                "storage_gb": 256,
                "mrp": 89999.0,
                "launch_date": (self.end_date - timedelta(days=180)).strftime("%Y-%m-%d"),
                "successor_model": "Galaxy S27",
                "days_to_successor": 180,
                "base_elasticity": 1.75,
                "base_daily_demand": 14.0,
                "target_segment": "Enterprise & Mainstream Premium"
            },
            # High-Volume Mid-Tier
            {
                "product_id": "SKU_ONEPLUS_13_256",
                "brand": "OnePlus",
                "model": "OnePlus 13",
                "variant": "256GB Emerald Green",
                "category": "Flagship Killer",
                "ram_gb": 12,
                "storage_gb": 256,
                "mrp": 64999.0,
                "launch_date": (self.end_date - timedelta(days=140)).strftime("%Y-%m-%d"),
                "successor_model": "OnePlus 14",
                "days_to_successor": 220,
                "base_elasticity": 1.9,
                "base_daily_demand": 18.0,
                "target_segment": "Performance Gamers & Young Pros"
            },
            # Mass Market Tier
            {
                "product_id": "SKU_REDMI_NOTE_15_PRO",
                "brand": "Xiaomi",
                "model": "Redmi Note 15 Pro",
                "variant": "128GB Midnight",
                "category": "Mass Mid-Range",
                "ram_gb": 8,
                "storage_gb": 128,
                "mrp": 28999.0,
                "launch_date": (self.end_date - timedelta(days=120)).strftime("%Y-%m-%d"),
                "successor_model": "Redmi Note 16 Pro",
                "days_to_successor": 160,
                "base_elasticity": 2.4,
                "base_daily_demand": 35.0,
                "target_segment": "Value Conscious Mass Market"
            },
            # Samsung Mid-Range
            {
                "product_id": "SKU_GALAXY_A56_128",
                "brand": "Samsung",
                "model": "Galaxy A56",
                "variant": "128GB Awesome Lilac",
                "category": "Upper Mid-Range",
                "ram_gb": 8,
                "storage_gb": 128,
                "mrp": 38999.0,
                "launch_date": (self.end_date - timedelta(days=150)).strftime("%Y-%m-%d"),
                "successor_model": "Galaxy A57",
                "days_to_successor": 210,
                "base_elasticity": 2.1,
                "base_daily_demand": 22.0,
                "target_segment": "Youth & Tier-2 Aspirants"
            },
            # Premium Android Ultra
            {
                "product_id": "SKU_S26_ULTRA_512",
                "brand": "Samsung",
                "model": "Galaxy S26 Ultra",
                "variant": "512GB Titanium Black",
                "category": "Ultra Premium",
                "ram_gb": 16,
                "storage_gb": 512,
                "mrp": 139999.0,
                "launch_date": (self.end_date - timedelta(days=180)).strftime("%Y-%m-%d"),
                "successor_model": "Galaxy S27 Ultra",
                "days_to_successor": 180,
                "base_elasticity": 1.2,
                "base_daily_demand": 5.5,
                "target_segment": "C-Suite & Power Users"
            }
        ]
        return pd.DataFrame(products)

    def generate_stores(self) -> pd.DataFrame:
        """Return store master data."""
        return pd.DataFrame(STORES_MASTER)

    def generate_costs(self, products_df: pd.DataFrame) -> pd.DataFrame:
        """Generate procurement and inventory cost structures."""
        costs = []
        for _, p in products_df.iterrows():
            # Standard electronics offline dealer margins: 12% to 22%
            if p["product_id"] == SHOWCASE_SCENARIO["product_id"]:
                unit_cost = SHOWCASE_SCENARIO["unit_cost"]
            elif "Ultra" in p["model"] or "Pro" in p["model"]:
                unit_cost = round(p["mrp"] * 0.78, -2)
            else:
                unit_cost = round(p["mrp"] * 0.81, -2)

            landed_cost = unit_cost + 450.0 # handling, insurance, inbound freight
            costs.append({
                "product_id": p["product_id"],
                "unit_cost": float(unit_cost),
                "landed_cost": float(landed_cost),
                "daily_holding_cost_rate": DEFAULT_DAILY_HOLDING_COST_RATE,
                "annual_financing_rate": DEFAULT_ANNUAL_FINANCING_RATE,
                "post_successor_depreciation_rate": DEFAULT_POST_SUCCESSOR_DEPRECIATION
            })
        return pd.DataFrame(costs)

    def generate_competitors(self, products_df: pd.DataFrame) -> pd.DataFrame:
        """Generate daily competitor price tracking records across Indian channels."""
        date_range = pd.date_range(start=self.start_date, end=self.end_date, freq="D")
        competitor_names = ["Amazon India", "Flipkart", "Croma", "Vijay Sales"]
        records = []

        for p_idx, product in products_df.iterrows():
            mrp = product["mrp"]
            pid = product["product_id"]
            
            # Baseline competitor price typically 4-10% below MRP
            base_comp_price = round(mrp * 0.92, -2)
            if pid == SHOWCASE_SCENARIO["product_id"]:
                base_comp_price = SHOWCASE_SCENARIO["competitor_avg_price"]

            for dt in date_range:
                # Festive discount dip (Diwali / Big Billion Days in late Oct / Nov)
                festive_mult = 1.0
                if dt.month in [10, 11] and (dt.day >= 15 and dt.day <= 28):
                    festive_mult = 0.94
                elif dt.month == 1 and dt.day in range(20, 27): # Republic Day
                    festive_mult = 0.96

                for comp in competitor_names:
                    # Online typically discounts slightly deeper than offline chains
                    channel_bias = 0.985 if comp in ["Amazon India", "Flipkart"] else 1.005
                    noise = np.random.normal(0, 0.008)
                    price = round(base_comp_price * festive_mult * channel_bias * (1 + noise), -2)
                    
                    # Ensure price <= MRP
                    price = min(price, mrp)

                    # Availability: Pixel 10 Pro has online stockout during recent 45 days (Showcase scenario)
                    availability = "In Stock"
                    if pid == "SKU_PIXEL_10_PRO" and dt >= (self.end_date - timedelta(days=45)):
                        if comp in ["Amazon India", "Flipkart"]:
                            availability = "Out of Stock"

                    records.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "product_id": pid,
                        "competitor": comp,
                        "competitor_price": float(price),
                        "availability": availability,
                        "promotion_tag": "Festive Deal" if festive_mult < 1.0 else "Regular"
                    })

        return pd.DataFrame(records)

    def generate_sales_and_inventory(
        self,
        products_df: pd.DataFrame,
        stores_df: pd.DataFrame,
        costs_df: pd.DataFrame,
        competitors_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Simulate daily sales transactions and inventory trajectories per store."""
        date_range = pd.date_range(start=self.start_date, end=self.end_date, freq="D")
        sales_records = []
        inventory_records = []

        cost_map = costs_df.set_index("product_id")["unit_cost"].to_dict()

        # Group competitor prices by date and product
        comp_summary = competitors_df.groupby(["date", "product_id"]).agg(
            competitor_avg_price=("competitor_price", "mean"),
            competitor_min_price=("competitor_price", "min"),
            competitor_stockouts=("availability", lambda s: (s == "Out of Stock").sum())
        ).reset_index()
        comp_lookup = comp_summary.set_index(["date", "product_id"]).to_dict("index")

        # Initial inventory per store
        current_inventory_state: Dict[Tuple[str, str], int] = {}
        for _, store in stores_df.iterrows():
            for _, product in products_df.iterrows():
                pid = product["product_id"]
                sid = store["store_id"]
                
                # Setup showcase inventory distribution
                if pid == SHOWCASE_SCENARIO["product_id"]:
                    # Total 800 across 5 stores (Spec Section 1)
                    allocations = {
                        "STORE_MUM_01": 250,
                        "STORE_DEL_02": 220,
                        "STORE_BLR_03": 150,
                        "STORE_HYD_04": 100,
                        "STORE_PUN_05": 80
                    }
                    current_inventory_state[(sid, pid)] = allocations.get(sid, 160)
                elif pid == "SKU_GALAXY_S26_256":
                    # Store balancing showcase: Store MUM has high demand/low stock, Store PUN has overstock
                    allocations = {
                        "STORE_MUM_01": 25,  # Low stock, high velocity
                        "STORE_DEL_02": 60,
                        "STORE_BLR_03": 50,
                        "STORE_HYD_04": 40,
                        "STORE_PUN_05": 180  # Excess stock, low velocity
                    }
                    current_inventory_state[(sid, pid)] = allocations.get(sid, 50)
                elif pid == "SKU_PIXEL_10_PRO":
                    # Limited stock supply crunch
                    current_inventory_state[(sid, pid)] = np.random.randint(15, 30)
                else:
                    current_inventory_state[(sid, pid)] = np.random.randint(40, 150)

        tx_id_counter = 100000

        for dt in date_range:
            dt_str = dt.strftime("%Y-%m-%d")
            is_weekend = dt.weekday() >= 5
            weekend_boost = 1.30 if is_weekend else 1.0

            # Festive boost
            festive_boost = 1.0
            if dt.month in [10, 11] and (dt.day >= 15 and dt.day <= 28):
                festive_boost = 1.65
            elif dt.month == 1 and dt.day in range(20, 27):
                festive_boost = 1.35

            for _, store in stores_df.iterrows():
                sid = store["store_id"]
                footfall = store["footfall_index"]

                for _, product in products_df.iterrows():
                    pid = product["product_id"]
                    mrp = product["mrp"]
                    base_elasticity = product["base_elasticity"]
                    base_demand = product["base_daily_demand"] * (footfall / 1.15)
                    unit_cost = cost_map.get(pid, mrp * 0.8)

                    comp_data = comp_lookup.get((dt_str, pid), {
                        "competitor_avg_price": mrp * 0.92,
                        "competitor_min_price": mrp * 0.90,
                        "competitor_stockouts": 0
                    })
                    comp_avg = comp_data["competitor_avg_price"]
                    comp_stockouts = comp_data["competitor_stockouts"]

                    # Retailer current pricing behavior in historical data
                    if pid == SHOWCASE_SCENARIO["product_id"]:
                        # Held at 79,999 in recent period
                        selling_price = SHOWCASE_SCENARIO["current_price"]
                    elif pid == "SKU_PIXEL_10_PRO" and comp_stockouts >= 2:
                        # Price increased due to competitor stockouts
                        selling_price = mrp * 0.98
                    else:
                        # Typical store price floating slightly above online comp (convenience premium)
                        selling_price = round(comp_avg * 1.015, -2)

                    # Ensure bounded within [unit_cost, mrp]
                    selling_price = max(unit_cost * 1.02, min(selling_price, mrp))

                    # Demand calculation with price elasticity
                    # Spec Section 9 & 10: D = f(P, C, I, S, L, T, M)
                    price_ratio = selling_price / (comp_avg + 1e-4)
                    
                    # Log-log elasticity formula
                    elasticity_factor = (price_ratio) ** (-base_elasticity)
                    stockout_boost = 1.25 if comp_stockouts >= 2 else 1.0

                    # Lifecycle degradation factor for aging models
                    days_remaining = product["days_to_successor"] - (self.end_date - dt).days
                    if days_remaining <= 30 and pid in ["SKU_IPHONE_17_256", "SKU_IPHONE_16_128"]:
                        lifecycle_drag = 0.85
                    else:
                        lifecycle_drag = 1.0

                    expected_units = (
                        base_demand
                        * elasticity_factor
                        * weekend_boost
                        * festive_boost
                        * stockout_boost
                        * lifecycle_drag
                    )

                    # Actual simulated units sold (poisson distribution)
                    simulated_sales = np.random.poisson(expected_units)

                    # Cap sales by opening inventory
                    opening_stock = current_inventory_state.get((sid, pid), 50)
                    units_sold = min(opening_stock, simulated_sales)

                    # Replenishment logic (periodic restocking except when near successor launch)
                    stock_in = 0
                    if days_remaining > 45 and opening_stock - units_sold < 20:
                        stock_in = np.random.choice([0, 30, 50], p=[0.7, 0.2, 0.1])

                    closing_stock = opening_stock - units_sold + stock_in
                    current_inventory_state[(sid, pid)] = closing_stock

                    # Log inventory row
                    inventory_records.append({
                        "date": dt_str,
                        "store_id": sid,
                        "product_id": pid,
                        "opening_inventory": opening_stock,
                        "units_sold": units_sold,
                        "stock_in": stock_in,
                        "closing_inventory": closing_stock,
                        "inventory_age_days": max(10, 240 - days_remaining)
                    })

                    # Log sales transactions
                    if units_sold > 0:
                        tx_id_counter += 1
                        sales_records.append({
                            "transaction_id": f"TXN_{tx_id_counter}",
                            "date": dt_str,
                            "store_id": sid,
                            "product_id": pid,
                            "selling_price": float(selling_price),
                            "units_sold": int(units_sold),
                            "total_revenue": float(selling_price * units_sold),
                            "discount_amount": float((mrp - selling_price) * units_sold),
                            "customer_segment": np.random.choice(["Walk-in", "Loyalty Member", "Corporate"], p=[0.7, 0.2, 0.1]),
                            "payment_method": np.random.choice(["UPI / Credit Card", "EMI / Financing", "Cash"], p=[0.65, 0.25, 0.10])
                        })

        return pd.DataFrame(sales_records), pd.DataFrame(inventory_records)

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        """Generate complete synthetic dataset and save to disk."""
        print("Generating product master...")
        products_df = self.generate_products()

        print("Generating store master...")
        stores_df = self.generate_stores()

        print("Generating procurement & inventory costs...")
        costs_df = self.generate_costs(products_df)

        print("Generating competitor price observations...")
        competitors_df = self.generate_competitors(products_df)

        print("Generating historical sales & inventory logs...")
        sales_df, inventory_df = self.generate_sales_and_inventory(
            products_df, stores_df, costs_df, competitors_df
        )

        # Save to SYNTHETIC_DATA_DIR
        products_df.to_csv(SYNTHETIC_DATA_DIR / "products.csv", index=False)
        stores_df.to_csv(SYNTHETIC_DATA_DIR / "stores.csv", index=False)
        costs_df.to_csv(SYNTHETIC_DATA_DIR / "costs.csv", index=False)
        competitors_df.to_csv(SYNTHETIC_DATA_DIR / "competitors.csv", index=False)
        sales_df.to_csv(SYNTHETIC_DATA_DIR / "sales.csv", index=False)
        inventory_df.to_csv(SYNTHETIC_DATA_DIR / "inventory.csv", index=False)

        print(f"Data generation complete! Saved to {SYNTHETIC_DATA_DIR}")
        print(f"Products: {len(products_df)}, Stores: {len(stores_df)}, Sales Txns: {len(sales_df)}, Inventory records: {len(inventory_df)}")

        return {
            "products": products_df,
            "stores": stores_df,
            "costs": costs_df,
            "competitors": competitors_df,
            "sales": sales_df,
            "inventory": inventory_df
        }

if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.generate_all()
