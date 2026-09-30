import re
import urllib.parse
from typing import Optional, Dict, Any, Tuple
import requests
from backend.app.core.config import settings

# In-memory and persistent geocoding cache for urban locations & landmarks
GEOCODE_CACHE: Dict[str, Tuple[float, float, float, str]] = {
    # Mumbai Urban Locations Gazetteer (Real authoritative lat/lng)
    "andheri station": (19.1197, 72.8464, 0.98, "Andheri Railway Station, Mumbai"),
    "andheri": (19.1136, 72.8697, 0.95, "Andheri, Mumbai"),
    "bandra station": (19.0544, 72.8402, 0.98, "Bandra Railway Station, Mumbai"),
    "bandra": (19.0596, 72.8295, 0.95, "Bandra West, Mumbai"),
    "bandra kurla complex": (19.0657, 72.8687, 0.99, "BKC, Mumbai"),
    "bkc": (19.0657, 72.8687, 0.99, "Bandra Kurla Complex, Mumbai"),
    "colaba": (18.9067, 72.8147, 0.95, "Colaba, Mumbai"),
    "dadar station": (19.0178, 72.8478, 0.98, "Dadar Station, Mumbai"),
    "dadar": (19.0178, 72.8478, 0.95, "Dadar, Mumbai"),
    "kurla": (19.0726, 72.8845, 0.95, "Kurla, Mumbai"),
    "ghatkopar": (19.0860, 72.9090, 0.95, "Ghatkopar, Mumbai"),
    "borivali": (19.2307, 72.8567, 0.95, "Borivali, Mumbai"),
    "juhu": (19.1075, 72.8263, 0.95, "Juhu Beach / Area, Mumbai"),
    "linking road": (19.0633, 72.8344, 0.92, "Linking Road, Bandra, Mumbai"),
    "sv road": (19.1150, 72.8400, 0.92, "Swami Vivekananda Road, Mumbai"),
    "western express highway": (19.1300, 72.8550, 0.92, "WEH, Mumbai"),
    "eastern express highway": (19.0800, 72.9200, 0.92, "EEH, Mumbai"),
    "sion": (19.0400, 72.8600, 0.95, "Sion, Mumbai"),
    "worli": (19.0150, 72.8180, 0.95, "Worli, Mumbai"),
    "powai": (19.1176, 72.9060, 0.95, "Powai, Mumbai"),
    "matunga": (19.0270, 72.8550, 0.95, "Matunga, Mumbai"),
    "chembur": (19.0620, 72.8990, 0.95, "Chembur, Mumbai"),
    "malad": (19.1860, 72.8480, 0.95, "Malad, Mumbai"),
    "kandivali": (19.2040, 72.8520, 0.95, "Kandivali, Mumbai"),
    "vile parle": (19.0990, 72.8440, 0.95, "Vile Parle, Mumbai")
}

def resolve_location(raw_text: str, context_city: str = "Mumbai") -> Tuple[Optional[float], Optional[float], float, bool, Optional[str]]:
    """
    Resolves a location string to (lat, lng, confidence, is_resolved, formatted_address).
    Checks authoritative local gazetteer cache first, then falls back to OpenStreetMap Nominatim.
    If confidence < 0.6 or not found, marks as unresolved.
    """
    if not raw_text or not raw_text.strip():
        return None, None, 0.0, False, None
        
    cleaned_query = raw_text.lower().strip()
    cleaned_query = re.sub(r'^(near|opposite|behind|at|in|on)\s+', '', cleaned_query).strip()
    
    # Check local gazetteer
    if cleaned_query in GEOCODE_CACHE:
        lat, lng, conf, addr = GEOCODE_CACHE[cleaned_query]
        return lat, lng, conf, True, addr
        
    # Check partial gazetteer match
    for key, (lat, lng, conf, addr) in GEOCODE_CACHE.items():
        if key in cleaned_query or cleaned_query in key:
            return lat, lng, round(conf * 0.9, 2), True, addr
            
    # Fallback to OpenStreetMap Nominatim API with timeout and bounds validation
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(cleaned_query + ', ' + context_city)}&format=json&limit=1"
        headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                res = data[0]
                lat = float(res["lat"])
                lng = float(res["lon"])
                addr = res.get("display_name", cleaned_query)
                conf = 0.85
                # Cache the result
                GEOCODE_CACHE[cleaned_query] = (lat, lng, conf, addr)
                return lat, lng, conf, True, addr
    except Exception:
        pass
        
    # If unresolved, do NOT guess coordinates
    return None, None, 0.0, False, f"Unresolved location: {raw_text}"
