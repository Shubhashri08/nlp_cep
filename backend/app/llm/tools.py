"""Read-only, parameterised query tools for the planning assistant.

Every tool returns {"rows": [...], "citation": {...}} where the citation records the table(s), the primary keys of
the records used, and the SQL that actually executed (compiled from the SQLAlchemy query). The LLM never writes SQL.
"""
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from backend.app.llm.providers import ToolSpec
from backend.app.models.entities import (
    CitizenRequest, InfrastructureGap, Recommendation, RequestStatus, UrbanGrowth, Ward,
)
from backend.app.nlp.lexicon import CATEGORIES


def _sql(q: Query) -> str:
    try:
        return str(q.statement.compile(dialect=q.session.bind.dialect, compile_kwargs={"literal_binds": True}))
    except Exception:
        return str(q.statement)


def _citation(table: str, ids: List[int], description: str, sql: str) -> Dict[str, Any]:
    return {"table_name": table, "record_ids": [int(i) for i in ids if i is not None][:50], "description": description,
            "query_executed": re.sub(r"\s+", " ", sql)[:2000], "timestamp": datetime.now(timezone.utc).isoformat()}


def resolve_ward(db: Session, ref: Optional[str]) -> Optional[Ward]:
    """Accepts 'H/E', 'H-East', 'H East ward', 'ward K/W', a ward name, or a locality such as 'Bandra East'."""
    if not ref:
        return None
    s = str(ref).strip().upper().replace("WARD", "").strip()
    s = re.sub(r"[\s\-]+", "/", s).strip("/")
    for full, short in (("NORTH", "N"), ("SOUTH", "S"), ("EAST", "E"), ("WEST", "W"), ("CENTRAL", "C")):
        s = re.sub(rf"/{full}$", f"/{short}", s)
    w = db.query(Ward).filter(Ward.ward_code == s).first()
    if w:
        return w
    low = str(ref).lower().strip()
    for w in db.query(Ward).all():
        if low in w.name.lower() or any(low == loc.strip().lower() or low in loc.strip().lower() for loc in (w.localities or "").split(",")):
            return w
    return None


# ------------------------------------------------------------------------------------------ tools
def list_wards(db: Session, sort_by: str = "priority", limit: int = 10) -> Dict[str, Any]:
    order = {"priority": Ward.priority_score.desc(), "population": Ward.population.desc(), "density": Ward.population_density.desc(),
             "area": Ward.area_sq_km.desc(), "low_lying": Ward.low_lying_share.desc()}.get(sort_by, Ward.priority_score.desc())
    q = db.query(Ward).order_by(order).limit(max(1, min(24, int(limit))))
    rows = q.all()
    return {"rows": [{"ward_code": w.ward_code, "name": w.name, "localities": w.localities, "population": w.population,
                      "density_per_sqkm": round(w.population_density), "area_sq_km": w.area_sq_km,
                      "priority_score": round(w.priority_score or 0, 1), "growth_class": w.growth_class,
                      "share_below_5m_elevation": w.low_lying_share} for w in rows],
            "citation": _citation("wards", [w.id for w in rows], f"Wards ordered by {sort_by}", _sql(q))}


def get_ward_profile(db: Session, ward: str) -> Dict[str, Any]:
    w = resolve_ward(db, ward)
    if not w:
        return {"rows": [], "error": f"Ward '{ward}' not found. Use codes like 'H/E' or locality names."}
    cq = (db.query(CitizenRequest.primary_category, func.count(CitizenRequest.id)).filter(CitizenRequest.ward_id == w.id)
          .group_by(CitizenRequest.primary_category).order_by(func.count(CitizenRequest.id).desc()))
    gq = db.query(InfrastructureGap).filter(InfrastructureGap.ward_id == w.id).order_by(InfrastructureGap.deficit_percentage.desc())
    gaps = gq.all()
    open_n = db.query(CitizenRequest).filter(CitizenRequest.ward_id == w.id, CitizenRequest.status == RequestStatus.OPEN).count()
    factors = (w.priority_factors or {}).get("factors", []) if isinstance(w.priority_factors, dict) else []
    return {
        "rows": [{"ward_code": w.ward_code, "name": w.name, "localities": w.localities, "population_estimate": w.population,
                  "area_sq_km": w.area_sq_km, "density_per_sqkm": round(w.population_density), "priority_score": round(w.priority_score or 0, 1),
                  "priority_factors": [{"factor": f["factor"], "value": f["raw_value"], "contribution": f["weighted_contribution"]} for f in factors],
                  "growth_class": w.growth_class, "mean_elevation_m": w.mean_elevation_m, "share_below_5m": w.low_lying_share,
                  "open_complaints": open_n, "complaints_by_category": dict(cq.all()),
                  "infrastructure_gaps": [{"sector": g.sector, "deficit": g.deficit_amount, "unit": g.unit, "deficit_pct": g.deficit_percentage,
                                           "severity": g.severity} for g in gaps]}],
        "citation": _citation("wards, citizen_requests, infrastructure_gaps", [w.id] + [g.id for g in gaps],
                              f"Profile of ward {w.ward_code}", _sql(cq) + " ; " + _sql(gq)),
    }


def complaint_statistics(db: Session, category: Optional[str] = None, ward: Optional[str] = None, months: int = 12,
                         group_by: str = "ward", status: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.now()
    y, m = now.year, now.month - int(months)
    while m <= 0:
        y, m = y - 1, m + 12
    group_col = {"ward": Ward.ward_code, "category": CitizenRequest.primary_category,
                 "month": func.strftime("%Y-%m", CitizenRequest.created_at), "language": CitizenRequest.language}.get(group_by, Ward.ward_code)
    q = (db.query(group_col.label("key"), func.count(CitizenRequest.id).label("n"), func.min(CitizenRequest.id))
         .join(Ward, CitizenRequest.ward_id == Ward.id).filter(CitizenRequest.created_at >= datetime(y, m, 1)))
    cats = []
    if category:
        cats = [c for c in CATEGORIES if c == category.upper() or category.upper() in c]
        q = q.filter(CitizenRequest.primary_category.in_(cats or [category.upper()]))
    w = resolve_ward(db, ward) if ward else None
    if ward and w:
        q = q.filter(CitizenRequest.ward_id == w.id)
    if status:
        q = q.filter(CitizenRequest.status == status.upper())
    q = q.group_by(group_col).order_by(func.count(CitizenRequest.id).desc())
    rows = q.all()
    return {"rows": [{group_by: k, "complaints": n} for k, n, _ in rows],
            "filters": {"category": cats or category, "ward": w.ward_code if w else ward, "months": months, "status": status},
            "citation": _citation("citizen_requests JOIN wards", [w.id] if w else [], f"Complaint counts grouped by {group_by}", _sql(q))}


def infrastructure_gaps(db: Session, sector: Optional[str] = None, ward: Optional[str] = None, severity: Optional[str] = None,
                        limit: int = 10) -> Dict[str, Any]:
    q = db.query(InfrastructureGap, Ward.ward_code, Ward.name).join(Ward, InfrastructureGap.ward_id == Ward.id)
    if sector:
        q = q.filter(InfrastructureGap.sector.ilike(f"%{sector}%"))
    w = resolve_ward(db, ward) if ward else None
    if w:
        q = q.filter(InfrastructureGap.ward_id == w.id)
    if severity:
        q = q.filter(InfrastructureGap.severity == severity.upper())
    q = q.order_by(InfrastructureGap.deficit_percentage.desc()).limit(max(1, min(50, int(limit))))
    rows = q.all()
    return {"rows": [{"ward_code": c, "ward": n, "sector": g.sector, "required": g.required_capacity, "existing": g.existing_capacity,
                      "deficit": g.deficit_amount, "unit": g.unit, "deficit_pct": g.deficit_percentage, "severity": g.severity,
                      "data_confidence": (g.evidence or {}).get("data_confidence", "MEDIUM"), "norm": g.norm_reference} for g, c, n in rows],
            "citation": _citation("infrastructure_gaps JOIN wards", [g.id for g, _, _ in rows], "Norm-based capacity deficits", _sql(q))}


def forecast_demand(db: Session, metric: str = "complaint_volume", ward: Optional[str] = None, horizon_months: int = 12) -> Dict[str, Any]:
    from backend.app.forecasting.demand_model import METRICS
    from backend.app.services.analysis import forecast_for
    if metric not in METRICS:
        return {"rows": [], "error": f"metric must be one of {list(METRICS)}"}
    w = resolve_ward(db, ward) if ward else None
    try:
        res = forecast_for(db, metric, w.id if w else None, max(1, min(24, int(horizon_months))))
    except ValueError as exc:
        return {"rows": [], "error": str(exc)}
    hist = res["history"][-12:]
    last12 = sum(h["actual_value"] for h in hist) / max(1, len(hist))
    next_vals = [p["predicted_value"] for p in res["forecast"]]
    return {"rows": res["forecast"],
            "summary": {"metric": metric, "unit": METRICS[metric]["unit"], "ward": w.ward_code if w else "city",
                        "last_12m_average": round(last12, 2), "forecast_average": round(sum(next_vals) / len(next_vals), 2),
                        "growth_pct": round(100 * (sum(next_vals) / len(next_vals) - last12) / last12, 2) if last12 else None,
                        "backtest": res["metrics"]},
            "citation": _citation("service_demand_records, model_versions", [w.id] if w else [],
                                  f"GradientBoosting panel forecast of {metric}",
                                  f"SELECT month, value FROM service_demand_records WHERE metric = '{metric}'" + (f" AND ward_id = {w.id}" if w else ""))}


def urban_growth(db: Session, ward: Optional[str] = None, growth_class: Optional[str] = None, limit: int = 24) -> Dict[str, Any]:
    q = db.query(UrbanGrowth, Ward.ward_code, Ward.name, Ward.area_sq_km).join(Ward, UrbanGrowth.ward_id == Ward.id)
    w = resolve_ward(db, ward) if ward else None
    if w:
        q = q.filter(UrbanGrowth.ward_id == w.id)
    if growth_class:
        q = q.filter(UrbanGrowth.growth_class == growth_class.upper())
    q = q.order_by(UrbanGrowth.built_up_change_sq_km.desc()).limit(int(limit))
    rows = q.all()
    return {"rows": [{"ward_code": c, "ward": n, "period": f"{g.period_start_year}-{g.year}", "built_up_sq_km": g.built_up_area_sq_km,
                      "built_up_share_pct": round(100 * g.built_up_area_sq_km / a, 1), "built_up_change_sq_km": g.built_up_change_sq_km,
                      "vegetation_change_sq_km": round(-g.vegetation_loss_sq_km, 3), "complaint_growth_pct": g.complaint_growth_pct,
                      "growth_class": g.growth_class, "evidence": g.evidence} for g, c, n, a in rows],
            "citation": _citation("urban_growth JOIN wards", [g.id for g, *_ in rows], "Sentinel-2 derived growth patterns", _sql(q))}


def recommendations(db: Session, ward: Optional[str] = None, sector: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    q = db.query(Recommendation, Ward.ward_code).join(Ward, Recommendation.ward_id == Ward.id)
    w = resolve_ward(db, ward) if ward else None
    if w:
        q = q.filter(Recommendation.ward_id == w.id)
    if sector:
        q = q.filter(Recommendation.sector.ilike(f"%{sector}%"))
    q = q.order_by(Recommendation.score.desc()).limit(max(1, min(20, int(limit))))
    rows = q.all()
    return {"rows": [{"ward_code": c, "title": r.title, "sector": r.sector, "score": r.score, "priority": r.priority_level,
                      "proposal": r.recommendation_text, "estimated_cost_cr": r.estimated_cost_cr, "status": r.status} for r, c in rows],
            "citation": _citation("recommendations JOIN wards", [r.id for r, _ in rows], "MCDA-ranked interventions", _sql(q))}


def search_complaints(db: Session, query: str, top_k: int = 5, ward: Optional[str] = None) -> Dict[str, Any]:
    import numpy as np
    from backend.app.models.entities import RequestEmbedding
    from backend.app.nlp.embeddings import get_embedding_engine
    qv = np.asarray(get_embedding_engine().encode(query))
    q = db.query(RequestEmbedding.embedding_vector, CitizenRequest.id, CitizenRequest.original_text, CitizenRequest.primary_category,
                 CitizenRequest.status, Ward.ward_code).join(CitizenRequest, RequestEmbedding.request_id == CitizenRequest.id) \
        .outerjoin(Ward, CitizenRequest.ward_id == Ward.id)
    w = resolve_ward(db, ward) if ward else None
    if w:
        q = q.filter(CitizenRequest.ward_id == w.id)
    rows = [r for r in q.all() if len(r[0]) == len(qv)]
    if not rows or not np.any(qv):
        return {"rows": [], "citation": _citation("request_embeddings", [], "Semantic search (no matches)", _sql(q))}
    sims = np.array([r[0] for r in rows]) @ qv
    top = np.argsort(sims)[::-1][: max(1, min(20, int(top_k)))]
    out = [{"id": rows[i][1], "text": rows[i][2], "category": rows[i][3], "status": rows[i][4].value, "ward_code": rows[i][5],
            "similarity": round(float(sims[i]), 3)} for i in top]
    return {"rows": out, "citation": _citation("request_embeddings JOIN citizen_requests", [r["id"] for r in out],
                                               f"Semantic similarity search for '{query}'", _sql(q))}


def infrastructure_demand(db: Session, target_year: int = 2031) -> Dict[str, Any]:
    from backend.app.services.analysis import infrastructure_demand_projection
    res = infrastructure_demand_projection(db, int(target_year))
    top = sorted(res["wards"], key=lambda r: -r["additional_water_mld"])[:8]
    return {"rows": top, "city_totals": res["city_totals"], "method": res["method"],
            "citation": _citation("demographic_data, infrastructure_assets, service_demand_records", [r["ward_id"] for r in top],
                                  f"Norm-based requirements for {target_year}", "SELECT * FROM demographic_data WHERE census_year = 2011")}


def simulate_scenario(db: Session, parameters: Dict[str, float], wards: Optional[List[str]] = None) -> Dict[str, Any]:
    from backend.app.scenarios.engine import scenario_engine
    from backend.app.services.analysis import scenario_baseline
    ids = [w.id for w in (resolve_ward(db, r) for r in (wards or [])) if w] or None
    res = scenario_engine.simulate_scenario(scenario_baseline(db, ids), parameters or {})
    return {"rows": [{"score_change": res["score_breakdown"]["score_change"], "capital_cost_cr": res["capital_cost_cr"],
                      "deltas": res["delta_metrics"], "assumptions": res["assumptions"]}],
            "citation": _citation("wards, infrastructure_gaps, transportation_data, environmental_data", ids or [],
                                  "What-if simulation (not saved)", "scenario_baseline() aggregation over scope")}


TOOL_FUNCS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "list_wards": list_wards, "get_ward_profile": get_ward_profile, "complaint_statistics": complaint_statistics,
    "infrastructure_gaps": infrastructure_gaps, "forecast_demand": forecast_demand, "urban_growth": urban_growth,
    "recommendations": recommendations, "search_complaints": search_complaints, "infrastructure_demand": infrastructure_demand,
    "simulate_scenario": simulate_scenario,
}

_WARD = {"type": "string", "description": "Ward code (e.g. 'H/E', 'K/W') or locality name (e.g. 'Bandra East')"}
TOOL_SPECS: List[ToolSpec] = [
    ToolSpec("list_wards", "List Mumbai BMC wards ranked by a metric.", {"type": "object", "properties": {
        "sort_by": {"type": "string", "enum": ["priority", "population", "density", "area", "low_lying"]},
        "limit": {"type": "integer"}}}),
    ToolSpec("get_ward_profile", "Full profile of one ward: population, priority factors, complaints by category, infrastructure gaps.",
             {"type": "object", "properties": {"ward": _WARD}, "required": ["ward"]}),
    ToolSpec("complaint_statistics", "Count citizen complaints, optionally filtered by category / ward / status, grouped by ward, category, month or language.",
             {"type": "object", "properties": {"category": {"type": "string", "enum": CATEGORIES}, "ward": _WARD,
                                               "months": {"type": "integer", "description": "look-back window (default 12)"},
                                               "group_by": {"type": "string", "enum": ["ward", "category", "month", "language"]},
                                               "status": {"type": "string", "enum": ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]}}}),
    ToolSpec("infrastructure_gaps", "Norm-based infrastructure deficits (water, waste, drainage, healthcare, education, transit, open space).",
             {"type": "object", "properties": {"sector": {"type": "string"}, "ward": _WARD,
                                               "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MODERATE", "LOW"]},
                                               "limit": {"type": "integer"}}}),
    ToolSpec("forecast_demand", "Forecast monthly service demand for the city or a ward.",
             {"type": "object", "properties": {"metric": {"type": "string", "enum": ["complaint_volume", "water_demand_mld", "waste_generation_tpd", "transit_ridership"]},
                                               "ward": _WARD, "horizon_months": {"type": "integer"}}, "required": ["metric"]}),
    ToolSpec("urban_growth", "Satellite-derived urban growth pattern per ward (built-up / vegetation change, growth class).",
             {"type": "object", "properties": {"ward": _WARD, "growth_class": {"type": "string", "enum": ["RAPID_EXPANSION", "DENSIFYING", "GREENING", "STABLE"]},
                                               "limit": {"type": "integer"}}}),
    ToolSpec("recommendations", "Evidence-based, MCDA-ranked interventions.",
             {"type": "object", "properties": {"ward": _WARD, "sector": {"type": "string"}, "limit": {"type": "integer"}}}),
    ToolSpec("search_complaints", "Semantic search over complaint texts.",
             {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}, "ward": _WARD}, "required": ["query"]}),
    ToolSpec("infrastructure_demand", "Projected infrastructure requirements for a future year based on Census population projections.",
             {"type": "object", "properties": {"target_year": {"type": "integer"}}}),
    ToolSpec("simulate_scenario", "Run a what-if scenario preview. Parameters: transit_capacity_delta_pct, new_bus_stops, drainage_upgrade_pct, "
             "population_growth_rate_pct, density_rezoning_pct, water_supply_augmentation_mld, waste_processing_expansion_pct, "
             "new_health_facilities, new_schools, green_cover_increase_pct.",
             {"type": "object", "properties": {"parameters": {"type": "object"}, "wards": {"type": "array", "items": {"type": "string"}}},
              "required": ["parameters"]}),
]


def execute_tool(db: Session, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn = TOOL_FUNCS.get(name)
    if not fn:
        return {"error": f"Unknown tool {name}"}
    try:
        return fn(db, **{k: v for k, v in (args or {}).items() if v is not None})
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:  # never let a tool crash the request
        return {"error": f"{name} failed: {exc}"}
