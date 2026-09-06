"""
Multi-Store Inventory Balancer
Optimizes stock distribution across physical retail store branches to prevent stockouts
at high-velocity stores and reduce overstock markdown risks at slow-moving stores.
"""
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from src.config import INTER_STORE_TRANSFER_COST_PER_UNIT

class MultiStoreBalancer:
    def __init__(self, transfer_cost_per_unit: float = INTER_STORE_TRANSFER_COST_PER_UNIT):
        self.transfer_cost_per_unit = transfer_cost_per_unit

    def analyze_sku_across_stores(
        self,
        product_id: str,
        product_name: str,
        unit_cost: float,
        mrp: float,
        store_data: List[Dict[str, Any]],
        target_days_of_supply: int = 25
    ) -> Dict[str, Any]:
        """
        Analyzes store-level days of supply (Inventory / Daily Velocity).
        Recommends profitable inter-store transfers where the margin preserved
        far exceeds the transfer logistics cost.
        """
        records = []
        for s in store_data:
            inv = s["current_inventory"]
            vel = max(0.2, s["daily_sales_velocity"])
            days_of_supply = inv / vel

            if days_of_supply < 12:
                status = "Stockout Imminent"
                need = int(max(0, (target_days_of_supply * vel) - inv))
                surplus = 0
            elif days_of_supply > 45:
                status = "Excess Overstock"
                surplus = int(max(0, inv - (target_days_of_supply * vel)))
                need = 0
            else:
                status = "Balanced"
                need = 0
                surplus = 0

            records.append({
                "store_id": s["store_id"],
                "store_name": s["store_name"],
                "city": s["city"],
                "current_inventory": inv,
                "daily_sales_velocity": round(vel, 1),
                "days_of_supply": round(days_of_supply, 1),
                "status": status,
                "need_units": need,
                "surplus_units": surplus
            })

        store_df = pd.DataFrame(records)

        # Match surplus stores to deficit stores
        transfers = []
        surplus_stores = store_df[store_df["surplus_units"] > 5].sort_values("surplus_units", ascending=False).to_dict("records")
        deficit_stores = store_df[store_df["need_units"] > 5].sort_values("need_units", ascending=False).to_dict("records")

        for d_store in deficit_stores:
            needed = d_store["need_units"]
            for s_store in surplus_stores:
                if needed <= 0 or s_store["surplus_units"] <= 0:
                    continue

                transfer_qty = min(needed, s_store["surplus_units"])
                if transfer_qty >= 5:
                    total_transfer_cost = transfer_qty * self.transfer_cost_per_unit
                    # Estimated gross margin preserved by avoiding stockout or fire-sale
                    margin_per_unit = mrp * 0.15
                    net_benefit = (transfer_qty * margin_per_unit) - total_transfer_cost

                    transfers.append({
                        "from_store_id": s_store["store_id"],
                        "from_store_name": s_store["store_name"],
                        "to_store_id": d_store["store_id"],
                        "to_store_name": d_store["store_name"],
                        "transfer_units": int(transfer_qty),
                        "transfer_cost": float(total_transfer_cost),
                        "estimated_margin_saved": float(net_benefit),
                        "reason": (
                            f"Move {transfer_qty} units from {s_store['store_name']} ({s_store['days_of_supply']:.0f} days supply) "
                            f"to {d_store['store_name']} ({d_store['days_of_supply']:.0f} days supply) "
                            f"to prevent stockout while clearing overstock."
                        )
                    })

                    needed -= transfer_qty
                    s_store["surplus_units"] -= transfer_qty

        return {
            "product_id": product_id,
            "product_name": product_name,
            "stores_summary": store_df.to_dict("records"),
            "recommended_transfers": transfers,
            "total_transfers_count": len(transfers)
        }
