"""What-if scenario simulation and multi-criteria evaluation.

The baseline is aggregated from the database for the chosen scope (city or selected wards) by
backend/app/services/baseline.py. Levers are translated into indicator changes with documented
elasticities / planning norms, then both baseline and simulated states are scored on an 8-criterion
service-adequacy index (0–100). Capital cost uses indicative unit costs (analytics/norms.py).
"""
from typing import Any, Dict, List, Tuple

from backend.app.analytics.norms import UNIT_COSTS_CR, norm

LEVERS = {
    "transit_capacity_delta_pct": {"label": "Bus / transit capacity change", "unit": "%", "min": -20, "max": 100, "default": 0},
    "new_bus_stops": {"label": "New bus stops", "unit": "stops", "min": 0, "max": 2000, "default": 0},
    "drainage_upgrade_pct": {"label": "Drain network upgraded to 50 mm/h", "unit": "% of gap", "min": 0, "max": 100, "default": 0},
    "population_growth_rate_pct": {"label": "Population growth", "unit": "%", "min": -10, "max": 50, "default": 0},
    "density_rezoning_pct": {"label": "Additional population from FSI / rezoning", "unit": "%", "min": 0, "max": 50, "default": 0},
    "water_supply_augmentation_mld": {"label": "Water supply augmentation", "unit": "MLD", "min": 0, "max": 1000, "default": 0},
    "waste_processing_expansion_pct": {"label": "Waste processing capacity change", "unit": "%", "min": 0, "max": 200, "default": 0},
    "new_health_facilities": {"label": "New primary health facilities", "unit": "facilities", "min": 0, "max": 500, "default": 0},
    "new_schools": {"label": "New schools", "unit": "schools", "min": 0, "max": 500, "default": 0},
    "green_cover_increase_pct": {"label": "Green / open space added", "unit": "% of area", "min": 0, "max": 20, "default": 0},
}

CRITERIA_WEIGHTS = {
    "water_adequacy": 0.15, "waste_adequacy": 0.10, "health_adequacy": 0.12, "education_adequacy": 0.10,
    "drainage_adequacy": 0.15, "mobility": 0.13, "flood_safety": 0.15, "open_space": 0.10,
}

ELASTICITY = {
    "ridership_to_capacity": (0.65, "Transit ridership elasticity to service supply ≈ 0.5–0.7 (Litman, VTPI 2021)"),
    "congestion_to_capacity": (0.32, "Congestion cross-elasticity to transit capacity ≈ −0.3 (Litman 2021; Mumbai CMP 2016)"),
    "ridership_to_stops": (0.30, "Access elasticity: ridership rises ~0.3 % per 1 % more stops (walk-access literature)"),
    "flood_to_drainage": (0.60, "Share of flood risk attributable to drainage capacity (MCGM BRIMSTOWAD appraisal, indicative)"),
    "flood_to_green": (0.015, "Flood risk reduction per percentage point of added pervious green cover (indicative)"),
    "congestion_to_population": (0.5, "Congestion scales with √(population) at fixed road supply"),
}


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def score_state(m: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    pop = max(1.0, m["total_population"])
    crit = {
        "water_adequacy": _clip01(m["water_supplied_mld"] / max(0.01, m["required_water_mld"])),
        "waste_adequacy": _clip01(m["waste_processed_tpd"] / max(0.01, m["waste_generated_tpd"])),
        "health_adequacy": _clip01(m["health_facilities"] * norm("primary_health_per_pop") / pop),
        "education_adequacy": _clip01(m["schools"] * norm("school_per_pop") / pop),
        "drainage_adequacy": _clip01(m["drainage_capacity_m3s"] / max(0.01, m["drainage_required_m3s"])),
        "mobility": _clip01((3.0 - m["avg_peak_congestion_index"]) / 2.0),
        "flood_safety": _clip01(1.0 - m["flood_risk_score"]),
        "open_space": _clip01(m["open_space_sqm_per_capita"] / norm("open_space_sqm_per_capita")),
    }
    total = 100.0 * sum(CRITERIA_WEIGHTS[k] * v for k, v in crit.items())
    return round(total, 2), {k: round(v * 100, 1) for k, v in crit.items()}


class ScenarioAnalysisEngine:
    def simulate_scenario(self, baseline: Dict[str, float], parameters: Dict[str, Any]) -> Dict[str, Any]:
        p = {k: float(parameters.get(k, spec["default"]) or 0) for k, spec in LEVERS.items()}
        b = dict(baseline)
        s = dict(baseline)
        assumptions: List[str] = []
        cost = 0.0

        # Population
        pop_factor = (1 + p["population_growth_rate_pct"] / 100) * (1 + p["density_rezoning_pct"] / 100)
        s["total_population"] = round(b["total_population"] * pop_factor)
        if pop_factor != 1:
            assumptions.append(f"Population ×{pop_factor:.3f}; per-capita demand at CPHEEO 135 lpcd water and 0.45 kg/day waste.")

        # Transit
        cap = p["transit_capacity_delta_pct"] / 100
        stops_ratio = p["new_bus_stops"] / max(1.0, b["bus_stops"])
        e_r, ref_r = ELASTICITY["ridership_to_capacity"]
        e_s, ref_s = ELASTICITY["ridership_to_stops"]
        s["bus_stops"] = b["bus_stops"] + p["new_bus_stops"]
        s["daily_transit_ridership"] = round(b["daily_transit_ridership"] * (1 + e_r * cap) * (1 + e_s * stops_ratio) * pop_factor)
        e_c, ref_c = ELASTICITY["congestion_to_capacity"]
        e_p, ref_p = ELASTICITY["congestion_to_population"]
        excess = (b["avg_peak_congestion_index"] - 1.0) * (1 - e_c * cap - 0.5 * e_c * stops_ratio) * (pop_factor ** e_p)
        s["avg_peak_congestion_index"] = round(max(1.0, min(3.0, 1.0 + excess)), 3)
        if cap or stops_ratio:
            assumptions += [ref_r, ref_c] + ([ref_s] if stops_ratio else [])
            cost += UNIT_COSTS_CR["transit_capacity_pct"]["value"] * max(0.0, p["transit_capacity_delta_pct"]) * (b["total_population"] / 12.4e6)
            cost += UNIT_COSTS_CR["bus_stop"]["value"] * p["new_bus_stops"]
        if pop_factor != 1:
            assumptions.append(ref_p)

        # Drainage & flood
        gap_m3s = max(0.0, b["drainage_required_m3s"] - b["drainage_capacity_m3s"])
        added = gap_m3s * p["drainage_upgrade_pct"] / 100
        s["drainage_capacity_m3s"] = round(b["drainage_capacity_m3s"] + added, 2)
        green_pp = p["green_cover_increase_pct"]
        s["green_share_pct"] = round(min(100.0, b["green_share_pct"] + green_pp), 2)
        # More pervious surface lowers required capacity (rational method)
        s["drainage_required_m3s"] = round(b["drainage_required_m3s"] * (1 - (norm("runoff_coeff_built") - norm("runoff_coeff_green")) * green_pp / 100 / max(0.3, b["runoff_coefficient"])), 2)
        e_f, ref_f = ELASTICITY["flood_to_drainage"]
        e_g, ref_g = ELASTICITY["flood_to_green"]
        closed_share = added / gap_m3s if gap_m3s else 0.0
        s["flood_risk_score"] = round(max(0.02, b["flood_risk_score"] * (1 - e_f * closed_share) * (1 - e_g * green_pp)), 3)
        ratio = s["flood_risk_score"] / max(0.01, b["flood_risk_score"])
        s["monthly_flood_complaints"] = round(b["monthly_flood_complaints"] * ratio * pop_factor, 1)
        if added:
            assumptions.append(ref_f)
            cost += UNIT_COSTS_CR["storm_drain_upgrade_per_m3s"]["value"] * added
        if green_pp:
            assumptions.append(ref_g)
            cost += UNIT_COSTS_CR["open_space_per_ha"]["value"] * green_pp / 100 * b["area_sq_km"] * 100

        # Water
        s["required_water_mld"] = round(s["total_population"] * norm("water_lpcd") / 1e6, 2)
        s["water_supplied_mld"] = round(b["water_supplied_mld"] + p["water_supply_augmentation_mld"], 2)
        s["water_gap_mld"] = round(max(0.0, s["required_water_mld"] - s["water_supplied_mld"]), 2)
        cost += UNIT_COSTS_CR["water_augmentation_per_mld"]["value"] * p["water_supply_augmentation_mld"]

        # Waste
        s["waste_generated_tpd"] = round(s["total_population"] * norm("waste_kg_per_capita") / 1000, 2)
        s["waste_processed_tpd"] = round(b["waste_processed_tpd"] * (1 + p["waste_processing_expansion_pct"] / 100), 2)
        s["uncollected_waste_pct"] = round(max(0.0, 100 * (1 - s["waste_processed_tpd"] / max(0.01, s["waste_generated_tpd"]))), 1)
        cost += UNIT_COSTS_CR["waste_processing_per_tpd"]["value"] * (s["waste_processed_tpd"] - b["waste_processed_tpd"])

        # Social infrastructure
        s["health_facilities"] = b["health_facilities"] + p["new_health_facilities"]
        s["schools"] = b["schools"] + p["new_schools"]
        s["residents_per_health_facility"] = round(s["total_population"] / max(1, s["health_facilities"]))
        s["residents_per_school"] = round(s["total_population"] / max(1, s["schools"]))
        cost += UNIT_COSTS_CR["primary_health_centre"]["value"] * p["new_health_facilities"]
        cost += UNIT_COSTS_CR["school"]["value"] * p["new_schools"]

        # Open space
        green_area_sqm = s["green_share_pct"] / 100 * b["area_sq_km"] * 1e6
        s["open_space_sqm_per_capita"] = round(green_area_sqm / max(1, s["total_population"]), 2)

        base_score, base_crit = score_state(b)
        sim_score, sim_crit = score_state(s)
        deltas = {}
        for k, v in s.items():
            if isinstance(v, (int, float)) and isinstance(b.get(k), (int, float)) and v != b[k]:
                deltas[f"{k}_delta"] = round(v - b[k], 3)
        unknown = [k for k in parameters if k not in LEVERS]
        if unknown:
            assumptions.append(f"Ignored unsupported levers: {unknown}.")
        assumptions.append("Capital costs use indicative unit rates (analytics/norms.py) for ranking, not budgeting.")

        return {
            "parameters": {k: v for k, v in p.items() if v},
            "baseline_metrics": b,
            "simulated_metrics": s,
            "delta_metrics": deltas,
            "assumptions": list(dict.fromkeys(assumptions)),
            "score": sim_score,
            "score_breakdown": {
                "baseline_score": base_score, "simulated_score": sim_score, "score_change": round(sim_score - base_score, 2),
                "weights": CRITERIA_WEIGHTS, "baseline_criteria": base_crit, "simulated_criteria": sim_crit,
                "score_gain_per_100cr": round((sim_score - base_score) / (cost / 100), 3) if cost > 0 else None,
            },
            "capital_cost_cr": round(cost, 1),
            "evidence_status": "BASELINE_FROM_DB · ELASTICITY_MODEL",
        }


def compare_scenarios(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    keys = ["total_population", "daily_transit_ridership", "avg_peak_congestion_index", "flood_risk_score",
            "monthly_flood_complaints", "water_gap_mld", "uncollected_waste_pct", "residents_per_health_facility",
            "residents_per_school", "open_space_sqm_per_capita", "green_share_pct"]
    table = []
    for k in keys:
        row = {"metric": k, "baseline": scenarios[0]["baseline_metrics"].get(k) if scenarios else None}
        for sc in scenarios:
            row[str(sc["id"])] = sc["simulated_metrics"].get(k)
        table.append(row)
    ranking = sorted(
        [{"id": sc["id"], "title": sc["title"], "score": sc.get("score"), "capital_cost_cr": sc.get("capital_cost_cr"),
          "score_change": (sc.get("score_breakdown") or {}).get("score_change"),
          "score_gain_per_100cr": (sc.get("score_breakdown") or {}).get("score_gain_per_100cr")} for sc in scenarios],
        key=lambda r: -(r["score"] or 0))
    criteria = {str(sc["id"]): (sc.get("score_breakdown") or {}).get("simulated_criteria") for sc in scenarios}
    return {"metrics_table": table, "ranking": ranking, "criteria": criteria, "weights": CRITERIA_WEIGHTS}


scenario_engine = ScenarioAnalysisEngine()
