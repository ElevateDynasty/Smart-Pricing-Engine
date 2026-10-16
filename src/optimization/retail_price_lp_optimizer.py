"""
Retail Price Revenue & Portfolio Linear Programming (LP) Optimizer

Inspired by and extending:
    https://github.com/ozzienobayrak/Retail_Price_Revenue_Optimisation
    (Özlem Albayrak, Data Scientist / Economist)

Key Components:
1. RetailPriceRevenueSimulator:
   - Evaluates demand response across candidate price grids (P_grid in [grid_low, grid_high]).
   - Implements supply feasibility capping under Low (80%), Medium (100%), and High (120%)
     inventory scenarios: Q_feasible = min(Q_pred, Available_Stock).
   - Computes point price elasticity via finite difference price shocks (delta = 5%).
   - Produces price-sales and price-revenue curves.

2. RetailPortfolioLPOptimizer (Linear Programming Integration):
   - Formulates the global multi-product / multi-store retail pricing problem as an
     exact Mixed-Integer Linear Program (MILP / LP) solved via scipy.optimize.milp
     or scipy.optimize.linprog using the HiGHS solver engine.
   - Objective: Maximize Total Portfolio Revenue (or Profit).
   - Constraints:
       * Exactly one price chosen per SKU: SUM_m x_km = 1  forall k
       * Shared warehouse / store inventory capacity budget: SUM_km Q_km * x_km <= Total_Stock
       * Portfolio minimum gross margin floor: SUM_km (R_km - C_k * Q_km) * x_km >= theta * SUM_km R_km * x_km
       * Maximum portfolio price drift / inflation cap: (1/K) SUM_km ((P_km - P_k0)/P_k0) * x_km <= Delta_max
       * Minimum portfolio unit volume floor (footfall protection): SUM_km Q_km * x_km >= Min_Units
   - Seamlessly couples with MultiStoreBalancer (transportation LP) for spatial multi-branch rebalancing.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds, linprog

from src.models.demand_forecaster import DemandForecaster
from src.optimization.multi_store_balancer import MultiStoreBalancer


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PriceSimulationPoint:
    candidate_price: float
    price_change_pct: float
    predicted_demand: float
    feasible_sales: float
    predicted_revenue: float
    predicted_profit: float
    margin_pct: float
    stock_capped: bool


@dataclass
class SingleProductSimulationResult:
    product_id: str
    product_name: str
    current_price: float
    unit_cost: float
    mrp: float
    available_stock: int
    scenario: str
    finite_difference_elasticity_5pct: Optional[float]
    best_revenue_price: float
    best_revenue_value: float
    best_profit_price: float
    best_profit_value: float
    status_quo_revenue: float
    status_quo_profit: float
    sim_table: List[PriceSimulationPoint]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "current_price": round(self.current_price, 2),
            "unit_cost": round(self.unit_cost, 2),
            "mrp": round(self.mrp, 2),
            "available_stock": self.available_stock,
            "scenario": self.scenario,
            "finite_difference_elasticity_5pct": (
                round(self.finite_difference_elasticity_5pct, 3)
                if self.finite_difference_elasticity_5pct is not None else None
            ),
            "best_revenue_price": round(self.best_revenue_price, 2),
            "best_revenue_value": round(self.best_revenue_value, 2),
            "best_profit_price": round(self.best_profit_price, 2),
            "best_profit_value": round(self.best_profit_value, 2),
            "status_quo_revenue": round(self.status_quo_revenue, 2),
            "status_quo_profit": round(self.status_quo_profit, 2),
            "sim_table": [
                {
                    "candidate_price": round(pt.candidate_price, 2),
                    "price_change_pct": round(pt.price_change_pct, 4),
                    "predicted_demand": round(pt.predicted_demand, 2),
                    "feasible_sales": round(pt.feasible_sales, 2),
                    "predicted_revenue": round(pt.predicted_revenue, 2),
                    "predicted_profit": round(pt.predicted_profit, 2),
                    "margin_pct": round(pt.margin_pct, 4),
                    "stock_capped": pt.stock_capped
                }
                for pt in self.sim_table
            ]
        }


@dataclass
class PortfolioLPResult:
    solver_status: str                     # "optimal", "feasible", "infeasible"
    objective_type: str                   # "revenue" or "profit"
    total_portfolio_revenue: float
    total_portfolio_profit: float
    total_portfolio_units: float
    portfolio_margin_pct: float
    average_price_drift_pct: float
    status_quo_revenue: float
    status_quo_profit: float
    revenue_lift: float
    revenue_lift_pct: float
    profit_lift: float
    profit_lift_pct: float
    selected_items: List[Dict[str, Any]]
    binding_constraints: List[str]
    transfer_plan: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solver_status": self.solver_status,
            "objective_type": self.objective_type,
            "total_portfolio_revenue": round(self.total_portfolio_revenue, 2),
            "total_portfolio_profit": round(self.total_portfolio_profit, 2),
            "total_portfolio_units": round(self.total_portfolio_units, 2),
            "portfolio_margin_pct": round(self.portfolio_margin_pct, 4),
            "average_price_drift_pct": round(self.average_price_drift_pct, 4),
            "status_quo_revenue": round(self.status_quo_revenue, 2),
            "status_quo_profit": round(self.status_quo_profit, 2),
            "revenue_lift": round(self.revenue_lift, 2),
            "revenue_lift_pct": round(self.revenue_lift_pct, 2),
            "profit_lift": round(self.profit_lift, 2),
            "profit_lift_pct": round(self.profit_lift_pct, 2),
            "selected_items": self.selected_items,
            "binding_constraints": self.binding_constraints,
            "transfer_plan": self.transfer_plan
        }


# ---------------------------------------------------------------------------
# Simulator Class (ozzienobayrak formulation)
# ---------------------------------------------------------------------------

class RetailPriceRevenueSimulator:
    """
    Simulates retail price elasticity and revenue curves under supply constraints,
    directly implementing the methodology from Retail_Price_Revenue_Optimisation.
    """
    SCENARIO_MULTIPLIERS = {
        "Low": 0.8,
        "Medium": 1.0,
        "High": 1.2
    }

    def __init__(self, forecaster: Optional[DemandForecaster] = None):
        self.forecaster = forecaster or DemandForecaster()

    def get_inventory_capacity(
        self,
        base_inventory: int,
        scenario: str = "Medium"
    ) -> int:
        """Applies scenario multiplier (Low 80%, Medium 100%, High 120%) to base stock."""
        mult = self.SCENARIO_MULTIPLIERS.get(scenario, 1.0)
        return int(max(1, round(base_inventory * mult)))

    def simulate_sku_prices(
        self,
        product_id: str,
        product_name: str,
        current_price: float,
        unit_cost: float,
        mrp: float,
        current_inventory: int,
        competitor_avg_price: float,
        competitor_min_price: float,
        scenario: str = "Medium",
        grid_low: float = 0.80,
        grid_high: float = 1.20,
        n_prices: int = 9,
        days_to_successor: int = 60,
        competitor_stockout_flag: int = 0,
        footfall_index: float = 1.2,
        is_weekend: int = 0,
        is_festive_season: int = 0
    ) -> SingleProductSimulationResult:
        """
        Evaluates candidate prices, predicts demand via LightGBM, caps feasible sales
        to available stock under the chosen inventory scenario, and calculates revenue.
        """
        available_stock = self.get_inventory_capacity(current_inventory, scenario)

        # Enforce legal metrology ceiling (cannot price above MRP) and wholesale floor (P >= unit_cost)
        min_p = max(float(unit_cost), current_price * grid_low)
        max_p = min(float(mrp), current_price * grid_high)
        if max_p < min_p:
            max_p = min_p

        price_grid = np.unique(np.round(np.linspace(min_p, max_p, n_prices), 2))
        if current_price not in price_grid:
            price_grid = np.unique(np.sort(np.append(price_grid, round(current_price, 2))))

        points: List[PriceSimulationPoint] = []
        best_rev_p = current_price
        best_rev_val = -1.0
        best_prof_p = current_price
        best_prof_val = -1e9

        status_quo_rev = 0.0
        status_quo_prof = 0.0

        for p in price_grid:
            # Predict demand via demand forecaster
            pred_demand = float(self.forecaster.predict_point(
                selling_price=p,
                mrp=mrp,
                competitor_avg_price=competitor_avg_price,
                competitor_min_price=competitor_min_price,
                unit_cost=unit_cost,
                opening_inventory=available_stock,
                days_to_successor=days_to_successor,
                competitor_stockout_flag=competitor_stockout_flag,
                footfall_index=footfall_index,
                is_weekend=is_weekend,
                is_festive_season=is_festive_season
            ))
            pred_demand = max(0.0, pred_demand)

            # Cap feasible sales to available stock
            feasible = min(pred_demand, float(available_stock))
            stock_capped = bool(pred_demand > available_stock)

            revenue = p * feasible
            profit = (p - unit_cost) * feasible
            margin_pct = (p - unit_cost) / (p + 1e-6)
            price_change = (p - current_price) / (current_price + 1e-6)

            pt = PriceSimulationPoint(
                candidate_price=float(p),
                price_change_pct=float(price_change),
                predicted_demand=float(pred_demand),
                feasible_sales=float(feasible),
                predicted_revenue=float(revenue),
                predicted_profit=float(profit),
                margin_pct=float(margin_pct),
                stock_capped=stock_capped
            )
            points.append(pt)

            if revenue > best_rev_val:
                best_rev_val = revenue
                best_rev_p = p

            if profit > best_prof_val:
                best_prof_val = profit
                best_prof_p = p

            if abs(p - current_price) < 1e-2:
                status_quo_rev = revenue
                status_quo_prof = profit

        # If current_price wasn't evaluated exactly, estimate status quo
        if status_quo_rev == 0.0 and len(points) > 0:
            status_quo_rev = points[0].predicted_revenue
            status_quo_prof = points[0].predicted_profit

        # Finite Difference Elasticity at delta = +5% (ozzienobayrak formulation)
        p_base = current_price
        p_up = min(float(mrp), p_base * 1.05)
        delta_pct = (p_up - p_base) / p_base if p_base > 0 else 0.05
        
        q_base = float(self.forecaster.predict_point(
            selling_price=p_base, mrp=mrp,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            unit_cost=unit_cost, opening_inventory=available_stock,
            days_to_successor=days_to_successor,
            competitor_stockout_flag=competitor_stockout_flag,
            footfall_index=footfall_index
        ))
        q_up = float(self.forecaster.predict_point(
            selling_price=p_up, mrp=mrp,
            competitor_avg_price=competitor_avg_price,
            competitor_min_price=competitor_min_price,
            unit_cost=unit_cost, opening_inventory=available_stock,
            days_to_successor=days_to_successor,
            competitor_stockout_flag=competitor_stockout_flag,
            footfall_index=footfall_index
        ))

        finite_diff_elasticity = None
        if q_base > 1e-4 and delta_pct > 1e-4:
            raw_e = -((q_up - q_base) / q_base) / delta_pct
            finite_diff_elasticity = float(np.clip(raw_e, 0.0, 10.0))

        return SingleProductSimulationResult(
            product_id=product_id,
            product_name=product_name,
            current_price=current_price,
            unit_cost=unit_cost,
            mrp=mrp,
            available_stock=available_stock,
            scenario=scenario,
            finite_difference_elasticity_5pct=finite_diff_elasticity,
            best_revenue_price=best_rev_p,
            best_revenue_value=best_rev_val,
            best_profit_price=best_prof_p,
            best_profit_value=best_prof_val,
            status_quo_revenue=status_quo_rev,
            status_quo_profit=status_quo_prof,
            sim_table=points
        )


# ---------------------------------------------------------------------------
# Linear Programming (LP / MILP) Portfolio Optimizer
# ---------------------------------------------------------------------------

class RetailPortfolioLPOptimizer:
    """
    Integrates Linear Programming / Mixed-Integer Linear Programming (MILP)
    to solve portfolio-wide optimal retail pricing.

    Given candidate price options for K products (derived from RetailPriceRevenueSimulator),
    this solves:

        Maximize   SUM_{k=1}^K SUM_{m=1}^M  c_{k,m} * x_{k,m}
        Subject to:
          (1) SUM_m x_{k,m} = 1                    for all k (exactly one price per item)
          (2) SUM_{k,m} Q_{k,m} * x_{k,m} <= Cap   (total inventory capacity limit)
          (3) SUM_{k,m} [M_{k,m} - theta * R_{k,m}] * x_{k,m} >= 0  (portfolio margin floor)
          (4) (1/K) SUM_{k,m} ((P_{k,m} - P_k0)/P_k0) * x_{k,m} <= Delta_max (price drift cap)
          (5) SUM_{k,m} Q_{k,m} * x_{k,m} >= Min_Q (optional unit footfall floor)
          (6) x_{k,m} in {0, 1}

    Solved with scipy.optimize.milp (exact binary HiGHS solver) or linprog (LP relaxation).
    """

    def __init__(self, simulator: Optional[RetailPriceRevenueSimulator] = None):
        self.simulator = simulator or RetailPriceRevenueSimulator()
        self.balancer = MultiStoreBalancer()

    def optimize_portfolio(
        self,
        item_simulations: List[SingleProductSimulationResult],
        objective: str = "revenue",               # "revenue" or "profit"
        total_inventory_capacity: Optional[float] = None,
        min_portfolio_margin_pct: Optional[float] = None,
        max_portfolio_price_drift_pct: Optional[float] = 0.08,  # e.g. +8% avg price increase max
        min_total_units: Optional[float] = None,
        use_integer_milp: bool = True,
        multi_store_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> PortfolioLPResult:
        """
        Solves the constrained portfolio pricing Linear Program.
        """
        K = len(item_simulations)
        if K == 0:
            raise ValueError("item_simulations list cannot be empty.")

        # Build variable indices and flattened vectors
        # For each SKU k, there are M_k candidate price options
        flat_prices = []
        flat_demands = []
        flat_revenues = []
        flat_profits = []
        flat_drifts = []
        flat_sku_indices = []

        for k, sim in enumerate(item_simulations):
            for pt in sim.sim_table:
                flat_prices.append(pt.candidate_price)
                flat_demands.append(pt.feasible_sales)
                flat_revenues.append(pt.predicted_revenue)
                flat_profits.append(pt.predicted_profit)
                flat_drifts.append(pt.price_change_pct)
                flat_sku_indices.append(k)

        num_vars = len(flat_prices)
        c_rev = np.array(flat_revenues, dtype=float)
        c_prof = np.array(flat_profits, dtype=float)
        q_units = np.array(flat_demands, dtype=float)
        p_drifts = np.array(flat_drifts, dtype=float)
        p_prices = np.array(flat_prices, dtype=float)

        # Objective vector: milp minimizes c^T x, so negate for maximization
        if objective == "profit":
            c_obj = -c_prof
        else:
            c_obj = -c_rev

        # Constraints
        # (1) Exactly one price per SKU (K equality constraints)
        A_rows = []
        lhs = []
        rhs = []
        constraint_names = []

        for k in range(K):
            row = np.zeros(num_vars)
            for v_idx, sku_k in enumerate(flat_sku_indices):
                if sku_k == k:
                    row[v_idx] = 1.0
            A_rows.append(row)
            lhs.append(1.0)
            rhs.append(1.0)
            constraint_names.append(f"select_one_price_sku_{item_simulations[k].product_id}")

        # (2) Total Inventory Capacity Budget: SUM q_i x_i <= total_inventory_capacity
        if total_inventory_capacity is not None and total_inventory_capacity > 0:
            A_rows.append(q_units)
            lhs.append(0.0)
            rhs.append(float(total_inventory_capacity))
            constraint_names.append("inventory_capacity_budget")

        # (3) Minimum Portfolio Gross Margin: SUM (profit_i - theta * rev_i) x_i >= 0
        if min_portfolio_margin_pct is not None and min_portfolio_margin_pct > 0:
            margin_coefs = c_prof - (min_portfolio_margin_pct * c_rev)
            A_rows.append(margin_coefs)
            lhs.append(0.0)
            rhs.append(np.inf)
            constraint_names.append("portfolio_margin_floor")

        # (4) Maximum Portfolio Price Drift: (1/K) SUM price_change_pct_i x_i <= max_drift
        if max_portfolio_price_drift_pct is not None:
            drift_coefs = p_drifts / float(K)
            A_rows.append(drift_coefs)
            lhs.append(-np.inf)
            rhs.append(float(max_portfolio_price_drift_pct))
            constraint_names.append("max_portfolio_price_drift")

        # (5) Minimum Total Units (Footfall protection): SUM q_i x_i >= min_total_units
        if min_total_units is not None and min_total_units > 0:
            A_rows.append(q_units)
            lhs.append(float(min_total_units))
            rhs.append(np.inf)
            constraint_names.append("min_total_units_floor")

        A_mat = np.vstack(A_rows)
        lhs_vec = np.array(lhs)
        rhs_vec = np.array(rhs)

        # Solve using scipy.optimize.milp (HiGHS exact integer solver)
        constraints = LinearConstraint(A_mat, lhs_vec, rhs_vec)
        integrality = np.ones(num_vars) if use_integer_milp else np.zeros(num_vars)
        bounds = Bounds(lb=0.0, ub=1.0)

        res = milp(
            c=c_obj,
            integrality=integrality,
            bounds=bounds,
            constraints=constraints
        )

        solver_status = "optimal" if res.success else "feasible"
        if not res.success or res.x is None:
            # Fall back to LP relaxation with linprog
            A_ub = []
            b_ub = []
            A_eq = []
            b_eq = []

            for i, name in enumerate(constraint_names):
                if lhs[i] == rhs[i]:
                    A_eq.append(A_rows[i])
                    b_eq.append(lhs[i])
                else:
                    if rhs[i] < np.inf:
                        A_ub.append(A_rows[i])
                        b_ub.append(rhs[i])
                    if lhs[i] > -np.inf:
                        A_ub.append(-A_rows[i])
                        b_ub.append(-lhs[i])

            res_lp = linprog(
                c=c_obj,
                A_ub=np.array(A_ub) if A_ub else None,
                b_ub=np.array(b_ub) if b_ub else None,
                A_eq=np.array(A_eq) if A_eq else None,
                b_eq=np.array(b_eq) if b_eq else None,
                bounds=(0.0, 1.0),
                method="highs"
            )

            if res_lp.success and res_lp.x is not None:
                x_sol = res_lp.x
                solver_status = "feasible_lp_relaxation"
            else:
                # Fall back to unconstrained simulation best
                solver_status = "infeasible_fallback"
                x_sol = np.zeros(num_vars)
                for k, sim in enumerate(item_simulations):
                    best_price = sim.best_profit_price if objective == "profit" else sim.best_revenue_price
                    # find matching var index
                    for v_idx, sku_k in enumerate(flat_sku_indices):
                        if sku_k == k and abs(flat_prices[v_idx] - best_price) < 1e-2:
                            x_sol[v_idx] = 1.0
                            break
        else:
            x_sol = res.x

        # Decode selections
        selected_items = []
        tot_rev = 0.0
        tot_prof = 0.0
        tot_units = 0.0
        tot_drift = 0.0
        status_quo_rev = 0.0
        status_quo_prof = 0.0

        for k, sim in enumerate(item_simulations):
            status_quo_rev += sim.status_quo_revenue
            status_quo_prof += sim.status_quo_profit

            # Pick the variable with highest weight for sku k
            best_v_for_k = None
            best_weight = -1.0
            for v_idx, sku_k in enumerate(flat_sku_indices):
                if sku_k == k:
                    if x_sol[v_idx] > best_weight:
                        best_weight = x_sol[v_idx]
                        best_v_for_k = v_idx

            if best_v_for_k is not None:
                sel_p = flat_prices[best_v_for_k]
                sel_q = flat_demands[best_v_for_k]
                sel_r = flat_revenues[best_v_for_k]
                sel_m = flat_profits[best_v_for_k]
                sel_d = flat_drifts[best_v_for_k]

                tot_rev += sel_r
                tot_prof += sel_m
                tot_units += sel_q
                tot_drift += sel_d

                selected_items.append({
                    "product_id": sim.product_id,
                    "product_name": sim.product_name,
                    "current_price": round(sim.current_price, 2),
                    "optimal_price": round(sel_p, 2),
                    "price_change_pct": round(sel_d, 4),
                    "feasible_sales": round(sel_q, 2),
                    "predicted_revenue": round(sel_r, 2),
                    "predicted_profit": round(sel_m, 2),
                    "margin_pct": round((sel_p - sim.unit_cost) / (sel_p + 1e-6), 4),
                    "status_quo_revenue": round(sim.status_quo_revenue, 2),
                    "status_quo_profit": round(sim.status_quo_profit, 2),
                    "revenue_lift": round(sel_r - sim.status_quo_revenue, 2),
                    "finite_difference_elasticity": (
                        round(sim.finite_difference_elasticity_5pct, 3)
                        if sim.finite_difference_elasticity_5pct is not None else None
                    )
                })

        avg_drift = tot_drift / float(K) if K > 0 else 0.0
        portfolio_margin = tot_prof / tot_rev if tot_rev > 0 else 0.0

        rev_lift = tot_rev - status_quo_rev
        rev_lift_pct = (rev_lift / status_quo_rev * 100.0) if status_quo_rev > 0 else 0.0
        prof_lift = tot_prof - status_quo_prof
        prof_lift_pct = (prof_lift / status_quo_prof * 100.0) if status_quo_prof > 0 else 0.0

        # Check binding constraints
        binding = []
        if total_inventory_capacity is not None and abs(tot_units - total_inventory_capacity) < 2.0:
            binding.append("inventory_capacity_budget")
        if min_portfolio_margin_pct is not None and abs(portfolio_margin - min_portfolio_margin_pct) < 0.01:
            binding.append("portfolio_margin_floor")
        if max_portfolio_price_drift_pct is not None and abs(avg_drift - max_portfolio_price_drift_pct) < 0.01:
            binding.append("max_portfolio_price_drift")

        # Multi-Store Inventory Balancer coupling if store data is provided
        transfer_plan = None
        if multi_store_data:
            transfer_records = []
            for item in selected_items:
                pid = item["product_id"]
                if pid in multi_store_data:
                    res_bal = self.balancer.analyze_sku_across_stores(
                        product_id=pid,
                        product_name=item["product_name"],
                        unit_cost=float([s.unit_cost for s in item_simulations if s.product_id == pid][0]),
                        mrp=float([s.mrp for s in item_simulations if s.product_id == pid][0]),
                        store_data=multi_store_data[pid]
                    )
                    transfer_records.append(res_bal)
            if transfer_records:
                transfer_plan = {
                    "method": "Transportation Linear Program (HiGHS)",
                    "analyzed_skus": len(transfer_records),
                    "sku_transfers": transfer_records
                }

        return PortfolioLPResult(
            solver_status=solver_status,
            objective_type=objective,
            total_portfolio_revenue=tot_rev,
            total_portfolio_profit=tot_prof,
            total_portfolio_units=tot_units,
            portfolio_margin_pct=portfolio_margin,
            average_price_drift_pct=avg_drift,
            status_quo_revenue=status_quo_rev,
            status_quo_profit=status_quo_prof,
            revenue_lift=rev_lift,
            revenue_lift_pct=rev_lift_pct,
            profit_lift=prof_lift,
            profit_lift_pct=prof_lift_pct,
            selected_items=selected_items,
            binding_constraints=binding,
            transfer_plan=transfer_plan
        )
