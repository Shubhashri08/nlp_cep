from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Recommendation, Ward
from backend.app.schemas.dss_schemas import RecommendationResponse

router = APIRouter()

@router.get("", response_model=List[RecommendationResponse])
def get_recommendations(
    ward_id: Optional[int] = Query(None),
    sector: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Recommendation, Ward).join(Ward, Recommendation.ward_id == Ward.id)
    if ward_id:
        q = q.filter(Recommendation.ward_id == ward_id)
    if sector:
        q = q.filter(Recommendation.sector == sector)
    if priority:
        q = q.filter(Recommendation.priority_level == priority)
        
    records = q.order_by(Recommendation.score.desc()).all()
    results = []
    for r, w in records:
        results.append(RecommendationResponse(
            id=r.id,
            ward_id=r.ward_id,
            ward_name=w.name,
            sector=r.sector,
            title=r.title,
            recommendation_text=r.recommendation_text,
            priority_level=r.priority_level,
            score=r.score,
            contributing_factors=r.contributing_factors or [],
            supporting_evidence=r.supporting_evidence or [],
            methodology=r.methodology,
            created_at=r.created_at
        ))
    return results
