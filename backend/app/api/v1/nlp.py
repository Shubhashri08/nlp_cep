from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.gis.spatial_ops import find_ward_for_point
from backend.app.models.entities import CitizenRequest, PlanningDocument, User, UserRole, Ward
from backend.app.nlp.classifier import get_classifier
from backend.app.nlp.documents import analyze_document, extract_text
from backend.app.nlp.lexicon import CATEGORIES
from backend.app.nlp.pipeline import process_text
from backend.app.nlp.summarizer import summarize_complaint_cluster
from backend.app.schemas.dss_schemas import NLPAnalysisResult, NLPAnalyzeRequest, PlanningDocumentResponse

router = APIRouter(dependencies=[Depends(get_current_user)])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@router.post("/analyze", response_model=NLPAnalysisResult)
def analyze_text(payload: NLPAnalyzeRequest, db: Session = Depends(get_db)):
    """Runs language ID, normalisation, multi-label classification, NER, geocoding and summarisation."""
    res = process_text(payload.text, fallback_lat=payload.latitude, fallback_lng=payload.longitude, db=db, compute_embedding=False)
    ward = None
    if res["latitude"] is not None:
        ward = find_ward_for_point(res["latitude"], res["longitude"], db.query(Ward).all())
    if ward is None and res.get("mentioned_ward_code"):
        ward = db.query(Ward).filter(Ward.ward_code == res["mentioned_ward_code"]).first()
    db.commit()  # persist geocode cache entries
    return NLPAnalysisResult(
        original_text=res["original_text"], cleaned_text=res["cleaned_text"], language=res["language"],
        language_confidence=res["language_confidence"], primary_category=res["primary_category"], confidence=res["confidence"],
        categories=res["categories"], entities=res["entities"], summary=res["summary"], resolved_location=res["address"],
        resolved_lat=res["latitude"], resolved_lng=res["longitude"], geocoding_confidence=res["geocoding_confidence"],
        geocoding_method=res["geocoding_method"], is_location_resolved=res["is_location_resolved"],
        ward_id=ward.id if ward else None, ward_name=ward.name if ward else None, model_version=res["model_version"],
    )


@router.get("/categories")
def get_nlp_categories():
    clf = get_classifier()
    return {"total_categories": len(CATEGORIES), "categories": CATEGORIES, "model_version": clf.model_version,
            "metrics": {k: clf.metrics.get(k) for k in ("held_out", "gold_set")}}


@router.get("/cluster-summary")
def cluster_summary(ward_id: int, category: str, limit: int = 300, db: Session = Depends(get_db)):
    ward = db.get(Ward, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    rows = (db.query(CitizenRequest).filter(CitizenRequest.ward_id == ward_id, CitizenRequest.primary_category == category)
            .order_by(CitizenRequest.created_at.desc()).limit(limit).all())
    records = [{"id": r.id, "original_text": r.original_text, "cleaned_text": r.cleaned_text, "entities": r.entities,
                "status": r.status.value} for r in rows]
    return {"ward_id": ward_id, "ward_name": ward.name, "category": category, **summarize_complaint_cluster(records, ward.name, category)}


@router.post("/documents", response_model=PlanningDocumentResponse, status_code=201)
async def upload_document(request: Request, file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None),
                          title: Optional[str] = Form(None), db: Session = Depends(get_db),
                          user: User = Depends(require_role(UserRole.PLANNER, UserRole.ANALYST))):
    """Analyse an urban development report (PDF / TXT upload, or pasted text)."""
    filename = None
    pages = 1
    if file is not None:
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (15 MB max)")
        filename = file.filename
        try:
            body, pages = extract_text(filename, data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not read document: {exc}")
    elif text:
        body = text
    else:
        raise HTTPException(status_code=422, detail="Provide a file or text")
    if len(body.split()) < 20:
        raise HTTPException(status_code=422, detail="Document has too little extractable text (scanned PDFs need OCR first)")
    doc_title = title or (filename.rsplit(".", 1)[0] if filename else body.strip().split("\n")[0][:80])
    wards = {w.ward_code: {"id": w.id, "name": w.name} for w in db.query(Ward).all()}
    result = analyze_document(doc_title, body, wards)
    doc = PlanningDocument(title=doc_title, filename=filename, uploaded_by=user.id, text_length=result["text_length"], page_count=pages,
                           summary=result["summary"], summary_method=result["summary_method"], key_sentences=result["key_sentences"],
                           sector_distribution=result["sector_distribution"], sections=result["sections"], entities=result["entities"],
                           wards_mentioned=result["wards_mentioned"])
    db.add(doc)
    db.flush()
    audit(db, user, "DOCUMENT_ANALYZED", "PLANNING_DOCUMENT", doc.id, {"title": doc_title, "pages": pages}, request)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/documents", response_model=List[PlanningDocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return db.query(PlanningDocument).order_by(PlanningDocument.created_at.desc()).all()


@router.get("/documents/{doc_id}", response_model=PlanningDocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(PlanningDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
