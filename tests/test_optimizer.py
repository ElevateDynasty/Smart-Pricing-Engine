"""
Tests for Constrained Lifecycle Profit Optimizer and Multi-Store Balancer
"""
import pytest
from src.optimization.lifecycle_optimizer import LifecycleOptimizer
from src.optimization.multi_store_balancer import MultiStoreBalancer
from src.optimization.price_path_generator import PricePathGenerator
from src.models.demand_forecaster import DemandForecaster

def test_optimizer_mrp_constraint():
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()
    optimizer = LifecycleOptimizer(forecaster)

    res = optimizer.optimize_sku(
        product_id="SKU_IPHONE_17_256",
        product_name="iPhone 17 256GB",
        current_price=79999.0,
        mrp=84999.0,
        unit_cost=68000.0,
        current_inventory=800,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        days_to_successor=60
    )

    # Constraint checks
    assert res.recommended_price <= res.mrp, "Price must never exceed MRP (Legal Metrology)"
    assert res.recommended_price >= res.unit_cost, "Price must not be below acquisition cost"
    assert res.expected_daily_demand > 0
    assert len(res.profit_curve) > 0

def test_price_path_generator():
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()
    optimizer = LifecycleOptimizer(forecaster)
    path_gen = PricePathGenerator(optimizer)

    path = path_gen.generate_pricing_path(
        product_id="SKU_IPHONE_17_256",
        product_name="iPhone 17 256GB",
        current_price=79999.0,
        mrp=84999.0,
        unit_cost=68000.0,
        current_inventory=800,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        total_days=60,
        num_phases=4
    )
    assert len(path) == 4
    assert path[0]["starting_inventory"] == 800

def test_multi_store_balancer():
    balancer = MultiStoreBalancer()
    store_data = [
        {"store_id": "STORE_1", "store_name": "Store A", "city": "City A", "current_inventory": 10, "daily_sales_velocity": 4.0},
        {"store_id": "STORE_2", "store_name": "Store B", "city": "City B", "current_inventory": 120, "daily_sales_velocity": 1.0}
    ]
    analysis = balancer.analyze_sku_across_stores(
        product_id="TEST_SKU",
        product_name="Test Phone",
        unit_cost=50000.0,
        mrp=65000.0,
        store_data=store_data
    )
    assert len(analysis["recommended_transfers"]) > 0
    transfer = analysis["recommended_transfers"][0]
    assert transfer["from_store_id"] == "STORE_2"
    assert transfer["to_store_id"] == "STORE_1"
