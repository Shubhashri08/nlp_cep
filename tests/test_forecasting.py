import pytest
from backend.app.forecasting.demand_model import demand_forecaster
from backend.app.scenarios.engine import scenario_engine
from backend.app.recommendations.engine import recommendation_engine

def test_demand_forecast():
    preds, metrics, importances = demand_forecaster.forecast_demand(
        recent_values=[30.0, 35.0, 40.0],
        pop_density=25.0,
        deficit_pct=15.0,
        horizon_months=6
    )
    assert len(preds) == 6
    assert preds[0]["predicted_value"] > 0
    assert preds[0]["lower_bound"] <= preds[0]["predicted_value"] <= preds[0]["upper_bound"]
    assert "mae" in metrics
    assert len(importances) > 0

def test_scenario_simulation():
    baseline = {
        "daily_transit_ridership": 500000,
        "avg_peak_congestion_index": 2.2,
        "flood_risk_score": 0.7,
        "monthly_flood_complaints": 40
    }
    params = {
        "transit_capacity_delta_pct": 20.0,
        "drainage_upgrade_investment_cr": 25.0
    }
    res = scenario_engine.simulate_scenario(baseline, params)
    assert res["simulated_metrics"]["daily_transit_ridership"] > baseline["daily_transit_ridership"]
    assert res["simulated_metrics"]["avg_peak_congestion_index"] < baseline["avg_peak_congestion_index"]
    assert res["delta_metrics"]["peak_congestion_index_delta"] < 0
    assert len(res["assumptions"]) >= 2

def test_recommendation_scoring():
    score, factors = recommendation_engine.compute_ward_priority_score(
        complaint_density_per_sqkm=8.5,
        infrastructure_deficit_pct=28.0,
        population_density_k=42.0,
        flood_risk_score=0.75,
        demand_growth_pct=12.0
    )
    assert 0.0 <= score <= 100.0
    assert len(factors) == 5
