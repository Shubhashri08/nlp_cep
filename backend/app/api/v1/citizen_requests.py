from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import CitizenRequest, RequestEmbedding, Ward, RequestStatus
from backend.app.schemas.dss_schemas import (
    CitizenRequestCreate, CitizenRequestResponse,
    SemanticSearchRequest, SemanticSearchResult, BulkIngestResponse
)
from backend.app.nlp.pipeline import nlp_pipeline
from backend.app.nlp.embeddings import embedding_engine
from backend.app.gis.spatial_ops import find_ward_for_point

router = APIRouter()

@router.get("", response_model=List[CitizenRequestResponse])
def get_citizen_requests(
    ward_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    q = db.query(CitizenRequest)
    if ward_id:
        q = q.filter(CitizenRequest.ward_id == ward_id)
    if category:
        q = q.filter(CitizenRequest.primary_category == category)
    if status:
        q = q.filter(CitizenRequest.status == status)
        
    records = q.order_by(CitizenRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    # Enrich with ward_name
    results = []
    for r in records:
        w_name = r.ward.name if r.ward else None
        results.append(CitizenRequestResponse(
            id=r.id,
            request_uid=r.request_uid,
            original_text=r.original_text,
            cleaned_text=r.cleaned_text,
            language=r.language,
            language_confidence=r.language_confidence,
            primary_category=r.primary_category,
            categories=r.categories or [],
            confidence=r.confidence,
            model_version=r.model_version,
            entities=r.entities or [],
            summary=r.summary,
            raw_location_text=r.raw_location_text,
            latitude=r.latitude,
            longitude=r.longitude,
            geocoding_confidence=r.geocoding_confidence,
            is_location_resolved=r.is_location_resolved,
            address=r.address,
            ward_id=r.ward_id,
            ward_name=w_name,
            source=r.source,
            status=r.status,
            cluster_id=r.cluster_id,
            created_at=r.created_at
        ))
    return results

@router.post("", response_model=CitizenRequestResponse)
def create_citizen_request(
    req_in: CitizenRequestCreate,
    db: Session = Depends(get_db)
):
    # 1. Process text through full NLP Pipeline
    nlp_res = nlp_pipeline.process_text(
        req_in.text,
        fallback_lat=req_in.latitude,
        fallback_lng=req_in.longitude
    )
    
    # 2. Determine Ward from coordinates if not provided
    assigned_ward_id = req_in.ward_id
    if not assigned_ward_id and nlp_res["latitude"] and nlp_res["longitude"]:
        wards = db.query(Ward).all()
        matched_ward = find_ward_for_point(nlp_res["latitude"], nlp_res["longitude"], wards)
        if matched_ward:
            assigned_ward_id = matched_ward.id

    count = db.query(CitizenRequest).count()
    new_uid = f"CR-2026-{1001 + count}"
    
    new_req = CitizenRequest(
        request_uid=new_uid,
        original_text=req_in.text,
        cleaned_text=nlp_res["cleaned_text"],
        language=nlp_res["language"],
        language_confidence=nlp_res["language_confidence"],
        primary_category=nlp_res["primary_category"],
        categories=nlp_res["categories"],
        confidence=nlp_res["confidence"],
        model_version=nlp_res["model_version"],
        entities=nlp_res["entities"],
        summary=nlp_res["summary"],
        raw_location_text=nlp_res["raw_location_text"],
        latitude=nlp_res["latitude"],
        longitude=nlp_res["longitude"],
        geocoding_confidence=nlp_res["geocoding_confidence"],
        is_location_resolved=nlp_res["is_location_resolved"],
        address=nlp_res["address"] or req_in.address,
        ward_id=assigned_ward_id,
        source=req_in.source or "Web Portal",
        status=RequestStatus.OPEN,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_req)
    db.flush()
    
    # 3. Store semantic embedding
    emb = RequestEmbedding(
        request_id=new_req.id,
        embedding_vector=nlp_res["embedding_vector"],
        embedding_model="sentence-lsa-dense-64d"
    )
    db.add(emb)
    db.commit()
    db.refresh(new_req)
    
    w_name = new_req.ward.name if new_req.ward else None
    return CitizenRequestResponse(
        id=new_req.id,
        request_uid=new_req.request_uid,
        original_text=new_req.original_text,
        cleaned_text=new_req.cleaned_text,
        language=new_req.language,
        language_confidence=new_req.language_confidence,
        primary_category=new_req.primary_category,
        categories=new_req.categories or [],
        confidence=new_req.confidence,
        model_version=new_req.model_version,
        entities=new_req.entities or [],
        summary=new_req.summary,
        raw_location_text=new_req.raw_location_text,
        latitude=new_req.latitude,
        longitude=new_req.longitude,
        geocoding_confidence=new_req.geocoding_confidence,
        is_location_resolved=new_req.is_location_resolved,
        address=new_req.address,
        ward_id=new_req.ward_id,
        ward_name=w_name,
        source=new_req.source,
        status=new_req.status,
        cluster_id=new_req.cluster_id,
        created_at=new_req.created_at
    )

@router.post("/search/semantic", response_model=List[SemanticSearchResult])
def semantic_search_requests(
    search_req: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Performs dense vector similarity search across all citizen grievance embeddings.
    """
    query_vec = embedding_engine.encode(search_req.query)
    
    all_embeddings = (
        db.query(RequestEmbedding, CitizenRequest, Ward)
        .join(CitizenRequest, RequestEmbedding.request_id == CitizenRequest.id)
        .outerjoin(Ward, CitizenRequest.ward_id == Ward.id)
        .all()
    )
    
    scored_results = []
    for emb_obj, req_obj, ward_obj in all_embeddings:
        # Filter by category if requested
        if search_req.category and req_obj.primary_category != search_req.category:
            continue
        if search_req.ward_id and req_obj.ward_id != search_req.ward_id:
            continue
            
        sim = embedding_engine.compute_similarity(query_vec, emb_obj.embedding_vector)
        scored_results.append({
            "id": req_obj.id,
            "request_uid": req_obj.request_uid,
            "text": req_obj.original_text,
            "primary_category": req_obj.primary_category,
            "similarity_score": round(sim, 4),
            "ward_name": ward_obj.name if ward_obj else None,
            "latitude": req_obj.latitude,
            "longitude": req_obj.longitude,
            "created_at": req_obj.created_at
        })
        
    scored_results = sorted(scored_results, key=lambda x: x["similarity_score"], reverse=True)
    return [SemanticSearchResult(**r) for r in scored_results[:search_req.top_k]]
