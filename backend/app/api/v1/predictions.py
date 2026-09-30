from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.forecasting.demand_model import METRICS, get_forecaster
from backend.app.models.entities import User, UserRole, Ward
from backend.app.schemas.dss_schemas import ForecastPoint, ForecastResponse
from backend.app.services import analysis

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/metrics")
def list_metrics():
    fc = get_forecaster()
    return [{"id": k, **v, "trained": fc.is_ready(k), "backtest": fc.models[k].metrics if fc.is_ready(k) else None}
            for k, v in METRICS.items()]


@router.get("/forecast", response_model=ForecastResponse)
def get_demand_forecast(target_metric: str = Query("complaint_volume"), ward_id: Optional[int] = None,
                        horizon_months: int = Query(12, ge=1, le=24), db: Session = Depends(get_db)):
    if target_metric not in METRICS:
        raise HTTPException(status_code=422, detail=f"target_metric must be one of {list(METRICS)}")
    ward = db.get(Ward, ward_id) if ward_id else None
    if ward_id and not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    try:
        res = analysis.forecast_for(db, target_metric, ward_id, horizon_months)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    fc = get_forecaster()
    return ForecastResponse(
        target_metric=target_metric, metric_label=METRICS[target_metric]["label"], unit=METRICS[target_metric]["unit"],
        ward_id=ward_id, ward_name=ward.name if ward else "All wards (sum of ward forecasts)",
        model_name="GradientBoostingPanelForecaster", model_version=fc.model_version,
        historical_data=res["history"], forecast=[ForecastPoint(**p) for p in res["forecast"]],
        metrics=res["metrics"], feature_importance=res["feature_importance"],
        provenance="DERIVED from citizen_requests" if target_metric == "complaint_volume" else "SYNTHETIC service records",
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/infrastructure-demand")
def infrastructure_demand(target_year: int = Query(2031, ge=2026, le=2051), db: Session = Depends(get_db)):
    """Future infrastructure & service requirements from projected population and planning norms."""
    return analysis.infrastructure_demand_projection(db, target_year)


@router.post("/retrain")
def retrain(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.ANALYST))):
    analysis.refresh_complaint_volume(db)
    metrics = analysis.train_forecaster(db)
    growth = analysis.refresh_predictions(db)
    analysis.recompute_priorities_and_recommendations(db, growth)
    audit(db, user, "FORECASTER_RETRAINED", "MODEL", None, {m: v["mape_pct"] for m, v in metrics.items()}, request)
    db.commit()
    return {"metrics": metrics}
