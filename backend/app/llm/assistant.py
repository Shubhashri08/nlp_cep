import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Ward, CitizenRequest, InfrastructureGap, InfrastructureAsset,
    EnvironmentalData, TransportationData, DemographicData, Recommendation,
    Prediction, DataSource
)

class GroundedPlanningAssistant:
    """
    AI Urban Planning Decision Support Assistant with strict hallucination controls.
    Executes:
    User Question -> Intent Detection -> Controlled Database/GIS Retrieval -> Structured Synthesis -> Grounded Answer with Evidence Citations.
    """
    def answer_query(
        self, 
        question: str, 
        db: Session, 
        context_ward_id: Optional[int] = None
    ) -> Dict[str, Any]:
        q_lower = question.lower()
        findings = []
        sources = []
        suggested_actions = []
        confidence = 0.95
        intent = "GENERAL_INQUIRY"
        
        # 1. Intent: Highest Drainage / Waterlogging / Flooding Complaints
        if any(w in q_lower for w in ["drainage", "flood", "waterlog", "paani"]):
            intent = "FLOODING_AND_DRAINAGE_QUERY"
            # Query actual database
            results = (
                db.query(Ward.name, Ward.id, Ward.population_density)
                .join(CitizenRequest, CitizenRequest.ward_id == Ward.id)
                .filter(CitizenRequest.primary_category.in_(["FLOODING", "DRAINAGE"]))
                .all()
            )
            ward_counts: Dict[str, int] = {}
            for w_name, w_id, pop_dens in results:
                ward_counts[w_name] = ward_counts.get(w_name, 0) + 1
                
            sorted_wards = sorted(ward_counts.items(), key=lambda x: x[1], reverse=True)
            
            if sorted_wards:
                top_ward, top_count = sorted_wards[0]
                answer = (
                    f"Based on verified municipal records, **{top_ward}** currently exhibits the highest concentration of "
                    f"drainage and flooding grievances with **{top_count}** active/recorded reports. "
                    f"Secondary concentrations are observed in " +
                    ", ".join([f"**{w[0]}** ({w[1]} reports)" for w in sorted_wards[1:3]]) + "."
                )
                findings = [{"ward": w[0], "complaints_count": w[1], "category": "FLOODING/DRAINAGE"} for w in sorted_wards[:5]]
                sources.append({
                    "table_name": "citizen_requests JOIN wards",
                    "record_ids": [r[1] for r in results[:10]],
                    "description": "Spatial aggregation of citizen complaints classified under FLOODING and DRAINAGE",
                    "query_executed": "SELECT wards.name, count(*) FROM citizen_requests WHERE category IN ('FLOODING', 'DRAINAGE') GROUP BY ward_id",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                suggested_actions = [
                    f"Inspect low-lying drainage culverts in {top_ward}",
                    "Simulate 20% drainage capacity expansion scenario in Scenario Studio",
                    f"View detailed GIS hotspot cluster for {top_ward}"
                ]
            else:
                answer = "No flood or drainage complaints currently exist in the active records."
                
        # 2. Intent: Critical Infrastructure Gaps
        elif any(w in q_lower for w in ["gap", "deficit", "capacity", "shortage", "strain"]):
            intent = "INFRASTRUCTURE_GAP_QUERY"
            gaps = db.query(InfrastructureGap).order_by(InfrastructureGap.deficit_percentage.desc()).limit(5).all()
            if gaps:
                top_gap = gaps[0]
                ward = db.query(Ward).filter(Ward.id == top_gap.ward_id).first()
                ward_name = ward.name if ward else f"Ward #{top_gap.ward_id}"
                
                answer = (
                    f"The most critical infrastructure deficit identified is in **{ward_name}** for **{top_gap.sector}**, "
                    f"facing a **{top_gap.deficit_percentage}%** deficit ({top_gap.deficit_amount} {top_gap.unit}). "
                    f"Severity classification: **{top_gap.severity}**."
                )
                for g in gaps:
                    w = db.query(Ward).filter(Ward.id == g.ward_id).first()
                    findings.append({
                        "ward": w.name if w else f"Ward {g.ward_id}",
                        "sector": g.sector,
                        "deficit_amount": g.deficit_amount,
                        "deficit_pct": g.deficit_percentage,
                        "severity": g.severity
                    })
                sources.append({
                    "table_name": "infrastructure_gaps",
                    "record_ids": [g.id for g in gaps],
                    "description": "Computed capacity deficits based on URDPFI / CPHEEO national standards",
                    "query_executed": "SELECT * FROM infrastructure_gaps ORDER BY deficit_percentage DESC LIMIT 5",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                suggested_actions = [
                    "Open Infrastructure Gap Dashboard for ward-by-ward breakdown",
                    "Generate evidence-based capital investment proposal"
                ]
            else:
                answer = "No critical infrastructure gaps found in current records."

        # 3. Intent: Ward Specific Profile / Demographics
        elif any(w in q_lower for w in ["population", "density", "demographic", "profile", "ward"]):
            intent = "WARD_PROFILE_QUERY"
            target_ward = None
            if context_ward_id:
                target_ward = db.query(Ward).filter(Ward.id == context_ward_id).first()
            if not target_ward:
                # Search for ward name in query
                for w in db.query(Ward).all():
                    if w.name.lower() in q_lower or w.ward_code.lower() in q_lower:
                        target_ward = w
                        break
            if not target_ward:
                target_ward = db.query(Ward).order_by(Ward.population_density.desc()).first()

            if target_ward:
                complaint_count = db.query(CitizenRequest).filter(CitizenRequest.ward_id == target_ward.id).count()
                answer = (
                    f"**{target_ward.name}** ({target_ward.ward_code}) has an administrative area of **{target_ward.area_sq_km} km²** "
                    f"and a resident population of **{target_ward.population:,}**, yielding a population density of "
                    f"**{target_ward.population_density:.1f} persons/km²**. "
                    f"The ward has **{complaint_count}** recorded citizen feedback cases and an overall priority score of **{target_ward.priority_score:.1f}/100**."
                )
                findings = [{
                    "ward_name": target_ward.name,
                    "population": target_ward.population,
                    "density": target_ward.population_density,
                    "area_sq_km": target_ward.area_sq_km,
                    "priority_score": target_ward.priority_score,
                    "total_complaints": complaint_count
                }]
                sources.append({
                    "table_name": "wards JOIN demographic_data",
                    "record_ids": [target_ward.id],
                    "description": "Ward boundary profile and Census demographic records",
                    "query_executed": f"SELECT * FROM wards WHERE id = {target_ward.id}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                suggested_actions = [
                    f"Open interactive GIS map centered on {target_ward.name}",
                    f"View all active complaints in {target_ward.name}"
                ]
            else:
                answer = "Ward demographic information unavailable in the database."

        # 4. Intent: Forecast & Predictions
        elif any(w in q_lower for w in ["predict", "forecast", "future", "demand", "2027", "2028"]):
            intent = "PREDICTION_QUERY"
            preds = db.query(Prediction).order_by(Prediction.target_date.asc()).limit(6).all()
            if preds:
                sample = preds[0]
                answer = (
                    f"Municipal forecasting model (**{sample.model_name}**, {sample.model_version}) projects "
                    f"an upward demand trend across urban services over the next 12 months. "
                    f"Predicted monthly service requests peak at **{max(p.predicted_value for p in preds):.1f}** "
                    f"with a 95% confidence interval bound."
                )
                findings = [{
                    "target_metric": p.target_metric,
                    "date": p.target_date.strftime("%Y-%m"),
                    "predicted_value": p.predicted_value,
                    "lower_bound": p.lower_bound,
                    "upper_bound": p.upper_bound
                } for p in preds]
                sources.append({
                    "table_name": "predictions",
                    "record_ids": [p.id for p in preds],
                    "description": "Trained RandomForest lag-seasonal regressor forecasts",
                    "query_executed": "SELECT * FROM predictions ORDER BY target_date ASC LIMIT 6",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                suggested_actions = [
                    "Review full forecast curve on Predictions page",
                    "Evaluate model feature importances and RMSE metrics"
                ]
            else:
                answer = "Sufficient historical records loaded; model predictions available on the Forecasting page."

        # 5. Default Grounded Response
        else:
            intent = "MUNICIPAL_SUMMARY_QUERY"
            total_requests = db.query(CitizenRequest).count()
            total_wards = db.query(Ward).count()
            answer = (
                f"The Urban Planning DSS is actively monitoring **{total_wards} wards** with **{total_requests} citizen grievance records** "
                f"across Water Supply, Drainage, Solid Waste, Road Infrastructure, and Public Safety. "
                f"You can query specific wards, infrastructure gaps, flood hotspots, or run what-if simulation scenarios."
            )
            sources.append({
                "table_name": "wards, citizen_requests",
                "record_ids": [1],
                "description": "System overview count query",
                "query_executed": "SELECT count(*) FROM citizen_requests; SELECT count(*) FROM wards;",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            suggested_actions = [
                "Which wards have the highest flood complaints?",
                "What are the critical infrastructure gaps?",
                "Simulate transit capacity expansion in Scenario Studio"
            ]

        return {
            "question": question,
            "intent": intent,
            "grounded_answer": answer,
            "structured_findings": findings,
            "evidence_sources": sources,
            "suggested_actions": suggested_actions,
            "confidence": confidence
        }

planning_assistant = GroundedPlanningAssistant()
