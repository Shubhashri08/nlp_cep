"""Test fixtures: an isolated temporary SQLite DB + model directory, seeded with a compact but real-shaped dataset
(3 real OSM wards with Census figures, OSM assets, synthetic complaints and monthly series)."""
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="dss_test_")
os.environ.update({
    "DSS_ENV_FILE": os.path.join(_TMP, "no.env"),  # never read the developer's .env (API keys) in tests
    "DATABASE_URL": f"sqlite:///{os.path.join(_TMP, 'test.db')}",
    "MODELS_DIR": os.path.join(_TMP, "models"),
    "JWT_SECRET": "test-secret-key-with-sufficient-length-1234567890",
    "DEMO_MODE": "false",
    "NOMINATIM_ENABLED": "false",
    "LLM_PROVIDER": "none",
    "ENV": "dev",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

TEST_WARDS = ["H/E", "K/W", "M/E"]
PASSWORD = "Test@12345"


def _seed():
    from datetime import date

    from backend.app.analytics.demography import project_population
    from backend.app.core.security import get_password_hash
    from backend.app.database.session import Base, SessionLocal, engine
    from backend.app.gis.spatial_ops import find_ward_for_point
    from backend.app.models.entities import (
        CitizenRequest, DemographicData, EnvironmentalData, InfrastructureAsset, LandUseData, RequestEmbedding,
        RequestStatus, SatelliteObservation, ServiceDemandRecord, TransportationData, User, UserRole, Ward,
    )
    from backend.app.nlp.classifier import get_classifier
    from backend.app.nlp.embeddings import get_embedding_engine
    from backend.app.nlp.pipeline import process_text
    from backend.app.services import analysis
    from scripts.ingest.census import load_census_table
    from scripts.ingest.common import external_path, load_json
    from scripts.synthetic import environmental_series, generate_complaints, month_starts, service_series
    from datetime import datetime

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for role in UserRole:
        db.add(User(email=f"{role.value.lower()}@test.gov.in", full_name=role.value.title(), role=role,
                    hashed_password=get_password_hash(PASSWORD)))
    fc = load_json(external_path("mumbai_wards.geojson"))
    census = load_census_table()
    assets = load_json(external_path("osm_assets.json"))
    gaz = load_json(external_path("osm_gazetteer.json"))
    wards = {}
    for f in fc["features"]:
        p = f["properties"]
        if p["ward_code"] not in TEST_WARDS:
            continue
        pop = project_population(census[p["ward_code"]]["population_2011"], 2026)
        w = Ward(ward_code=p["ward_code"], name=f"{p['ward_code']} Ward", localities=p["localities"], area_sq_km=p["area_sq_km"],
                 population=pop, population_density=pop / p["area_sq_km"], boundary_geojson=f["geometry"],
                 center_lat=p["center_lat"], center_lng=p["center_lng"], low_lying_share=0.2, mean_elevation_m=8.0)
        db.add(w)
        db.flush()
        wards[p["ward_code"]] = w
        c = census[p["ward_code"]]
        db.add(DemographicData(ward_id=w.id, census_year=2011, total_population=c["population_2011"], male_population=c["males"],
                               female_population=c["females"], households=c["households"], literacy_rate=c["literacy_rate_pct"],
                               child_population_0_6=c["children_0_6"], workers=c["workers"], growth_rate_percent=0.38))
        db.add(LandUseData(ward_id=w.id, year=2026, residential_pct=40, commercial_pct=8, industrial_pct=5, agricultural_pct=0,
                           forest_green_pct=6, waterbody_pct=1, mixed_use_pct=5, unmapped_pct=35))
        db.add(TransportationData(ward_id=w.id, road_length_km=150, road_density_km_per_sq_km=10, bus_stops_count=40,
                                  daily_transit_ridership=int(pop * 0.7), avg_peak_congestion_index=2.1))
        for year, built, veg in ((2019, 0.55, 0.20), (2026, 0.58, 0.18)):
            db.add(SatelliteObservation(ward_id=w.id, observation_date=datetime(year, 1, 15), coverage_area_sq_km=w.area_sq_km,
                                        mean_ndvi=0.2, mean_ndbi=-0.05, mean_ndwi=-0.3, built_up_area_sq_km=w.area_sq_km * built,
                                        vegetation_area_sq_km=w.area_sq_km * veg, water_area_sq_km=0.2))
    for a in assets:
        if a["ward_code"] in wards:
            db.add(InfrastructureAsset(asset_uid=f"OSM-{a['osm_id']}", name=a["name"][:200], asset_type=a["asset_type"],
                                       subtype=a["subtype"], ward_id=wards[a["ward_code"]].id, latitude=a["lat"], longitude=a["lng"]))
    db.commit()

    months = month_starts(date(2026, 9, 1), 30)
    attrs = []
    for i, (code, w) in enumerate(wards.items()):
        a = {"code": code, "population": w.population, "area": w.area_sq_km, "density": w.population_density,
             "geometry": w.boundary_geojson, "low_lying": 0.2, "literacy": 88.0, "green_share": 6.0, "health_gap": 0.4,
             "transit_gap": 0.5, "trips_per_capita": 1.35, "pt_share": 0.52}
        attrs.append(a)
        s = service_series(a, months, 0.004, seed=i)
        for j, m in enumerate(months):
            for metric in ("water_demand_mld", "waste_generation_tpd", "transit_ridership"):
                db.add(ServiceDemandRecord(ward_id=w.id, metric=metric, month=m, value=s[metric][j], unit="x"))
            db.add(ServiceDemandRecord(ward_id=w.id, metric="water_supplied_mld", month=m, value=w.population * 135e-6 * 0.85, unit="MLD"))
            db.add(ServiceDemandRecord(ward_id=w.id, metric="waste_processed_tpd", month=m, value=s["waste_generation_tpd"][j] * 0.7, unit="TPD"))
        for row in environmental_series(a, months, seed=i):
            db.add(EnvironmentalData(ward_id=w.id, elevation_m=8.0, flood_risk_score=0.5, vegetation_coverage_pct=18.0, **row))
    db.commit()

    get_classifier()  # trains into the temp model dir
    by_ward = {}
    for g in gaz:
        by_ward.setdefault(g.get("ward_code"), []).append(g)
    all_w = list(wards.values())
    for k, rec in enumerate(generate_complaints(attrs, by_ward, date(2026, 9, 1), 30, total=500, seed=5), start=1):
        res = process_text(rec["text"], fallback_lat=rec["fallback_point"][0], fallback_lng=rec["fallback_point"][1],
                           allow_network_geocoding=False, compute_embedding=False)
        w = find_ward_for_point(res["latitude"], res["longitude"], all_w) or wards[rec["ward_code"]]
        db.add(CitizenRequest(request_uid=f"CR-T-{k:05d}", original_text=rec["text"], cleaned_text=res["cleaned_text"],
                              language=res["language"], language_confidence=res["language_confidence"],
                              primary_category=res["primary_category"], categories=res["categories"], confidence=res["confidence"],
                              model_version=res["model_version"], entities=res["entities"], summary=res["summary"],
                              latitude=res["latitude"], longitude=res["longitude"], is_location_resolved=True, ward_id=w.id,
                              status=RequestStatus(rec["status"]), created_at=rec["created_at"].replace(tzinfo=None)))
    db.commit()
    emb = get_embedding_engine()
    for r in db.query(CitizenRequest).all():
        db.add(RequestEmbedding(request_id=r.id, embedding_vector=emb.encode(r.cleaned_text)))
    db.commit()

    analysis.refresh_complaint_volume(db)
    analysis.train_forecaster(db)
    growth = analysis.refresh_predictions(db)
    analysis.compute_growth(db)
    analysis.recompute_gaps(db)
    analysis.recompute_priorities_and_recommendations(db, growth)
    db.close()


@pytest.fixture(scope="session")
def seeded():
    _seed()
    return True


@pytest.fixture(scope="session")
def client(seeded):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as c:
        yield c


def _token(client, role: str) -> dict:
    r = client.post("/api/v1/auth/login", data={"username": f"{role.lower()}@test.gov.in", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return _token(client, "ADMIN")


@pytest.fixture(scope="session")
def planner_headers(client):
    return _token(client, "PLANNER")


@pytest.fixture(scope="session")
def viewer_headers(client):
    return _token(client, "VIEWER")


@pytest.fixture(scope="session")
def analyst_headers(client):
    return _token(client, "ANALYST")
