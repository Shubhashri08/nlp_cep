import pytest
from backend.app.gis.hotspots import detect_issue_hotspots
from backend.app.gis.infrastructure_gap import compute_ward_infrastructure_gaps
from backend.app.gis.remote_sensing import calculate_spectral_indices, process_satellite_scene
import numpy as np

def test_hotspot_detection():
    sample_complaints = [
        {"id": 1, "latitude": 19.1197, "longitude": 72.8464, "primary_category": "FLOODING", "original_text": "Waterlogging 1"},
        {"id": 2, "latitude": 19.1205, "longitude": 72.8470, "primary_category": "FLOODING", "original_text": "Waterlogging 2"},
        {"id": 3, "latitude": 19.1189, "longitude": 72.8455, "primary_category": "DRAINAGE", "original_text": "Drain blocked 3"},
        {"id": 4, "latitude": 18.9220, "longitude": 72.8340, "primary_category": "WASTE_MANAGEMENT", "original_text": "Garbage in Colaba"}
    ]
    hotspots = detect_issue_hotspots(sample_complaints, eps_km=1.0, min_samples=2)
    assert len(hotspots) >= 1
    top = hotspots[0]
    assert top["point_count"] >= 2
    assert top["severity_level"] in ("HIGH", "MEDIUM", "LOW")

def test_infrastructure_gap_computation():
    assets = [
        {"asset_type": "WATER_SUPPLY", "capacity": 30.0, "capacity_unit": "MLD"}
    ]
    complaints = {"WATER_SUPPLY": 12, "FLOODING": 8}
    gaps = compute_ward_infrastructure_gaps(
        ward_id=1,
        ward_name="Test Ward",
        population=500000,
        area_sq_km=10.0,
        assets=assets,
        complaints_count_by_cat=complaints
    )
    assert len(gaps) >= 1
    water_gap = next((g for g in gaps if g["sector"] == "Water Supply"), None)
    assert water_gap is not None
    assert water_gap["deficit_amount"] > 0

def test_remote_sensing_indices():
    nir = np.array([[0.5, 0.4], [0.3, 0.6]])
    red = np.array([[0.1, 0.15], [0.2, 0.1]])
    swir = np.array([[0.2, 0.25], [0.3, 0.2]])
    green = np.array([[0.15, 0.2], [0.25, 0.15]])
    
    indices = calculate_spectral_indices(nir, red, swir, green)
    assert "ndvi" in indices
    assert "ndbi" in indices
    assert "ndwi" in indices
    assert -1.0 <= indices["ndvi"].min() <= 1.0
