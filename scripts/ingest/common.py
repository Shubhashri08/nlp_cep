"""Shared helpers for open-data ingestion: cached Overpass / HTTP access and geometry utilities."""
import json
import math
import os
import time
from typing import Any, Dict, Optional

import requests

from backend.app.core.config import settings

EXTERNAL_DIR = settings.EXTERNAL_DATA_DIR
USER_AGENT = settings.NOMINATIM_USER_AGENT

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# south, west, north, east
BBOX = tuple(settings.CITY_BBOX)
BBOX_STR = ",".join(str(v) for v in BBOX)


def external_path(*parts: str) -> str:
    path = os.path.join(EXTERNAL_DIR, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def overpass(query: str, cache_file: str, refresh: bool = False, attempts: int = 10) -> Dict[str, Any]:
    """Runs an Overpass QL query with on-disk caching, retries and mirror fallback."""
    path = external_path("osm", cache_file)
    if os.path.exists(path) and not refresh:
        return load_json(path)

    last_error: Optional[str] = None
    for attempt in range(attempts):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=400,
            )
            if resp.status_code == 200 and resp.text.lstrip().startswith("{"):
                data = resp.json()
                if data.get("remark") and "runtime error" in data["remark"]:
                    last_error = data["remark"]
                else:
                    save_json(path, data)
                    return data
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
        wait = min(60, 10 * (attempt + 1))
        print(f"  [overpass] {endpoint} failed ({(last_error or '').splitlines()[0][:80]}); retrying in {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(
        f"Overpass query for {cache_file} failed after {attempts} attempts: {last_error}. "
        f"Re-run later, or place a cached copy at {path}."
    )


def download(url: str, cache_rel_path: str, refresh: bool = False) -> str:
    path = external_path(*cache_rel_path.split("/"))
    if os.path.exists(path) and not refresh:
        return path
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


def geodesic_area_sq_km(geom) -> float:
    """Area of a lon/lat shapely geometry using a local equal-area (sinusoidal) projection.
    Accurate to well under 1% at city scale."""
    from shapely.ops import transform

    lat0 = geom.centroid.y
    k_lat = 110_574.0
    k_lon = 111_320.0

    def _proj(x, y, z=None):
        import numpy as np
        x = np.asarray(x)
        y = np.asarray(y)
        return x * k_lon * np.cos(np.radians(y)), y * k_lat

    projected = transform(_proj, geom)
    return abs(projected.area) / 1_000_000.0


def line_length_km(coords) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
