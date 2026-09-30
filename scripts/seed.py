"""Builds the Urban Planning DSS database from cached open data + clearly labelled synthetic series.

  python -m scripts.ingest.fetch_all     # once, needs internet (OSM, Census, Sentinel-2, DEM)
  python -m scripts.seed --reset         # builds backend/data/urban_planning.db

Steps: wards (OSM) · census demographics · land use (OSM) · satellite indices (Sentinel-2) · DEM ·
assets (OSM) · transport (OSM + estimates) · synthetic complaints through the NLP pipeline · monthly
service series · model training (classifier, embeddings, forecaster) · growth · gaps · forecasts ·
priorities · recommendations · hotspots · data catalogue with measured quality.
"""
import argparse
import os
import random
import secrets
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone

import numpy as np
from shapely.geometry import shape

from backend.app.analytics.demography import CITY_ANNUAL_GROWTH, project_population
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.database.session import Base, SessionLocal, engine
from backend.app.gis.spatial_ops import find_ward_for_point
from backend.app.models.entities import (
    AuditLog, CitizenRequest, DataQualityReport, DataSource, DemographicData, EnvironmentalData,
    InfrastructureAsset, LandUseData, ModelRegistry, Provenance, RequestEmbedding, RequestStatus,
    SatelliteObservation, Scenario, ServiceDemandRecord, TransportationData, User, UserRole, Ward, Zone,
)
from backend.app.nlp.classifier import get_classifier
from backend.app.nlp.embeddings import get_embedding_engine, reset_embedding_engine
from backend.app.nlp.pipeline import process_text
from backend.app.scenarios.engine import scenario_engine
from backend.app.services import analysis
from scripts.ingest.census import load_census_table
from scripts.ingest.common import external_path, load_json
from scripts.synthetic import environmental_series, generate_complaints, month_starts, service_series

SEED_YEAR = 2026
END_MONTH = date(2026, 9, 1)  # last complete month of synthetic series
HISTORY_MONTHS = 36

DEMO_USERS = [
    ("admin@municipal.gov.in", "Municipal Systems Administrator", UserRole.ADMIN),
    ("planner@municipal.gov.in", "Chief Town Planner", UserRole.PLANNER),
    ("analyst@municipal.gov.in", "GIS & Data Analyst", UserRole.ANALYST),
    ("viewer@municipal.gov.in", "Ward Committee Member", UserRole.VIEWER),
]


def log(msg):
    print(f"[seed] {msg}", flush=True)


def _opt(path):
    p = external_path(path)
    return load_json(p) if os.path.exists(p) else None


def main(reset: bool, complaints_total: int):
    t0 = time.time()
    if reset:
        log("dropping existing tables")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Ward).first():
        log("database already seeded (use --reset to rebuild)")
        return

    wards_fc = _opt("mumbai_wards.geojson")
    if not wards_fc:
        sys.exit("Missing backend/data/external/mumbai_wards.geojson – run `python -m scripts.ingest.fetch_all` first.")
    census = load_census_table()
    landuse = _opt("osm_landuse.json") or {}
    ward_stats = _opt("osm_ward_stats.json") or {}
    assets_osm = _opt("osm_assets.json") or []
    gazetteer = _opt("osm_gazetteer.json") or []
    sentinel = _opt("sentinel/sentinel_indices.json")
    dem = (_opt("dem_ward_stats.json") or {}).get("wards", {})

    # ------------------------------------------------------------------ users
    password = settings.DEMO_PASSWORD or secrets.token_urlsafe(10)
    for email, name, role in DEMO_USERS:
        db.add(User(email=email, full_name=name, role=role, hashed_password=get_password_hash(password), is_active=True))
    db.commit()
    log(f"created {len(DEMO_USERS)} users (password: {'from DEMO_PASSWORD' if settings.DEMO_PASSWORD else password})")

    # ------------------------------------------------------------------ zones & wards
    zones = {}
    for f in wards_fc["features"]:
        zname = f["properties"]["zone"]
        if zname not in zones:
            z = Zone(name=zname, description="BMC administrative zone")
            db.add(z)
            db.flush()
            zones[zname] = z.id
    wards = {}
    for f in wards_fc["features"]:
        p = f["properties"]
        code = p["ward_code"]
        c = census[code]
        pop_now = project_population(c["population_2011"], SEED_YEAR)
        d = dem.get(code, {})
        w = Ward(ward_code=code, name=f"{code} Ward ({p['localities'].split(',')[0].strip()})", localities=p["localities"],
                 zone_id=zones[p["zone"]], osm_relation_id=p["osm_relation_id"], area_sq_km=p["area_sq_km"],
                 population=pop_now, population_density=round(pop_now / p["area_sq_km"], 1), boundary_geojson=f["geometry"],
                 center_lat=p["center_lat"], center_lng=p["center_lng"],
                 mean_elevation_m=d.get("mean_elevation_m"), low_lying_share=d.get("share_below_5m"),
                 boundary_source=Provenance.OSM.value)
        db.add(w)
        db.flush()
        wards[code] = w
        common = dict(male_population=c["males"], female_population=c["females"], households=c["households"],
                      literacy_rate=c["literacy_rate_pct"], child_population_0_6=c["children_0_6"], workers=c["workers"],
                      sc_population=c["sc_population"], st_population=c["st_population"], sex_ratio=c["sex_ratio"])
        db.add(DemographicData(ward_id=w.id, census_year=2011, total_population=c["population_2011"],
                               growth_rate_percent=round(CITY_ANNUAL_GROWTH * 100, 3), provenance=Provenance.CENSUS.value, **common))
        scale = pop_now / c["population_2011"]
        db.add(DemographicData(ward_id=w.id, census_year=SEED_YEAR, total_population=pop_now,
                               growth_rate_percent=round(CITY_ANNUAL_GROWTH * 100, 3), provenance=Provenance.ESTIMATED.value,
                               **{**common, "male_population": int(c["males"] * scale), "female_population": int(c["females"] * scale),
                                  "households": int(c["households"] * scale), "workers": int(c["workers"] * scale)}))
    db.commit()
    log(f"{len(wards)} wards from OSM with Census 2011 demographics (projected to {SEED_YEAR})")

    # ------------------------------------------------------------------ land use, satellite, DEM
    for code, w in wards.items():
        lu = landuse.get(code)
        if lu:
            db.add(LandUseData(ward_id=w.id, year=SEED_YEAR, residential_pct=lu["residential"], commercial_pct=lu["commercial"],
                               industrial_pct=lu["industrial"], agricultural_pct=lu["agricultural"], forest_green_pct=lu["green"],
                               waterbody_pct=lu["water"], mixed_use_pct=lu["mixed"], unmapped_pct=lu["unmapped"],
                               building_count=(ward_stats.get(code) or {}).get("buildings"), provenance=Provenance.OSM.value))
    if sentinel:
        for year, ep in sentinel["epochs"].items():
            obs_date = datetime.strptime(ep["scenes"][0]["date"], "%Y-%m-%d")
            cc = float(np.mean([s["cloud_cover"] or 0 for s in ep["scenes"]]))
            scene_ids = ",".join(s["id"] for s in ep["scenes"])[:200]
            city = ep["city"]
            db.add(SatelliteObservation(ward_id=None, observation_date=obs_date, satellite_name="Sentinel-2 L2A (median composite)",
                                        scene_id=scene_ids, spatial_resolution_m=33.0, coverage_area_sq_km=city["area_sq_km"],
                                        mean_ndvi=city["mean_ndvi"], mean_ndbi=city["mean_ndbi"], mean_ndwi=city["mean_ndwi"],
                                        built_up_area_sq_km=city["built_up_sq_km"], vegetation_area_sq_km=city["vegetation_sq_km"],
                                        water_area_sq_km=city["water_sq_km"], cloud_cover_pct=cc, provenance=Provenance.SENTINEL.value,
                                        raster_file_path=f"sentinel/overlay_{year}_ndvi.png"))
            for code, st in ep["wards"].items():
                if code in wards and st.get("mean_ndvi") is not None:
                    db.add(SatelliteObservation(ward_id=wards[code].id, observation_date=obs_date, satellite_name="Sentinel-2 L2A (median composite)",
                                                scene_id=scene_ids, spatial_resolution_m=33.0, coverage_area_sq_km=st["area_sq_km"],
                                                mean_ndvi=st["mean_ndvi"], mean_ndbi=st["mean_ndbi"], mean_ndwi=st["mean_ndwi"],
                                                built_up_area_sq_km=st["built_up_sq_km"], vegetation_area_sq_km=st["vegetation_sq_km"],
                                                water_area_sq_km=st["water_sq_km"], cloud_cover_pct=cc, provenance=Provenance.SENTINEL.value))
        log(f"satellite observations for epochs {sorted(sentinel['epochs'])}")
    else:
        log("WARNING: no Sentinel-2 results; growth analysis will be unavailable (run scripts.ingest.sentinel)")
    db.commit()

    # ------------------------------------------------------------------ assets
    for a in assets_osm:
        w = wards.get(a["ward_code"])
        if not w:
            continue
        cap, unit = (a["beds"], "beds") if a.get("beds") else (None, None)
        db.add(InfrastructureAsset(asset_uid=f"OSM-{a['osm_id']}", name=a["name"][:200], asset_type=a["asset_type"], subtype=a["subtype"],
                                   capacity=cap, capacity_unit=unit, capacity_estimated=cap is None, ward_id=w.id,
                                   latitude=a["lat"], longitude=a["lng"], osm_id=a["osm_id"], provenance=Provenance.OSM.value))
    db.commit()
    log(f"{len(assets_osm)} infrastructure assets from OSM")

    counts = analysis.asset_counts(db)
    latest_sat = {}
    if sentinel:
        last_epoch = max(sentinel["epochs"])
        latest_sat = {c: st for c, st in sentinel["epochs"][last_epoch]["wards"].items()}

    # ------------------------------------------------------------------ transport (OSM + estimates)
    for code, w in wards.items():
        st = ward_stats.get(code) or {}
        c = counts.get(w.id, {})
        road_km = st.get("road_km_total") or 0.0
        stations = c.get("RAIL_STATION", 0) + c.get("METRO_STATION", 0)
        # Mumbai CMP (2016): ~1.35 trips/capita/day, ~52 % of trips by public transport; access factor from station/stop density
        access = min(1.25, 0.8 + 0.05 * stations + 0.002 * c.get("BUS_STOP", 0))
        ridership = int(w.population * 1.35 * 0.52 * access)
        road_per_1000 = road_km / max(1, w.population / 1000)
        congestion = round(min(3.0, max(1.1, 1.0 + 1.6 * (w.population_density / 60000) + 0.6 / max(0.15, road_per_1000) * 0.1)), 3)
        db.add(TransportationData(ward_id=w.id, year=SEED_YEAR, road_length_km=road_km,
                                  road_density_km_per_sq_km=round(road_km / w.area_sq_km, 2), road_km_by_class=st.get("road_km_by_class"),
                                  bus_stops_count=c.get("BUS_STOP", 0), rail_stations_count=c.get("RAIL_STATION", 0),
                                  metro_stations_count=c.get("METRO_STATION", 0), daily_transit_ridership=ridership,
                                  avg_peak_congestion_index=congestion,
                                  provenance="OSM+ESTIMATED" if st else "ESTIMATED"))
    db.commit()
    log("transport indicators (OSM network + CMP-based ridership estimates)")

    # ------------------------------------------------------------------ monthly environment & service series (synthetic)
    months = month_starts(END_MONTH, HISTORY_MONTHS)
    rng = random.Random(3)
    ward_attrs = {}
    for i, (code, w) in enumerate(sorted(wards.items())):
        lu = landuse.get(code, {})
        sat = latest_sat.get(code, {})
        built_share = 100 * sat["built_up_sq_km"] / w.area_sq_km if sat else 55.0
        lit = census[code]["literacy_rate_pct"]
        attrs = {
            "code": code, "population": w.population, "area": w.area_sq_km, "density": w.population_density,
            "geometry": w.boundary_geojson, "low_lying": w.low_lying_share or 0.1, "literacy": lit,
            "green_share": lu.get("green", 5.0), "industrial_share": lu.get("industrial", 2.0), "built_share": built_share,
            "health_gap": max(0.0, 1 - counts.get(w.id, {}).get("HEALTHCARE", 0) * 15000 / w.population),
            "transit_gap": max(0.0, 1 - (counts.get(w.id, {}).get("BUS_STOP", 0) / max(1, 4 * (sat.get("built_up_sq_km") or w.area_sq_km * 0.6)))),
            "consumption_lpcd": 150 + rng.uniform(-8, 8),
            "trips_per_capita": 1.35, "pt_share": 0.52,
        }
        ward_attrs[code] = attrs
        for row in environmental_series(attrs, months, seed=100 + i):
            db.add(EnvironmentalData(ward_id=w.id, elevation_m=w.mean_elevation_m or 10.0, flood_risk_score=0.0,
                                     vegetation_coverage_pct=round(100 * (sat.get("vegetation_sq_km") or 0) / w.area_sq_km, 2) if sat else lu.get("green", 0),
                                     provenance=Provenance.SYNTHETIC.value, **row))
        series = service_series(attrs, months, CITY_ANNUAL_GROWTH, seed=200 + i)
        # Supply-side records: equity-weighted – lower-literacy wards (proxy for informal settlements) receive less
        supply_ratio = min(1.05, max(0.72, 0.8 + (lit - 83) / 60 + rng.uniform(-0.05, 0.05)))
        processing_ratio = min(1.0, max(0.6, 0.72 + (lit - 83) / 50 + rng.uniform(-0.06, 0.06)))
        for j, m in enumerate(months):
            for metric, unit in (("water_demand_mld", "MLD"), ("waste_generation_tpd", "TPD"), ("transit_ridership", "trips/day")):
                db.add(ServiceDemandRecord(ward_id=w.id, metric=metric, month=m, value=series[metric][j], unit=unit,
                                           provenance=Provenance.SYNTHETIC.value))
            req_water = w.population * 135 / 1e6
            db.add(ServiceDemandRecord(ward_id=w.id, metric="water_supplied_mld", month=m, unit="MLD", provenance=Provenance.SYNTHETIC.value,
                                       value=round(req_water * supply_ratio * (0.97 if m.month in (4, 5) else 1.0), 3)))
            db.add(ServiceDemandRecord(ward_id=w.id, metric="waste_processed_tpd", month=m, unit="TPD", provenance=Provenance.SYNTHETIC.value,
                                       value=round(series["waste_generation_tpd"][j] * processing_ratio, 3)))
    db.commit()
    log(f"{HISTORY_MONTHS}-month environmental and service-demand series (synthetic, labelled)")

    # ------------------------------------------------------------------ NLP models
    clf = get_classifier()
    clf_metrics = clf.train()
    log(f"classifier trained: gold-set micro-F1 {clf_metrics['gold_set']['micro_f1']}, held-out micro-F1 {clf_metrics['held_out']['micro_f1']}")

    # ------------------------------------------------------------------ complaints through the NLP pipeline
    gaz_by_ward = defaultdict(list)
    for g in gazetteer:
        if g.get("ward_code"):
            gaz_by_ward[g["ward_code"]].append(g)
    synth = generate_complaints(list(ward_attrs.values()), gaz_by_ward, END_MONTH, HISTORY_MONTHS, total=complaints_total)
    all_wards = list(wards.values())
    code_to_id = {c: w.id for c, w in wards.items()}
    correct = 0
    t_nlp = time.time()
    for k, rec in enumerate(synth, start=1):
        gps = rec["gps"]
        res = process_text(rec["text"], fallback_lat=gps[0] if gps else None, fallback_lng=gps[1] if gps else None,
                           allow_network_geocoding=False, compute_embedding=False)
        if not res["is_location_resolved"]:
            # 20 % of residents without GPS also typed no recognisable place: ward office records the ward
            lat, lng = None, None
        else:
            lat, lng = res["latitude"], res["longitude"]
        ward = find_ward_for_point(lat, lng, all_wards) if lat is not None else None
        ward_id = ward.id if ward else code_to_id[rec["ward_code"]]
        correct += res["primary_category"] == rec["true_category"]
        created = rec["created_at"].replace(tzinfo=None)
        db.add(CitizenRequest(
            request_uid=f"CR-{created.year}-{k:06d}", original_text=rec["text"], cleaned_text=res["cleaned_text"],
            language=res["language"], language_confidence=res["language_confidence"], primary_category=res["primary_category"],
            categories=res["categories"], confidence=res["confidence"], model_version=res["model_version"],
            entities=res["entities"], summary=res["summary"], raw_location_text=res["raw_location_text"],
            latitude=lat, longitude=lng, geocoding_confidence=res["geocoding_confidence"], geocoding_method=res["geocoding_method"],
            is_location_resolved=lat is not None, address=res["address"], ward_id=ward_id, source=rec["source"],
            provenance=Provenance.SYNTHETIC.value, status=RequestStatus(rec["status"]), created_at=created,
            resolved_at=rec["resolved_at"].replace(tzinfo=None) if rec["resolved_at"] else None))
        if k % 1000 == 0:
            db.commit()
    db.commit()
    synth_acc = correct / max(1, len(synth))
    log(f"{len(synth)} synthetic complaints processed by the NLP pipeline in {time.time() - t_nlp:.0f}s "
        f"(classifier agreement with generator label: {synth_acc:.1%})")

    # Embeddings: fit LSA on corpus + complaints, then store vectors
    reset_embedding_engine()
    emb = get_embedding_engine()
    texts = [r.cleaned_text for r in db.query(CitizenRequest.cleaned_text)]
    emb_info = emb.fit(texts)
    reqs = db.query(CitizenRequest).all()
    vecs = emb.encode_many([r.cleaned_text for r in reqs])
    db.bulk_save_objects([RequestEmbedding(request_id=r.id, embedding_vector=[round(float(x), 5) for x in v], embedding_model=emb.model_name)
                          for r, v in zip(reqs, vecs)])
    db.commit()
    log(f"embeddings: {emb_info}")

    db.add(ModelRegistry(model_name="GrievanceClassifier", model_type="NLP_CLASSIFIER", version=clf.model_version,
                         training_dataset=f"Generated multilingual corpus ({clf_metrics['training_samples']} samples) + hand-written gold set",
                         parameters={"features": clf_metrics["features"], "estimator": "OneVsRest LogisticRegression(C=8, balanced)", "threshold": 0.35},
                         metrics={**clf_metrics, "synthetic_complaint_agreement": round(synth_acc, 4)}, artifact_path=clf.model_path))
    db.add(ModelRegistry(model_name="SemanticEmbeddings", model_type="EMBEDDING", version=emb.model_name,
                         training_dataset=f"classifier corpus + {len(texts)} complaints", parameters={"method": "TF-IDF → TruncatedSVD"},
                         metrics={"dimensions": emb_info["dimensions"], "explained_variance": emb_info["explained_variance"]},
                         artifact_path=emb.artifact_path))
    db.add(ModelRegistry(model_name="HybridNER", model_type="NER", version="v2.0-gazetteer-patterns",
                         training_dataset="OSM gazetteer (Greater Mumbai) + domain lexicons", parameters={"method": "gazetteer longest-match + patterns"},
                         metrics={"gazetteer_entries": len(gazetteer)}))
    db.commit()

    # ------------------------------------------------------------------ analytics
    analysis.refresh_complaint_volume(db)
    fc_metrics = analysis.train_forecaster(db)
    log("forecasters: " + ", ".join(f"{m} MAPE {v['mape_pct']}% (naive {v['seasonal_naive_mape_pct']}%)" for m, v in fc_metrics.items()))
    demand_growth = analysis.refresh_predictions(db)

    growth = analysis.compute_growth(db)
    log(f"urban growth: {growth['city'].get('class_counts')}")

    # Flood exposure (DEM + Sentinel imperviousness + flood complaints) written onto the environmental records
    fc_counts = analysis.complaints_by_category(db)
    dens = {w.id: (fc_counts.get(w.id, {}).get("FLOODING", 0) + fc_counts.get(w.id, {}).get("DRAINAGE", 0)) / w.area_sq_km for w in wards.values()}
    max_d = max(dens.values()) if dens else 1.0
    for code, w in wards.items():
        sat = latest_sat.get(code)
        built_share = 100 * sat["built_up_sq_km"] / w.area_sq_km if sat else 55.0
        base = analysis.flood_exposure(w.low_lying_share or 0.1, built_share, dens[w.id], max_d)
        for e in db.query(EnvironmentalData).filter(EnvironmentalData.ward_id == w.id):
            rain_factor = 0.55 + 0.45 * min(1.0, e.rainfall_mm / 600)
            e.flood_risk_score = round(min(1.0, base * rain_factor / 1.0), 3) if e.rainfall_mm > 50 else round(base * 0.5, 3)
    # Keep the annual (worst-month) exposure on the latest record so ward profiles show the planning value
    for w in wards.values():
        latest_env = db.query(EnvironmentalData).filter(EnvironmentalData.ward_id == w.id).order_by(EnvironmentalData.recorded_at.desc()).first()
        worst = max(e.flood_risk_score for e in db.query(EnvironmentalData).filter(EnvironmentalData.ward_id == w.id))
        latest_env.flood_risk_score = worst
    db.commit()

    gaps = analysis.recompute_gaps(db)
    log(f"{len(gaps)} infrastructure gap assessments")
    recs = analysis.recompute_priorities_and_recommendations(db, demand_growth)
    log(f"{len(recs)} recommendations; ward priority scores updated")
    n_spots = analysis.assign_hotspot_clusters(db)
    log(f"{n_spots} category hotspots assigned")

    # ------------------------------------------------------------------ data catalogue & quality
    _catalogue(db, wards_fc, census, assets_osm, sentinel, dem, landuse, ward_stats)

    # ------------------------------------------------------------------ example scenarios
    planner = db.query(User).filter(User.role == UserRole.PLANNER).first()
    baseline = analysis.scenario_baseline(db)
    examples = [
        ("Monsoon resilience package", "Upgrade 40 % of the drainage gap and add green cover.", {"drainage_upgrade_pct": 40, "green_cover_increase_pct": 2}),
        ("Transit-first growth", "Absorb 10 % growth with 25 % more bus capacity and 500 new stops.",
         {"population_growth_rate_pct": 10, "transit_capacity_delta_pct": 25, "new_bus_stops": 500}),
        ("Social infrastructure catch-up", "New dispensaries and schools plus water augmentation.",
         {"new_health_facilities": 150, "new_schools": 200, "water_supply_augmentation_mld": 150}),
    ]
    for title, desc, params in examples:
        r = scenario_engine.simulate_scenario(baseline, params)
        db.add(Scenario(title=title, description=desc, creator_id=planner.id, scope_ward_ids=None, parameters=r["parameters"],
                        baseline_metrics=r["baseline_metrics"], simulated_metrics=r["simulated_metrics"], delta_metrics=r["delta_metrics"],
                        assumptions=r["assumptions"], score=r["score"], score_breakdown=r["score_breakdown"],
                        capital_cost_cr=r["capital_cost_cr"], evidence_status=r["evidence_status"]))
    db.add(AuditLog(user_id=None, action="DATABASE_SEEDED", resource_type="SYSTEM", details={"duration_s": round(time.time() - t0, 1)}))
    db.commit()
    db.close()
    log(f"done in {time.time() - t0:.0f}s -> {settings.DATABASE_URL}")


def _quality(db, source_id, total, missing, geo_valid, freshness_days, dup_rate=0.0, consistency=1.0):
    completeness = 1 - missing / max(1, total)
    overall = round(0.35 * completeness + 0.25 * geo_valid + 0.15 * (1 - dup_rate) + 0.15 * consistency + 0.10 * max(0.0, 1 - freshness_days / 3650), 3)
    db.add(DataQualityReport(data_source_id=source_id, total_records=total, completeness_score=round(completeness, 3), duplicate_rate=round(dup_rate, 4),
                             missing_values_count=missing, geographic_validity_rate=round(geo_valid, 3), freshness_days=freshness_days,
                             consistency_score=round(consistency, 3), overall_quality_score=overall))
    return overall


def _catalogue(db, wards_fc, census, assets_osm, sentinel, dem, landuse, ward_stats):
    now = datetime.now(timezone.utc)
    census_total = sum(c["population_2011"] for c in census.values())
    unnamed = sum(1 for a in assets_osm if a["name"].startswith("Unnamed"))
    n_req = db.query(CitizenRequest).count()
    unresolved = db.query(CitizenRequest).filter(CitizenRequest.latitude.is_(None)).count()
    entries = [
        dict(source_name="BMC Ward Boundaries (admin_level 10)", provider="OpenStreetMap contributors", dataset_type="GeoJSON polygons",
             provenance="OSM", source_url="https://www.openstreetmap.org/relation/7885399", license="ODbL 1.0",
             geographic_scope="Greater Mumbai (24 wards)", update_frequency="On demand (Overpass API)",
             schema_info={"fields": ["ward_code", "geometry", "area_sq_km"]}, notes="Relation members assembled into polygons with shapely.",
             q=(len(wards_fc["features"]), 24 - len(wards_fc["features"]), 1.0, 30)),
        dict(source_name="Census 2011 Primary Census Abstract (ward-wise)", provider="Office of the Registrar General & Census Commissioner, India (via OpenCity)",
             dataset_type="CSV", provenance="CENSUS", source_url="https://data.opencity.in/dataset/mumbai-ward-wise-census-data",
             license="Public domain (GoI)", geographic_scope="Greater Mumbai", update_frequency="Decennial",
             schema_info={"fields": ["population", "households", "literates", "workers", "sc", "st"]},
             notes=f"Aggregated from census wards to BMC wards; total {census_total:,} matches official 12,442,373. Projected to {SEED_YEAR} with 2001–11 CAGR.",
             q=(len(census), 0, 1.0, (now.year - 2011) * 365)),
        dict(source_name="OSM amenities, transit stops & utilities", provider="OpenStreetMap contributors", dataset_type="Points",
             provenance="OSM", source_url="https://overpass-api.de", license="ODbL 1.0", geographic_scope="Greater Mumbai",
             update_frequency="On demand", schema_info={"asset_types": sorted({a['asset_type'] for a in assets_osm})},
             notes="Volunteered data: facility coverage (e.g. bus stops, schools) is known to be incomplete.",
             q=(len(assets_osm), unnamed, 1.0, 30)),
        dict(source_name="OSM land use & road network statistics", provider="OpenStreetMap contributors", dataset_type="Polygons / server-side stats",
             provenance="OSM", source_url="https://overpass-api.de", license="ODbL 1.0", geographic_scope="Greater Mumbai",
             update_frequency="On demand", schema_info={"landuse_buckets": ["residential", "commercial", "industrial", "green", "water", "mixed"]},
             notes="Land-use shares clipped to ward polygons; 'unmapped' is area without landuse tags.",
             q=(len(landuse) + len(ward_stats), 48 - len(landuse) - len(ward_stats), 1.0, 30)),
    ]
    if sentinel:
        scenes = sum(len(e["scenes"]) for e in sentinel["epochs"].values())
        valid = float(np.mean([e["city"]["valid_fraction"] for e in sentinel["epochs"].values()]))
        entries.append(dict(source_name="Sentinel-2 L2A multispectral composites", provider="ESA Copernicus via Microsoft Planetary Computer",
                            dataset_type="Satellite raster (B03/B04/B08/B11/SCL)", provenance="SENTINEL",
                            source_url="https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", license="Copernicus open licence",
                            geographic_scope="Greater Mumbai", update_frequency="5-day revisit; composited per dry season",
                            schema_info={"epochs": sorted(sentinel["epochs"]), "indices": ["NDVI", "NDBI", "NDWI"], "grid_deg": sentinel["grid_resolution_deg"]},
                            notes=f"{scenes} scenes; SCL cloud masking, per-pixel median, PIF radiometric normalisation between epochs.",
                            q=(scenes, 0, valid, 240)))
    if dem:
        entries.append(dict(source_name="Copernicus DEM GLO-30", provider="ESA via Microsoft Planetary Computer", dataset_type="Elevation raster",
                            provenance="SENTINEL", source_url="https://planetarycomputer.microsoft.com/dataset/cop-dem-glo-30",
                            license="Copernicus DEM licence", geographic_scope="Greater Mumbai", update_frequency="Static (2011–2015 acquisition)",
                            schema_info={"fields": ["mean_elevation_m", "share_below_5m"]}, notes="Surface model (includes buildings); used for low-lying exposure.",
                            q=(len(dem), 24 - len(dem), 1.0, 3650)))
    entries += [
        dict(source_name="Citizen grievances (demonstration)", provider="Generated by scripts/synthetic.py", dataset_type="Text + point records",
             provenance="SYNTHETIC", source_url=None, license="n/a", geographic_scope="Greater Mumbai",
             update_frequency="New submissions via app", schema_info={"records": n_req},
             notes="No open, geolocated Mumbai grievance dataset exists; texts are synthetic but locations use real OSM places and "
                   "category rates follow real ward attributes (DEM, Census, OSM gaps). Replace via the import endpoint.",
             q=(n_req, unresolved, 1 - unresolved / max(1, n_req), 0)),
        dict(source_name="Monthly service demand & supply series (demonstration)", provider="Generated by scripts/synthetic.py",
             dataset_type="Time series", provenance="SYNTHETIC", source_url=None, license="n/a", geographic_scope="Greater Mumbai",
             update_frequency="Monthly", schema_info={"metrics": ["water_demand_mld", "water_supplied_mld", "waste_generation_tpd", "waste_processed_tpd", "transit_ridership"]},
             notes="Driven by Census population, CPHEEO / MoHUA norms and Mumbai CMP trip rates; ward supply levels are illustrative.",
             q=(db.query(ServiceDemandRecord).count(), 0, 1.0, 0)),
        dict(source_name="Monthly environmental readings (demonstration)", provider="Generated by scripts/synthetic.py (IMD climatology based)",
             dataset_type="Time series", provenance="SYNTHETIC", source_url=None, license="n/a", geographic_scope="Greater Mumbai",
             update_frequency="Monthly", schema_info={"fields": ["rainfall_mm", "aqi_pm25", "aqi_pm10", "avg_temperature_c", "flood_risk_score"]},
             notes="Rainfall follows IMD Santacruz normals; PM2.5 follows typical seasonality. Flood risk combines real DEM + Sentinel inputs.",
             q=(db.query(EnvironmentalData).count(), 0, 1.0, 0)),
    ]
    for e in entries:
        total, missing, geo_valid, fresh = e.pop("q")
        src = DataSource(date_collected=now, **e)
        db.add(src)
        db.flush()
        src.quality_score = _quality(db, src.id, total, missing, geo_valid, fresh)
    db.commit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop and rebuild all tables")
    ap.add_argument("--complaints", type=int, default=3200)
    args = ap.parse_args()
    main(args.reset, args.complaints)
