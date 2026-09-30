import re
from typing import List, Dict, Any, Optional

# Municipal Gazetters and patterns for Urban Planning NER
WARD_PATTERNS = [
    r'\b(?:ward|prabhag)\s*(?:no\.?|number)?\s*([a-zA-Z0-9\-]+)\b',
    r'\b(?:zone)\s*([0-9a-zA-Z\-]+)\b'
]

ROAD_PATTERNS = [
    r'\b([A-Z][a-zA-Z0-9\s\-]+(?:Road|Marg|Street|Avenue|Lane|Gali|Highway|Expressway|Flyover|Bypass|Chowk|Rasta))\b',
    r'\b([a-zA-Z0-9\-]+\s+(?:road|marg|street|highway|expressway|flyover|chowk|circle|junction|rasta))\b'
]

LANDMARK_PATTERNS = [
    r'\b([A-Z][a-zA-Z0-9\s\-]+(?:Station|Railway Station|Metro Station|Bus Stand|Depot|Hospital|School|College|Park|Garden|Lake|Bridge|Market|Mall|Mandir|Masjid|Church|Nagar|Colony|Layout|Sector\s*\d+))\b',
    r'\bnear\s+([A-Z][a-zA-Z0-9\s\-]+(?:\b|\.|\,))',
    r'\bopposite\s+([A-Z][a-zA-Z0-9\s\-]+(?:\b|\.|\,))',
    r'\bbehind\s+([A-Z][a-zA-Z0-9\s\-]+(?:\b|\.|\,))'
]

INFRASTRUCTURE_TERNS = [
    (r'\b(?:potholes?|pothole|crater|pavement|footpath|divider)\b', "ROAD_INFRA"),
    (r'\b(?:water\s*pipeline|tap\s*water|water\s*tanker|pipeline\s*leakage|nal)\b', "WATER_INFRA"),
    (r'\b(?:drain|drainage|sewer|manhole|storm\s*water\s*drain|gutter|naala)\b', "DRAINAGE_INFRA"),
    (r'\b(?:garbage\s*bin|dumping\s*ground|waste\s*collection|kachra\s*peti)\b', "WASTE_INFRA"),
    (r'\b(?:streetlight|light\s*pole|electric\s*pole|transformer|high\s*voltage\s*wire)\b', "ELECTRICAL_INFRA"),
    (r'\b(?:primary\s*health\s*center|dispensary|hospital|clinic|aspatal)\b', "HEALTH_INFRA"),
    (r'\b(?:government\s*school|municipal\s*school|high\s*school|library)\b', "EDU_INFRA"),
    (r'\b(?:bus\s*stop|bus\s*shelter|metro\s*station|traffic\s*signal)\b', "TRANSIT_INFRA")
]

INCIDENT_TERMS = [
    (r'\b(?:waterlogging|flooding|water\s*accumulation|submerged|paani\s*bhara)\b', "FLOODING_INCIDENT"),
    (r'\b(?:traffic\s*jam|gridlock|congestion|chakka\s*jam)\b', "TRAFFIC_INCIDENT"),
    (r'\b(?:leakage|burst|pipe\s*burst|water\s*contamination)\b', "LEAKAGE_INCIDENT"),
    (r'\b(?:overflowing|sewage\s*overflow|drain\s*blockage)\b', "DRAIN_OVERFLOW"),
    (r'\b(?:garbage\s*dump|foul\s*smell|stench|uncollected\s*waste)\b', "WASTE_ACCUMULATION"),
    (r'\b(?:sparking|wire\s*hanging|blackout|power\s*cut)\b', "ELECTRICAL_FAULT"),
    (r'\b(?:dengue\s*outbreak|malaria\s*risk|mosquito\s*breeding)\b', "HEALTH_HAZARD")
]

TEMPORAL_PATTERNS = [
    r'\b(?:every\s*monsoon|monsoon|during\s*rain|rainy\s*season)\b',
    r'\b(?:last\s*\d+\s*(?:days|weeks|months)|since\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday))\b',
    r'\b(?:morning|evening|night|rush\s*hours?|peak\s*hours?)\b'
]

ORGANIZATION_PATTERNS = [
    r'\b(?:BMC|BBMP|MCD|NDMC|PMC|TMC|MMRDA|BMRDA|Police|PWD|Traffic\s*Police|Electricity\s*Board|MSEDCL|BESCOM)\b'
]

def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extracts structured named entities from urban grievance/planning text.
    Returns: List of entities with text, label, confidence, start_char, end_char.
    """
    entities: List[Dict[str, Any]] = []
    seen_spans = set()
    
    # 1. Wards
    for pattern in WARD_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": "WARD",
                    "confidence": 0.95,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)
                
    # 2. Roads
    for pattern in ROAD_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": "ROAD",
                    "confidence": 0.90,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)
                
    # 3. Landmarks & Specific Locations
    for pattern in LANDMARK_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(1).strip() if match.groups() else match.group(0).strip(),
                    "label": "LOCATION_LANDMARK",
                    "confidence": 0.88,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)

    # 4. Infrastructure Types
    for pattern, label in INFRASTRUCTURE_TERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": label,
                    "confidence": 0.92,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)
                
    # 5. Incident Types
    for pattern, label in INCIDENT_TERMS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": label,
                    "confidence": 0.91,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)

    # 6. Temporal References
    for pattern in TEMPORAL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": "TEMPORAL",
                    "confidence": 0.85,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)

    # 7. Organizations
    for pattern in ORGANIZATION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            if span not in seen_spans:
                entities.append({
                    "text": match.group(0).strip(),
                    "label": "ORGANIZATION",
                    "confidence": 0.98,
                    "start_char": span[0],
                    "end_char": span[1]
                })
                seen_spans.add(span)
                
    return sorted(entities, key=lambda x: x.get("start_char", 0))
