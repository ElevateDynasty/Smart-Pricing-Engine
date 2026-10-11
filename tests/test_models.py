"""
Tests for ML Demand Forecaster and Elasticity Estimator
"""
import pytest
import numpy as np
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator
from src.data.data_pipeline import DataPipeline

def test_demand_forecaster_predict():
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()
    
    # Test point prediction
    pred = forecaster.predict_point(
        selling_price=79999.0,
        mrp=84999.0,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        unit_cost=68000.0,
        opening_inventory=800,
        days_to_successor=60
    )
    assert isinstance(pred, float)
    assert pred >= 0.0

def test_demand_forecaster_curve():
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()

    prices = np.array([75000.0, 78000.0, 82000.0])
    demands = forecaster.predict_demand_curve(
        candidate_prices=prices,
        mrp=84999.0,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        unit_cost=68000.0,
        opening_inventory=800
    )
    assert len(demands) == 3
    assert all(d >= 0 for d in demands)

def test_elasticity_estimator():
    dp = DataPipeline()
    df = dp.build_unified_dataset()
    est = ElasticityEstimator()
    results = est.fit(df)
    assert len(results) > 0
    first_pid = list(results.keys())[0]
    meta = est.get_elasticity(first_pid)
    assert "elasticity" in meta
    # When identifiable, elasticity is positive; if unidentifiable, it is safely None
    if meta["identifiable"]:
        assert meta["elasticity"] > 0

def test_demand_forecaster_monotonicity():
    """Assert that higher prices never produce higher predicted demand (Law of Demand)."""
    from src.models.model_evaluator import ModelEvaluator
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()

    prices = np.linspace(70000.0, 84999.0, 31)
    demands = forecaster.predict_demand_curve(
        candidate_prices=prices,
        mrp=84999.0,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        unit_cost=68000.0,
        opening_inventory=800,
        days_to_successor=60
    )

    # Monotonic non-increasing check: diffs <= 0 within floating precision
    diffs = np.diff(demands)
    violations = (diffs > 1e-4).sum()
    assert violations == 0, f"Demand curve violates monotonicity at {violations} points: {diffs[diffs > 1e-4]}"

    # Also verify via ModelEvaluator utility
    eval_res = ModelEvaluator.evaluate_price_curve_monotonicity(prices, demands)
    assert eval_res["is_predominantly_monotonic"] is True
    assert eval_res["monotonic_violations"] == 0

def test_elasticity_recovery():
    """Verify that estimated elasticity reflects relative price sensitivities across products."""
    dp = DataPipeline()
    df = dp.build_unified_dataset()
    est = ElasticityEstimator()
    results = est.fit(df)

    # Check that estimated elasticities exist and are identifiable
    identifiable_skus = [pid for pid, r in results.items() if r["identifiable"] and r["elasticity"] is not None]
    assert len(identifiable_skus) >= 4, f"Expected at least 4 identifiable SKUs, found {len(identifiable_skus)}"

    # Highly elastic products (e.g., iPhone 16 base elasticity 2.8) should show higher sensitivity than inelastic products
    if "SKU_IPHONE_16_128" in results and "SKU_PIXEL_10_PRO" in results:
        e_iphone = results["SKU_IPHONE_16_128"]["elasticity"]
        e_pixel = results["SKU_PIXEL_10_PRO"]["elasticity"]
        if e_iphone is not None and e_pixel is not None:
            assert e_iphone > e_pixel, f"iPhone 16 elasticity ({e_iphone}) should exceed Pixel 10 Pro ({e_pixel})"
