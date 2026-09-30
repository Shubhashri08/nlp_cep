from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import (
    Ward, CitizenRequest, InfrastructureAsset, EnvironmentalData, SatelliteObservation
)
from backend.app.gis.hotspots import detect_issue_hotspots

router = APIRouter()

@router.get("/layers")
def get_gis_layers_manifest():
    return {
        "available_layers": [
            {"id": "wards", "name": "Municipal Ward Boundaries", "type": "polygon", "default": True},
            {"id": "hotspots", "name": "Issue Hotspots (DBSCAN)", "type": "circle", "default": True},
            {"id": "complaints", "name": "Citizen Grievances", "type": "point", "default": True},
            {"id": "infrastructure", "name": "Critical Infrastructure Assets", "type": "point", "default": False},
            {"id": "flood_risk", "name": "Flood Vulnerability Index", "type": "polygon", "default": False},
            {"id": "remote_sensing", "name": "Satellite NDVI / NDBI Trends", "type": "raster_stats", "default": False}
        ]
    }

@router.get("/hotspots")
def get_spatial_hotspots(
    eps_km: float = Query(1.0, ge=0.2, le=5.0),
    min_samples: int = Query(2, ge=2, le=10),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(CitizenRequest).filter(
        CitizenRequest.latitude.isnot(None),
        CitizenRequest.longitude.isnot(None)
    )
    if category:
        q = q.filter(CitizenRequest.primary_category == category)
        
    complaints = [{
        "id": c.id,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "primary_category": c.primary_category,
        "original_text": c.original_text,
        "ward_id": c.ward_id
    } for c in q.all()]
    
    hotspots = detect_issue_hotspots(complaints, eps_km=eps_km, min_samples=min_samples)
    return {
        "total_hotspots": len(hotspots),
        "hotspots": hotspots
    }

@router.get("/infrastructure")
def get_infrastructure_map_points(
    asset_type: Optional[str] = Query(None),
    ward_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(InfrastructureAsset)
    if asset_type:
        q = q.filter(InfrastructureAsset.asset_type == asset_type)
    if ward_id:
        q = q.filter(InfrastructureAsset.ward_id == ward_id)
        
    assets = q.all()
    return [{
        "id": a.id,
        "uid": a.asset_uid,
        "name": a.name,
        "asset_type": a.asset_type,
        "capacity": a.capacity,
        "unit": a.capacity_unit,
        "ward_id": a.ward_id,
        "latitude": a.latitude,
        "longitude": a.longitude,
        "condition_score": a.condition_score
    } for a in assets]
