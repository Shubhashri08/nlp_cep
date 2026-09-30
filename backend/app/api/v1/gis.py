import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.gis.hotspots import detect_issue_hotspots
from backend.app.models.entities import CitizenRequest, InfrastructureAsset
from backend.app.api.v1.wards import get_all_wards_geojson

router = APIRouter(dependencies=[Depends(get_current_user)])
# Satellite overlays are public imagery loaded by <img> tags (no auth header), served separately.
public_router = APIRouter()

SENTINEL_DIR = os.path.join(settings.EXTERNAL_DATA_DIR, "sentinel")

CHOROPLETHS = {
    "priority": {"property": "priority_score", "label": "Planning priority score", "ramp": "severity", "unit": "/100"},
    "density": {"property": "density", "label": "Population density", "ramp": "density", "unit": "persons/km²"},
    "complaints": {"property": "complaints_per_1000", "label": "Complaints per 1,000 residents", "ramp": "severity", "unit": ""},
    "deficit": {"property": "mean_deficit_pct", "label": "Mean infrastructure deficit", "ramp": "severity", "unit": "%"},
    "flood": {"property": "flood_risk", "label": "Flood exposure index", "ramp": "severity", "unit": "0–1"},
    "green": {"property": "green_pct", "label": "Green / open land (OSM)", "ramp": "green", "unit": "%"},
    "residential": {"property": "residential_pct", "label": "Residential land use (OSM)", "ramp": "density", "unit": "%"},
    "industrial": {"property": "industrial_pct", "label": "Industrial land use (OSM)", "ramp": "severity", "unit": "%"},
    "transit": {"property": "bus_stops", "label": "Bus stops mapped (OSM)", "ramp": "density", "unit": "stops"},
    "congestion": {"property": "congestion_index", "label": "Peak congestion index (estimate)", "ramp": "severity", "unit": "1–3"},
    "pm25": {"property": "pm25", "label": "PM2.5 (latest month)", "ramp": "severity", "unit": "µg/m³"},
    "elevation": {"property": "elevation_m", "label": "Mean elevation (Copernicus DEM)", "ramp": "density", "unit": "m"},
    "growth": {"property": "growth_class", "label": "Urban growth pattern", "ramp": "categorical", "unit": ""},
}


def _sentinel_meta():
    path = os.path.join(SENTINEL_DIR, "sentinel_indices.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/layers")
def get_gis_layers_manifest():
    meta = _sentinel_meta()
    overlays = []
    if meta:
        for epoch in sorted(meta["epochs"]):
            if os.path.exists(os.path.join(SENTINEL_DIR, f"overlay_{epoch}_ndvi.png")):
                overlays.append({"id": f"ndvi_{epoch}", "name": f"Sentinel-2 NDVI {epoch}", "url": f"{settings.API_V1_STR}/gis/overlays/overlay_{epoch}_ndvi.png"})
        if os.path.exists(os.path.join(SENTINEL_DIR, "overlay_builtup_change.png")):
            epochs = sorted(meta["epochs"])
            overlays.append({"id": "builtup_change", "name": f"New built-up {epochs[0]}→{epochs[-1]}", "url": f"{settings.API_V1_STR}/gis/overlays/overlay_builtup_change.png"})
    return {
        "vector_layers": [
            {"id": "wards", "name": "Ward boundaries (OSM)", "endpoint": "/wards/geojson/all"},
            {"id": "hotspots", "name": "Complaint hotspots (DBSCAN)", "endpoint": "/gis/hotspots"},
            {"id": "complaints", "name": "Citizen complaints", "endpoint": "/citizen-requests/points"},
            {"id": "assets", "name": "Infrastructure assets (OSM)", "endpoint": "/gis/infrastructure"},
        ],
        "choropleths": [{"id": k, **v} for k, v in CHOROPLETHS.items()],
        "raster_overlays": overlays,
        "overlay_bounds": meta.get("overlay_bounds") if meta else None,
    }


@router.get("/choropleth/{layer_id}")
def get_choropleth(layer_id: str, db: Session = Depends(get_db)):
    if layer_id not in CHOROPLETHS:
        raise HTTPException(status_code=404, detail=f"Unknown layer. Options: {list(CHOROPLETHS)}")
    fc = get_all_wards_geojson(db)
    spec = CHOROPLETHS[layer_id]
    values = [f["properties"].get(spec["property"]) for f in fc["features"]]
    numeric = [v for v in values if isinstance(v, (int, float))]
    return {**fc, "layer": {"id": layer_id, **spec,
                            "min": min(numeric) if numeric else None, "max": max(numeric) if numeric else None}}


@router.get("/hotspots")
def get_spatial_hotspots(eps_km: float = Query(0.6, ge=0.2, le=5.0), min_samples: int = Query(8, ge=3, le=50),
                         category: Optional[str] = None, months: int = Query(12, ge=1, le=60), db: Session = Depends(get_db)):
    from datetime import datetime
    now = datetime.now()
    y, m = now.year, now.month - months
    while m <= 0:
        y, m = y - 1, m + 12
    q = db.query(CitizenRequest).filter(CitizenRequest.latitude.isnot(None), CitizenRequest.created_at >= datetime(y, m, 1))
    if category:
        q = q.filter(CitizenRequest.primary_category == category)
    pts = [{"id": c.id, "latitude": c.latitude, "longitude": c.longitude, "primary_category": c.primary_category,
            "original_text": c.summary or c.original_text, "ward_id": c.ward_id} for c in q.all()]
    spots = detect_issue_hotspots(pts, eps_km=eps_km, min_samples=min_samples)
    return {"total_hotspots": len(spots), "points_considered": len(pts),
            "parameters": {"eps_km": eps_km, "min_samples": min_samples, "months": months, "category": category},
            "hotspots": spots}


@router.get("/infrastructure")
def get_infrastructure_points(asset_type: Optional[str] = None, ward_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(InfrastructureAsset)
    if asset_type:
        q = q.filter(InfrastructureAsset.asset_type == asset_type)
    if ward_id:
        q = q.filter(InfrastructureAsset.ward_id == ward_id)
    return [{"id": a.id, "uid": a.asset_uid, "name": a.name, "asset_type": a.asset_type, "subtype": a.subtype,
             "capacity": a.capacity, "unit": a.capacity_unit, "ward_id": a.ward_id, "latitude": a.latitude,
             "longitude": a.longitude, "provenance": a.provenance} for a in q.all()]


@public_router.get("/overlays/{name}")
def get_overlay(name: str):
    if "/" in name or "\\" in name or not name.startswith("overlay_") or not name.endswith(".png"):
        raise HTTPException(status_code=404, detail="Not found")
    path = os.path.join(SENTINEL_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Overlay not generated – run scripts.ingest.sentinel")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
