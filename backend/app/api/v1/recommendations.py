import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.llm.providers import get_llm
from backend.app.models.entities import Recommendation, User, UserRole, Ward
from backend.app.schemas.dss_schemas import RecommendationResponse, RecommendationStatusUpdate
from backend.app.services import analysis

router = APIRouter(dependencies=[Depends(get_current_user)])


def _out(r: Recommendation, w: Ward) -> RecommendationResponse:
    return RecommendationResponse(
        id=r.id, ward_id=r.ward_id, ward_name=w.name, ward_code=w.ward_code, sector=r.sector, title=r.title,
        recommendation_text=r.recommendation_text, priority_level=r.priority_level, score=r.score,
        estimated_cost_cr=r.estimated_cost_cr, contributing_factors=r.contributing_factors or [],
        supporting_evidence=r.supporting_evidence or [], methodology=r.methodology, status=r.status or "PROPOSED",
        llm_brief=r.llm_brief, created_at=r.created_at)


@router.get("", response_model=List[RecommendationResponse])
def get_recommendations(ward_id: Optional[int] = None, sector: Optional[str] = None, priority: Optional[str] = None,
                        status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Recommendation, Ward).join(Ward, Recommendation.ward_id == Ward.id)
    if ward_id:
        q = q.filter(Recommendation.ward_id == ward_id)
    if sector:
        q = q.filter(Recommendation.sector == sector)
    if priority:
        q = q.filter(Recommendation.priority_level == priority)
    if status:
        q = q.filter(Recommendation.status == status)
    return [_out(r, w) for r, w in q.order_by(Recommendation.score.desc()).all()]


@router.patch("/{rec_id}/status", response_model=RecommendationResponse)
def update_status(rec_id: int, payload: RecommendationStatusUpdate, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_role(UserRole.PLANNER))):
    r = db.get(Recommendation, rec_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    old, r.status = r.status, payload.status
    audit(db, user, "RECOMMENDATION_STATUS", "RECOMMENDATION", r.id, {"from": old, "to": r.status}, request)
    db.commit()
    return _out(r, db.get(Ward, r.ward_id))


@router.post("/regenerate")
def regenerate(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.PLANNER))):
    recs = analysis.recompute_priorities_and_recommendations(db)
    audit(db, user, "RECOMMENDATIONS_REGENERATED", "RECOMMENDATION", None, {"count": len(recs)}, request)
    db.commit()
    return {"count": len(recs)}


@router.post("/{rec_id}/brief", response_model=RecommendationResponse)
def generate_brief(rec_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.PLANNER, UserRole.ANALYST))):
    """LLM-written planner brief grounded only in the recommendation's evidence (requires an LLM provider)."""
    r = db.get(Recommendation, rec_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    llm = get_llm()
    if not llm.available:
        raise HTTPException(status_code=503, detail="No LLM provider configured (set LLM_PROVIDER and an API key)")
    w = db.get(Ward, r.ward_id)
    evidence = {"ward": w.name, "population": w.population, "sector": r.sector, "title": r.title, "proposal": r.recommendation_text,
                "score": r.score, "priority": r.priority_level, "estimated_cost_cr": r.estimated_cost_cr,
                "factors": r.contributing_factors, "evidence": r.supporting_evidence}
    try:
        r.llm_brief = llm.complete(
            system="You write concise briefs for municipal councillors. Use only the JSON evidence. Explain why the intervention "
                   "is needed, what it involves, indicative cost and risks of inaction. 120 words max. No invented figures.",
            user=json.dumps(evidence, default=str), max_tokens=300)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")
    db.commit()
    return _out(r, w)
