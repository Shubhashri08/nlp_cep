from typing import Optional, List, Dict, Any, Tuple
from shapely.geometry import shape, Point, Polygon, MultiPolygon
import math

def point_in_geojson_polygon(lat: float, lng: float, geojson_geom: Dict[str, Any]) -> bool:
    """Checks if a (lat, lng) point falls within a GeoJSON Polygon or MultiPolygon."""
    try:
        geom = shape(geojson_geom)
        pt = Point(lng, lat)  # Note GeoJSON is (x=longitude, y=latitude)
        return geom.contains(pt)
    except Exception:
        return False

def calculate_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_ward_for_point(lat: float, lng: float, wards: List[Any]) -> Optional[Any]:
    """Finds the containing Ward object for a given latitude and longitude coordinate."""
    pt = Point(lng, lat)
    # Check polygon containment
    for ward in wards:
        if ward.boundary_geojson:
            try:
                poly = shape(ward.boundary_geojson)
                if poly.contains(pt):
                    return ward
            except Exception:
                pass
                
    # Fallback to nearest ward center if slightly outside boundary
    closest_ward = None
    min_dist = float("inf")
    for ward in wards:
        dist = calculate_haversine_distance_km(lat, lng, ward.center_lat, ward.center_lng)
        if dist < min_dist:
            min_dist = dist
            closest_ward = ward
            
    if min_dist < 10.0:  # Within 10km
        return closest_ward
    return None
