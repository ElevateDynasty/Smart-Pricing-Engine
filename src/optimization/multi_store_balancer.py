"""
Multi-Store Inventory Balancer
Optimizes stock distribution across physical retail store branches to prevent stockouts
at high-velocity stores and reduce overstock markdown risks at slow-moving stores.

Solved exactly as a TRANSPORTATION PROBLEM (linear program) with
scipy.optimize.linprog (HiGHS solver):

    maximize   SUM_{i,j} (v_j - c_ij) * x_ij      # net margin preserved
    subject to SUM_j x_ij <= surplus_i            # source capacity
               SUM_i x_ij <= demand_j             # destination need
               x_ij >= 0

where v_j is the gross margin per unit saved at the deficit store and c_ij is
the per-unit transfer logistics cost. Only transfers with positive net benefit
are chosen by the solver — no greedy matching, no heuristics.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from scipy.optimize import linprog
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
        target_days_of_supply: int = 25,
        margin_per_unit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyzes store-level days of supply (Inventory / Daily Velocity) and
        solves the profit-maximizing inter-store transfer plan as a
        transportation linear program (see module docstring).

        margin_per_unit defaults to 15% of MRP — the estimated gross margin
        preserved per unit by moving stock before a stockout/fire-sale.
        """
        margin_per_unit = margin_per_unit or (mrp * 0.15)

        records = []
        for s in store_data:
            inv = int(s["current_inventory"])
            vel = max(0.2, float(s["daily_sales_velocity"]))
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

        # --- LP: transportation problem over surplus (sources) -> deficit (sinks) ---
        sources = store_df[store_df["surplus_units"] > 5].reset_index(drop=True)
        sinks = store_df[store_df["need_units"] > 5].reset_index(drop=True)

        transfers: List[Dict[str, Any]] = []
        solver_status = "no-flow-needed"

        if len(sources) > 0 and len(sinks) > 0:
            n_src, n_snk = len(sources), len(sinks)
            n_var = n_src * n_snk

            # Minimize negative net benefit => maximize net margin preserved
            c_obj = np.zeros(n_var)
            for i in range(n_src):
                for j in range(n_snk):
                    net_unit = margin_per_unit - self.transfer_cost_per_unit
                    c_obj[i * n_snk + j] = -net_unit

            # Capacity constraints: SUM_j x_ij <= surplus_i  (n_src rows)
            # Demand constraints:    SUM_i x_ij <= need_j    (n_snk rows)
            A_ub, b_ub = [], []
            for i in range(n_src):
                row = np.zeros(n_var)
                row[i * n_snk:(i + 1) * n_snk] = 1.0
                A_ub.append(row)
                b_ub.append(float(sources.iloc[i]["surplus_units"]))
            for j in range(n_snk):
                row = np.zeros(n_var)
                row[j::n_snk] = 1.0
                A_ub.append(row)
                b_ub.append(float(sinks.iloc[j]["need_units"]))

            res = linprog(
                c=c_obj,
                A_ub=np.array(A_ub),
                b_ub=np.array(b_ub),
                bounds=[(0, None)] * n_var,
                method="highs"
            )
            solver_status = "optimal" if res.success else f"suboptimal:{res.status}"

            if res.success:
                flow = np.floor(res.x + 1e-6).astype(int)  # integer units
                for i in range(n_src):
                    for j in range(n_snk):
                        qty = int(flow[i * n_snk + j])
                        if qty >= 5:
                            s_store = sources.iloc[i]
                            d_store = sinks.iloc[j]
                            total_cost = qty * self.transfer_cost_per_unit
                            gross_saved = qty * margin_per_unit
                            net_benefit = gross_saved - total_cost
                            transfers.append({
                                "from_store_id": s_store["store_id"],
                                "from_store_name": s_store["store_name"],
                                "to_store_id": d_store["store_id"],
                                "to_store_name": d_store["store_name"],
                                "transfer_units": qty,
                                "transfer_cost": float(total_cost),
                                "estimated_margin_saved": float(gross_saved),
                                "net_benefit": float(net_benefit),
                                "reason": (
                                    f"LP-optimal: move {qty} units from {s_store['store_name']} "
                                    f"({s_store['days_of_supply']:.0f} days supply) to {d_store['store_name']} "
                                    f"({d_store['days_of_supply']:.0f} days supply) — net benefit "
                                    f"₹{int(net_benefit):,} after ₹{self.transfer_cost_per_unit}/unit logistics."
                                )
                            })

        transfers.sort(key=lambda t: t["net_benefit"], reverse=True)

        return {
            "product_id": product_id,
            "product_name": product_name,
            "solver": "scipy.optimize.linprog (HiGHS) — transportation LP",
            "solver_status": solver_status,
            "stores_summary": store_df.to_dict("records"),
            "recommended_transfers": transfers,
            "total_transfers_count": len(transfers),
            "total_net_benefit": round(float(sum(t["net_benefit"] for t in transfers)), 2)
        }
