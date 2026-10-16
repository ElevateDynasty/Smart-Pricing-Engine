"""
Unit tests for Competitor Game Theory Simulator
"""
import pytest
from src.optimization.competitor_game_theory import CompetitorGameTheorySimulator


def test_game_theory_convergence():
    simulator = CompetitorGameTheorySimulator(offline_premium=1000.0, reaction_sensitivity=0.55)
    result = simulator.simulate_duopoly_dynamics(
        initial_store_price=79999.0,
        initial_comp_price=77999.0,
        unit_cost=68000.0,
        mrp=89900.0,
        ai_recommended_price=79000.0,
        max_rounds=6
    )

    assert result["is_converged"] is True
    assert result["convergence_rounds"] <= 6
    assert result["price_war_triggered"] is False
    assert result["stability_score"] >= 75.0
    assert result["nash_store_price"] >= 68000.0
    assert result["nash_store_price"] <= 89900.0
    assert len(result["rounds_history"]) > 0
    assert "summary_memo" in result


def test_game_theory_offline_premium_retention():
    simulator = CompetitorGameTheorySimulator(offline_premium=1500.0)
    result = simulator.simulate_duopoly_dynamics(
        initial_store_price=80000.0,
        initial_comp_price=75000.0,
        unit_cost=65000.0,
        mrp=85000.0
    )

    # Verifies offline premium is preserved above costs
    assert result["offline_premium_preserved"] > 0
    assert result["nash_store_price"] > result["nash_competitor_price"]
