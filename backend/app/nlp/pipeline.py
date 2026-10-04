"""End-to-end grievance NLP: clean → language ID → normalise → classify → NER → geocode → embed → summarise."""
from typing import Any, Dict, Optional

from backend.app.nlp.classifier import get_classifier
from backend.app.nlp.cleaner import clean_text, detect_language
from backend.app.nlp.embeddings import get_embedding_engine
from backend.app.nlp.geocoder import in_study_area, resolve_location
from backend.app.nlp.ner import extract_entities, location_entities
from backend.app.nlp.summarizer import summarize_single_complaint


def process_text(
    text: str,
    fallback_lat: Optional[float] = None,
    fallback_lng: Optional[float] = None,
    db=None,
    allow_network_geocoding: Optional[bool] = None,
    compute_embedding: bool = True,
) -> Dict[str, Any]:
    classifier = get_classifier()
    cleaned = clean_text(text)
    lang, lang_conf = detect_language(cleaned)
    primary, conf, cats = classifier.predict(cleaned)
    entities = extract_entities(cleaned)

    lat = lng = None
    geo_conf = 0.0
    method = "NONE"
    address = None
    raw_loc = None
    ward_code = None
    locs = location_entities(entities)
    if locs:
        raw_loc = locs[0]["text"]
        ward_code = next((e.get("ward_code") for e in locs if e.get("ward_code")), None)

    if fallback_lat is not None and fallback_lng is not None and in_study_area(fallback_lat, fallback_lng):
        # Device GPS is the most precise evidence – never overridden by text geocoding
        lat, lng, geo_conf, method = fallback_lat, fallback_lng, 1.0, "USER_GPS"
        address = f"GPS {fallback_lat:.5f}, {fallback_lng:.5f}" + (f" (mentions {raw_loc})" if raw_loc else "")
    else:
        for ent in locs[:3]:
            if ent.get("lat") is not None:  # gazetteer hit carries coordinates
                lat, lng, geo_conf, method = ent["lat"], ent["lng"], ent["confidence"], "GAZETTEER"
                address, raw_loc = ent["text"], ent["text"]
                break
            if ent["label"] == "WARD":
                continue
            res = resolve_location(ent["text"], db=db, allow_network=allow_network_geocoding)
            if res["resolved"]:
                lat, lng, geo_conf, method, address = res["lat"], res["lng"], res["confidence"], res["method"], res["address"]
                raw_loc = ent["text"]
                break

    return {
        "original_text": text,
        "cleaned_text": cleaned,
        "language": lang,
        "language_confidence": lang_conf,
        "primary_category": primary,
        "confidence": conf,
        "categories": cats,
        "entities": entities,
        "summary": summarize_single_complaint(cleaned, primary, entities),
        "raw_location_text": raw_loc,
        "latitude": lat,
        "longitude": lng,
        "geocoding_confidence": geo_conf,
        "geocoding_method": method,
        "is_location_resolved": lat is not None,
        "address": address,
        "mentioned_ward_code": ward_code,
        "embedding_vector": get_embedding_engine().encode(cleaned) if compute_embedding else None,
        "model_version": classifier.model_version,
    }
