from collections import defaultdict
from datetime import datetime
from statistics import median
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.gis.hotspots import detect_issue_hotspots
from backend.app.models.entities import (
    CitizenRequest, DataSource, DemographicData, InfrastructureGap, LandUseData, RequestStatus, SatelliteObservation,
    UrbanGrowth, User, UserRole, Ward,
)
from backend.app.schemas.dss_schemas import DashboardOverview
from backend.app.services import analysis

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(db: Session = Depends(get_db)):
    by_status = dict(db.query(CitizenRequest.status, func.count(CitizenRequest.id)).group_by(CitizenRequest.status).all())
    total = sum(by_status.values())
    cats = (db.query(CitizenRequest.primary_category, func.count(CitizenRequest.id))
            .group_by(CitizenRequest.primary_category).order_by(func.count(CitizenRequest.id).desc()).all())
    langs = db.query(CitizenRequest.language, func.count(CitizenRequest.id)).group_by(CitizenRequest.language).all()

    ward_rows = (db.query(Ward.id, Ward.name, Ward.ward_code, Ward.priority_score, Ward.population, func.count(CitizenRequest.id))
                 .outerjoin(CitizenRequest, CitizenRequest.ward_id == Ward.id).group_by(Ward.id)
                 .order_by(Ward.priority_score.desc()).all())
    rankings = [{"ward_id": i, "ward_name": n, "ward_code": c, "priority_score": round(p or 0, 1), "complaint_count": k,
                 "complaints_per_1000": round(1000 * k / max(1, pop), 2)} for i, n, c, p, pop, k in ward_rows]

    month_col = func.strftime("%Y-%m", CitizenRequest.created_at)
    trend = defaultdict(lambda: {"count": 0, "resolved": 0})
    for m, st, n in db.query(month_col, CitizenRequest.status, func.count(CitizenRequest.id)).group_by(month_col, CitizenRequest.status):
        trend[m]["count"] += n
        if st in (RequestStatus.RESOLVED, RequestStatus.CLOSED):
            trend[m]["resolved"] += n
    monthly = [{"month": m, **v} for m, v in sorted(trend.items())][-24:]

    durations = [(r - c).total_seconds() / 86400 for c, r in db.query(CitizenRequest.created_at, CitizenRequest.resolved_at)
                 .filter(CitizenRequest.resolved_at.isnot(None)).all()]

    since = datetime(datetime.now().year - 1, datetime.now().month, 1)
    pts = [{"latitude": la, "longitude": ln, "primary_category": c} for la, ln, c in
           db.query(CitizenRequest.latitude, CitizenRequest.longitude, CitizenRequest.primary_category)
           .filter(CitizenRequest.latitude.isnot(None), CitizenRequest.created_at >= since)]
    hotspots = detect_issue_hotspots(pts, eps_km=0.6, min_samples=8)

    prov = (db.query(DataSource.provenance, func.count(DataSource.id), func.avg(DataSource.quality_score))
            .group_by(DataSource.provenance).all())
    avg_q = db.query(func.avg(DataSource.quality_score)).scalar()
    return DashboardOverview(
        total_requests=total,
        open_requests=by_status.get(RequestStatus.OPEN, 0),
        in_progress_requests=by_status.get(RequestStatus.IN_PROGRESS, 0),
        resolved_requests=by_status.get(RequestStatus.RESOLVED, 0) + by_status.get(RequestStatus.CLOSED, 0),
        median_resolution_days=round(median(durations), 1) if durations else None,
        high_priority_wards_count=db.query(Ward).filter(Ward.priority_score >= 60).count(),
        total_infrastructure_gaps=db.query(InfrastructureGap).count(),
        critical_gaps_count=db.query(InfrastructureGap).filter(InfrastructureGap.severity == "CRITICAL").count(),
        avg_quality_score=round(float(avg_q), 3) if avg_q is not None else 0.0,
        top_issue_categories=[{"category": c, "count": n} for c, n in cats],
        ward_complaint_rankings=rankings,
        monthly_trend=monthly,
        language_distribution=[{"language": l, "count": n} for l, n in langs],
        active_hotspots_count=len(hotspots),
        population_total=int(db.query(func.sum(Ward.population)).scalar() or 0),
        data_provenance=[{"provenance": p, "sources": n, "avg_quality": round(float(q or 0), 3)} for p, n, q in prov],
    )


@router.get("/infrastructure-gaps")
def get_all_infrastructure_gaps(sector: Optional[str] = None, severity: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(InfrastructureGap, Ward).join(Ward, InfrastructureGap.ward_id == Ward.id)
    if sector:
        q = q.filter(InfrastructureGap.sector == sector)
    if severity:
        q = q.filter(InfrastructureGap.severity == severity)
    return [{"id": g.id, "ward_id": g.ward_id, "ward_name": w.name, "ward_code": w.ward_code, "sector": g.sector,
             "required_capacity": g.required_capacity, "existing_capacity": g.existing_capacity, "deficit_amount": g.deficit_amount,
             "deficit_percentage": g.deficit_percentage, "unit": g.unit, "severity": g.severity,
             "complaint_density": g.complaint_density, "norm_reference": g.norm_reference, "evidence": g.evidence,
             "assessment_date": g.assessment_date.isoformat() if g.assessment_date else None}
            for g, w in q.order_by(InfrastructureGap.deficit_percentage.desc()).all()]


@router.post("/infrastructure-gaps/recompute")
def recompute_gaps(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.PLANNER, UserRole.ANALYST))):
    gaps = analysis.recompute_gaps(db)
    recs = analysis.recompute_priorities_and_recommendations(db)
    audit(db, user, "GAPS_RECOMPUTED", "ANALYTICS", None, {"gaps": len(gaps), "recommendations": len(recs)}, request)
    db.commit()
    return {"gaps": len(gaps), "recommendations": len(recs)}


@router.get("/urban-growth")
def get_urban_growth(db: Session = Depends(get_db)):
    city = db.query(SatelliteObservation).filter(SatelliteObservation.ward_id.is_(None)).order_by(SatelliteObservation.observation_date).all()
    wards = {w.id: w for w in db.query(Ward).all()}
    rows = []
    for g in db.query(UrbanGrowth).all():
        w = wards.get(g.ward_id)
        start = g.built_up_area_sq_km - g.built_up_change_sq_km
        rows.append({"ward_id": g.ward_id, "ward_code": w.ward_code, "ward_name": w.name, "period": f"{g.period_start_year}–{g.year}",
                     "built_up_start_sq_km": round(start, 3), "built_up_end_sq_km": g.built_up_area_sq_km,
                     "built_up_change_sq_km": g.built_up_change_sq_km,
                     "built_up_change_pct": round(100 * g.built_up_change_sq_km / start, 2) if start else None,
                     "built_up_share_pct": round(100 * g.built_up_area_sq_km / w.area_sq_km, 1),
                     "vegetation_change_sq_km": round(-g.vegetation_loss_sq_km, 3), "water_change_sq_km": g.water_body_change_sq_km,
                     "annual_built_up_growth_pct": g.annual_growth_rate_pct, "complaint_growth_pct": g.complaint_growth_pct,
                     "population_density": w.population_density, "growth_class": g.growth_class, "evidence": g.evidence})
    rows.sort(key=lambda r: -(r["built_up_change_pct"] or -1e9))
    series = [{"date": o.observation_date.strftime("%Y-%m-%d"), "year": o.observation_date.year, "satellite": o.satellite_name,
               "scenes": (o.scene_id or "").count(",") + 1 if o.scene_id else 0, "mean_ndvi": o.mean_ndvi, "mean_ndbi": o.mean_ndbi,
               "mean_ndwi": o.mean_ndwi, "built_up_sq_km": o.built_up_area_sq_km, "vegetation_sq_km": o.vegetation_area_sq_km,
               "water_sq_km": o.water_area_sq_km, "cloud_cover_pct": o.cloud_cover_pct} for o in city]
    class_counts = defaultdict(int)
    for r in rows:
        class_counts[r["growth_class"]] += 1
    summary = {}
    if len(series) >= 2:
        a, b = series[0], series[-1]
        summary = {"period": f"{a['year']}–{b['year']}",
                   "built_up_change_pct": round(100 * (b["built_up_sq_km"] - a["built_up_sq_km"]) / a["built_up_sq_km"], 2),
                   "vegetation_change_pct": round(100 * (b["vegetation_sq_km"] - a["vegetation_sq_km"]) / a["vegetation_sq_km"], 2),
                   "water_change_pct": round(100 * (b["water_sq_km"] - a["water_sq_km"]) / a["water_sq_km"], 2) if a["water_sq_km"] else None,
                   "class_counts": dict(class_counts)}
    return {"satellite_series": series, "ward_growth": rows, "growth_summary": summary,
            "method": "Sentinel-2 L2A dry-season median composites; land cover from NDVI/NDWI/NDBI thresholds after PIF "
                      "radiometric normalisation. Growth classes combine built-up change, built-up share and complaint growth."}


@router.post("/urban-growth/recompute")
def recompute_growth(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.ANALYST))):
    res = analysis.compute_growth(db)
    audit(db, user, "GROWTH_RECOMPUTED", "ANALYTICS", None, res["city"].get("class_counts"), request)
    db.commit()
    return res["city"]


@router.get("/demographics")
def get_demographics(db: Session = Depends(get_db)):
    wards = {w.id: w for w in db.query(Ward).all()}
    land = {l.ward_id: l for l in db.query(LandUseData).all()}
    out = []
    for d in db.query(DemographicData).filter(DemographicData.census_year == 2011).all():
        w = wards[d.ward_id]
        lu = land.get(d.ward_id)
        out.append({"ward_id": w.id, "ward_code": w.ward_code, "ward_name": w.name, "area_sq_km": w.area_sq_km,
                    "population_2011": d.total_population, "population_current": w.population, "density": w.population_density,
                    "households": d.households, "avg_household_size": round(d.total_population / max(1, d.households), 2),
                    "literacy_rate": d.literacy_rate, "sex_ratio": d.sex_ratio, "children_0_6_pct": round(100 * (d.child_population_0_6 or 0) / d.total_population, 2),
                    "workers_pct": round(100 * (d.workers or 0) / d.total_population, 2), "sc_pct": round(100 * (d.sc_population or 0) / d.total_population, 2),
                    "st_pct": round(100 * (d.st_population or 0) / d.total_population, 2),
                    "land_use": {"residential": lu.residential_pct, "commercial": lu.commercial_pct, "industrial": lu.industrial_pct,
                                 "green": lu.forest_green_pct, "water": lu.waterbody_pct, "mixed": lu.mixed_use_pct,
                                 "unmapped": lu.unmapped_pct} if lu else None})
    return sorted(out, key=lambda r: r["ward_code"])
