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

def test_prediction_intervals_validity():
    """Verify that conformal prediction intervals satisfy lower <= point <= upper and are strictly non-increasing."""
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()

    # 1. Point prediction with intervals
    point_res = forecaster.predict_point(
        selling_price=79999.0,
        mrp=84999.0,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        unit_cost=68000.0,
        opening_inventory=800,
        days_to_successor=60,
        return_interval=True
    )
    assert isinstance(point_res, tuple) and len(point_res) == 3
    pred, lo, hi = point_res
    assert lo <= pred <= hi or np.isclose(lo, pred)

    # 2. Curve prediction with intervals
    prices = np.linspace(72000.0, 84999.0, 25)
    curve_res = forecaster.predict_demand_curve(
        candidate_prices=prices,
        mrp=84999.0,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        unit_cost=68000.0,
        opening_inventory=800,
        days_to_successor=60,
        return_intervals=True
    )
    assert isinstance(curve_res, tuple) and len(curve_res) == 3
    demands, demands_lo, demands_hi = curve_res
    assert len(demands) == len(prices)
    assert len(demands_lo) == len(prices)
    assert len(demands_hi) == len(prices)

    # Coverage ordering at all price points
    for d_l, d, d_h in zip(demands_lo, demands, demands_hi):
        assert d_l <= d <= d_h or np.isclose(d_l, d)

    # Monotonicity check on upper and lower bounds
    assert ((np.diff(demands_lo) > 1e-4).sum()) == 0, "Lower demand bound must be monotonic non-increasing"
    assert ((np.diff(demands_hi) > 1e-4).sum()) == 0, "Upper demand bound must be monotonic non-increasing"

def test_optimizer_prediction_intervals():
    """Verify that LifecycleOptimizer returns calibrated uncertainty bands for demand and profit."""
    from src.optimization.lifecycle_optimizer import LifecycleOptimizer
    forecaster = DemandForecaster(model_type="lightgbm")
    forecaster.load()
    optimizer = LifecycleOptimizer(forecaster)

    res = optimizer.optimize_sku(
        product_id="SKU_IPHONE_17_256",
        product_name="Apple iPhone 17 (256GB)",
        current_price=79999.0,
        mrp=84999.0,
        unit_cost=68000.0,
        current_inventory=300,
        competitor_avg_price=77999.0,
        competitor_min_price=76999.0,
        days_to_successor=60
    )

    assert res.demand_curve_lower is not None
    assert res.demand_curve_upper is not None
    assert res.profit_curve_lower is not None
    assert res.profit_curve_upper is not None
    assert len(res.demand_curve_lower) == len(res.demand_curve)
    assert len(res.demand_curve_upper) == len(res.demand_curve)
    assert len(res.profit_curve_lower) == len(res.profit_curve)
    assert len(res.profit_curve_upper) == len(res.profit_curve)


