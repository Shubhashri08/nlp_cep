from collections import Counter
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.api.serializers import citizen_request_out
from backend.app.database.session import get_db
from backend.app.models.entities import (
    CitizenRequest, DemographicData, EnvironmentalData, InfrastructureGap, LandUseData, Prediction, Recommendation,
    RequestStatus, SatelliteObservation, TransportationData, UrbanGrowth, User, Ward,
)
from backend.app.schemas.dss_schemas import WardProfile, WardSummary
from backend.app.services.analysis import asset_counts

router = APIRouter(dependencies=[Depends(get_current_user)])


def _summaries(db: Session) -> List[WardSummary]:
    totals = dict(db.query(CitizenRequest.ward_id, func.count(CitizenRequest.id)).group_by(CitizenRequest.ward_id).all())
    opens = dict(db.query(CitizenRequest.ward_id, func.count(CitizenRequest.id))
                 .filter(CitizenRequest.status == RequestStatus.OPEN).group_by(CitizenRequest.ward_id).all())
    crit = dict(db.query(InfrastructureGap.ward_id, func.count(InfrastructureGap.id))
                .filter(InfrastructureGap.severity.in_(["CRITICAL", "HIGH"])).group_by(InfrastructureGap.ward_id).all())
    out = []
    for w in db.query(Ward).all():
        out.append(WardSummary(
            id=w.id, ward_code=w.ward_code, name=w.name, localities=w.localities, zone_name=w.zone.name if w.zone else None,
            area_sq_km=w.area_sq_km, population=w.population, population_density=w.population_density,
            center_lat=w.center_lat, center_lng=w.center_lng, priority_score=w.priority_score or 0.0,
            growth_class=w.growth_class, mean_elevation_m=w.mean_elevation_m, low_lying_share=w.low_lying_share,
            total_complaints=totals.get(w.id, 0), open_complaints=opens.get(w.id, 0), critical_gaps_count=crit.get(w.id, 0)))
    return sorted(out, key=lambda x: -x.priority_score)


@router.get("", response_model=List[WardSummary])
def get_wards(db: Session = Depends(get_db)):
    return _summaries(db)


@router.get("/geojson/all")
def get_all_wards_geojson(db: Session = Depends(get_db)):
    """Ward polygons with indicator properties for choropleth styling."""
    summaries = {s.id: s for s in _summaries(db)}
    land = {l.ward_id: l for l in db.query(LandUseData).order_by(LandUseData.year).all()}
    trans = {t.ward_id: t for t in db.query(TransportationData).order_by(TransportationData.id).all()}
    env = {e.ward_id: e for e in db.query(EnvironmentalData).order_by(EnvironmentalData.recorded_at).all()}
    growth = {g.ward_id: g for g in db.query(UrbanGrowth).all()}
    gaps = {}
    for g in db.query(InfrastructureGap).all():
        gaps.setdefault(g.ward_id, []).append(g.deficit_percentage)
    features = []
    for w in db.query(Ward).all():
        s = summaries[w.id]
        lu, tr, en, gr = land.get(w.id), trans.get(w.id), env.get(w.id), growth.get(w.id)
        features.append({
            "type": "Feature", "id": w.id, "geometry": w.boundary_geojson,
            "properties": {
                "id": w.id, "ward_code": w.ward_code, "name": w.name, "localities": w.localities,
                "population": w.population, "density": w.population_density, "area_sq_km": w.area_sq_km,
                "priority_score": w.priority_score, "total_complaints": s.total_complaints,
                "complaints_per_1000": round(1000 * s.total_complaints / max(1, w.population), 3),
                "critical_gaps": s.critical_gaps_count,
                "mean_deficit_pct": round(sum(gaps.get(w.id, [0])) / max(1, len(gaps.get(w.id, [0]))), 1),
                "residential_pct": lu.residential_pct if lu else None, "commercial_pct": lu.commercial_pct if lu else None,
                "industrial_pct": lu.industrial_pct if lu else None, "green_pct": lu.forest_green_pct if lu else None,
                "water_pct": lu.waterbody_pct if lu else None,
                "road_density": tr.road_density_km_per_sq_km if tr else None, "bus_stops": tr.bus_stops_count if tr else None,
                "congestion_index": tr.avg_peak_congestion_index if tr else None,
                "flood_risk": en.flood_risk_score if en else None, "pm25": en.aqi_pm25 if en else None,
                "elevation_m": w.mean_elevation_m, "low_lying_share": w.low_lying_share,
                "growth_class": w.growth_class, "built_up_change_sq_km": gr.built_up_change_sq_km if gr else None,
                "center_lat": w.center_lat, "center_lng": w.center_lng,
            },
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/{ward_id}/profile", response_model=WardProfile)
def get_ward_profile(ward_id: int, db: Session = Depends(get_db)):
    ward = db.get(Ward, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    summary = next(s for s in _summaries(db) if s.id == ward_id)
    cats = Counter(c for (c,) in db.query(CitizenRequest.primary_category).filter(CitizenRequest.ward_id == ward_id))
    gaps = db.query(InfrastructureGap).filter(InfrastructureGap.ward_id == ward_id).order_by(InfrastructureGap.deficit_percentage.desc()).all()
    demo = db.query(DemographicData).filter(DemographicData.ward_id == ward_id).order_by(DemographicData.census_year.desc()).all()
    env_rows = db.query(EnvironmentalData).filter(EnvironmentalData.ward_id == ward_id).order_by(EnvironmentalData.recorded_at.desc()).limit(12).all()
    trans = db.query(TransportationData).filter(TransportationData.ward_id == ward_id).order_by(TransportationData.id.desc()).first()
    land = db.query(LandUseData).filter(LandUseData.ward_id == ward_id).order_by(LandUseData.year.desc()).first()
    sat = db.query(SatelliteObservation).filter(SatelliteObservation.ward_id == ward_id).order_by(SatelliteObservation.observation_date).all()
    growth = db.query(UrbanGrowth).filter(UrbanGrowth.ward_id == ward_id).order_by(UrbanGrowth.year.desc()).first()
    recs = db.query(Recommendation).filter(Recommendation.ward_id == ward_id).order_by(Recommendation.score.desc()).all()
    preds = (db.query(Prediction).filter(Prediction.ward_id == ward_id, Prediction.target_metric == "complaint_volume")
             .order_by(Prediction.target_date).all())
    recent = (db.query(CitizenRequest).filter(CitizenRequest.ward_id == ward_id)
              .order_by(CitizenRequest.created_at.desc()).limit(10).all())
    census = next((d for d in demo if d.census_year == 2011), None)
    current = demo[0] if demo else None
    latest_env = env_rows[0] if env_rows else None
    return WardProfile(
        ward_info=summary,
        boundary_geojson=ward.boundary_geojson,
        priority_factors=(ward.priority_factors or {}).get("factors", []) if isinstance(ward.priority_factors, dict) else [],
        demographics={
            "census_year": 2011, "population_2011": census.total_population if census else None,
            "population_current_estimate": current.total_population if current else ward.population,
            "estimate_year": current.census_year if current else None,
            "households": census.households if census else None, "literacy_rate": census.literacy_rate if census else None,
            "sex_ratio": census.sex_ratio if census else None, "children_0_6": census.child_population_0_6 if census else None,
            "workers": census.workers if census else None, "sc_population": census.sc_population if census else None,
            "st_population": census.st_population if census else None,
            "annual_growth_rate_percent": current.growth_rate_percent if current else None,
            "provenance": "CENSUS 2011 (projection: ESTIMATED)",
        } if demo else None,
        asset_counts=dict(asset_counts(db).get(ward_id, {})),
        infrastructure_gaps=[{"id": g.id, "sector": g.sector, "required": g.required_capacity, "existing": g.existing_capacity,
                              "deficit": g.deficit_amount, "deficit_pct": g.deficit_percentage, "unit": g.unit,
                              "severity": g.severity, "norm_reference": g.norm_reference, "evidence": g.evidence} for g in gaps],
        environmental_indicators={
            "flood_risk_score": latest_env.flood_risk_score, "elevation_m": ward.mean_elevation_m,
            "low_lying_share": ward.low_lying_share, "vegetation_pct": latest_env.vegetation_coverage_pct,
            "aqi_pm25_12m_avg": round(sum(e.aqi_pm25 for e in env_rows) / len(env_rows), 1),
            "rainfall_12m_mm": round(sum(e.rainfall_mm for e in env_rows), 0),
            "monthly": [{"month": e.recorded_at.strftime("%Y-%m"), "rainfall_mm": e.rainfall_mm, "pm25": e.aqi_pm25,
                         "flood_risk": e.flood_risk_score} for e in reversed(env_rows)],
            "provenance": "DEM/SENTINEL (elevation, vegetation) · SYNTHETIC (monthly readings)",
        } if latest_env else None,
        transportation_indicators={
            "road_length_km": trans.road_length_km, "road_density": trans.road_density_km_per_sq_km,
            "road_km_by_class": trans.road_km_by_class, "bus_stops": trans.bus_stops_count,
            "rail_stations": trans.rail_stations_count, "metro_stations": trans.metro_stations_count,
            "daily_ridership_estimate": trans.daily_transit_ridership, "congestion_index_estimate": trans.avg_peak_congestion_index,
            "provenance": trans.provenance,
        } if trans else None,
        land_use={"residential_pct": land.residential_pct, "commercial_pct": land.commercial_pct, "industrial_pct": land.industrial_pct,
                  "green_pct": land.forest_green_pct, "water_pct": land.waterbody_pct, "mixed_pct": land.mixed_use_pct,
                  "agricultural_pct": land.agricultural_pct, "unmapped_pct": land.unmapped_pct, "buildings": land.building_count,
                  "provenance": land.provenance} if land else None,
        satellite=[{"year": o.observation_date.year, "date": o.observation_date.strftime("%Y-%m-%d"), "mean_ndvi": o.mean_ndvi,
                    "mean_ndbi": o.mean_ndbi, "mean_ndwi": o.mean_ndwi, "built_up_sq_km": o.built_up_area_sq_km,
                    "vegetation_sq_km": o.vegetation_area_sq_km, "water_sq_km": o.water_area_sq_km} for o in sat],
        growth={"growth_class": growth.growth_class, "period": f"{growth.period_start_year}–{growth.year}",
                "built_up_change_sq_km": growth.built_up_change_sq_km, "vegetation_loss_sq_km": growth.vegetation_loss_sq_km,
                "annual_built_up_growth_pct": growth.annual_growth_rate_pct, "complaint_growth_pct": growth.complaint_growth_pct,
                "evidence": growth.evidence} if growth else None,
        top_complaint_categories=[{"category": k, "count": v} for k, v in cats.most_common()],
        recent_complaints=[citizen_request_out(r, ward.name) for r in recent],
        recommendations=[{"id": r.id, "sector": r.sector, "title": r.title, "recommendation_text": r.recommendation_text,
                          "priority_level": r.priority_level, "score": r.score, "estimated_cost_cr": r.estimated_cost_cr,
                          "status": r.status} for r in recs],
        predicted_demand=[{"metric": p.target_metric, "date": p.target_date.strftime("%Y-%m"), "predicted_value": p.predicted_value,
                           "lower": p.lower_bound, "upper": p.upper_bound} for p in preds],
    )
