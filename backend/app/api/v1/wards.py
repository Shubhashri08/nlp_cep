from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import (
    Ward, Zone, CitizenRequest, InfrastructureAsset,
    InfrastructureGap, DemographicData, TransportationData,
    EnvironmentalData, LandUseData, Recommendation, Prediction
)
from backend.app.schemas.dss_schemas import WardSummary, WardProfile

router = APIRouter()

@router.get("", response_model=List[WardSummary])
def get_wards(db: Session = Depends(get_db)):
    wards = db.query(Ward).all()
    summaries = []
    for w in wards:
        complaint_count = db.query(CitizenRequest).filter(CitizenRequest.ward_id == w.id).count()
        gaps_count = db.query(InfrastructureGap).filter(
            InfrastructureGap.ward_id == w.id, 
            InfrastructureGap.severity.in_(["CRITICAL", "HIGH"])
        ).count()
        zone_name = w.zone.name if w.zone else None
        
        summaries.append(WardSummary(
            id=w.id,
            ward_code=w.ward_code,
            name=w.name,
            zone_name=zone_name,
            area_sq_km=w.area_sq_km,
            population=w.population,
            population_density=w.population_density,
            center_lat=w.center_lat,
            center_lng=w.center_lng,
            priority_score=w.priority_score,
            total_complaints=complaint_count,
            critical_gaps_count=gaps_count
        ))
    return sorted(summaries, key=lambda x: x.priority_score, reverse=True)

@router.get("/{ward_id}/profile", response_model=WardProfile)
def get_ward_profile(ward_id: int, db: Session = Depends(get_db)):
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
        
    complaints = db.query(CitizenRequest).filter(CitizenRequest.ward_id == ward.id).all()
    
    # Categorize top complaints
    cat_counts: Dict[str, int] = {}
    for c in complaints:
        cat_counts[c.primary_category] = cat_counts.get(c.primary_category, 0) + 1
    top_cats = [{"category": k, "count": v} for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)]
    
    gaps = db.query(InfrastructureGap).filter(InfrastructureGap.ward_id == ward.id).all()
    assets = db.query(InfrastructureAsset).filter(InfrastructureAsset.ward_id == ward.id).all()
    demo = db.query(DemographicData).filter(DemographicData.ward_id == ward.id).first()
    env = db.query(EnvironmentalData).filter(EnvironmentalData.ward_id == ward.id).first()
    trans = db.query(TransportationData).filter(TransportationData.ward_id == ward.id).first()
    land = db.query(LandUseData).filter(LandUseData.ward_id == ward.id).first()
    recs = db.query(Recommendation).filter(Recommendation.ward_id == ward.id).all()
    preds = db.query(Prediction).filter(
        (Prediction.ward_id == ward.id) | (Prediction.ward_id.is_(None))
    ).limit(6).all()
    
    summary = WardSummary(
        id=ward.id,
        ward_code=ward.ward_code,
        name=ward.name,
        zone_name=ward.zone.name if ward.zone else None,
        area_sq_km=ward.area_sq_km,
        population=ward.population,
        population_density=ward.population_density,
        center_lat=ward.center_lat,
        center_lng=ward.center_lng,
        priority_score=ward.priority_score,
        total_complaints=len(complaints),
        critical_gaps_count=len([g for g in gaps if g.severity in ("CRITICAL", "HIGH")])
    )
    
    return WardProfile(
        ward_info=summary,
        boundary_geojson=ward.boundary_geojson,
        demographics={
            "total_population": demo.total_population,
            "households": demo.households,
            "literacy_rate": demo.literacy_rate,
            "growth_rate_percent": demo.growth_rate_percent
        } if demo else None,
        infrastructure_assets=[{
            "id": a.id,
            "name": a.name,
            "type": a.asset_type,
            "capacity": a.capacity,
            "unit": a.capacity_unit,
            "lat": a.latitude,
            "lng": a.longitude
        } for a in assets],
        infrastructure_gaps=[{
            "id": g.id,
            "sector": g.sector,
            "required": g.required_capacity,
            "existing": g.existing_capacity,
            "deficit": g.deficit_amount,
            "deficit_pct": g.deficit_percentage,
            "unit": g.unit,
            "severity": g.severity
        } for g in gaps],
        environmental_indicators={
            "rainfall_mm": env.rainfall_mm,
            "aqi_pm25": env.aqi_pm25,
            "flood_risk_score": env.flood_risk_score,
            "elevation_m": env.elevation_m,
            "vegetation_pct": env.vegetation_coverage_pct
        } if env else None,
        transportation_indicators={
            "road_length_km": trans.road_length_km,
            "road_density": trans.road_density_km_per_sq_km,
            "bus_stops": trans.bus_stops_count,
            "daily_ridership": trans.daily_transit_ridership,
            "congestion_index": trans.avg_peak_congestion_index
        } if trans else None,
        land_use={
            "residential_pct": land.residential_pct,
            "commercial_pct": land.commercial_pct,
            "industrial_pct": land.industrial_pct,
            "green_pct": land.forest_green_pct,
            "water_pct": land.waterbody_pct
        } if land else None,
        top_complaint_categories=top_cats,
        recent_complaints=complaints[:10],
        recommendations=[{
            "id": r.id,
            "sector": r.sector,
            "title": r.title,
            "recommendation_text": r.recommendation_text,
            "priority_level": r.priority_level,
            "score": r.score,
            "contributing_factors": r.contributing_factors,
            "supporting_evidence": r.supporting_evidence
        } for r in recs],
        predicted_demand=[{
            "metric": p.target_metric,
            "date": p.target_date.strftime("%Y-%m"),
            "predicted_value": p.predicted_value,
            "lower": p.lower_bound,
            "upper": p.upper_bound
        } for p in preds]
    )

@router.get("/geojson/all")
def get_all_wards_geojson(db: Session = Depends(get_db)):
    wards = db.query(Ward).all()
    features = []
    for w in wards:
        features.append({
            "type": "Feature",
            "id": w.id,
            "properties": {
                "id": w.id,
                "ward_code": w.ward_code,
                "name": w.name,
                "population": w.population,
                "density": w.population_density,
                "priority_score": w.priority_score,
                "area_sq_km": w.area_sq_km,
                "center_lat": w.center_lat,
                "center_lng": w.center_lng
            },
            "geometry": w.boundary_geojson
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }
