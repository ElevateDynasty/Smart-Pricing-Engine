"""
Data Pipeline for Loading, Validating, and Assembling Retail Data
Merges sales, competitor observations, store profiles, and inventory states into a unified analytics schema.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.config import SYNTHETIC_DATA_DIR, PROCESSED_DATA_DIR

class DataPipeline:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or SYNTHETIC_DATA_DIR
        self.processed_dir = PROCESSED_DATA_DIR

    def load_raw_data(self) -> Dict[str, pd.DataFrame]:
        """Load raw or synthetic CSV files."""
        tables = {}
        for name in ["products", "stores", "costs", "competitors", "sales", "inventory"]:
            fpath = self.data_dir / f"{name}.csv"
            if not fpath.exists():
                raise FileNotFoundError(f"Missing required data file: {fpath}. Please run data generation first.")
            tables[name] = pd.read_csv(fpath)
        return tables

    def build_unified_dataset(self) -> pd.DataFrame:
        """
        Merge sales, store info, product master, costs, and competitor metrics
        into an aggregated daily store-product observation table.
        """
        tables = self.load_raw_data()
        products_df = tables["products"]
        stores_df = tables["stores"]
        costs_df = tables["costs"]
        competitors_df = tables["competitors"]
        sales_df = tables["sales"]
        inventory_df = tables["inventory"]

        # Aggregate competitor metrics per date and product
        comp_agg = competitors_df.groupby(["date", "product_id"]).agg(
            competitor_avg_price=("competitor_price", "mean"),
            competitor_min_price=("competitor_price", "min"),
            competitor_max_price=("competitor_price", "max"),
            competitor_stockouts=("availability", lambda s: (s == "Out of Stock").sum()),
            competitor_total=("competitor", "count")
        ).reset_index()

        comp_agg["competitor_stockout_flag"] = (comp_agg["competitor_stockouts"] > 0).astype(int)

        # Merge inventory with sales
        # Note: inventory table has daily records for all store-product combinations
        base = inventory_df.merge(stores_df, on="store_id", how="left")
        base = base.merge(products_df, on="product_id", how="left")
        base = base.merge(costs_df, on="product_id", how="left")
        base = base.merge(comp_agg, on=["date", "product_id"], how="left")

        # Merge transaction selling price (average selling price for that day/store/product)
        sales_agg = sales_df.groupby(["date", "store_id", "product_id"]).agg(
            selling_price=("selling_price", "mean"),
            daily_revenue=("total_revenue", "sum")
        ).reset_index()

        df = base.merge(sales_agg, on=["date", "store_id", "product_id"], how="left")

        # If no sales occurred on that day, fill selling_price from competitor avg or product mrp * 0.92
        df["selling_price"] = df["selling_price"].fillna(
            df["competitor_avg_price"].fillna(df["mrp"] * 0.92)
        )
        df["daily_revenue"] = df["daily_revenue"].fillna(0.0)

        # Clean nulls
        df["competitor_avg_price"] = df["competitor_avg_price"].fillna(df["selling_price"])
        df["competitor_min_price"] = df["competitor_min_price"].fillna(df["selling_price"])
        df["competitor_max_price"] = df["competitor_max_price"].fillna(df["selling_price"])
        df["competitor_stockout_flag"] = df["competitor_stockout_flag"].fillna(0).astype(int)

        # Save processed dataset
        output_file = self.processed_dir / "unified_retail_daily.parquet"
        df.to_parquet(output_file, index=False)
        return df

if __name__ == "__main__":
    pipeline = DataPipeline()
    df = pipeline.build_unified_dataset()
    print(f"Unified dataset created with {len(df)} rows and {df.shape[1]} columns.")
