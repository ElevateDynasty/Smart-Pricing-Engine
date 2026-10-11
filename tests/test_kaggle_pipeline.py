"""
Tests for Kaggle Retail Price Optimization Pipeline
"""
import pytest
from pathlib import Path
from src.data.kaggle_pipeline import KaggleRetailPipeline, KAGGLE_RAW_CSV, KAGGLE_MODEL_FILE

def test_kaggle_pipeline_load_and_features():
    pipeline = KaggleRetailPipeline()
    if not KAGGLE_RAW_CSV.exists():
        pytest.skip("Kaggle retail_price.csv not present locally")

    df = pipeline.load_and_preprocess()
    assert len(df) > 0
    assert "competitor_avg_price" in df.columns
    assert "price_ratio_comp" in df.columns
    assert "price_delta_comp" in df.columns
    assert "qty" in df.columns

def test_kaggle_pipeline_training():
    pipeline = KaggleRetailPipeline()
    if not KAGGLE_RAW_CSV.exists():
        pytest.skip("Kaggle retail_price.csv not present locally")

    df = pipeline.load_and_preprocess()
    results = pipeline.train_demand_forecaster(df)
    assert "metrics" in results
    assert "mae" in results["metrics"]
    assert "rmse" in results["metrics"]
    assert "r2" in results["metrics"]
    # Issue 3: Kaggle model out-of-time R2 must be positive
    assert results["metrics"]["r2"] > 0, f"Expected positive R2, got {results['metrics']['r2']}"
    assert "res_p10" in results["metrics"]
    assert "res_p90" in results["metrics"]
    assert KAGGLE_MODEL_FILE.exists()

def test_kaggle_demand_adapter():
    from src.data.kaggle_pipeline import KaggleDemandAdapter
    import numpy as np
    if not KAGGLE_MODEL_FILE.exists() or not KAGGLE_RAW_CSV.exists():
        pytest.skip("Kaggle model or data missing")

    adapter = KaggleDemandAdapter()
    adapter.current_product_id = "bed1"
    prices = np.array([40.0, 50.0, 60.0])
    demands, d_lo, d_hi = adapter.predict_demand_curve(
        candidate_prices=prices,
        mrp=80.0,
        competitor_avg_price=55.0,
        competitor_min_price=45.0,
        unit_cost=30.0,
        opening_inventory=100,
        return_intervals=True
    )
    assert len(demands) == 3
    assert len(d_lo) == 3
    assert len(d_hi) == 3
    for lo, pt, hi in zip(d_lo, demands, d_hi):
        assert lo <= pt <= hi or np.isclose(lo, pt)

def test_kaggle_pipeline_elasticity():
    pipeline = KaggleRetailPipeline()
    if not KAGGLE_RAW_CSV.exists():
        pytest.skip("Kaggle retail_price.csv not present locally")

    df = pipeline.load_and_preprocess()
    elasticities = pipeline.estimate_elasticity(df)
    assert isinstance(elasticities, dict)
    assert len(elasticities) > 0

