import math
from typing import Any, Dict, List, Optional

from shapely.geometry import Point, shape
from shapely.prepared import prep

_PREPARED: Dict[Any, Any] = {}


def _prepared(ward) -> Any:
    key = (getattr(ward, "id", None), id(ward.boundary_geojson))
    geom = _PREPARED.get(key)
    if geom is None:
        geom = prep(shape(ward.boundary_geojson))
        _PREPARED[key] = geom
    return geom


def point_in_geojson_polygon(lat: float, lng: float, geojson_geom: Dict[str, Any]) -> bool:
    try:
        return shape(geojson_geom).contains(Point(lng, lat))  # GeoJSON order is (lng, lat)
    except Exception:
        return False


def calculate_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_ward_for_point(lat: float, lng: float, wards: List[Any], max_snap_km: float = 1.0) -> Optional[Any]:
    """Ward whose polygon contains the point; points just outside (e.g. on the coastline) snap to the nearest
    ward centre within max_snap_km. Returns None for points outside the city."""
    if lat is None or lng is None:
        return None
    pt = Point(lng, lat)
    for ward in wards:
        if ward.boundary_geojson and _prepared(ward).contains(pt):
            return ward
    best, best_d = None, float("inf")
    for ward in wards:
        try:
            d = shape(ward.boundary_geojson).distance(pt) * 111.0  # degrees → ~km
        except Exception:
            continue
        if d < best_d:
            best, best_d = ward, d
    return best if best_d <= max_snap_km else None
