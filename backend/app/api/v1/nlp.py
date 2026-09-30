from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from backend.app.nlp.pipeline import nlp_pipeline
from backend.app.nlp.classifier import CATEGORIES
from backend.app.schemas.dss_schemas import NLPAnalysisResult

router = APIRouter()

class NLPTestInput(BaseModel):
    text: str
    context_city: str = "Mumbai"

@router.post("/analyze", response_model=NLPAnalysisResult)
def analyze_text(payload: NLPTestInput):
    """
    Live NLP execution endpoint:
    Processes raw citizen text through language detection, transliteration normalization,
    multi-class & multi-label classification, NER, location resolution, and summarization.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    res = nlp_pipeline.process_text(payload.text, context_city=payload.context_city)
    return NLPAnalysisResult(
        original_text=res["original_text"],
        cleaned_text=res["cleaned_text"],
        language=res["language"],
        language_confidence=res["language_confidence"],
        primary_category=res["primary_category"],
        confidence=res["confidence"],
        categories=res["categories"],
        entities=res["entities"],
        summary=res["summary"],
        resolved_location=res["raw_location_text"],
        resolved_lat=res["latitude"],
        resolved_lng=res["longitude"],
        geocoding_confidence=res["geocoding_confidence"],
        is_location_resolved=res["is_location_resolved"],
        model_version=res["model_version"]
    )

@router.get("/categories")
def get_nlp_categories():
    return {
        "total_categories": len(CATEGORIES),
        "categories": CATEGORIES
    }
