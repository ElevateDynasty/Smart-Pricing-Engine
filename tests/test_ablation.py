"""
Unit tests for Model Ablation Suite
"""
import pytest
import pandas as pd
from src.evaluation.model_ablation import ModelAblationHarness
from src.data.data_pipeline import DataPipeline


def test_model_ablation_harness():
    pipeline = DataPipeline()
    df = pipeline.build_unified_dataset()
    assert df is not None and len(df) > 100

    harness = ModelAblationHarness()
    results = harness.run_ablation_study(df)

    assert isinstance(results, pd.DataFrame)
    assert len(results) == 4
    expected_cols = [
        "Model Architecture",
        "Enforces Law of Demand",
        "Monotonicity Violation Rate (%)",
        "Validation MAE (units)",
        "Validation RMSE (units)",
        "Validation R²",
        "Expected Net Profit (₹)"
    ]
    for col in expected_cols:
        assert col in results.columns

    # Check that Monotone model has 0.0% monotonicity violations
    mono_row = results[results["Model Architecture"].str.contains("Monotone")].iloc[0]
    assert mono_row["Monotonicity Violation Rate (%)"] == 0.0
