from datetime import date

import numpy as np

from backend.app.forecasting.demand_model import MetricForecaster
from backend.app.recommendations.engine import RecommendationEngine
from backend.app.scenarios.engine import compare_scenarios, scenario_engine, score_state

BASELINE = {
    "total_population": 1_000_000, "area_sq_km": 50.0, "daily_transit_ridership": 600_000, "avg_peak_congestion_index": 2.2,
    "bus_stops": 400, "flood_risk_score": 0.6, "monthly_flood_complaints": 40.0, "drainage_required_m3s": 400.0,
    "drainage_capacity_m3s": 200.0, "runoff_coefficient": 0.75, "required_water_mld": 135.0, "water_supplied_mld": 115.0,
    "water_gap_mld": 20.0, "waste_generated_tpd": 450.0, "waste_processed_tpd": 330.0, "uncollected_waste_pct": 26.7,
    "health_facilities": 40, "schools": 150, "residents_per_health_facility": 25000, "residents_per_school": 6667,
    "green_share_pct": 5.0, "open_space_sqm_per_capita": 2.5,
}


def _history(n_wards=6, months=36, seed=0):
    rng = np.random.default_rng(seed)
    start = date(2023, 10, 1)
    ms = []
    y, m = start.year, start.month
    for _ in range(months):
        ms.append(date(y, m, 1))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    hist = {}
    for w in range(n_wards):
        base = 50 + 20 * w
        vals = [base * (1 + 0.004 * i) * (1.4 if d.month in (6, 7, 8, 9) else 1.0) * (1 + rng.normal(0, 0.03)) for i, d in enumerate(ms)]
        hist[w] = (ms, vals, 20000 + 1000 * w)
    return hist


def test_forecaster_beats_seasonal_naive_and_has_intervals():
    hist = _history()
    mf = MetricForecaster("complaint_volume")
    metrics = mf.fit(hist)
    assert metrics["mape_pct"] < 15
    assert metrics["test_samples"] > 0
    ms, vals, dens = hist[0]
    preds = mf.forecast(ms, vals, dens, 12)
    assert len(preds) == 12
    assert all(p["lower_bound"] <= p["predicted_value"] <= p["upper_bound"] for p in preds)
    widths = [p["upper_bound"] - p["lower_bound"] for p in preds]
    assert widths[-1] > widths[0]  # uncertainty grows with horizon
    monsoon = [p["predicted_value"] for p in preds if p["date"].endswith(("-07", "-08"))]
    dry = [p["predicted_value"] for p in preds if p["date"].endswith(("-01", "-02"))]
    assert np.mean(monsoon) > np.mean(dry)  # learned seasonality


def test_scenario_drainage_and_transit_effects():
    r = scenario_engine.simulate_scenario(BASELINE, {"drainage_upgrade_pct": 50, "transit_capacity_delta_pct": 20})
    s = r["simulated_metrics"]
    assert s["drainage_capacity_m3s"] == 300.0
    assert s["flood_risk_score"] < BASELINE["flood_risk_score"]
    assert s["daily_transit_ridership"] > BASELINE["daily_transit_ridership"]
    assert s["avg_peak_congestion_index"] < BASELINE["avg_peak_congestion_index"]
    assert r["capital_cost_cr"] > 0
    assert r["score_breakdown"]["score_change"] > 0
    assert any("Litman" in a for a in r["assumptions"])


def test_scenario_population_growth_increases_demand():
    r = scenario_engine.simulate_scenario(BASELINE, {"population_growth_rate_pct": 10})
    s = r["simulated_metrics"]
    assert s["total_population"] == 1_100_000
    assert s["required_water_mld"] == 148.5
    assert r["score_breakdown"]["score_change"] < 0  # more people, same infrastructure → worse adequacy


def test_score_bounds_and_compare():
    score, crit = score_state(BASELINE)
    assert 0 <= score <= 100 and set(crit) >= {"water_adequacy", "flood_safety"}
    a = scenario_engine.simulate_scenario(BASELINE, {"new_health_facilities": 30})
    b = scenario_engine.simulate_scenario(BASELINE, {"water_supply_augmentation_mld": 20})
    cmp = compare_scenarios([{**a, "id": 1, "title": "Health"}, {**b, "id": 2, "title": "Water"}])
    assert len(cmp["ranking"]) == 2 and cmp["metrics_table"]


def test_priority_scores_are_relative_and_explained():
    eng = RecommendationEngine()
    scores = eng.compute_priority_scores({
        1: {"complaint_density": 5, "infrastructure_deficit": 60, "population_density": 50000, "flood_exposure": 0.8, "demand_growth": 5},
        2: {"complaint_density": 1, "infrastructure_deficit": 10, "population_density": 10000, "flood_exposure": 0.1, "demand_growth": 0},
    })
    assert scores[1][0] == 100.0 and scores[2][0] == 0.0
    assert len(scores[1][1]) == 5


def test_recommendation_scores_differ_by_evidence():
    eng = RecommendationEngine()
    gap = {"sector": "Water Supply", "severity": "CRITICAL", "deficit_amount": 20.0, "deficit_percentage": 45.0, "unit": "MLD"}
    wards = [
        {"id": 1, "name": "A", "population": 900_000, "area_sq_km": 20, "gaps": [gap], "complaints_by_category": {"WATER_SUPPLY": 120}, "growth": {}, "demand_growth_pct": 4},
        {"id": 2, "name": "B", "population": 200_000, "area_sq_km": 20, "gaps": [dict(gap, severity="HIGH", deficit_percentage=22.0)],
         "complaints_by_category": {"WATER_SUPPLY": 5}, "growth": {}, "demand_growth_pct": 1},
    ]
    recs = eng.generate(wards)
    assert len(recs) == 2 and recs[0]["ward_id"] == 1 and recs[0]["score"] > recs[1]["score"]
    assert recs[0]["estimated_cost_cr"] > 0 and recs[0]["supporting_evidence"]
