from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Ward, Prediction
from backend.app.schemas.dss_schemas import ForecastResponse, ForecastPoint
from backend.app.forecasting.demand_model import demand_forecaster

router = APIRouter()

@router.get("/forecast", response_model=ForecastResponse)
def get_demand_forecast(
    ward_id: Optional[int] = Query(None),
    target_metric: str = Query("monthly_citizen_requests_aggregate"),
    horizon_months: int = Query(12, ge=3, le=24),
    db: Session = Depends(get_db)
):
    ward_name = "Metropolitan Jurisdiction (All Wards)"
    pop_density = 28.5
    deficit_pct = 18.0
    
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if ward:
            ward_name = ward.name
            pop_density = ward.population_density / 1000.0
            deficit_pct = ward.priority_score * 0.4
            
    recent_historical = [
        {"date": "2025-10", "actual_value": 34.0},
        {"date": "2025-11", "actual_value": 38.0},
        {"date": "2025-12", "actual_value": 36.0},
        {"date": "2026-01", "actual_value": 41.0},
        {"date": "2026-02", "actual_value": 44.0},
        {"date": "2026-03", "actual_value": 49.0}
    ]
    
    preds, metrics, importances = demand_forecaster.forecast_demand(
        recent_values=[h["actual_value"] for h in recent_historical],
        pop_density=pop_density,
        deficit_pct=deficit_pct,
        horizon_months=horizon_months
    )
    
    return ForecastResponse(
        target_metric=target_metric,
        ward_id=ward_id,
        ward_name=ward_name,
        model_name="RandomForestLagRegressor",
        model_version=demand_forecaster.model_version,
        historical_data=recent_historical,
        forecast=[ForecastPoint(**p) for p in preds],
        metrics=metrics,
        feature_importance=importances,
        generated_at=datetime.now(timezone.utc)
    )
