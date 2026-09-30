from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.api.serializers import citizen_request_out
from backend.app.database.session import get_db
from backend.app.gis.spatial_ops import find_ward_for_point
from backend.app.models.entities import (
    CitizenRequest, Provenance, RequestEmbedding, RequestStatus, User, UserRole, Ward,
)
from backend.app.nlp.embeddings import get_embedding_engine
from backend.app.nlp.pipeline import process_text
from backend.app.schemas.dss_schemas import (
    CitizenRequestCreate, CitizenRequestPage, CitizenRequestResponse, SemanticSearchRequest, SemanticSearchResult,
    StatusUpdate,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=CitizenRequestPage)
def list_citizen_requests(
    ward_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[RequestStatus] = None,
    language: Optional[str] = None,
    q: Optional[str] = Query(None, description="substring search in text"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(CitizenRequest)
    if ward_id:
        query = query.filter(CitizenRequest.ward_id == ward_id)
    if category:
        query = query.filter(CitizenRequest.primary_category == category)
    if status:
        query = query.filter(CitizenRequest.status == status)
    if language:
        query = query.filter(CitizenRequest.language == language)
    if q:
        query = query.filter(CitizenRequest.original_text.ilike(f"%{q}%"))
    total = query.count()
    rows = query.order_by(CitizenRequest.created_at.desc()).offset(offset).limit(limit).all()
    return CitizenRequestPage(total=total, limit=limit, offset=offset, items=[citizen_request_out(r) for r in rows])


@router.get("/points")
def complaint_points(category: Optional[str] = None, status: Optional[RequestStatus] = None, months: int = Query(12, ge=1, le=60),
                     db: Session = Depends(get_db)):
    """Lightweight geolocated points for map layers."""
    since = datetime.now() .replace(day=1)
    year, month = since.year, since.month - months
    while month <= 0:
        year, month = year - 1, month + 12
    q = db.query(CitizenRequest.id, CitizenRequest.latitude, CitizenRequest.longitude, CitizenRequest.primary_category,
                 CitizenRequest.status, CitizenRequest.summary, CitizenRequest.created_at).filter(
        CitizenRequest.latitude.isnot(None), CitizenRequest.created_at >= datetime(year, month, 1))
    if category:
        q = q.filter(CitizenRequest.primary_category == category)
    if status:
        q = q.filter(CitizenRequest.status == status)
    return [{"id": i, "lat": la, "lng": ln, "category": c, "status": s.value, "summary": sm, "date": d.strftime("%Y-%m-%d")}
            for i, la, ln, c, s, sm, d in q.all()]


@router.get("/{request_id}", response_model=CitizenRequestResponse)
def get_citizen_request(request_id: int, db: Session = Depends(get_db)):
    r = db.get(CitizenRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    return citizen_request_out(r)


@router.post("", response_model=CitizenRequestResponse, status_code=201)
def create_citizen_request(req_in: CitizenRequestCreate, request: Request, db: Session = Depends(get_db),
                           user: User = Depends(require_role(UserRole.PLANNER, UserRole.ANALYST))):
    res = process_text(req_in.text, fallback_lat=req_in.latitude, fallback_lng=req_in.longitude, db=db)
    ward_id = req_in.ward_id
    if not ward_id and res["latitude"] is not None:
        ward = find_ward_for_point(res["latitude"], res["longitude"], db.query(Ward).all())
        ward_id = ward.id if ward else None
    if not ward_id and res.get("mentioned_ward_code"):
        ward = db.query(Ward).filter(Ward.ward_code == res["mentioned_ward_code"]).first()
        ward_id = ward.id if ward else None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r = CitizenRequest(
        original_text=req_in.text, cleaned_text=res["cleaned_text"], language=res["language"],
        language_confidence=res["language_confidence"], primary_category=res["primary_category"], categories=res["categories"],
        confidence=res["confidence"], model_version=res["model_version"], entities=res["entities"], summary=res["summary"],
        raw_location_text=res["raw_location_text"], latitude=res["latitude"], longitude=res["longitude"],
        geocoding_confidence=res["geocoding_confidence"], geocoding_method=res["geocoding_method"],
        is_location_resolved=res["is_location_resolved"], address=res["address"] or req_in.address, ward_id=ward_id,
        source=req_in.source or "Web Portal", provenance=Provenance.CITIZEN.value, status=RequestStatus.OPEN, created_at=now,
    )
    db.add(r)
    db.flush()
    r.request_uid = f"CR-{now.year}-{r.id:06d}"
    db.add(RequestEmbedding(request_id=r.id, embedding_vector=res["embedding_vector"], embedding_model=get_embedding_engine().model_name))
    audit(db, user, "CITIZEN_REQUEST_CREATED", "CITIZEN_REQUEST", r.id, {"category": r.primary_category}, request)
    db.commit()
    db.refresh(r)
    return citizen_request_out(r)


@router.patch("/{request_id}/status", response_model=CitizenRequestResponse)
def update_status(request_id: int, payload: StatusUpdate, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_role(UserRole.PLANNER))):
    r = db.get(CitizenRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    old = r.status.value
    r.status = payload.status
    r.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None) if payload.status in (RequestStatus.RESOLVED, RequestStatus.CLOSED) else None
    audit(db, user, "STATUS_CHANGED", "CITIZEN_REQUEST", r.id, {"from": old, "to": payload.status.value}, request)
    db.commit()
    db.refresh(r)
    return citizen_request_out(r)


@router.post("/search/semantic", response_model=List[SemanticSearchResult])
def semantic_search(search: SemanticSearchRequest, db: Session = Depends(get_db)):
    engine = get_embedding_engine()
    qv = np.asarray(engine.encode(search.query))
    if not np.any(qv):
        return []
    q = (db.query(RequestEmbedding.embedding_vector, CitizenRequest, Ward.name)
         .join(CitizenRequest, RequestEmbedding.request_id == CitizenRequest.id)
         .outerjoin(Ward, CitizenRequest.ward_id == Ward.id))
    if search.category:
        q = q.filter(CitizenRequest.primary_category == search.category)
    if search.ward_id:
        q = q.filter(CitizenRequest.ward_id == search.ward_id)
    rows = q.all()
    if not rows:
        return []
    mat = np.array([v for v, _, _ in rows if len(v) == len(qv)])
    rows = [r for r in rows if len(r[0]) == len(qv)]
    sims = mat @ qv
    top = np.argsort(sims)[::-1][: search.top_k]
    return [SemanticSearchResult(id=rows[i][1].id, request_uid=rows[i][1].request_uid, text=rows[i][1].original_text,
                                 primary_category=rows[i][1].primary_category, similarity_score=round(float(sims[i]), 4),
                                 ward_name=rows[i][2], latitude=rows[i][1].latitude, longitude=rows[i][1].longitude,
                                 status=rows[i][1].status.value, created_at=rows[i][1].created_at) for i in top]
