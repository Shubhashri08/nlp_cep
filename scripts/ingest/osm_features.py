"""OpenStreetMap features for Greater Mumbai, aggregated to BMC wards.

Produces (backend/data/external/):
  osm_assets.json        – amenities / transit / utility points assigned to wards
  osm_ward_stats.json    – per-ward road km by class, building count (computed server-side by Overpass)
  osm_landuse.json       – per-ward land-use area shares from landuse/leisure/natural polygons
  osm_gazetteer.json     – place names (suburbs, neighbourhoods, stations, named roads) with coordinates
Raw Overpass responses are cached under external/osm/ (not committed; see .gitignore).
"""
from collections import defaultdict
from typing import Dict, List, Optional

from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import linemerge, polygonize, unary_union
from shapely.strtree import STRtree

from scripts.ingest.common import (
    BBOX_STR, external_path, geodesic_area_sq_km, load_json, overpass, save_json,
)

ROAD_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"]

POI_QUERY = f"""
[out:json][timeout:300];
(
  nwr["amenity"~"^(hospital|clinic|doctors|school|college|university|fire_station|police|library|waste_transfer_station|recycling|toilets)$"]({BBOX_STR});
  node["highway"="bus_stop"]({BBOX_STR});
  nwr["railway"="station"]({BBOX_STR});
  nwr["station"="subway"]({BBOX_STR});
  nwr["man_made"~"^(water_tower|water_works|wastewater_plant|reservoir_covered|pumping_station)$"]({BBOX_STR});
  nwr["leisure"~"^(park|playground|sports_centre)$"]["name"]({BBOX_STR});
);
out center tags;
"""

LANDUSE_QUERY = f"""
[out:json][timeout:300];
(
  way["landuse"]({BBOX_STR});
  rel["landuse"]({BBOX_STR});
  way["leisure"~"^(park|garden|golf_course|nature_reserve|pitch|recreation_ground)$"]({BBOX_STR});
  way["natural"~"^(wood|scrub|wetland|water|grassland|mangrove)$"]({BBOX_STR});
  rel["natural"~"^(wood|wetland|water)$"]({BBOX_STR});
  rel["leisure"~"^(park|nature_reserve)$"]({BBOX_STR});
);
out geom;
"""

GAZETTEER_QUERY = f"""
[out:json][timeout:240];
(
  node["place"~"^(suburb|neighbourhood|quarter|locality|village)$"]["name"]({BBOX_STR});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]["name"]({BBOX_STR});
  nwr["railway"="station"]["name"]({BBOX_STR});
  nwr["amenity"~"^(hospital|college|university|marketplace)$"]["name"]({BBOX_STR});
  nwr["tourism"~"^(attraction|museum)$"]["name"]({BBOX_STR});
  nwr["shop"="mall"]["name"]({BBOX_STR});
  nwr["leisure"="park"]["name"]({BBOX_STR});
  nwr["natural"~"^(water|beach|peak)$"]["name"]({BBOX_STR});
);
out center tags;
"""


def _ward_stats_query(relation_id: int) -> str:
    road_re = "|".join(ROAD_CLASSES)
    return f"""
[out:json][timeout:300];
rel({relation_id});
foreach -> .w (
  .w map_to_area -> .a;
  way(area.a)["highway"~"^({road_re})$"] -> .r;
  for.r (t["highway"]) {{ make stat highway=_.val, km=sum(length())/1000; out; }}
  way(area.a)["building"];
  make stat buildings=count(ways); out;
);
"""


# ---- classification of POIs into planning asset types ---------------------------------------
def classify_poi(tags: Dict[str, str]) -> Optional[tuple]:
    amenity = tags.get("amenity")
    if amenity in ("hospital",):
        return "HEALTHCARE", "hospital"
    if amenity in ("clinic", "doctors"):
        return "HEALTHCARE", "clinic"
    if amenity == "school":
        return "EDUCATION", "school"
    if amenity in ("college", "university"):
        return "EDUCATION", amenity
    if amenity == "library":
        return "EDUCATION", "library"
    if amenity == "fire_station":
        return "EMERGENCY", "fire_station"
    if amenity == "police":
        return "PUBLIC_SAFETY", "police"
    if amenity in ("waste_transfer_station", "recycling"):
        return "WASTE_MANAGEMENT", amenity
    if amenity == "toilets":
        return "SANITATION", "public_toilet"
    if tags.get("highway") == "bus_stop":
        return "BUS_STOP", "bus_stop"
    if tags.get("station") == "subway" or tags.get("subway") == "yes":
        return "METRO_STATION", "metro"
    if tags.get("railway") == "station":
        if tags.get("station") in ("light_rail", "monorail"):
            return "METRO_STATION", tags.get("station")
        return "RAIL_STATION", "suburban_rail"
    mm = tags.get("man_made")
    if mm in ("water_tower", "water_works", "reservoir_covered", "pumping_station"):
        return "WATER_SUPPLY", mm
    if mm == "wastewater_plant":
        return "DRAINAGE", "wastewater_plant"
    if tags.get("leisure") in ("park", "playground", "sports_centre"):
        return "PARKS", tags["leisure"]
    return None


def _center(el) -> Optional[tuple]:
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    c = el.get("center")
    if c:
        return c["lat"], c["lon"]
    return None


class WardIndex:
    def __init__(self, wards_fc: dict):
        self.codes = [f["properties"]["ward_code"] for f in wards_fc["features"]]
        self.geoms = [shape(f["geometry"]) for f in wards_fc["features"]]
        self.tree = STRtree(self.geoms)

    def locate(self, lat: float, lon: float) -> Optional[str]:
        pt = Point(lon, lat)
        for idx in self.tree.query(pt):
            if self.geoms[idx].contains(pt):
                return self.codes[idx]
        return None


def build_assets(wards_fc: dict, refresh: bool = False) -> List[dict]:
    data = overpass(POI_QUERY, "pois_raw.json", refresh=refresh)
    index = WardIndex(wards_fc)
    seen = set()
    assets = []
    for el in data["elements"]:
        tags = el.get("tags", {})
        cls = classify_poi(tags)
        loc = _center(el)
        if not cls or not loc:
            continue
        ward = index.locate(*loc)
        if not ward:
            continue
        uid = f"{el['type'][0]}{el['id']}"
        if uid in seen:
            continue
        seen.add(uid)
        beds = tags.get("beds") or tags.get("capacity:beds")
        assets.append({
            "osm_id": uid,
            "name": tags.get("name") or tags.get("name:en") or f"Unnamed {cls[1].replace('_', ' ')}",
            "asset_type": cls[0],
            "subtype": cls[1],
            "ward_code": ward,
            "lat": round(loc[0], 6),
            "lng": round(loc[1], 6),
            "beds": int(beds) if beds and str(beds).isdigit() else None,
            "operator": tags.get("operator"),
        })
    save_json(external_path("osm_assets.json"), assets)
    counts = defaultdict(int)
    for a in assets:
        counts[a["asset_type"]] += 1
    print(f"  [features] {len(assets)} assets: {dict(counts)}")
    return assets


def build_ward_stats(wards_fc: dict, refresh: bool = False) -> Dict[str, dict]:
    stats = {}
    for f in wards_fc["features"]:
        p = f["properties"]
        code = p["ward_code"]
        cache = f"ward_stats_{code.replace('/', '_')}.json"
        data = overpass(_ward_stats_query(p["osm_relation_id"]), cache, refresh=refresh)
        roads = {}
        buildings = 0
        for el in data["elements"]:
            t = el.get("tags", {})
            if "highway" in t:
                roads[t["highway"]] = round(float(t["km"]), 2)
            if "buildings" in t:
                buildings = int(t["buildings"])
        stats[code] = {"road_km_by_class": roads, "road_km_total": round(sum(roads.values()), 2), "buildings": buildings}
        print(f"  [features] {code}: {stats[code]['road_km_total']} road-km, {buildings} buildings")
    save_json(external_path("osm_ward_stats.json"), stats)
    return stats


LANDUSE_BUCKETS = {
    "residential": "residential",
    "commercial": "commercial", "retail": "commercial", "office": "commercial",
    "industrial": "industrial", "port": "industrial", "railway": "industrial", "depot": "industrial", "garages": "industrial",
    "farmland": "agricultural", "farmyard": "agricultural", "orchard": "agricultural", "meadow": "agricultural", "plant_nursery": "agricultural",
    "forest": "green", "grass": "green", "recreation_ground": "green", "village_green": "green", "cemetery": "green",
    "park": "green", "garden": "green", "golf_course": "green", "nature_reserve": "green", "pitch": "green",
    "wood": "green", "scrub": "green", "grassland": "green", "wetland": "green", "mangrove": "green",
    "basin": "water", "reservoir": "water", "water": "water", "salt_pond": "water",
    "construction": "mixed", "brownfield": "mixed", "greenfield": "mixed", "education": "mixed",
    "institutional": "mixed", "military": "mixed", "religious": "mixed", "landfill": "industrial",
}


def _landuse_bucket(tags: Dict[str, str]) -> Optional[str]:
    for key in ("landuse", "leisure", "natural"):
        v = tags.get(key)
        if v and v in LANDUSE_BUCKETS:
            return LANDUSE_BUCKETS[v]
    return None


def _el_polygon(el):
    try:
        if el["type"] == "way" and el.get("geometry"):
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                return Polygon(coords).buffer(0)
        elif el["type"] == "relation":
            outers = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                      for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
            polys = list(polygonize(linemerge(unary_union(outers)))) if outers else []
            return unary_union(polys).buffer(0) if polys else None
    except Exception:
        return None
    return None


def build_landuse(wards_fc: dict, refresh: bool = False) -> Dict[str, dict]:
    data = overpass(LANDUSE_QUERY, "landuse_raw.json", refresh=refresh)
    buckets = defaultdict(list)
    for el in data["elements"]:
        b = _landuse_bucket(el.get("tags", {}))
        if not b:
            continue
        poly = _el_polygon(el)
        if poly is not None and not poly.is_empty:
            buckets[b].append(poly)
    merged = {b: unary_union(polys) for b, polys in buckets.items()}

    result = {}
    for f in wards_fc["features"]:
        code = f["properties"]["ward_code"]
        ward_geom = shape(f["geometry"])
        ward_area = geodesic_area_sq_km(ward_geom)
        shares = {}
        claimed = None
        # Water and green take precedence over urban uses where polygons overlap
        for b in ["water", "green", "industrial", "commercial", "residential", "agricultural", "mixed"]:
            if b not in merged:
                shares[b] = 0.0
                continue
            part = merged[b].intersection(ward_geom)
            if claimed is not None and not part.is_empty:
                part = part.difference(claimed)
            area = geodesic_area_sq_km(part) if not part.is_empty else 0.0
            shares[b] = round(100.0 * area / ward_area, 2)
            if not part.is_empty:
                claimed = part if claimed is None else unary_union([claimed, part])
        shares["unmapped"] = round(max(0.0, 100.0 - sum(shares.values())), 2)
        result[code] = shares
    save_json(external_path("osm_landuse.json"), result)
    print(f"  [features] land use shares computed for {len(result)} wards")
    return result


def build_gazetteer(wards_fc: dict, refresh: bool = False) -> List[dict]:
    data = overpass(GAZETTEER_QUERY, "gazetteer_raw.json", refresh=refresh)
    index = WardIndex(wards_fc)
    entries: Dict[str, dict] = {}
    for el in data["elements"]:
        tags = el.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        loc = _center(el)
        if not name or not loc or len(name) < 3:
            continue
        if not all(ord(ch) < 128 for ch in name):
            continue
        if tags.get("place"):
            kind = "PLACE"
        elif tags.get("highway"):
            kind = "ROAD"
        elif tags.get("railway") == "station":
            kind = "STATION"
        else:
            kind = "LANDMARK"
        key = name.lower().strip()
        # Roads are split into many ways; keep the first occurrence as the representative point
        if key in entries and not (entries[key]["kind"] == "ROAD" and kind != "ROAD"):
            continue
        entries[key] = {
            "name": name,
            "kind": kind,
            "lat": round(loc[0], 6),
            "lng": round(loc[1], 6),
            "ward_code": index.locate(*loc),
        }
    out = sorted(entries.values(), key=lambda e: e["name"])
    save_json(external_path("osm_gazetteer.json"), out)
    print(f"  [features] gazetteer: {len(out)} named places")
    return out


def run_all(refresh: bool = False):
    wards_fc = load_json(external_path("mumbai_wards.geojson"))
    build_assets(wards_fc, refresh)
    build_gazetteer(wards_fc, refresh)
    build_ward_stats(wards_fc, refresh)
    build_landuse(wards_fc, refresh)


if __name__ == "__main__":
    run_all()
