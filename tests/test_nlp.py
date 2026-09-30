import pytest
from backend.app.nlp.cleaner import clean_text, detect_language, normalize_multilingual_text
from backend.app.nlp.classifier import nlp_classifier
from backend.app.nlp.ner import extract_entities
from backend.app.nlp.geocoder import resolve_location
from backend.app.nlp.embeddings import embedding_engine
from backend.app.nlp.pipeline import nlp_pipeline

def test_clean_text():
    dirty = "   Severe   waterlogging  near   school!!!   "
    cleaned = clean_text(dirty)
    assert cleaned == "Severe waterlogging near school!"

def test_multilingual_detection():
    marathi_text = "रस्त्यावर कचरा साचला आहे आणि दुर्गंधी पसरली आहे"
    lang, conf = detect_language(marathi_text)
    assert lang in ("mr", "hi")
    
    hinglish_text = "Andheri rasta par paani bhar gaya hai aur khadde pad gaye hain"
    lang2, conf2 = detect_language(hinglish_text)
    assert lang2 == "hi-en"

def test_classification():
    text = "The road near the school is flooded with knee deep water"
    cat, conf, multi_cats = nlp_classifier.predict(text)
    assert cat in ("FLOODING", "DRAINAGE", "ROAD_INFRASTRUCTURE")
    assert conf > 0.3
    assert len(multi_cats) >= 1

def test_ner_extraction():
    text = "There is severe waterlogging near Andheri Station every monsoon."
    entities = extract_entities(text)
    labels = [e["label"] for e in entities]
    assert "LOCATION_LANDMARK" in labels or "WARD" in labels or "ROAD" in labels
    assert "FLOODING_INCIDENT" in labels

def test_geocoding_resolution():
    lat, lng, conf, ok, addr = resolve_location("Andheri Station")
    assert ok is True
    assert lat is not None and lng is not None
    assert 19.0 <= lat <= 19.3
    assert 72.7 <= lng <= 73.0

def test_embeddings_and_similarity():
    v1 = embedding_engine.encode("Heavy flooding and waterlogging during monsoon rains")
    v2 = embedding_engine.encode("Knee deep rainwater accumulation submerging roads")
    v3 = embedding_engine.encode("Property tax assessment filing deadline")
    
    sim_related = embedding_engine.compute_similarity(v1, v2)
    sim_unrelated = embedding_engine.compute_similarity(v1, v3)
    assert sim_related > sim_unrelated

def test_full_nlp_pipeline():
    res = nlp_pipeline.process_text("Deep potholes and broken road divider on Linking Road Bandra")
    assert res["primary_category"] == "ROAD_INFRASTRUCTURE"
    assert res["is_location_resolved"] is True
    assert len(res["embedding_vector"]) > 0
