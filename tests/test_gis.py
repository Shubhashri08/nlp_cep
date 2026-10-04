import numpy as np

from backend.app.analytics.growth import classify_growth, ward_growth_profile
from backend.app.gis.hotspots import detect_issue_hotspots
from backend.app.gis.infrastructure_gap import compute_ward_infrastructure_gaps
from backend.app.gis.remote_sensing import calculate_spectral_indices, classify_land_cover


def test_spectral_indices_and_land_cover():
    nir = np.array([[0.45, 0.10, 0.25]])
    red = np.array([[0.05, 0.08, 0.20]])
    swir = np.array([[0.20, 0.05, 0.30]])
    green = np.array([[0.08, 0.20, 0.15]])
    idx = calculate_spectral_indices(nir, red, swir, green)
    assert idx["ndvi"][0, 0] > 0.7          # dense vegetation
    assert idx["ndwi"][0, 1] > 0.0          # water
    lc = classify_land_cover(idx["ndvi"], idx["ndbi"], idx["ndwi"])
    assert lc["vegetation"][0, 0] and lc["water"][0, 1] and lc["built_up"][0, 2]


def test_spectral_indices_zero_denominator_is_nan():
    z = np.zeros((1, 1))
    assert np.isnan(calculate_spectral_indices(z, z, z, z)["ndvi"][0, 0])


def test_dbscan_hotspots():
    pts = [{"id": i, "latitude": 19.0 + i * 0.0005, "longitude": 72.85, "primary_category": "FLOODING"} for i in range(10)]
    pts += [{"id": 99, "latitude": 19.2, "longitude": 72.95, "primary_category": "TRAFFIC"}]
    spots = detect_issue_hotspots(pts, eps_km=0.3, min_samples=4, return_members=True)
    assert len(spots) == 1
    assert spots[0]["point_count"] == 10 and spots[0]["category"] == "FLOODING"
    assert 99 not in spots[0]["member_ids"]


def test_infrastructure_gaps_use_norms():
    gaps = compute_ward_infrastructure_gaps(
        ward_id=1, population=300_000, area_sq_km=10.0,
        asset_counts={"HEALTHCARE": 10, "EDUCATION_SCHOOL": 30, "BUS_STOP": 12, "RAIL_STATION": 1},
        complaints_by_category={"FLOODING": 25, "DRAINAGE": 10}, built_up_sq_km=7.0, green_share_pct=4.0,
        water_supplied_mld=30.0, waste_processed_tpd=100.0, low_lying_share=0.3)
    by = {g["sector"]: g for g in gaps}
    assert by["Healthcare Capacity"]["required_capacity"] == 20.0       # 300k / 15k
    assert by["Education"]["deficit_amount"] == 30.0                     # 60 required − 30
    assert by["Water Supply"]["required_capacity"] == 40.5               # 300k × 135 lpcd
    assert by["Drainage & Storm Water"]["severity"] == "CRITICAL"        # 30 % below 5 m
    assert by["Open Space"]["evidence"]["open_space_sqm_per_capita"] < 10
    assert all(g["norm_reference"] for g in gaps)


def test_growth_classification():
    assert classify_growth(10.0, -2.0, 40.0, 0.0) == "RAPID_EXPANSION"
    assert classify_growth(1.0, 0.0, 70.0, 0.0) == "DENSIFYING"
    assert classify_growth(-1.0, 15.0, 30.0, 0.0) == "GREENING"
    assert classify_growth(0.5, 0.0, 30.0, 5.0) == "STABLE"
    prof = ward_growth_profile(10.0, {"2019": {"built_up_sq_km": 5.0, "vegetation_sq_km": 3.0, "water_sq_km": 0.1},
                                      "2026": {"built_up_sq_km": 5.6, "vegetation_sq_km": 2.6, "water_sq_km": 0.1}}, 12.0, 0.38)
    assert prof["built_up_change_pct"] == 12.0 and prof["growth_class"] == "RAPID_EXPANSION"
