"""Fetch the 24 BMC (Greater Mumbai) administrative ward boundaries from OpenStreetMap.

OSM models BMC wards as boundary=administrative, admin_level=10 relations ("A Ward", "H/E Ward", ...).
Relation member ways are assembled into (Multi)Polygons with shapely.
Output: backend/data/external/mumbai_wards.geojson
"""
from typing import Dict, List

from shapely.geometry import LineString, MultiPolygon, Polygon, mapping
from shapely.ops import linemerge, polygonize, unary_union

from scripts.ingest.common import BBOX_STR, external_path, geodesic_area_sq_km, overpass, save_json

# BMC administrative zones (Zones I–VII) and commonly known localities per ward.
WARD_META: Dict[str, Dict[str, str]] = {
    "A": {"zone": "Zone I (City South)", "localities": "Colaba, Fort, Churchgate, Nariman Point"},
    "B": {"zone": "Zone I (City South)", "localities": "Dongri, Masjid Bunder, Sandhurst Road"},
    "C": {"zone": "Zone I (City South)", "localities": "Marine Lines, Bhuleshwar, Kalbadevi"},
    "D": {"zone": "Zone I (City South)", "localities": "Grant Road, Malabar Hill, Tardeo"},
    "E": {"zone": "Zone I (City South)", "localities": "Byculla, Mazgaon, Agripada"},
    "F/N": {"zone": "Zone II (City Central)", "localities": "Matunga, Sion, Wadala"},
    "F/S": {"zone": "Zone II (City Central)", "localities": "Parel, Sewri, Lalbaug"},
    "G/N": {"zone": "Zone II (City Central)", "localities": "Dadar, Mahim, Dharavi"},
    "G/S": {"zone": "Zone II (City Central)", "localities": "Worli, Prabhadevi, Lower Parel"},
    "H/E": {"zone": "Zone III (Western Suburbs South)", "localities": "Bandra East, Santacruz East, Khar East"},
    "H/W": {"zone": "Zone III (Western Suburbs South)", "localities": "Bandra West, Khar West, Santacruz West"},
    "K/E": {"zone": "Zone III (Western Suburbs South)", "localities": "Andheri East, Jogeshwari East, Vile Parle East"},
    "K/W": {"zone": "Zone IV (Western Suburbs Central)", "localities": "Andheri West, Juhu, Vile Parle West"},
    "P/S": {"zone": "Zone IV (Western Suburbs Central)", "localities": "Goregaon"},
    "P/N": {"zone": "Zone IV (Western Suburbs Central)", "localities": "Malad"},
    "L": {"zone": "Zone V (Eastern Suburbs South)", "localities": "Kurla, Sakinaka, Chandivali"},
    "M/E": {"zone": "Zone V (Eastern Suburbs South)", "localities": "Govandi, Mankhurd, Deonar, Trombay"},
    "M/W": {"zone": "Zone V (Eastern Suburbs South)", "localities": "Chembur, Tilak Nagar"},
    "N": {"zone": "Zone VI (Eastern Suburbs North)", "localities": "Ghatkopar, Vikhroli"},
    "S": {"zone": "Zone VI (Eastern Suburbs North)", "localities": "Bhandup, Powai, Kanjurmarg"},
    "T": {"zone": "Zone VI (Eastern Suburbs North)", "localities": "Mulund"},
    "R/S": {"zone": "Zone VII (Western Suburbs North)", "localities": "Kandivali"},
    "R/C": {"zone": "Zone VII (Western Suburbs North)", "localities": "Borivali"},
    "R/N": {"zone": "Zone VII (Western Suburbs North)", "localities": "Dahisar"},
}

QUERY = f"""
[out:json][timeout:240];
rel["boundary"="administrative"]["admin_level"="10"]({BBOX_STR});
out geom;
"""


def _assemble(members: List[dict]):
    outers, inners = [], []
    for m in members:
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        line = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        (inners if m.get("role") == "inner" else outers).append(line)
    polys = list(polygonize(linemerge(unary_union(outers))))
    if not polys:
        return None
    geom = unary_union(polys)
    if inners:
        holes = list(polygonize(linemerge(unary_union(inners))))
        if holes:
            geom = geom.difference(unary_union(holes))
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom


def ward_code_from_name(name: str) -> str:
    return name.replace("Ward", "").strip()


def fetch_ward_boundaries(refresh: bool = False) -> dict:
    data = overpass(QUERY, "wards_admin10.json", refresh=refresh)
    features = []
    for el in data["elements"]:
        name = el.get("tags", {}).get("name", "")
        code = ward_code_from_name(name)
        if code not in WARD_META:
            continue
        geom = _assemble(el.get("members", []))
        if geom is None or geom.is_empty:
            print(f"  [boundaries] could not assemble polygon for {name}")
            continue
        if isinstance(geom, Polygon):
            geom = MultiPolygon([geom]) if False else geom
        centroid = geom.representative_point()
        features.append({
            "type": "Feature",
            "properties": {
                "ward_code": code,
                "name": f"{code} Ward",
                "zone": WARD_META[code]["zone"],
                "localities": WARD_META[code]["localities"],
                "osm_relation_id": el["id"],
                "area_sq_km": round(geodesic_area_sq_km(geom), 3),
                "center_lat": round(centroid.y, 6),
                "center_lng": round(centroid.x, 6),
            },
            "geometry": mapping(geom.simplify(0.00005, preserve_topology=True)),
        })
    missing = set(WARD_META) - {f["properties"]["ward_code"] for f in features}
    if missing:
        print(f"  [boundaries] WARNING: missing wards from OSM: {sorted(missing)}")
    fc = {"type": "FeatureCollection", "features": sorted(features, key=lambda f: f["properties"]["ward_code"])}
    save_json(external_path("mumbai_wards.geojson"), fc)
    print(f"  [boundaries] {len(features)} ward polygons written")
    return fc


if __name__ == "__main__":
    fetch_ward_boundaries()
