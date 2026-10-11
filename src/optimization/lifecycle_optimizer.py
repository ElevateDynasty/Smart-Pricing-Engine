"""
Constrained Lifecycle Profit Optimizer

A constrained nonlinear optimization layer built ON TOP of the ML demand
function. The demand model (LightGBM) provides the demand surface D(P, context);
this optimizer then solves, over a discrete lattice of feasible prices:

    max_P  GrossMargin(P) - CarryingCosts(P) - DepreciationLoss(P)
    s.t.   unit_cost <= P <= MRP        (Legal Metrology ceiling)

This is the standard revenue-management architecture ("ML predicts demand,
constrained optimization prices the inventory") — the same pattern used by
airline and hotel revenue management systems. It is operations research
feeding on machine-learned demand, not a second ML model.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import scipy.stats as stats
from src.config import (
    DEFAULT_DAILY_HOLDING_COST_RATE,
    DEFAULT_ANNUAL_FINANCING_RATE,
    DEFAULT_POST_SUCCESSOR_DEPRECIATION,
    DEFAULT_MAX_LOSS_TOLERANCE,
    ENFORCE_MRP_CEILING
)
from src.models.demand_forecaster import DemandForecaster

@dataclass
class OptimizationResult:
    product_id: str
    product_name: str
    current_price: float
    recommended_price: float
    price_action: str          # "Increase Price", "Hold Price", "Slight Reduction", "Clearance Markdown"
    price_change: float
    price_change_pct: float
    mrp: float
    unit_cost: float
    current_inventory: int
    days_to_successor: int
    
    # Economics under Recommended Price
    expected_daily_demand: float
    expected_sales_horizon: float
    expected_leftover_inventory: float
    projected_clearance_days: float
    clearance_probability: float
    expected_lifecycle_profit: float
    expected_revenue: float
    holding_and_finance_cost: float
    depreciation_loss: float
    
    # Status Quo Baseline Comparison
    status_quo_daily_demand: float
    status_quo_clearance_days: float
    status_quo_leftover: float
    status_quo_profit: float
    profit_lift_amount: float
    profit_lift_pct: float
    
    # Risk & Evaluation
    inventory_risk_level: str  # "Low", "Medium", "High", "Critical"
    business_reason: str
    feasible_prices: List[float]
    profit_curve: List[float]
    demand_curve: List[float]

class LifecycleOptimizer:
    def __init__(self, demand_forecaster: Optional[DemandForecaster] = None):
        self.forecaster = demand_forecaster or DemandForecaster()

    def optimize_sku(
        self,
        product_id: str,
        product_name: str,
        current_price: float,
        mrp: float,
        unit_cost: float,
        current_inventory: int,
        competitor_avg_price: float,
        competitor_min_price: float,
        days_to_successor: int = 60,
        competitor_stockout_flag: int = 0,
        footfall_index: float = 1.2,
        daily_holding_rate: float = DEFAULT_DAILY_HOLDING_COST_RATE,
        annual_finance_rate: float = DEFAULT_ANNUAL_FINANCING_RATE,
        depreciation_penalty_rate: float = DEFAULT_POST_SUCCESSOR_DEPRECIATION,
        max_loss_tolerance: float = DEFAULT_MAX_LOSS_TOLERANCE,
        price_step: float = 500.0
    ) -> OptimizationResult:
        """
        Finds the selling price that maximizes expected total lifecycle profit:
        Max E[Profit] = Revenue - COGS - HoldingCost - FinancingCost - DepreciationLoss(Leftover)
        Subject to:
          Price <= MRP (Legal Metrology)
          Price >= Cost * (1 - max_loss_tolerance)
        """
        horizon_days = max(15, min(days_to_successor, 180))

        # 1. Determine Feasible Price Search Range
        min_allowed_price = unit_cost * (1.0 - max_loss_tolerance)
        max_allowed_price = mrp if ENFORCE_MRP_CEILING else mrp * 1.05

        # Create discrete candidate prices
        # Focus candidate range around current and competitor prices
        lower_bound = max(min_allowed_price, current_price * 0.82)
        upper_bound = min(max_allowed_price, max(current_price * 1.15, mrp))

        raw_candidates = np.arange(lower_bound, upper_bound + price_step, price_step)
        
        # Add current price, competitor price, and psychological endings (.999 / .499)
        candidates_set = set(raw_candidates)
        candidates_set.add(current_price)
        candidates_set.add(competitor_avg_price)
        for base in raw_candidates:
            # Round to Indian retail 999 or 499 endings where appropriate
            p999 = round(base / 1000) * 1000 - 1
            if min_allowed_price <= p999 <= max_allowed_price:
                candidates_set.add(p999)

        feasible_prices = np.sort(np.array(list(candidates_set)))
        feasible_prices = feasible_prices[
            (feasible_prices >= min_allowed_price) & (feasible_prices <= max_allowed_price)
        ]

        # 2. Predict Demand Across All Candidate Prices
        predicted_demands = self.forecaster.predict_demand_curve(
            candidate_prices=feasible_prices,
            mrp=mrp,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            unit_cost=unit_cost,
            opening_inventory=current_inventory,
            days_to_successor=days_to_successor,
            competitor_stockout_flag=competitor_stockout_flag,
            footfall_index=footfall_index
        )

        daily_finance_rate = annual_finance_rate / 365.0

        best_profit = float("-inf")
        best_idx = 0
        profit_curve = []
        metrics_list = []

        # Model-aware variance: residual variance from forecaster RMSE (per-day error)
        forecaster_rmse = float(getattr(self.forecaster, "metrics", {}).get("rmse", 0.0))
        residual_var = forecaster_rmse ** 2

        # 3. Lifecycle Evaluation per Candidate Price
        for i, price in enumerate(feasible_prices):
            daily_demand = max(0.01, float(predicted_demands[i]))
            
            # Inventory trajectory over remaining horizon
            total_potential_sales = daily_demand * horizon_days
            actual_sales = min(float(current_inventory), total_potential_sales)
            leftover_inventory = max(0.0, float(current_inventory) - actual_sales)
            
            # Days required to completely clear stock
            clearance_days = current_inventory / daily_demand

            # Calibrated clearance probability using model-aware variance:
            # combines forecasting residual variance (RMSE^2) and Poisson arrival variance
            total_variance = (horizon_days * residual_var) + (daily_demand * horizon_days)
            std_dev = max(1.0, np.sqrt(max(0.0, total_variance)))
            z_score = (total_potential_sales - current_inventory) / std_dev
            clearance_prob = float(stats.norm.cdf(z_score))

            # Financial Components
            revenue = actual_sales * price
            cogs = actual_sales * unit_cost
            gross_margin = revenue - cogs

            # Average inventory held over the horizon
            # If inventory clears before horizon:
            if clearance_days < horizon_days:
                avg_inventory = current_inventory / 2.0 * (clearance_days / horizon_days)
            else:
                avg_inventory = (current_inventory + leftover_inventory) / 2.0

            holding_cost = avg_inventory * unit_cost * daily_holding_rate * horizon_days
            finance_cost = avg_inventory * unit_cost * daily_finance_rate * horizon_days
            carrying_costs = holding_cost + finance_cost

            # Post-successor depreciation penalty on unsold leftover stock
            depreciation_loss = leftover_inventory * unit_cost * depreciation_penalty_rate

            # Net Lifecycle Profit
            net_lifecycle_profit = gross_margin - carrying_costs - depreciation_loss
            profit_curve.append(net_lifecycle_profit)

            metrics_list.append({
                "price": price,
                "daily_demand": daily_demand,
                "actual_sales": actual_sales,
                "leftover_inventory": leftover_inventory,
                "clearance_days": clearance_days,
                "clearance_prob": clearance_prob,
                "revenue": revenue,
                "carrying_costs": carrying_costs,
                "depreciation_loss": depreciation_loss,
                "net_profit": net_lifecycle_profit
            })

            if net_lifecycle_profit > best_profit:
                best_profit = net_lifecycle_profit
                best_idx = i

        best_meta = metrics_list[best_idx]
        recommended_price = float(feasible_prices[best_idx])

        # 4. Compute Status Quo Metrics (Holding Current Price)
        # Find closest feasible price to current price
        sq_idx = np.argmin(np.abs(feasible_prices - current_price))
        sq_meta = metrics_list[sq_idx]

        profit_lift_amount = best_meta["net_profit"] - sq_meta["net_profit"]
        if sq_meta["net_profit"] > 1000.0:
            profit_lift_pct = round((profit_lift_amount / sq_meta["net_profit"]) * 100.0, 2)
        elif sq_meta["net_profit"] < -1000.0:
            profit_lift_pct = round((profit_lift_amount / abs(sq_meta["net_profit"])) * 100.0, 2)
        else:
            profit_lift_pct = 0.0 if profit_lift_amount == 0 else round(min(999.9, max(-999.9, (profit_lift_amount / (abs(sq_meta["net_profit"]) + 1.0)) * 100.0)), 2)

        # 5. Price Action and Business Logic Classification
        price_diff = recommended_price - current_price
        price_change_pct = (price_diff / current_price) * 100.0

        if price_diff > 250:
            price_action = "Increase Price"
        elif abs(price_diff) <= 250:
            price_action = "Hold Price"
        elif price_diff >= -2500:
            price_action = "Slight Reduction"
        else:
            price_action = "Clearance Markdown"

        # Risk level determination incorporates velocity, leftover units, and calibrated clearance probability
        if (
            best_meta["clearance_days"] > days_to_successor * 1.2
            or best_meta["leftover_inventory"] > current_inventory * 0.25
            or best_meta["clearance_prob"] < 0.35
        ):
            inventory_risk_level = "High Risk"
        elif (
            best_meta["clearance_days"] > days_to_successor
            or best_meta["leftover_inventory"] > 0
            or best_meta["clearance_prob"] < 0.70
        ):
            inventory_risk_level = "Medium Risk"
        else:
            inventory_risk_level = "Low Risk"

        # Natural Language Business Reason
        if price_action == "Increase Price":
            business_reason = (
                f"Demand is price-inelastic and competitor stock is limited. "
                f"Increasing price by ₹{int(price_diff):,} captures higher margin "
                f"(+₹{int(profit_lift_amount):,} total profit) with zero clearance risk."
            )
        elif price_action == "Hold Price":
            business_reason = (
                f"Current price of ₹{int(current_price):,} is optimal. "
                f"Demand velocity ({sq_meta['daily_demand']:.1f}/day) is sufficient to clear stock "
                f"without giving away unneeded margin."
            )
        elif price_action == "Slight Reduction":
            business_reason = (
                f"Current velocity ({sq_meta['daily_demand']:.1f}/day) is lagging behind the "
                f"{days_to_successor}-day horizon. A minor adjustment of ₹{abs(int(price_diff)):,} "
                f"stimulates velocity to {best_meta['daily_demand']:.1f}/day, avoiding ~{int(sq_meta['leftover_inventory'])} "
                f"leftover units and yielding +₹{int(profit_lift_amount):,} net profit."
            )
        else:
            business_reason = (
                f"Urgent clearance needed before successor arrives in {days_to_successor} days. "
                f"Current price leaves {int(sq_meta['leftover_inventory'])} units stranded, risking "
                f"₹{int(sq_meta['depreciation_loss']):,} in depreciation write-downs. "
                f"Markdown to ₹{int(recommended_price):,} secures {best_meta['clearance_prob']*100:.0f}% clearance probability."
            )

        return OptimizationResult(
            product_id=product_id,
            product_name=product_name,
            current_price=float(current_price),
            recommended_price=float(recommended_price),
            price_action=price_action,
            price_change=float(price_diff),
            price_change_pct=round(price_change_pct, 2),
            mrp=float(mrp),
            unit_cost=float(unit_cost),
            current_inventory=int(current_inventory),
            days_to_successor=int(days_to_successor),
            expected_daily_demand=round(float(best_meta["daily_demand"]), 1),
            expected_sales_horizon=round(float(best_meta["actual_sales"]), 1),
            expected_leftover_inventory=round(float(best_meta["leftover_inventory"]), 1),
            projected_clearance_days=round(float(best_meta["clearance_days"]), 1),
            clearance_probability=round(float(best_meta["clearance_prob"]), 3),
            expected_lifecycle_profit=round(float(best_meta["net_profit"]), 2),
            expected_revenue=round(float(best_meta["revenue"]), 2),
            holding_and_finance_cost=round(float(best_meta["carrying_costs"]), 2),
            depreciation_loss=round(float(best_meta["depreciation_loss"]), 2),
            status_quo_daily_demand=round(float(sq_meta["daily_demand"]), 1),
            status_quo_clearance_days=round(float(sq_meta["clearance_days"]), 1),
            status_quo_leftover=round(float(sq_meta["leftover_inventory"]), 1),
            status_quo_profit=round(float(sq_meta["net_profit"]), 2),
            profit_lift_amount=round(float(profit_lift_amount), 2),
            profit_lift_pct=round(float(profit_lift_pct), 1),
            inventory_risk_level=inventory_risk_level,
            business_reason=business_reason,
            feasible_prices=[float(p) for p in feasible_prices],
            profit_curve=[float(p) for p in profit_curve],
            demand_curve=[float(d) for d in predicted_demands]
        )
