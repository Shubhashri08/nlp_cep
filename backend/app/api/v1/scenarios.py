from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Scenario, User
from backend.app.schemas.dss_schemas import ScenarioCreateRequest, ScenarioResponse
from backend.app.scenarios.engine import scenario_engine
from backend.app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[ScenarioResponse])
def get_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).order_by(Scenario.created_at.desc()).all()
    return scenarios

@router.post("", response_model=ScenarioResponse)
def create_scenario(
    scenario_in: ScenarioCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Baseline city indicators
    baseline = {
        "daily_transit_ridership": 450000,
        "avg_peak_congestion_index": 2.25,
        "flood_risk_score": 0.68,
        "monthly_flood_complaints": 38,
        "total_population": 4440000,
        "required_water_mld": 599.4,
        "required_waste_tpd": 1998.0,
        "uncollected_waste_pct": 18.5
    }
    
    sim_res = scenario_engine.simulate_scenario(baseline, scenario_in.parameters)
    
    scenario_obj = Scenario(
        title=scenario_in.title,
        description=scenario_in.description,
        creator_id=current_user.id,
        parameters=scenario_in.parameters,
        baseline_metrics=sim_res["baseline_metrics"],
        simulated_metrics=sim_res["simulated_metrics"],
        delta_metrics=sim_res["delta_metrics"],
        assumptions=sim_res["assumptions"],
        evidence_status=sim_res["evidence_status"],
        created_at=datetime.now(timezone.utc)
    )
    db.add(scenario_obj)
    db.commit()
    db.refresh(scenario_obj)
    return scenario_obj

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario_by_id(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario
