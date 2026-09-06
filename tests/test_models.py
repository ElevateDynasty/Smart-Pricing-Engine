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
    assert meta["elasticity"] > 0
