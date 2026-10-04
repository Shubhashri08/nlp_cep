"""Location resolution: OSM gazetteer first, then bounded Nominatim (with DB cache). Never guesses coordinates."""
import logging
from typing import Any, Dict, Optional

import requests

from backend.app.core.config import settings
from backend.app.nlp.gazetteer import KIND_CONFIDENCE, get_gazetteer

logger = logging.getLogger("urban_planning_dss")

SOUTH, WEST, NORTH, EAST = settings.CITY_BBOX


def in_study_area(lat: Optional[float], lng: Optional[float]) -> bool:
    return lat is not None and lng is not None and SOUTH <= lat <= NORTH and WEST <= lng <= EAST


def _result(lat=None, lng=None, conf=0.0, address=None, method="NONE", ward_code=None) -> Dict[str, Any]:
    return {"lat": lat, "lng": lng, "confidence": conf, "address": address, "method": method,
            "resolved": lat is not None, "ward_code": ward_code}


def _nominatim(query: str) -> Optional[Dict[str, Any]]:
    params = {
        "q": f"{query}, {settings.CITY_NAME}",
        "format": "json",
        "limit": 1,
        "viewbox": f"{WEST},{NORTH},{EAST},{SOUTH}",
        "bounded": 1,
        "countrycodes": "in",
    }
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", params=params,
                            headers={"User-Agent": settings.NOMINATIM_USER_AGENT}, timeout=4.0)
        if resp.status_code == 200 and resp.json():
            hit = resp.json()[0]
            lat, lng = float(hit["lat"]), float(hit["lon"])
            if in_study_area(lat, lng):
                importance = float(hit.get("importance") or 0.3)
                return _result(lat, lng, round(min(0.8, 0.5 + importance / 2), 2), hit.get("display_name"), "NOMINATIM")
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.info("Nominatim lookup failed for %r: %s", query, exc)
    return None


def resolve_location(raw_text: str, db=None, allow_network: Optional[bool] = None) -> Dict[str, Any]:
    """Resolves a location phrase to coordinates inside the study area.
    Order: OSM gazetteer → cached lookup (geocode_cache table) → Nominatim (bounded to the city bbox)."""
    if not raw_text or not raw_text.strip():
        return _result()
    gaz = get_gazetteer()
    entry = gaz.lookup(raw_text)
    if entry:
        return _result(entry.lat, entry.lng, KIND_CONFIDENCE[entry.kind], f"{entry.name}, {settings.CITY_NAME}",
                       "GAZETTEER", entry.ward_code)

    key = raw_text.lower().strip()[:250]
    if db is not None:
        from backend.app.models.entities import GeocodeCacheEntry
        cached = db.query(GeocodeCacheEntry).filter(GeocodeCacheEntry.query == key).first()
        if cached:
            if cached.latitude is None:
                return _result()
            return _result(cached.latitude, cached.longitude, cached.confidence, cached.address, cached.method + "_CACHED")

    allow = settings.NOMINATIM_ENABLED if allow_network is None else allow_network
    res = _nominatim(raw_text) if allow else None
    if db is not None and allow:
        from backend.app.models.entities import GeocodeCacheEntry
        db.add(GeocodeCacheEntry(query=key, latitude=res["lat"] if res else None, longitude=res["lng"] if res else None,
                                 confidence=res["confidence"] if res else 0.0, address=res["address"] if res else None,
                                 method="NOMINATIM" if res else "NONE"))
        db.flush()
    return res or _result()
