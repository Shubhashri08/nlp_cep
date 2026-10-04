from unittest import mock

import pytest

from backend.app.nlp.cleaner import clean_text, detect_language, normalize_multilingual_text
from backend.app.nlp.geocoder import in_study_area, resolve_location
from backend.app.nlp.ner import extract_entities, normalize_ward_code
from backend.app.nlp.summarizer import summarize_complaint_cluster, textrank_summary


def test_clean_text_collapses_noise():
    assert clean_text("  Garbage!!!   <b>here</b>\n\n now ") == "Garbage! here now"


@pytest.mark.parametrize("text", [
    "The pipeline leakage near the divider has been reported",
    "Short circuit in the electric pole outside the flyover",
    "Traffic signal broken near the populated junction",
])
def test_plain_english_is_not_tagged_code_mixed(text):
    assert detect_language(text)[0] == "en"


def test_hinglish_detected():
    assert detect_language("Paani nahi aa raha 3 din se, rasta bhi kharab hai")[0] == "hi-en"


def test_devanagari_hindi_vs_marathi():
    assert detect_language("तीन दिन से पानी नहीं आ रहा है")[0] == "hi"
    assert detect_language("आमच्या भागात पाणी नाही आहे")[0] == "mr"


def test_normalisation_adds_glosses():
    out = normalize_multilingual_text("kachra peti bhar gayi")
    assert "garbage bin" in out and "kachra" in out


def test_ner_does_not_capture_whole_sentences():
    ents = extract_entities("There is severe waterlogging near Andheri Station every monsoon and the road is broken")
    texts = {e["text"] for e in ents}
    assert "Andheri Station" in texts
    assert all(len(e["text"].split()) <= 5 for e in ents)
    assert any(e["label"] == "FLOODING_INCIDENT" for e in ents)
    assert any(e["label"] == "TEMPORAL" for e in ents)


def test_ner_ward_patterns_are_tight():
    ents = extract_entities("My wardrobe was damaged by leakage from the ward area pipeline")
    assert not [e for e in ents if e["label"] == "WARD"]
    ents = extract_entities("Garbage not collected in Ward K/E and H-East ward")
    wards = [e for e in ents if e["label"] == "WARD"]
    assert {normalize_ward_code(e["text"]) for e in wards} == {"K/E", "H/E"}


def test_ner_aliases_resolve_via_gazetteer():
    ents = extract_entities("Streetlights off along BKC and on SV Road")
    labels = {e["text"]: e for e in ents}
    assert "BKC" in labels and labels["BKC"]["lat"] is not None
    assert "SV Road" in labels


def test_geocoder_gazetteer_hit():
    res = resolve_location("near Andheri Station")
    assert res["resolved"] and res["method"] == "GAZETTEER"
    assert in_study_area(res["lat"], res["lng"])


def test_geocoder_rejects_results_outside_city():
    fake = mock.Mock(status_code=200)
    fake.json.return_value = [{"lat": "53.01", "lon": "-2.23", "display_name": "Newcastle-under-Lyme, UK", "importance": 0.6}]
    with mock.patch("backend.app.nlp.geocoder.requests.get", return_value=fake):
        res = resolve_location("The road", allow_network=True)
    assert res["resolved"] is False and res["lat"] is None


def test_textrank_selects_sentences():
    text = ("Mumbai receives heavy monsoon rainfall. Storm water drains were designed for 25 mm per hour. "
            "BRIMSTOWAD recommended upgrading drains to 50 mm per hour. The city also has many parks. "
            "Upgrading drains reduces flooding in low lying wards.")
    res = textrank_summary(text, max_sentences=2)
    assert len(res["sentences"]) == 2
    assert any("drain" in s.lower() for s in res["sentences"])


def test_cluster_summary_traceable():
    recs = [{"id": i, "original_text": f"Garbage not picked up near Kurla station day {i}",
             "entities": [{"text": "Kurla", "label": "STATION"}, {"text": "uncollected", "label": "WASTE_ACCUMULATION"}],
             "status": "OPEN"} for i in range(5)]
    out = summarize_complaint_cluster(recs, "L Ward", "WASTE_MANAGEMENT", use_llm=False)
    assert out["cluster_count"] == 5 and out["source_record_ids"] == [0, 1, 2, 3, 4]
    assert "Kurla" in out["key_locations"]


def test_classifier_quality(seeded):
    from backend.app.nlp.classifier import get_classifier
    clf = get_classifier()
    assert clf.metrics["gold_set"]["primary_accuracy_any_label"] >= 0.85
    assert clf.metrics["gold_set"]["micro_f1"] >= 0.8
    cat, conf, cats = clf.predict("kachra kai din se nahi utha, bahut badbu")
    assert cat == "WASTE_MANAGEMENT" and conf > 0.5


def test_full_pipeline_keeps_user_gps(seeded):
    from backend.app.nlp.pipeline import process_text
    res = process_text("Potholes near Andheri Station", fallback_lat=19.07, fallback_lng=72.86, allow_network_geocoding=False)
    assert res["geocoding_method"] == "USER_GPS" and res["latitude"] == 19.07
    assert res["primary_category"] == "ROAD_INFRASTRUCTURE"
    res2 = process_text("Potholes near Andheri Station", allow_network_geocoding=False)
    assert res2["geocoding_method"] == "GAZETTEER" and abs(res2["latitude"] - 19.12) < 0.02
