from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.llm.providers import get_llm
from backend.app.models.entities import Scenario, User, UserRole
from backend.app.scenarios.engine import CRITERIA_WEIGHTS, LEVERS, compare_scenarios, scenario_engine
from backend.app.schemas.dss_schemas import ScenarioCompareRequest, ScenarioCreateRequest, ScenarioResponse
from backend.app.services.analysis import scenario_baseline

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/levers")
def get_levers():
    return {"levers": LEVERS, "criteria_weights": CRITERIA_WEIGHTS}


@router.get("/baseline")
def get_baseline(ward_ids: Optional[List[int]] = Query(None), db: Session = Depends(get_db)):
    try:
        return scenario_baseline(db, ward_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=List[ScenarioResponse])
def list_scenarios(db: Session = Depends(get_db)):
    return db.query(Scenario).order_by(Scenario.created_at.desc()).all()


@router.post("/preview")
def preview_scenario(payload: ScenarioCreateRequest, db: Session = Depends(get_db)):
    """Simulate without saving (used for live slider feedback)."""
    try:
        baseline = scenario_baseline(db, payload.ward_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return scenario_engine.simulate_scenario(baseline, payload.parameters)


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(payload: ScenarioCreateRequest, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_role(UserRole.PLANNER))):
    try:
        baseline = scenario_baseline(db, payload.ward_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    r = scenario_engine.simulate_scenario(baseline, payload.parameters)
    sc = Scenario(title=payload.title, description=payload.description, creator_id=user.id, scope_ward_ids=payload.ward_ids,
                  parameters=r["parameters"], baseline_metrics=r["baseline_metrics"], simulated_metrics=r["simulated_metrics"],
                  delta_metrics=r["delta_metrics"], assumptions=r["assumptions"], score=r["score"],
                  score_breakdown=r["score_breakdown"], capital_cost_cr=r["capital_cost_cr"], evidence_status=r["evidence_status"])
    db.add(sc)
    db.flush()
    audit(db, user, "SCENARIO_CREATED", "SCENARIO", sc.id, {"title": sc.title, "score": sc.score}, request)
    db.commit()
    db.refresh(sc)
    return sc


@router.post("/compare")
def compare(payload: ScenarioCompareRequest, db: Session = Depends(get_db)):
    rows = db.query(Scenario).filter(Scenario.id.in_(payload.scenario_ids)).all()
    if len(rows) != len(set(payload.scenario_ids)):
        raise HTTPException(status_code=404, detail="One or more scenarios not found")
    scs = [{"id": s.id, "title": s.title, "baseline_metrics": s.baseline_metrics, "simulated_metrics": s.simulated_metrics,
            "score": s.score, "score_breakdown": s.score_breakdown, "capital_cost_cr": s.capital_cost_cr, "parameters": s.parameters,
            "scope_ward_ids": s.scope_ward_ids} for s in rows]
    result = compare_scenarios(scs)
    result["scenarios"] = [{"id": s["id"], "title": s["title"], "parameters": s["parameters"], "scope_ward_ids": s["scope_ward_ids"]} for s in scs]
    scopes = {str(s["scope_ward_ids"]) for s in scs}
    result["warning"] = "Scenarios have different spatial scopes; compare scores, not absolute metrics." if len(scopes) > 1 else None
    result["narrative"] = None
    if payload.narrative:
        llm = get_llm()
        if llm.available:
            try:
                result["narrative"] = llm.complete(
                    system="You are an urban planning analyst. Compare scenarios strictly from the JSON provided. "
                           "State trade-offs (service adequacy, flood risk, mobility, cost). Do not invent numbers. Max 150 words.",
                    user=str({"ranking": result["ranking"], "criteria": result["criteria"], "parameters": result["scenarios"]}),
                    max_tokens=350)
            except Exception:
                result["narrative"] = None
        if not result["narrative"]:
            best = result["ranking"][0]
            eff = max(result["ranking"], key=lambda r: r["score_gain_per_100cr"] or -1)
            result["narrative"] = (f"'{best['title']}' achieves the highest service-adequacy score ({best['score']}). "
                                   f"'{eff['title']}' gives the most improvement per ₹100 Cr "
                                   f"({eff['score_gain_per_100cr']} points).")
    return result


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    sc = db.get(Scenario, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return sc


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: int, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_role(UserRole.PLANNER))):
    sc = db.get(Scenario, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if sc.creator_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the creator or an admin can delete this scenario")
    db.delete(sc)
    audit(db, user, "SCENARIO_DELETED", "SCENARIO", scenario_id, None, request)
    db.commit()
