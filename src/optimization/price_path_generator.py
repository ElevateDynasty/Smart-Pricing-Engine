"""
Dynamic Pricing Path Generator
Generates a multi-week, phased pricing schedule over the remaining product lifecycle horizon
to dynamically guide inventory clearance while preserving maximum margin early on.
"""
from typing import List, Dict, Any
import numpy as np
from src.optimization.lifecycle_optimizer import LifecycleOptimizer

class PricePathGenerator:
    def __init__(self, optimizer: LifecycleOptimizer):
        self.optimizer = optimizer

    def generate_pricing_path(
        self,
        product_id: str,
        product_name: str,
        current_price: float,
        mrp: float,
        unit_cost: float,
        current_inventory: int,
        competitor_avg_price: float,
        competitor_min_price: float,
        total_days: int = 60,
        num_phases: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Calculates optimal stepping pricing stages across the product horizon:
        e.g., Phase 1 (Days 60-45), Phase 2 (Days 44-30), Phase 3 (Days 29-15), Phase 4 (Days 14-0).
        """
        days_per_phase = max(7, total_days // num_phases)
        remaining_inv = float(current_inventory)
        path = []

        for phase in range(num_phases):
            start_day = total_days - (phase * days_per_phase)
            end_day = max(0, start_day - days_per_phase)
            phase_duration = start_day - end_day

            # Run optimizer for the remaining sub-horizon
            res = self.optimizer.optimize_sku(
                product_id=product_id,
                product_name=product_name,
                current_price=current_price,
                mrp=mrp,
                unit_cost=unit_cost,
                current_inventory=int(remaining_inv),
                competitor_avg_price=competitor_avg_price,
                competitor_min_price=competitor_min_price,
                days_to_successor=start_day
            )

            # Projected sales during this phase
            expected_phase_sales = min(remaining_inv, res.expected_daily_demand * phase_duration)
            end_inv = max(0.0, remaining_inv - expected_phase_sales)

            phase_label = f"Days {start_day}–{end_day+1}" if end_day > 0 else f"Days {start_day}–0 (Clearance)"

            path.append({
                "phase_index": phase + 1,
                "phase_label": phase_label,
                "days_remaining_start": start_day,
                "days_remaining_end": end_day,
                "starting_inventory": int(remaining_inv),
                "recommended_price": res.recommended_price,
                "expected_daily_sales": res.expected_daily_demand,
                "projected_units_sold": int(expected_phase_sales),
                "ending_inventory": int(end_inv),
                "price_action": res.price_action,
                "cumulative_clearance_pct": round(((current_inventory - end_inv) / current_inventory) * 100, 1)
            })

            remaining_inv = end_inv
            # Adapt current price towards recommended price for subsequent phases
            current_price = res.recommended_price
            if remaining_inv <= 0:
                for next_phase in range(phase + 1, num_phases):
                    n_start = total_days - (next_phase * days_per_phase)
                    n_end = max(0, n_start - days_per_phase)
                    n_label = f"Days {n_start}–{n_end+1}" if n_end > 0 else f"Days {n_start}–0 (Clearance)"
                    path.append({
                        "phase_index": next_phase + 1,
                        "phase_label": n_label,
                        "days_remaining_start": n_start,
                        "days_remaining_end": n_end,
                        "starting_inventory": 0,
                        "recommended_price": current_price,
                        "expected_daily_sales": 0.0,
                        "projected_units_sold": 0,
                        "ending_inventory": 0,
                        "price_action": "Stock Cleared",
                        "cumulative_clearance_pct": 100.0
                    })
                break

        return path
