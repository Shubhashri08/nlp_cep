"""Database-backed analytics shared by the seed script and the API (recompute endpoints)."""
import logging
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.analytics.growth import summarize_city, ward_growth_profile
from backend.app.analytics.norms import norm
from backend.app.forecasting.demand_model import METRICS, get_forecaster, reset_forecaster
from backend.app.gis.hotspots import detect_issue_hotspots
from backend.app.gis.infrastructure_gap import compute_ward_infrastructure_gaps
from backend.app.models.entities import (
    CitizenRequest, DemographicData, EnvironmentalData, InfrastructureAsset, InfrastructureGap, LandUseData,
    ModelRegistry, Prediction, Provenance, Recommendation, SatelliteObservation, ServiceDemandRecord,
    TransportationData, UrbanGrowth, Ward,
)
from backend.app.recommendations.engine import recommendation_engine

logger = logging.getLogger("urban_planning_dss")


# ----------------------------------------------------------------------------- helpers
def latest_by_ward(db: Session, model, order_col) -> Dict[int, Any]:
    rows = db.query(model).order_by(order_col.asc()).all()
    return {r.ward_id: r for r in rows}  # later rows overwrite earlier → latest wins


def asset_counts(db: Session) -> Dict[int, Dict[str, int]]:
    out: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ward_id, atype, subtype, n in (db.query(InfrastructureAsset.ward_id, InfrastructureAsset.asset_type,
                                                InfrastructureAsset.subtype, func.count(InfrastructureAsset.id))
                                       .group_by(InfrastructureAsset.ward_id, InfrastructureAsset.asset_type, InfrastructureAsset.subtype)):
        out[ward_id][atype] += n
        if atype == "EDUCATION" and subtype == "school":
            out[ward_id]["EDUCATION_SCHOOL"] += n
    return out


def complaints_by_category(db: Session, since: Optional[datetime] = None) -> Dict[int, Dict[str, int]]:
    q = db.query(CitizenRequest.ward_id, CitizenRequest.primary_category, func.count(CitizenRequest.id))
    if since:
        q = q.filter(CitizenRequest.created_at >= since)
    out: Dict[int, Dict[str, int]] = defaultdict(dict)
    for ward_id, cat, n in q.group_by(CitizenRequest.ward_id, CitizenRequest.primary_category):
        if ward_id:
            out[ward_id][cat] = n
    return out


def satellite_by_ward(db: Session) -> Dict[int, Dict[str, Dict[str, float]]]:
    out: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(dict)
    for o in db.query(SatelliteObservation).filter(SatelliteObservation.ward_id.isnot(None)).all():
        out[o.ward_id][str(o.observation_date.year)] = {
            "built_up_sq_km": o.built_up_area_sq_km, "vegetation_sq_km": o.vegetation_area_sq_km,
            "water_sq_km": o.water_area_sq_km, "mean_ndvi": o.mean_ndvi, "mean_ndbi": o.mean_ndbi,
            "provenance": o.provenance,
        }
    return out


def latest_service_value(db: Session, metric: str) -> Dict[int, float]:
    sub = (db.query(ServiceDemandRecord.ward_id, func.max(ServiceDemandRecord.month).label("m"))
           .filter(ServiceDemandRecord.metric == metric).group_by(ServiceDemandRecord.ward_id).subquery())
    rows = (db.query(ServiceDemandRecord.ward_id, ServiceDemandRecord.value)
            .join(sub, (ServiceDemandRecord.ward_id == sub.c.ward_id) & (ServiceDemandRecord.month == sub.c.m))
            .filter(ServiceDemandRecord.metric == metric).all())
    return {w: v for w, v in rows}


# ----------------------------------------------------------------------------- complaint volume series
def refresh_complaint_volume(db: Session) -> int:
    """Aggregates citizen_requests into the monthly complaint_volume series (per ward)."""
    db.query(ServiceDemandRecord).filter(ServiceDemandRecord.metric == "complaint_volume").delete()
    counts = Counter()
    for ward_id, created in db.query(CitizenRequest.ward_id, CitizenRequest.created_at).filter(CitizenRequest.ward_id.isnot(None)):
        counts[(ward_id, date(created.year, created.month, 1))] += 1
    if not counts:
        return 0
    months = sorted({m for _, m in counts})
    ward_ids = sorted({w for w, _ in counts})
    rows = [ServiceDemandRecord(ward_id=w, metric="complaint_volume", month=m, value=float(counts.get((w, m), 0)),
                                unit="complaints", provenance=Provenance.DERIVED.value)
            for w in ward_ids for m in months]
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


# ----------------------------------------------------------------------------- forecasting
def load_histories(db: Session) -> Dict[str, Dict[int, Tuple[List[date], List[float], float]]]:
    density = {w.id: w.population_density for w in db.query(Ward).all()}
    series: Dict[str, Dict[int, List[Tuple[date, float]]]] = defaultdict(lambda: defaultdict(list))
    for r in db.query(ServiceDemandRecord).order_by(ServiceDemandRecord.month.asc()):
        series[r.metric][r.ward_id].append((r.month, r.value))
    out = {}
    for metric, by_ward in series.items():
        out[metric] = {w: ([m for m, _ in pts], [v for _, v in pts], density.get(w, 0.0)) for w, pts in by_ward.items() if len(pts) >= 18}
    return out


def train_forecaster(db: Session) -> Dict[str, Dict[str, float]]:
    reset_forecaster()
    fc = get_forecaster()
    histories = load_histories(db)
    results = fc.train({m: h for m, h in histories.items() if m in METRICS})
    for metric, metrics in results.items():
        db.query(ModelRegistry).filter(ModelRegistry.model_name == f"DemandForecaster:{metric}").update({"status": "ARCHIVED"})
        db.add(ModelRegistry(
            model_name=f"DemandForecaster:{metric}", model_type="DEMAND_FORECASTER", version=fc.model_version,
            training_dataset=f"service_demand_records ({metric}, {len(histories[metric])} wards)",
            parameters={"algorithm": "GradientBoostingRegressor (panel, scale-normalised)", "n_estimators": 300,
                        "max_depth": 3, "learning_rate": 0.05, "features": fc.models[metric].feature_importance and list(fc.models[metric].feature_importance)},
            metrics=metrics, status="ACTIVE", artifact_path=fc.model_path))
    db.commit()
    return results


def forecast_for(db: Session, metric: str, ward_id: Optional[int], horizon: int) -> Dict[str, Any]:
    fc = get_forecaster()
    if not fc.is_ready(metric):
        raise ValueError(f"No trained model for metric '{metric}'. Run the seed / retrain endpoint first.")
    histories = load_histories(db).get(metric, {})
    if ward_id is not None:
        if ward_id not in histories:
            raise ValueError(f"No history for ward {ward_id} / {metric}")
        months, values, density = histories[ward_id]
        preds = fc.models[metric].forecast(months, values, density, horizon)
        history = [{"date": m.strftime("%Y-%m"), "actual_value": round(v, 2)} for m, v in zip(months, values)]
    else:
        # City total: forecast each ward and sum (intervals combined assuming independence)
        per_ward = {w: fc.models[metric].forecast(m, v, d, horizon) for w, (m, v, d) in histories.items()}
        months = next(iter(histories.values()))[0] if histories else []
        totals = defaultdict(float)
        for w, (ms, vs, _) in histories.items():
            for m, v in zip(ms, vs):
                totals[m] += v
        history = [{"date": m.strftime("%Y-%m"), "actual_value": round(totals[m], 2)} for m in sorted(totals)]
        preds = []
        for h in range(horizon):
            pts = [p[h] for p in per_ward.values()]
            mean = sum(p["predicted_value"] for p in pts)
            half = np.sqrt(sum(((p["upper_bound"] - p["predicted_value"])) ** 2 for p in pts))
            preds.append({"date": pts[0]["date"], "predicted_value": round(mean, 2),
                          "lower_bound": round(max(0.0, mean - half), 2), "upper_bound": round(mean + half, 2)})
    model = fc.models[metric]
    return {"history": history, "forecast": preds, "metrics": model.metrics, "feature_importance": model.feature_importance}


def refresh_predictions(db: Session, horizon: int = 12) -> Dict[int, float]:
    """Stores 12-month forecasts per ward/metric and returns forecast demand growth % (mean of metrics) per ward."""
    fc = get_forecaster()
    db.query(Prediction).delete()
    histories = load_histories(db)
    growth: Dict[int, List[float]] = defaultdict(list)
    now = datetime.now(timezone.utc)
    for metric, by_ward in histories.items():
        if not fc.is_ready(metric):
            continue
        model = fc.models[metric]
        for ward_id, (months, values, density) in by_ward.items():
            preds = model.forecast(months, values, density, horizon)
            last12 = float(np.mean(values[-12:]))
            next12 = float(np.mean([p["predicted_value"] for p in preds]))
            if last12 > 0:
                growth[ward_id].append(100 * (next12 - last12) / last12)
            for p in preds:
                db.add(Prediction(target_metric=metric, ward_id=ward_id, target_date=datetime.strptime(p["date"], "%Y-%m"),
                                  predicted_value=p["predicted_value"], lower_bound=p["lower_bound"], upper_bound=p["upper_bound"],
                                  model_name="GradientBoostingPanelForecaster", model_version=fc.model_version,
                                  input_features={"history_months": len(values), "last_observed": months[-1].isoformat()},
                                  feature_importance=model.feature_importance, generated_at=now))
    db.commit()
    return {w: round(float(np.mean(v)), 2) for w, v in growth.items()}


# ----------------------------------------------------------------------------- growth
def compute_growth(db: Session) -> Dict[str, Any]:
    wards = {w.id: w for w in db.query(Ward).all()}
    sat = satellite_by_ward(db)
    demo = latest_by_ward(db, DemographicData, DemographicData.census_year)
    now = datetime.now(timezone.utc)
    last12_start = datetime(now.year - 1, now.month, 1)
    prev12_start = datetime(now.year - 2, now.month, 1)
    recent = dict(db.query(CitizenRequest.ward_id, func.count(CitizenRequest.id)).filter(CitizenRequest.created_at >= last12_start).group_by(CitizenRequest.ward_id).all())
    previous = dict(db.query(CitizenRequest.ward_id, func.count(CitizenRequest.id)).filter(CitizenRequest.created_at >= prev12_start, CitizenRequest.created_at < last12_start).group_by(CitizenRequest.ward_id).all())

    db.query(UrbanGrowth).delete()
    profiles = []
    for wid, w in wards.items():
        epochs = sat.get(wid)
        if not epochs or len(epochs) < 2:
            continue
        cg = round(100 * (recent.get(wid, 0) - previous.get(wid, 0)) / previous[wid], 2) if previous.get(wid) else None
        cagr = (demo[wid].growth_rate_percent if wid in demo else 0.0)
        prof = ward_growth_profile(w.area_sq_km, epochs, cg, cagr)
        prof.update({"ward_id": wid, "ward_code": w.ward_code, "ward_name": w.name,
                     "evidence": next(iter(epochs.values())).get("provenance", "SENTINEL")})
        profiles.append(prof)
        w.growth_class = prof["growth_class"]
        db.add(UrbanGrowth(ward_id=wid, year=prof["end_year"], period_start_year=prof["start_year"],
                           built_up_area_sq_km=prof["built_up_end_sq_km"], built_up_change_sq_km=prof["built_up_change_sq_km"],
                           vegetation_loss_sq_km=round(-prof["vegetation_change_sq_km"], 3),
                           water_body_change_sq_km=prof["water_change_sq_km"], population_cagr_pct=prof["population_cagr_pct"],
                           complaint_growth_pct=cg or 0.0, annual_growth_rate_pct=prof["annual_built_up_growth_pct"],
                           growth_class=prof["growth_class"], evidence=prof["evidence"]))
    db.commit()
    return {"wards": profiles, "city": summarize_city(profiles)}


# ----------------------------------------------------------------------------- gaps
def recompute_gaps(db: Session) -> List[Dict[str, Any]]:
    wards = db.query(Ward).all()
    counts = asset_counts(db)
    complaints = complaints_by_category(db)
    sat = satellite_by_ward(db)
    land = latest_by_ward(db, LandUseData, LandUseData.year)
    water = latest_service_value(db, "water_supplied_mld")
    waste = latest_service_value(db, "waste_processed_tpd")
    db.query(InfrastructureGap).delete()
    all_gaps = []
    for w in wards:
        epochs = sat.get(w.id, {})
        latest = epochs[max(epochs)] if epochs else None
        lu = land.get(w.id)
        gaps = compute_ward_infrastructure_gaps(
            ward_id=w.id, population=w.population, area_sq_km=w.area_sq_km,
            asset_counts=counts.get(w.id, {}), complaints_by_category=complaints.get(w.id, {}),
            built_up_sq_km=latest["built_up_sq_km"] if latest else None,
            green_share_pct=lu.forest_green_pct if lu else None,
            water_supplied_mld=water.get(w.id), waste_processed_tpd=waste.get(w.id),
            land_cover_source=latest["provenance"] if latest else "OSM",
            low_lying_share=w.low_lying_share,
        )
        for g in gaps:
            row = InfrastructureGap(ward_id=w.id, sector=g["sector"], required_capacity=g["required_capacity"],
                                    existing_capacity=g["existing_capacity"], deficit_amount=g["deficit_amount"],
                                    deficit_percentage=g["deficit_percentage"], unit=g["unit"], severity=g["severity"],
                                    complaint_density=g["complaint_density"], norm_reference=g["norm_reference"], evidence=g["evidence"])
            db.add(row)
            db.flush()
            g["id"] = row.id
            all_gaps.append(g)
    db.commit()
    return all_gaps


# ----------------------------------------------------------------------------- flood exposure
def flood_exposure(share_below_5m: float, built_share: float, flood_complaint_density: float, max_density: float) -> float:
    """0–1 index: 50 % low-lying land (DEM), 30 % imperviousness (Sentinel), 20 % observed flood complaints."""
    return round(0.5 * min(1.0, share_below_5m / 0.35) + 0.3 * min(1.0, built_share / 100)
                 + 0.2 * (flood_complaint_density / max_density if max_density else 0.0), 3)


# ----------------------------------------------------------------------------- priorities & recommendations
def recompute_priorities_and_recommendations(db: Session, demand_growth: Optional[Dict[int, float]] = None) -> List[Dict[str, Any]]:
    wards = db.query(Ward).all()
    complaints = complaints_by_category(db)
    env = latest_by_ward(db, EnvironmentalData, EnvironmentalData.recorded_at)
    gaps_by_ward: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for g in db.query(InfrastructureGap).all():
        gaps_by_ward[g.ward_id].append({"id": g.id, "sector": g.sector, "severity": g.severity, "deficit_amount": g.deficit_amount,
                                        "deficit_percentage": g.deficit_percentage, "unit": g.unit,
                                        "norm_reference": g.norm_reference, "evidence": g.evidence})
    growth = {g.ward_id: g for g in db.query(UrbanGrowth).all()}
    if demand_growth is None:
        demand_growth = demand_growth_from_predictions(db)
    months = db.query(func.count(func.distinct(func.strftime("%Y-%m", CitizenRequest.created_at)))).scalar() or 1

    raw = {}
    for w in wards:
        total_c = sum(complaints.get(w.id, {}).values())
        gaps = gaps_by_ward.get(w.id, [])
        raw[w.id] = {
            "complaint_density": 1000 * total_c / max(1, w.population) / months * 12,
            # Low-confidence (incomplete OSM) sectors count at 60 % so data gaps don't masquerade as service gaps
            "infrastructure_deficit": (float(np.average([g["deficit_percentage"] for g in gaps],
                                                        weights=[0.6 if (g.get("evidence") or {}).get("data_confidence") == "LOW" else 1.0 for g in gaps]))
                                       if gaps else 0.0),
            "population_density": w.population_density,
            "flood_exposure": env[w.id].flood_risk_score if w.id in env else 0.0,
            "demand_growth": demand_growth.get(w.id, 0.0),
        }
    scores = recommendation_engine.compute_priority_scores(raw)
    for w in wards:
        score, factors = scores[w.id]
        w.priority_score = score
        w.priority_factors = {"factors": factors, "raw": raw[w.id]}

    ward_inputs = []
    for w in wards:
        g = growth.get(w.id)
        ward_inputs.append({
            "id": w.id, "name": w.name, "code": w.ward_code, "population": w.population, "area_sq_km": w.area_sq_km,
            "gaps": gaps_by_ward.get(w.id, []), "complaints_by_category": complaints.get(w.id, {}),
            "growth": {"built_up_change_pct": (100 * g.built_up_change_sq_km / max(0.01, g.built_up_area_sq_km - g.built_up_change_sq_km)) if g else 0.0},
            "demand_growth_pct": demand_growth.get(w.id, 0.0),
        })
    recs = recommendation_engine.generate(ward_inputs)
    db.query(Recommendation).delete()
    for r in recs:
        db.add(Recommendation(ward_id=r["ward_id"], sector=r["sector"], title=r["title"], recommendation_text=r["recommendation_text"],
                              priority_level=r["priority_level"], score=r["score"], contributing_factors=r["contributing_factors"],
                              supporting_evidence=r["supporting_evidence"], methodology=r["methodology"],
                              estimated_cost_cr=r["estimated_cost_cr"]))
    db.commit()
    return recs


# ----------------------------------------------------------------------------- hotspots
def assign_hotspot_clusters(db: Session, eps_km: float = 0.5, min_samples: int = 6) -> int:
    reqs = db.query(CitizenRequest).filter(CitizenRequest.latitude.isnot(None)).all()
    by_cat = defaultdict(list)
    for r in reqs:
        by_cat[r.primary_category].append(r)
    cluster_offset = 0
    n = 0
    for cat, items in by_cat.items():
        pts = [{"id": r.id, "latitude": r.latitude, "longitude": r.longitude, "primary_category": cat} for r in items]
        spots = detect_issue_hotspots(pts, eps_km=eps_km, min_samples=min_samples, return_members=True)
        for s in spots:
            for rid in s["member_ids"]:
                db.query(CitizenRequest).filter(CitizenRequest.id == rid).update({"cluster_id": cluster_offset + s["cluster_id"] + 1})
            n += 1
        cluster_offset += 1000
    db.commit()
    return n


# ----------------------------------------------------------------------------- scenario baseline
def scenario_baseline(db: Session, ward_ids: Optional[List[int]] = None) -> Dict[str, float]:
    q = db.query(Ward)
    if ward_ids:
        q = q.filter(Ward.id.in_(ward_ids))
    wards = q.all()
    if not wards:
        raise ValueError("No wards in scope")
    ids = [w.id for w in wards]
    pop = sum(w.population for w in wards)
    area = sum(w.area_sq_km for w in wards)
    counts = asset_counts(db)
    trans = latest_by_ward(db, TransportationData, TransportationData.id)
    env = latest_by_ward(db, EnvironmentalData, EnvironmentalData.recorded_at)
    land = latest_by_ward(db, LandUseData, LandUseData.year)
    gaps = db.query(InfrastructureGap).filter(InfrastructureGap.ward_id.in_(ids)).all()
    water = latest_service_value(db, "water_supplied_mld")
    waste = latest_service_value(db, "waste_processed_tpd")
    since = datetime(datetime.now().year - 1, datetime.now().month, 1)
    flood_12m = (db.query(func.count(CitizenRequest.id))
                 .filter(CitizenRequest.ward_id.in_(ids), CitizenRequest.primary_category.in_(["FLOODING", "DRAINAGE"]),
                         CitizenRequest.created_at >= since).scalar() or 0)

    def wavg(values: Dict[int, float]) -> float:
        tot = sum(w.population for w in wards if w.id in values)
        return sum(values[w.id] * w.population for w in wards if w.id in values) / tot if tot else 0.0

    drain_req = sum(g.required_capacity for g in gaps if g.sector == "Drainage & Storm Water")
    drain_have = sum(g.existing_capacity for g in gaps if g.sector == "Drainage & Storm Water")
    runoff = [g.evidence.get("runoff_coefficient") for g in gaps if g.sector == "Drainage & Storm Water" and g.evidence]
    green_area = sum((land[w.id].forest_green_pct if w.id in land else 0) / 100 * w.area_sq_km for w in wards)
    return {
        "scope": "city" if not ward_ids else f"{len(wards)} wards",
        "total_population": pop,
        "area_sq_km": round(area, 2),
        "daily_transit_ridership": sum(trans[i].daily_transit_ridership for i in ids if i in trans),
        "avg_peak_congestion_index": round(wavg({i: trans[i].avg_peak_congestion_index for i in ids if i in trans}), 3),
        "bus_stops": sum(counts.get(i, {}).get("BUS_STOP", 0) for i in ids),
        "flood_risk_score": round(wavg({i: env[i].flood_risk_score for i in ids if i in env}), 3),
        "monthly_flood_complaints": round(flood_12m / 12, 1),
        "drainage_required_m3s": round(drain_req, 2),
        "drainage_capacity_m3s": round(drain_have, 2),
        "runoff_coefficient": round(float(np.mean(runoff)), 3) if runoff else 0.7,
        "required_water_mld": round(pop * norm("water_lpcd") / 1e6, 2),
        "water_supplied_mld": round(sum(water.get(i, 0) for i in ids), 2),
        "water_gap_mld": round(max(0.0, pop * norm("water_lpcd") / 1e6 - sum(water.get(i, 0) for i in ids)), 2),
        "waste_generated_tpd": round(pop * norm("waste_kg_per_capita") / 1000, 2),
        "waste_processed_tpd": round(sum(waste.get(i, 0) for i in ids), 2),
        "uncollected_waste_pct": round(max(0.0, 100 * (1 - sum(waste.get(i, 0) for i in ids) / max(1, pop * norm("waste_kg_per_capita") / 1000))), 1),
        "health_facilities": sum(counts.get(i, {}).get("HEALTHCARE", 0) for i in ids),
        "schools": sum(counts.get(i, {}).get("EDUCATION_SCHOOL", 0) for i in ids),
        "residents_per_health_facility": round(pop / max(1, sum(counts.get(i, {}).get("HEALTHCARE", 0) for i in ids))),
        "residents_per_school": round(pop / max(1, sum(counts.get(i, {}).get("EDUCATION_SCHOOL", 0) for i in ids))),
        "green_share_pct": round(100 * green_area / max(0.01, area), 2),
        "open_space_sqm_per_capita": round(green_area * 1e6 / max(1, pop), 2),
    }


# ----------------------------------------------------------------------------- future infrastructure demand
def demand_growth_from_predictions(db: Session) -> Dict[int, float]:
    """Forecast next-12-month vs last-12-month growth (%) per ward, averaged across metrics."""
    growth: Dict[int, List[float]] = defaultdict(list)
    preds = defaultdict(list)
    for p in db.query(Prediction).all():
        preds[(p.ward_id, p.target_metric)].append(p.predicted_value)
    hist = load_histories(db)
    for (ward_id, metric), vals in preds.items():
        h = hist.get(metric, {}).get(ward_id)
        if h and len(h[1]) >= 12:
            last = float(np.mean(h[1][-12:]))
            if last > 0:
                growth[ward_id].append(100 * (float(np.mean(vals)) - last) / last)
    return {w: round(float(np.mean(v)), 2) for w, v in growth.items()}


def infrastructure_demand_projection(db: Session, target_year: int) -> Dict[str, Any]:
    """Norm-based infrastructure requirements for a future year from Census-based population projections."""
    from backend.app.analytics.demography import project_population
    counts = asset_counts(db)
    demo_2011 = {d.ward_id: d for d in db.query(DemographicData).filter(DemographicData.census_year == 2011).all()}
    water = latest_service_value(db, "water_supplied_mld")
    waste = latest_service_value(db, "waste_processed_tpd")
    land = latest_by_ward(db, LandUseData, LandUseData.year)
    rows = []
    totals = defaultdict(float)
    for w in db.query(Ward).order_by(Ward.ward_code).all():
        base = demo_2011[w.id].total_population if w.id in demo_2011 else w.population
        pop = project_population(base, target_year)
        c = counts.get(w.id, {})
        green_ha = (land[w.id].forest_green_pct if w.id in land else 0) / 100 * w.area_sq_km * 100
        row = {
            "ward_id": w.id, "ward_code": w.ward_code, "ward_name": w.name,
            "population_current": w.population, "population_projected": pop,
            "water_required_mld": round(pop * norm("water_lpcd") / 1e6, 2), "water_supplied_mld": round(water.get(w.id, 0), 2),
            "waste_generated_tpd": round(pop * norm("waste_kg_per_capita") / 1000, 2), "waste_processed_tpd": round(waste.get(w.id, 0), 2),
            "health_facilities_required": int(np.ceil(pop / norm("primary_health_per_pop"))), "health_facilities_existing": c.get("HEALTHCARE", 0),
            "schools_required": int(np.ceil(pop / norm("school_per_pop"))), "schools_existing": c.get("EDUCATION_SCHOOL", 0),
            "open_space_required_ha": round(pop * norm("open_space_sqm_per_capita") / 1e4, 1), "open_space_existing_ha": round(green_ha, 1),
        }
        row["additional_water_mld"] = round(max(0.0, row["water_required_mld"] - row["water_supplied_mld"]), 2)
        row["additional_waste_tpd"] = round(max(0.0, row["waste_generated_tpd"] - row["waste_processed_tpd"]), 2)
        row["additional_health_facilities"] = max(0, row["health_facilities_required"] - row["health_facilities_existing"])
        row["additional_schools"] = max(0, row["schools_required"] - row["schools_existing"])
        for k, v in row.items():
            if isinstance(v, (int, float)) and k not in ("ward_id",):
                totals[k] += v
        rows.append(row)
    return {"target_year": target_year, "method": "Census 2011 population projected with the 2001–2011 Greater Mumbai CAGR; "
            "requirements from CPHEEO / MoHUA / URDPFI norms", "wards": rows,
            "city_totals": {k: round(v, 2) for k, v in totals.items()}}
