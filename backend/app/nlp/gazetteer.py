"""Place-name gazetteer built from OpenStreetMap (osm_gazetteer.json) plus ward codes and common aliases.

Used by NER (to tag locations) and the geocoder (to resolve them). Entries outside the 24 BMC wards are dropped.
"""
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from backend.app.core.config import settings

# Common abbreviations / alternate spellings used by residents → canonical OSM name
ALIASES = {
    "bkc": "Bandra Kurla Complex",
    "bandra kurla complex": "Bandra Kurla Complex",
    "sv road": "Swami Vivekanand Road",
    "s v road": "Swami Vivekanand Road",
    "s.v. road": "Swami Vivekanand Road",
    "weh": "Western Express Highway",
    "eeh": "Eastern Express Highway",
    "lbs marg": "Lal Bahadur Shastri Marg",
    "lbs road": "Lal Bahadur Shastri Marg",
    "jvlr": "Jogeshwari - Vikhroli Link Road",
    "cst": "Chhatrapati Shivaji Maharaj Terminus",
    "csmt": "Chhatrapati Shivaji Maharaj Terminus",
    "vt station": "Chhatrapati Shivaji Maharaj Terminus",
    "dadar tt": "Dadar",
    "sgnp": "Sanjay Gandhi National Park",
    "national park": "Sanjay Gandhi National Park",
    "marine drive": "Marine Drive",
    "juhu beach": "Juhu Beach",
}

# Generic words that should never be treated as a place on their own
STOPWORDS = {
    "road", "station", "market", "garden", "park", "hospital", "school", "college", "colony", "nagar", "lane", "street",
    "east", "west", "north", "south", "bridge", "chowk", "circle", "junction", "the", "main road", "city", "area",
    "gate", "society", "building", "office", "temple", "church", "mosque", "ground", "playground", "sector i",
    "police station", "bus stop", "bus depot", "fire station", "post office", "lake", "beach", "creek", "fort",
}

KIND_CONFIDENCE = {"STATION": 0.95, "PLACE": 0.9, "LANDMARK": 0.88, "ROAD": 0.75, "WARD": 0.97}


@dataclass
class GazetteerEntry:
    name: str
    kind: str
    lat: float
    lng: float
    ward_code: Optional[str]


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class Gazetteer:
    def __init__(self, entries: List[GazetteerEntry], ward_centroids: Dict[str, Tuple[float, float]]):
        self.by_key: Dict[str, GazetteerEntry] = {}
        for e in entries:
            key = _norm(e.name)
            if len(key) < 4 or key in STOPWORDS:
                continue
            # Prefer stations / places over landmarks / roads with the same name
            existing = self.by_key.get(key)
            if existing is None or KIND_CONFIDENCE[e.kind] > KIND_CONFIDENCE[existing.kind]:
                self.by_key[key] = e
            # "Andheri Station" → Andheri (station) for convenience
            if e.kind == "STATION":
                self.by_key.setdefault(f"{key} station", e)
                self.by_key.setdefault(f"{key} railway station", e)
        for alias, canonical in ALIASES.items():
            target = self.by_key.get(_norm(canonical))
            if target:
                self.by_key[_norm(alias)] = target
        self.ward_centroids = ward_centroids
        # Longest names first so "Bandra Kurla Complex" wins over "Bandra"
        keys = sorted(self.by_key, key=len, reverse=True)
        self._pattern = re.compile(r"(?<![\w])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w])", re.IGNORECASE) if keys else None

    def find_mentions(self, text: str) -> List[Tuple[int, int, GazetteerEntry]]:
        if not self._pattern:
            return []
        norm_text = re.sub(r"[^\w\s/]", " ", text.lower())  # same length as text → offsets preserved
        norm_text = re.sub(r"\s", " ", norm_text)
        out = []
        for m in self._pattern.finditer(norm_text):
            entry = self.by_key.get(re.sub(r"\s+", " ", m.group(1)).strip())
            if entry:
                out.append((m.start(1), m.end(1), entry))
        return out

    def lookup(self, query: str) -> Optional[GazetteerEntry]:
        key = _norm(query)
        key = re.sub(r"^(near|opposite|behind|at|in|on|outside|next to)\s+", "", key)
        if key in self.by_key:
            return self.by_key[key]
        for suffix in (" station", " railway station", " west", " east", " road", " area"):
            if key.endswith(suffix) and key[: -len(suffix)] in self.by_key:
                return self.by_key[key[: -len(suffix)]]
        return None


@lru_cache(maxsize=1)
def get_gazetteer() -> Gazetteer:
    entries: List[GazetteerEntry] = []
    centroids: Dict[str, Tuple[float, float]] = {}
    gz_path = os.path.join(settings.EXTERNAL_DATA_DIR, "osm_gazetteer.json")
    wards_path = os.path.join(settings.EXTERNAL_DATA_DIR, "mumbai_wards.geojson")
    if os.path.exists(gz_path):
        with open(gz_path, encoding="utf-8") as f:
            for e in json.load(f):
                if e.get("ward_code"):
                    entries.append(GazetteerEntry(e["name"], e["kind"], e["lat"], e["lng"], e["ward_code"]))
    if os.path.exists(wards_path):
        with open(wards_path, encoding="utf-8") as f:
            for feat in json.load(f)["features"]:
                p = feat["properties"]
                centroids[p["ward_code"]] = (p["center_lat"], p["center_lng"])
                for loc in p.get("localities", "").split(","):
                    loc = loc.strip()
                    if loc:  # OSM entries added earlier take precedence over these ward-centroid fallbacks
                        entries.append(GazetteerEntry(loc, "PLACE", p["center_lat"], p["center_lng"], p["ward_code"]))
    return Gazetteer(entries, centroids)
