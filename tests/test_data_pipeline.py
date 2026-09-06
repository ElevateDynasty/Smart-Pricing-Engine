"""
Tests for Data Pipeline and Feature Engineering
"""
import pytest
import pandas as pd
from src.data.data_pipeline import DataPipeline
from src.data.feature_engineering import FeatureEngineer
from src.data.generate_synthetic_data import SyntheticDataGenerator

def test_data_pipeline_load():
    dp = DataPipeline()
    tables = dp.load_raw_data()
    assert "products" in tables
    assert "stores" in tables
    assert "sales" in tables
    assert "competitors" in tables
    assert len(tables["products"]) > 0
    assert len(tables["stores"]) == 5

def test_feature_engineering():
    dp = DataPipeline()
    raw = dp.build_unified_dataset()
    fe = FeatureEngineer()
    X, y = fe.prepare_training_data(raw)
    assert X.shape[0] == len(raw)
    assert "price_ratio_mrp" in X.columns
    assert "price_delta_comp" in X.columns
    assert "is_aging_model" in X.columns
    assert y.min() >= 0
