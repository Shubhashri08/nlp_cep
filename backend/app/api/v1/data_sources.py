from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import DataSource, DataQualityReport

router = APIRouter()

@router.get("")
def get_data_sources(db: Session = Depends(get_db)):
    sources = db.query(DataSource).all()
    reports = db.query(DataQualityReport).all()
    
    report_map = {r.data_source_id: r for r in reports}
    
    results = []
    for s in sources:
        r = report_map.get(s.id)
        results.append({
            "id": s.id,
            "source_name": s.source_name,
            "provider": s.provider,
            "dataset_type": s.dataset_type,
            "source_url": s.source_url,
            "license": s.license,
            "date_collected": s.date_collected.strftime("%Y-%m-%d"),
            "geographic_scope": s.geographic_scope,
            "update_frequency": s.update_frequency,
            "quality_score": s.quality_score,
            "quality_report": {
                "total_records": r.total_records,
                "completeness_score": r.completeness_score,
                "duplicate_rate": r.duplicate_rate,
                "missing_values_count": r.missing_values_count,
                "geographic_validity_rate": r.geographic_validity_rate,
                "freshness_days": r.freshness_days,
                "consistency_score": r.consistency_score,
                "overall_quality_score": r.overall_quality_score
            } if r else None
        })
    return results
