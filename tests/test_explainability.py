"""
Tests for ReasonGenerator and Explainability Engine
"""
import pytest
from src.explainability.reason_generator import ReasonGenerator
from src.optimization.lifecycle_optimizer import LifecycleOptimizer
from src.models.demand_forecaster import DemandForecaster

def test_reason_generator():
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

    memo = ReasonGenerator.generate_retailer_memo(res)
    assert "headline" in memo
    assert "key_rationale" in memo
    assert "offline_advantage" in memo
    assert len(memo["headline"]) > 10
