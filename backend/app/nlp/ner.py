"""Named Entity Recognition for urban grievance and planning text.

Hybrid approach:
  1. Gazetteer matching against ~3,700 OpenStreetMap place / road / station / landmark names in Greater Mumbai
     (longest match, case-insensitive) – labels LOCATION / ROAD / STATION / LANDMARK.
  2. Tight surface patterns for ward references ("Ward H/E", "K-West ward"), unseen road names
     (1–4 capitalised tokens + Road/Marg/…), and landmarks introduced by "near/opposite/behind".
  3. Domain lexicons for infrastructure objects, incident types, temporal expressions and organisations.
Overlapping spans are resolved by preferring gazetteer matches, then longer spans.
Confidence reflects the evidence type (gazetteer > pattern > lexicon), not a learned probability.
"""
import re
from typing import Any, Dict, List

from backend.app.nlp.gazetteer import KIND_CONFIDENCE, get_gazetteer
from backend.app.nlp.lexicon import MUNICIPAL_ORGS

WARD_CODE = r"(?:A|B|C|D|E|F[/\- ]?(?:N|S|North|South)|G[/\- ]?(?:N|S|North|South)|H[/\- ]?(?:E|W|East|West)|K[/\- ]?(?:E|W|East|West)|L|M[/\- ]?(?:E|W|East|West)|N|P[/\- ]?(?:N|S|North|South)|R[/\- ]?(?:N|S|C|North|South|Central)|S|T)"
WARD_PATTERNS = [
    re.compile(r"\bward\s+(?:no\.?\s*)?" + WARD_CODE + r"(?![\w/])", re.IGNORECASE),
    re.compile(r"\b" + WARD_CODE + r"\s+ward\b", re.IGNORECASE),
    re.compile(r"\bprabhag\s+(?:kramank\s+)?\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bward\s+(?:no\.?\s*)?\d{1,3}\b", re.IGNORECASE),
]
_CAP = r"[A-Z][a-zA-Z.'\-]*"
ROAD_PATTERN = re.compile(rf"\b((?:{_CAP}\s+){{0,3}}{_CAP}\s+(?:Road|Rd|Marg|Street|St|Lane|Path|Highway|Expressway|Flyover|Bypass|Chowk|Circle|Junction|Naka))\b")
LANDMARK_SUFFIX = re.compile(rf"\b((?:{_CAP}\s+){{0,3}}{_CAP}\s+(?:Station|Hospital|School|College|Market|Garden|Park|Lake|Bridge|Mall|Nagar|Colony|Chawl|Society|Depot|Temple|Mandir|Masjid|Church|Talao|Maidan))\b")
PREPOSITION_LANDMARK = re.compile(rf"\b(?:near|opposite|opp\.?|behind|outside|next to)\s+((?:{_CAP}\s*){{1,4}})")

INFRASTRUCTURE_TERMS = [
    (r"\b(?:potholes?|craters?|pavement|footpath|road\s*divider|speed\s*breaker|manhole\s*cover)\b", "ROAD_INFRA"),
    (r"\b(?:water\s*pipeline|pipeline|water\s*main|tap|water\s*tanker|tanker|water\s*meter|nal|tanki)\b", "WATER_INFRA"),
    (r"\b(?:drains?|drainage|sewer(?:\s*line)?|sewage\s*line|manhole|storm\s*water\s*drain|gutter|nullah|naala|nala|gatar|culvert)\b", "DRAINAGE_INFRA"),
    (r"\b(?:garbage\s*bins?|dustbins?|dumping\s*ground|waste\s*collection|kachra\s*peti|compost\w*|transfer\s*station)\b", "WASTE_INFRA"),
    (r"\b(?:streetlights?|street\s*lights?|light\s*poles?|electric\s*poles?|transformers?|high\s*voltage\s*wires?|cables?)\b", "ELECTRICAL_INFRA"),
    (r"\b(?:health\s*(?:post|centre|center)|dispensary|hospital|clinic|maternity\s*ward|ambulance|aspatal|dawaakhana)\b", "HEALTH_INFRA"),
    (r"\b(?:municipal\s*school|government\s*school|high\s*school|school|anganwadi|library|classrooms?)\b", "EDU_INFRA"),
    (r"\b(?:bus\s*stops?|bus\s*shelters?|metro\s*station|railway\s*station|foot\s*over\s*bridge|skywalk|traffic\s*signal|subway|underpass|flyover)\b", "TRANSIT_INFRA"),
    (r"\b(?:garden|playground|jogging\s*track|open\s*space|swings?)\b", "PARK_INFRA"),
]
INCIDENT_TERMS = [
    (r"\b(?:waterlogg?ing|waterlogged|flood(?:ing|ed)?|water\s*accumulation|submerged|inundat\w+|paani\s*bhara|pani\s*bharla)\b", "FLOODING_INCIDENT"),
    (r"\b(?:traffic\s*jam|gridlock|congestion|chakka\s*jam|traffic\s*jaam)\b", "TRAFFIC_INCIDENT"),
    (r"\b(?:leak(?:age|ing)?|burst|pipe\s*burst|contaminat\w+|ganda\s*pani)\b", "LEAKAGE_INCIDENT"),
    (r"\b(?:overflow(?:ing)?|sewage\s*overflow|block(?:ed|age)|choked|clogged)\b", "BLOCKAGE_INCIDENT"),
    (r"\b(?:garbage\s*dump(?:ing)?|foul\s*smell|stench|uncollected|durgandhi|badbu)\b", "WASTE_ACCUMULATION"),
    (r"\b(?:sparking|wires?\s*hanging|blackout|power\s*cuts?|outage|short\s*circuit)\b", "ELECTRICAL_FAULT"),
    (r"\b(?:dengue|malaria|mosquito\s*breeding|leptospirosis|outbreak)\b", "HEALTH_HAZARD"),
    (r"\b(?:collapse|dilapidated|cracks?|landslide)\b", "STRUCTURAL_RISK"),
    (r"\b(?:tree\s*cutting|dumping|effluent|encroach\w+)\b", "ENVIRONMENTAL_VIOLATION"),
]
TEMPORAL_TERMS = [
    r"\b(?:every|each|during)\s+monsoon\b", r"\bmonsoon\b", r"\bduring\s+(?:the\s+)?rains?\b",
    r"\b(?:for\s+)?(?:the\s+)?last\s+\d+\s+(?:days?|weeks?|months?|years?)\b",
    r"\b\d+\s+(?:days?|weeks?|months?)\b",
    r"\bsince\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|last\s+week|last\s+month|\d{4})\b",
    r"\b(?:every|at)\s+night\b", r"\b(?:rush|peak)\s+hours?\b", r"\bmorning\b", r"\bevening\b",
    r"\b(?:19|20)\d{2}\b",
]
ORG_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(o) for o in sorted(MUNICIPAL_ORGS, key=len, reverse=True)) + r")\b")

_COMPILED_INFRA = [(re.compile(p, re.IGNORECASE), l) for p, l in INFRASTRUCTURE_TERMS]
_COMPILED_INCIDENT = [(re.compile(p, re.IGNORECASE), l) for p, l in INCIDENT_TERMS]
_COMPILED_TEMPORAL = [re.compile(p, re.IGNORECASE) for p in TEMPORAL_TERMS]

LOCATION_LABELS = {"WARD", "LOCATION", "ROAD", "STATION", "LANDMARK"}
_GAZ_LABEL = {"PLACE": "LOCATION", "ROAD": "ROAD", "STATION": "STATION", "LANDMARK": "LANDMARK"}


def _entity(text, label, conf, start, end, source, **extra) -> Dict[str, Any]:
    d = {"text": text, "label": label, "confidence": conf, "start_char": start, "end_char": end, "source": source}
    d.update(extra)
    return d


def normalize_ward_code(raw: str) -> str:
    s = raw.upper().replace("WARD", "").replace("NO.", "").strip()
    s = re.sub(r"[\s\-]+", "/", s).strip("/")
    for full, short in (("NORTH", "N"), ("SOUTH", "S"), ("EAST", "E"), ("WEST", "W"), ("CENTRAL", "C")):
        s = s.replace(full, short)
    return s.replace("//", "/")


def extract_entities(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    candidates: List[Dict[str, Any]] = []

    # 1. Gazetteer (OSM)
    for start, end, entry in get_gazetteer().find_mentions(text):
        candidates.append(_entity(text[start:end], _GAZ_LABEL.get(entry.kind, "LOCATION"), KIND_CONFIDENCE[entry.kind],
                                  start, end, "gazetteer", lat=entry.lat, lng=entry.lng, ward_code=entry.ward_code))
    # 2. Patterns
    for pat in WARD_PATTERNS:
        for m in pat.finditer(text):
            code = normalize_ward_code(m.group(0))
            candidates.append(_entity(m.group(0).strip(), "WARD", 0.93, m.start(), m.end(), "pattern", ward_code=code))
    for m in ROAD_PATTERN.finditer(text):
        candidates.append(_entity(m.group(1), "ROAD", 0.7, m.start(1), m.end(1), "pattern"))
    for m in LANDMARK_SUFFIX.finditer(text):
        candidates.append(_entity(m.group(1), "LANDMARK", 0.68, m.start(1), m.end(1), "pattern"))
    for m in PREPOSITION_LANDMARK.finditer(text):
        span = m.group(1).strip()
        if span.split()[0].lower() not in {"the", "our", "my", "a", "this"}:
            candidates.append(_entity(span, "LANDMARK", 0.6, m.start(1), m.start(1) + len(span), "pattern"))
    # 3. Lexicons
    for pat, label in _COMPILED_INFRA:
        for m in pat.finditer(text):
            candidates.append(_entity(m.group(0), label, 0.85, m.start(), m.end(), "lexicon"))
    for pat, label in _COMPILED_INCIDENT:
        for m in pat.finditer(text):
            candidates.append(_entity(m.group(0), label, 0.85, m.start(), m.end(), "lexicon"))
    for pat in _COMPILED_TEMPORAL:
        for m in pat.finditer(text):
            candidates.append(_entity(m.group(0), "TEMPORAL", 0.8, m.start(), m.end(), "lexicon"))
    for m in ORG_PATTERN.finditer(text):
        candidates.append(_entity(m.group(0), "ORGANIZATION", 0.95, m.start(), m.end(), "lexicon"))

    # Overlap resolution: locations from the gazetteer first, then longer spans, then higher confidence
    priority = {"gazetteer": 0, "pattern": 1, "lexicon": 2}
    candidates.sort(key=lambda e: (priority[e["source"]], -(e["end_char"] - e["start_char"]), -e["confidence"]))
    taken: List[Dict[str, Any]] = []
    for c in candidates:
        if not any(c["start_char"] < t["end_char"] and t["start_char"] < c["end_char"] for t in taken):
            taken.append(c)
    return sorted(taken, key=lambda e: e["start_char"])


def location_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Location-type entities ordered by specificity (station/landmark > road > place > ward)."""
    rank = {"STATION": 0, "LANDMARK": 1, "ROAD": 2, "LOCATION": 3, "WARD": 4}
    locs = [e for e in entities if e["label"] in LOCATION_LABELS]
    return sorted(locs, key=lambda e: (rank[e["label"]], -e["confidence"]))
