"""Evidence-based ward prioritisation and intervention recommendations (Multi-Criteria Decision Analysis).

Ward priority (0–100) – weighted sum of min-max normalised criteria across all wards:
  complaint density 25 %, mean infrastructure deficit 25 %, population density 20 %,
  flood exposure 15 %, forecast demand growth 15 %.

Recommendation score (0–100) – per intervention, so recommendations are comparable across wards and sectors:
  gap severity 35 %, population affected 25 %, sector complaint pressure 20 %, growth pressure 20 %.
Every recommendation lists its inputs (contributing_factors) and the records they came from (supporting_evidence).
"""
from typing import Any, Dict, List, Optional, Tuple

from backend.app.analytics.norms import UNIT_COSTS_CR

PRIORITY_WEIGHTS = {
    "complaint_density": 0.25,
    "infrastructure_deficit": 0.25,
    "population_density": 0.20,
    "flood_exposure": 0.15,
    "demand_growth": 0.15,
}
REC_WEIGHTS = {"gap_severity": 0.35, "population": 0.25, "complaints": 0.20, "growth": 0.20}
SEVERITY_SCORE = {"CRITICAL": 1.0, "HIGH": 0.7, "MODERATE": 0.4, "LOW": 0.1}
# Gaps measured from incomplete volunteered data (OSM facility counts) are down-weighted so that data gaps
# are not mistaken for infrastructure gaps; DEMO = synthetic service records.
CONFIDENCE_FACTOR = {"HIGH": 1.0, "MEDIUM": 1.0, "DEMO": 0.9, "LOW": 0.6}

SECTOR_CATEGORIES = {
    "Water Supply": ["WATER_SUPPLY"],
    "Waste Management": ["WASTE_MANAGEMENT"],
    "Drainage & Storm Water": ["FLOODING", "DRAINAGE"],
    "Healthcare Capacity": ["HEALTHCARE"],
    "Education": ["EDUCATION"],
    "Public Transit Access": ["PUBLIC_TRANSPORT", "TRAFFIC"],
    "Open Space": ["PARKS", "ENVIRONMENT", "AIR_QUALITY"],
}


def _minmax(values: Dict[Any, float]) -> Dict[Any, float]:
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi - lo < 1e-9:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


class RecommendationEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(PRIORITY_WEIGHTS)

    # ---------------------------------------------------------------- ward priority
    def compute_priority_scores(self, wards: Dict[int, Dict[str, float]]) -> Dict[int, Tuple[float, List[Dict[str, Any]]]]:
        """wards: {ward_id: {complaint_density, infrastructure_deficit, population_density, flood_exposure, demand_growth}}"""
        normalised = {k: _minmax({w: v[k] for w, v in wards.items()}) for k in self.weights}
        labels = {
            "complaint_density": ("Citizen complaint rate", "{:.2f} complaints / 1,000 residents / yr"),
            "infrastructure_deficit": ("Mean infrastructure deficit", "{:.1f} %"),
            "population_density": ("Population density", "{:,.0f} persons/km²"),
            "flood_exposure": ("Flood exposure index", "{:.2f}"),
            "demand_growth": ("Forecast 12-month demand growth", "{:+.1f} %"),
        }
        out = {}
        for w, raw in wards.items():
            factors, total = [], 0.0
            for k, weight in self.weights.items():
                n = normalised[k][w] * 100
                total += n * weight
                factors.append({"factor": labels[k][0], "weight": weight, "raw_value": labels[k][1].format(raw[k]),
                                "normalized_score": round(n, 1), "weighted_contribution": round(n * weight, 2)})
            out[w] = (round(total, 2), factors)
        return out

    # ---------------------------------------------------------------- recommendations
    def generate(self, wards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """wards: list of {id, name, code, population, gaps:[...], complaints_by_category:{}, growth:{}, flood_exposure,
        demand_growth_pct}. Returns scored recommendations for every CRITICAL/HIGH gap."""
        pop_n = _minmax({w["id"]: float(w["population"]) for w in wards})
        growth_raw = {}
        for w in wards:
            g = w.get("growth") or {}
            growth_raw[w["id"]] = max(0.0, (g.get("built_up_change_pct") or 0.0)) + max(0.0, w.get("demand_growth_pct") or 0.0)
        growth_n = _minmax(growth_raw)
        complaint_raw = {}
        for w in wards:
            for sector, cats in SECTOR_CATEGORIES.items():
                complaint_raw[(w["id"], sector)] = sum(w["complaints_by_category"].get(c, 0) for c in cats) / max(0.1, w["area_sq_km"])
        complaint_n = _minmax(complaint_raw)

        recs = []
        for w in wards:
            for gap in w["gaps"]:
                if gap["severity"] not in ("CRITICAL", "HIGH"):
                    continue
                builder = _BUILDERS.get(gap["sector"])
                if not builder:
                    continue
                confidence = (gap.get("evidence") or {}).get("data_confidence", "MEDIUM")
                sev = SEVERITY_SCORE[gap["severity"]] * min(1.0, 0.5 + gap["deficit_percentage"] / 100) * CONFIDENCE_FACTOR.get(confidence, 1.0)
                comps = {
                    "gap_severity": sev,
                    "population": pop_n[w["id"]],
                    "complaints": complaint_n.get((w["id"], gap["sector"]), 0.0),
                    "growth": growth_n[w["id"]],
                }
                score = round(100 * sum(REC_WEIGHTS[k] * v for k, v in comps.items()), 2)
                title, text, cost, extra_evidence = builder(w, gap)
                caveat = (gap.get("evidence") or {}).get("caveat")
                if confidence == "LOW" and caveat:
                    text += f" Data caveat: {caveat}."
                sector_complaints = sum(w["complaints_by_category"].get(c, 0) for c in SECTOR_CATEGORIES[gap["sector"]])
                recs.append({
                    "ward_id": w["id"],
                    "ward_name": w["name"],
                    "sector": gap["sector"],
                    "title": title,
                    "recommendation_text": text,
                    "priority_level": "HIGH" if score >= 60 else ("MEDIUM" if score >= 40 else "LOW"),
                    "score": score,
                    "estimated_cost_cr": cost,
                    "contributing_factors": [
                        {"factor": "Gap severity", "weight": REC_WEIGHTS["gap_severity"], "value": f"{gap['severity']} ({gap['deficit_percentage']}% deficit)", "normalized_score": round(comps['gap_severity'] * 100, 1)},
                        {"factor": "Population affected", "weight": REC_WEIGHTS["population"], "value": f"{w['population']:,} residents", "normalized_score": round(comps['population'] * 100, 1)},
                        {"factor": "Complaint pressure", "weight": REC_WEIGHTS["complaints"], "value": f"{sector_complaints} related complaints", "normalized_score": round(comps['complaints'] * 100, 1)},
                        {"factor": "Growth pressure", "weight": REC_WEIGHTS["growth"], "value": f"built-up {((w.get('growth') or {}).get('built_up_change_pct') or 0):+.1f}%, demand {w.get('demand_growth_pct') or 0:+.1f}%", "normalized_score": round(comps['growth'] * 100, 1)},
                    ],
                    "supporting_evidence": [
                        {"dataset": "infrastructure_gaps", "record_id": gap.get("id"), "field": "deficit_amount",
                         "value": gap["deficit_amount"], "unit": gap["unit"], "norm": gap.get("norm_reference")},
                        {"dataset": "citizen_requests", "field": "count", "value": sector_complaints,
                         "categories": SECTOR_CATEGORIES[gap["sector"]]},
                        {"dataset": "wards", "record_id": w["id"], "field": "population", "value": w["population"]},
                    ] + extra_evidence,
                    "methodology": f"MCDA: severity 35% · population 25% · complaints 20% · growth 20% · data confidence {confidence}",
                })
        return sorted(recs, key=lambda r: -r["score"])


def _cost(key: str, qty: float) -> float:
    return round(UNIT_COSTS_CR[key]["value"] * qty, 2)


def _water(w, g):
    q = g["deficit_amount"]
    return (f"Augment water distribution in {w['name']}",
            f"Close the {q:.1f} MLD shortfall against the 135 lpcd norm through feeder main augmentation, pressure "
            f"management and leak reduction in the distribution zones serving {w['name']}.",
            _cost("water_augmentation_per_mld", q), [])


def _waste(w, g):
    q = g["deficit_amount"]
    return (f"Decentralised waste processing for {w['name']}",
            f"Add {q:.0f} TPD of decentralised composting / MRF capacity and increase collection frequency to "
            f"match generation at 0.45 kg/capita/day.",
            _cost("waste_processing_per_tpd", q), [])


def _drain(w, g):
    q = g["deficit_amount"]
    ll = (g.get("evidence") or {}).get("low_lying_share_below_5m")
    extra = [{"dataset": "copernicus_dem", "field": "share_below_5m", "value": ll}] if ll is not None else []
    return (f"Upgrade storm-water drains in {w['name']} to 50 mm/h",
            f"Increase peak drainage capacity by {q:.1f} m³/s (legacy 25 mm/h → BRIMSTOWAD 50 mm/h), prioritising "
            f"low-lying catchments{f' ({ll*100:.0f}% of the ward lies below 5 m)' if ll else ''}; pre-monsoon desilting "
            f"and pumping stations at outfalls.",
            _cost("storm_drain_upgrade_per_m3s", q), extra)


def _health(w, g):
    n = int(round(g["deficit_amount"]))
    return (f"Add {n} primary health facilities in {w['name']}",
            f"Open {n} dispensaries / urban health posts to reach one facility per 15,000 residents (URDPFI); "
            f"site them near the densest complaint clusters.",
            _cost("primary_health_centre", n), [])


def _school(w, g):
    n = int(round(g["deficit_amount"]))
    return (f"Expand school capacity in {w['name']}",
            f"Plan {n} additional school units (or equivalent classroom additions) to meet one school per 5,000 residents.",
            _cost("school", n), [])


def _transit(w, g):
    n = int(round(g["deficit_amount"]))
    return (f"Improve bus-stop coverage in {w['name']}",
            f"Add about {n} bus stops / shelters so built-up areas are within ~250 m of a stop, and "
            f"re-route feeder services to rail and metro stations.",
            _cost("bus_stop", n), [])


def _open_space(w, g):
    ha = g["deficit_amount"]
    per_capita = (g.get("evidence") or {}).get("open_space_sqm_per_capita")
    # Land is the binding constraint; recommend a realistic tranche (10 %) of the norm gap
    tranche = round(ha * 0.10, 1)
    return (f"Create new public open space in {w['name']}",
            f"Open space is {per_capita} m²/capita against a 10 m² norm. Secure ~{tranche} ha in the next plan period "
            f"through reservation of vacant plots, amenity-space handover in redevelopment and greening of nallah edges.",
            _cost("open_space_per_ha", tranche), [])


_BUILDERS = {
    "Water Supply": _water,
    "Waste Management": _waste,
    "Drainage & Storm Water": _drain,
    "Healthcare Capacity": _health,
    "Education": _school,
    "Public Transit Access": _transit,
    "Open Space": _open_space,
}

recommendation_engine = RecommendationEngine()
