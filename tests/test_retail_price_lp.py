"""
Tests for Retail Price Revenue Simulator & Portfolio Linear Programming Optimizer
Validating integration of ozzienobayrak/Retail_Price_Revenue_Optimisation methodology
and HiGHS Linear Programming (LP / MILP) constraints.
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient

from api.main import app
from src.optimization.retail_price_lp_optimizer import (
    RetailPriceRevenueSimulator,
    RetailPortfolioLPOptimizer,
    SingleProductSimulationResult,
    PortfolioLPResult
)

client = TestClient(app)


@pytest.fixture
def simulator():
    return RetailPriceRevenueSimulator()


@pytest.fixture
def lp_optimizer(simulator):
    return RetailPortfolioLPOptimizer(simulator=simulator)


@pytest.fixture
def sample_sku_simulations(simulator):
    """Generates simulation results for 3 flagship electronics items."""
    items = [
        {
            "product_id": "SKU_IPHONE_16",
            "product_name": "iPhone 16 (128GB)",
            "current_price": 69999.0,
            "unit_cost": 58000.0,
            "mrp": 79900.0,
            "current_inventory": 70,
            "competitor_avg_price": 66490.0,
            "competitor_min_price": 64999.0,
            "scenario": "Medium"
        },
        {
            "product_id": "SKU_GALAXY_S25",
            "product_name": "Samsung Galaxy S25 (256GB)",
            "current_price": 79999.0,
            "unit_cost": 64000.0,
            "mrp": 89999.0,
            "current_inventory": 85,
            "competitor_avg_price": 76990.0,
            "competitor_min_price": 74999.0,
            "scenario": "Medium"
        },
        {
            "product_id": "SKU_ONEPLUS_13",
            "product_name": "OnePlus 13 (256GB)",
            "current_price": 64999.0,
            "unit_cost": 52000.0,
            "mrp": 69999.0,
            "current_inventory": 90,
            "competitor_avg_price": 62990.0,
            "competitor_min_price": 61499.0,
            "scenario": "Medium"
        }
    ]
    return [
        simulator.simulate_sku_prices(
            product_id=it["product_id"],
            product_name=it["product_name"],
            current_price=it["current_price"],
            unit_cost=it["unit_cost"],
            mrp=it["mrp"],
            current_inventory=it["current_inventory"],
            competitor_avg_price=it["competitor_avg_price"],
            competitor_min_price=it["competitor_min_price"],
            scenario=it["scenario"],
            n_prices=9
        )
        for it in items
    ]


# ---------------------------------------------------------------------------
# Simulator Unit Tests
# ---------------------------------------------------------------------------

def test_simulator_grid_and_capping(simulator):
    """
    Validates price grid generation, inventory feasibility capping,
    and revenue computation (ozzienobayrak methodology).
    """
    res = simulator.simulate_sku_prices(
        product_id="SKU_TEST_01",
        product_name="Test Smartphone",
        current_price=50000.0,
        unit_cost=40000.0,
        mrp=60000.0,
        current_inventory=50,
        competitor_avg_price=49000.0,
        competitor_min_price=48000.0,
        scenario="Medium",
        n_prices=9
    )

    assert isinstance(res, SingleProductSimulationResult)
    assert len(res.sim_table) >= 9
    assert res.available_stock == 50

    for pt in res.sim_table:
        # Feasible sales must be non-negative and strictly <= available stock
        assert 0.0 <= pt.feasible_sales <= res.available_stock
        # Legal Metrology ceiling: Candidate price <= MRP
        assert pt.candidate_price <= res.mrp + 1e-4
        # Wholesale cost floor: Candidate price >= unit_cost
        assert pt.candidate_price >= res.unit_cost - 1e-4
        # Revenue = price * feasible sales
        assert abs(pt.predicted_revenue - (pt.candidate_price * pt.feasible_sales)) < 1e-3
        # Profit = (price - unit_cost) * feasible sales
        expected_profit = (pt.candidate_price - res.unit_cost) * pt.feasible_sales
        assert abs(pt.predicted_profit - expected_profit) < 1e-3

    # Best prices must be within evaluated grid
    grid_prices = [pt.candidate_price for pt in res.sim_table]
    assert res.best_revenue_price in grid_prices
    assert res.best_profit_price in grid_prices


def test_simulator_inventory_scenarios(simulator):
    """Validates Low (80%), Medium (100%), and High (120%) inventory capping multipliers."""
    base_inv = 100
    res_low = simulator.simulate_sku_prices(
        product_id="SKU_TEST_01", product_name="Test", current_price=50000.0,
        unit_cost=40000.0, mrp=60000.0, current_inventory=base_inv,
        competitor_avg_price=49000.0, competitor_min_price=48000.0,
        scenario="Low"
    )
    res_med = simulator.simulate_sku_prices(
        product_id="SKU_TEST_01", product_name="Test", current_price=50000.0,
        unit_cost=40000.0, mrp=60000.0, current_inventory=base_inv,
        competitor_avg_price=49000.0, competitor_min_price=48000.0,
        scenario="Medium"
    )
    res_hi = simulator.simulate_sku_prices(
        product_id="SKU_TEST_01", product_name="Test", current_price=50000.0,
        unit_cost=40000.0, mrp=60000.0, current_inventory=base_inv,
        competitor_avg_price=49000.0, competitor_min_price=48000.0,
        scenario="High"
    )

    assert res_low.available_stock == 80
    assert res_med.available_stock == 100
    assert res_hi.available_stock == 120


def test_simulator_finite_difference_elasticity(simulator):
    """Validates finite difference elasticity computation (+5% shock)."""
    res = simulator.simulate_sku_prices(
        product_id="SKU_TEST_01", product_name="Test", current_price=50000.0,
        unit_cost=40000.0, mrp=60000.0, current_inventory=100,
        competitor_avg_price=49000.0, competitor_min_price=48000.0
    )
    assert res.finite_difference_elasticity_5pct is not None
    assert 0.0 <= res.finite_difference_elasticity_5pct <= 10.0


# ---------------------------------------------------------------------------
# Linear Programming (LP / MILP) Portfolio Optimizer Tests
# ---------------------------------------------------------------------------

def test_portfolio_lp_unconstrained_optimization(lp_optimizer, sample_sku_simulations):
    """
    Validates that the LP solver selects exactly one price per SKU
    and achieves an optimal or feasible status.
    """
    res_rev = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue"
    )

    assert isinstance(res_rev, PortfolioLPResult)
    assert res_rev.solver_status in ("optimal", "feasible", "feasible_lp_relaxation")
    assert len(res_rev.selected_items) == len(sample_sku_simulations)
    assert res_rev.total_portfolio_revenue > 0

    # Ensure every SKU has a selected price
    selected_pids = {it["product_id"] for it in res_rev.selected_items}
    expected_pids = {s.product_id for s in sample_sku_simulations}
    assert selected_pids == expected_pids

    # When optimizing profit, portfolio profit must be strictly positive
    res_prof = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="profit"
    )
    assert res_prof.total_portfolio_profit > 0


def test_portfolio_lp_inventory_capacity_constraint(lp_optimizer, sample_sku_simulations):
    """
    Validates that total inventory capacity budget constraint is satisfied:
    SUM_k Q_k <= Total_Cap.
    """
    # Unconstrained volume
    res_uncon = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue"
    )
    uncon_units = res_uncon.total_portfolio_units

    # Enforce tight inventory capacity (e.g. 70% of unconstrained)
    tight_cap = uncon_units * 0.70
    res_tight = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue",
        total_inventory_capacity=tight_cap
    )

    assert res_tight.total_portfolio_units <= tight_cap + 1e-3
    assert res_tight.solver_status in ("optimal", "feasible", "feasible_lp_relaxation")


def test_portfolio_lp_margin_floor_constraint(lp_optimizer, sample_sku_simulations):
    """
    Validates that the minimum portfolio gross margin constraint is satisfied:
    Portfolio Margin >= min_portfolio_margin_pct.
    """
    min_margin = 0.18  # 18%
    res = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue",
        min_portfolio_margin_pct=min_margin
    )

    assert res.portfolio_margin_pct >= min_margin - 1e-4
    assert res.solver_status in ("optimal", "feasible", "feasible_lp_relaxation")


def test_portfolio_lp_price_drift_constraint(lp_optimizer, sample_sku_simulations):
    """
    Validates that portfolio price drift constraint prevents excessive inflation:
    Average Price Drift <= max_portfolio_price_drift_pct.
    """
    max_drift = 0.05  # +5% max average increase
    res = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue",
        max_portfolio_price_drift_pct=max_drift
    )

    assert res.average_price_drift_pct <= max_drift + 1e-4


def test_portfolio_lp_multi_store_coupling(lp_optimizer, sample_sku_simulations):
    """
    Validates coupling between Portfolio LP and Transportation LP (MultiStoreBalancer).
    """
    store_data = {
        "SKU_IPHONE_16": [
            {"store_id": "ST_01", "store_name": "Mumbai", "city": "Mumbai", "current_inventory": 8, "daily_sales_velocity": 1.5},
            {"store_id": "ST_02", "store_name": "Delhi", "city": "Delhi", "current_inventory": 75, "daily_sales_velocity": 0.8}
        ]
    }

    res = lp_optimizer.optimize_portfolio(
        item_simulations=sample_sku_simulations,
        objective="revenue",
        multi_store_data=store_data
    )

    assert res.transfer_plan is not None
    assert res.transfer_plan["method"] == "Transportation Linear Program (HiGHS)"
    assert res.transfer_plan["analyzed_skus"] >= 1


# ---------------------------------------------------------------------------
# FastAPI REST Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_retail_lp_simulate():
    """Tests POST /api/retail-lp/simulate endpoint."""
    payload = {
        "product_id": "SKU_API_001",
        "product_name": "FastAPI Test Phone",
        "current_price": 70000.0,
        "unit_cost": 56000.0,
        "mrp": 79999.0,
        "current_inventory": 60,
        "competitor_avg_price": 68000.0,
        "competitor_min_price": 66500.0,
        "scenario": "Medium",
        "n_prices": 7
    }
    resp = client.post("/api/retail-lp/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["product_id"] == "SKU_API_001"
    assert len(data["data"]["sim_table"]) >= 7


def test_api_retail_lp_optimize_portfolio():
    """Tests POST /api/retail-lp/optimize-portfolio endpoint."""
    payload = {
        "objective": "revenue",
        "min_portfolio_margin_pct": 0.15,
        "max_portfolio_price_drift_pct": 0.08
    }
    resp = client.post("/api/retail-lp/optimize-portfolio", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["method"] == "Mixed-Integer Linear Programming (HiGHS MILP / LP)"
    assert data["data"]["total_portfolio_revenue"] > 0
    assert len(data["data"]["selected_items"]) >= 3


def test_api_retail_lp_demo_portfolio():
    """Tests GET /api/retail-lp/demo-portfolio endpoint."""
    resp = client.get("/api/retail-lp/demo-portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["total_portfolio_profit"] > 0
