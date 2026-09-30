from typing import Dict, Any, Optional
from backend.app.nlp.cleaner import clean_text, detect_language, normalize_multilingual_text
from backend.app.nlp.classifier import nlp_classifier
from backend.app.nlp.ner import extract_entities
from backend.app.nlp.geocoder import resolve_location
from backend.app.nlp.embeddings import embedding_engine
from backend.app.nlp.summarizer import summarize_single_complaint
from backend.app.schemas.dss_schemas import NLPAnalysisResult, CategoryScore, EntityItem

class MasterNLPPipeline:
    """
    End-to-End Multilingual NLP Pipeline for Urban Decision Support.
    Executes:
    Text -> Language Detection -> Cleaning & Normalization -> Multi-class & Multi-label Classification
    -> NER -> Location Resolution / Geocoding -> Embedding Generation -> Summarization.
    """
    def __init__(self):
        self.classifier = nlp_classifier
        self.embedding_engine = embedding_engine

    def process_text(
        self, 
        text: str, 
        fallback_lat: Optional[float] = None, 
        fallback_lng: Optional[float] = None,
        context_city: str = "Mumbai"
    ) -> Dict[str, Any]:
        # 1. Text Cleaning & Language Detection
        cleaned = clean_text(text)
        lang, lang_conf = detect_language(cleaned)
        
        # 2. Multilingual Normalization (Hinglish / Marathi to English concepts)
        normalized_for_clf = normalize_multilingual_text(cleaned)
        
        # 3. Multi-label & Multi-class Classification
        primary_cat, conf, multi_cats = self.classifier.predict(normalized_for_clf)
        
        # 4. Named Entity Recognition
        entities = extract_entities(cleaned)
        
        # 5. Location Entity Resolution (Geocoding)
        resolved_lat = fallback_lat
        resolved_lng = fallback_lng
        geo_conf = 0.0
        is_resolved = False
        resolved_addr = None
        raw_loc_text = None
        
        # Look for location entities in NER
        loc_entities = [e["text"] for e in entities if e["label"] in ("LOCATION_LANDMARK", "ROAD", "WARD")]
        if loc_entities:
            raw_loc_text = loc_entities[0]
            lat, lng, c, ok, addr = resolve_location(raw_loc_text, context_city)
            if ok:
                resolved_lat, resolved_lng, geo_conf, is_resolved, resolved_addr = lat, lng, c, True, addr
        elif fallback_lat is not None and fallback_lng is not None:
            resolved_lat, resolved_lng = fallback_lat, fallback_lng
            geo_conf = 1.0
            is_resolved = True
            resolved_addr = f"Coordinates: {fallback_lat:.4f}, {fallback_lng:.4f}"
            
        # 6. Embedding Generation
        embedding_vector = self.embedding_engine.encode(cleaned)
        
        # 7. Single Complaint Summary
        summary = summarize_single_complaint(cleaned, primary_cat, entities)
        
        return {
            "original_text": text,
            "cleaned_text": cleaned,
            "language": lang,
            "language_confidence": lang_conf,
            "primary_category": primary_cat,
            "confidence": conf,
            "categories": multi_cats,
            "entities": entities,
            "summary": summary,
            "raw_location_text": raw_loc_text,
            "latitude": resolved_lat,
            "longitude": resolved_lng,
            "geocoding_confidence": geo_conf,
            "is_location_resolved": is_resolved,
            "address": resolved_addr,
            "embedding_vector": embedding_vector,
            "model_version": self.classifier.model_version
        }

nlp_pipeline = MasterNLPPipeline()
