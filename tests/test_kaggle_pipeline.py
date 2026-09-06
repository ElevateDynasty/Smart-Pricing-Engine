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
    assert KAGGLE_MODEL_FILE.exists()

def test_kaggle_pipeline_elasticity():
    pipeline = KaggleRetailPipeline()
    if not KAGGLE_RAW_CSV.exists():
        pytest.skip("Kaggle retail_price.csv not present locally")

    df = pipeline.load_and_preprocess()
    elasticities = pipeline.estimate_elasticity(df)
    assert isinstance(elasticities, dict)
    assert len(elasticities) > 0
