"""
Baseline Benchmarking Module
Directly compares AI Lifecycle Pricing against conventional retail heuristics:
1. Status Quo (Keep Current Price)
2. Blind Competitor Matching (Match Lowest Online Price)
3. Fixed Heuristic Rule (Fixed 15% Clearance Markdown)
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.optimization.lifecycle_optimizer import LifecycleOptimizer, OptimizationResult

class BaselineBenchmarking:
    def __init__(self, optimizer: LifecycleOptimizer):
        self.optimizer = optimizer

    def benchmark_sku(
        self,
        product_id: str,
        product_name: str,
        current_price: float,
        mrp: float,
        unit_cost: float,
        current_inventory: int,
        competitor_avg_price: float,
        competitor_min_price: float,
        days_to_successor: int = 60
    ) -> pd.DataFrame:
        """
        Runs complete simulation for:
        - Baseline A: Status Quo (Current Price)
        - Baseline B: Match Lowest Competitor
        - Baseline C: Fixed 15% Markdown
        - Strategy AI: Optimized Lifecycle Price
        """
        # 1. Run AI optimization
        ai_res = self.optimizer.optimize_sku(
            product_id=product_id,
            product_name=product_name,
            current_price=current_price,
            mrp=mrp,
            unit_cost=unit_cost,
            current_inventory=current_inventory,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            days_to_successor=days_to_successor
        )

        strategies = [
            ("Baseline A: Status Quo", current_price),
            ("Baseline B: Match Competitor", competitor_min_price),
            ("Baseline C: Fixed 15% Markdown", round(current_price * 0.85, -2)),
            ("AI Pricing Engine", ai_res.recommended_price)
        ]

        rows = []
        horizon = max(15, min(days_to_successor, 180))

        for strat_name, strat_price in strategies:
            # Predict demand at strategy price
            demand = self.optimizer.forecaster.predict_point(
                selling_price=strat_price,
                mrp=mrp,
                competitor_avg_price=competitor_avg_price,
                competitor_min_price=competitor_min_price,
                unit_cost=unit_cost,
                opening_inventory=current_inventory,
                days_to_successor=days_to_successor
            )
            daily_demand = max(0.01, float(demand))
            total_sales = min(float(current_inventory), daily_demand * horizon)
            leftover = max(0.0, float(current_inventory) - total_sales)
            clearance_days = current_inventory / daily_demand

            revenue = total_sales * strat_price
            cogs = total_sales * unit_cost
            gross_margin = revenue - cogs
            gross_margin_pct = (gross_margin / (revenue + 1e-5)) * 100.0

            # Carrying and depreciation
            avg_inv = (current_inventory + leftover) / 2.0
            carrying_cost = avg_inv * unit_cost * (0.0005 + 0.12/365.0) * horizon
            depreciation = leftover * unit_cost * 0.30
            net_profit = gross_margin - carrying_cost - depreciation

            clearance_pct = ((current_inventory - leftover) / current_inventory) * 100.0

            rows.append({
                "Strategy": strat_name,
                "Selling Price (₹)": round(strat_price),
                "Daily Demand (Units)": round(daily_demand, 1),
                "Total Sales (Units)": int(total_sales),
                "Leftover Stock (Units)": int(leftover),
                "Clearance (%)": round(clearance_pct, 1),
                "Clearance Time (Days)": round(clearance_days, 0),
                "Gross Margin (%)": round(gross_margin_pct, 1),
                "Total Revenue (₹)": round(revenue),
                "Depreciation Loss (₹)": round(depreciation),
                "Expected Net Profit (₹)": round(net_profit),
                "Profit Lift vs Status Quo (₹)": 0 # updated below
            })

        bench_df = pd.DataFrame(rows)
        sq_profit = bench_df.loc[bench_df["Strategy"] == "Baseline A: Status Quo", "Expected Net Profit (₹)"].values[0]
        bench_df["Profit Lift vs Status Quo (₹)"] = bench_df["Expected Net Profit (₹)"] - sq_profit

        return bench_df
