import re
import unicodedata
from typing import Tuple

# Common transliterated Hindi/Marathi/Hinglish urban keywords mapping to normalized English
HINGLISH_MARATHI_DICT = {
    # Water & Drainage
    "paani": "water", "pani": "water", "nal": "tap water", "jal": "water",
    "gutter": "drainage", "naala": "drain", "gatar": "drainage", "naali": "drain",
    "paani bhara": "waterlogging", "pani bharla": "waterlogging flooding",
    "jalsangrah": "waterlogging", "tutla": "broken", "footla": "broken burst",
    "leakage": "leakage", "ganda pani": "contaminated dirty water",
    
    # Roads & Traffic
    "khadde": "potholes", "khadda": "pothole", "khadde padlet": "potholes developed",
    "sadak": "road", "rasta": "road", "rastya": "road", "traffic jaam": "traffic congestion",
    "signal band": "traffic light broken", "divider": "road divider",
    "flyover": "flyover bridge", "pul": "bridge", "chakka jam": "severe traffic gridlock",
    
    # Waste Management
    "kachra": "garbage waste", "kachra peti": "garbage bin", "kachara": "garbage",
    "safai": "cleaning sanitation", "safai nahi": "no sanitation cleaning",
    "durgandhi": "foul smell stench", "vaas yetoy": "foul smell", "kuda": "garbage",
    "dumping ground": "waste dumping area",
    
    # Electricity & Streetlights
    "batti": "streetlight", "light band": "streetlight not working", "andhera": "darkness no lights",
    "vij": "electricity", "pole": "electric pole", "current": "exposed electricity wire",
    "taar": "electric wire", "short circuit": "short circuit",
    
    # Public Safety & Health
    "dawaakhana": "dispensary clinic", "rugnalay": "hospital", "aspatal": "hospital",
    "machhar": "mosquitoes dengue risk", "rograi": "disease outbreak", "chori": "theft public safety",
    "kutte": "stray dogs menace", "bhatki kutre": "stray dogs"
}

def clean_text(text: str) -> str:
    """Normalize whitespace, remove extraneous symbols, and normalize unicode."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove HTML tags if present
    text = re.sub(r'<[^>]+>', ' ', text)
    # Normalize excessive punctuation
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'[!?,.:;]{2,}', lambda m: m.group(0)[0], text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def detect_language(text: str) -> Tuple[str, float]:
    """
    Detects if text is English, Devanagari Hindi/Marathi, or Hinglish.
    Returns (lang_code, confidence).
    """
    if not text:
        return "en", 1.0
    
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
    total_chars = len(re.sub(r'\s', '', text)) or 1
    
    devanagari_ratio = devanagari_chars / total_chars
    if devanagari_ratio > 0.4:
        # Check specific Marathi characters/words vs Hindi
        marathi_markers = ["आहे", "नाही", "झाला", "रस्त्यावर", "पाणी", "कचरा", "येतोय"]
        if any(marker in text for marker in marathi_markers):
            return "mr", min(0.98, devanagari_ratio + 0.1)
        return "hi", min(0.98, devanagari_ratio + 0.1)
    
    # Check for Hinglish / Romanized Marathi keywords
    lower_text = text.lower()
    hinglish_matches = sum(1 for kw in HINGLISH_MARATHI_DICT if kw in lower_text)
    if hinglish_matches >= 1:
        return "hi-en", min(0.92, 0.6 + (hinglish_matches * 0.1))
    
    return "en", 0.95

def normalize_multilingual_text(text: str) -> str:
    """
    Cleans text and standardizes Hinglish / Marathi urban terms into standardized English concepts
    while preserving original location entities.
    """
    cleaned = clean_text(text)
    lower = cleaned.lower()
    
    expanded = lower
    for term, standard in HINGLISH_MARATHI_DICT.items():
        pattern = r'\b' + re.escape(term) + r'\b'
        expanded = re.sub(pattern, standard, expanded)
        
    return expanded
