import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_login_and_auth():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@municipal.gov.in", "password": "Admin@2026#DSS"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"

def test_get_wards():
    response = client.get("/api/v1/wards")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    assert "ward_code" in data[0]

def test_nlp_analyze_endpoint():
    response = client.post(
        "/api/v1/nlp/analyze",
        json={"text": "Waterlogging and potholes near Bandra Station on Linking Road"}
    )
    assert response.status_code == 200
    res = response.json()
    assert "primary_category" in res
    assert "entities" in res
    assert res["is_location_resolved"] is True

def test_analytics_overview():
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] > 0
    assert "top_issue_categories" in data

def test_predictions_forecast():
    response = client.get("/api/v1/predictions/forecast?horizon_months=6")
    assert response.status_code == 200
    data = response.json()
    assert len(data["forecast"]) == 6
    assert "feature_importance" in data

def test_grounded_assistant_query():
    response = client.post(
        "/api/v1/assistant/query",
        json={"question": "Which wards have the highest drainage complaints?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "grounded_answer" in data
    assert len(data["evidence_sources"]) > 0
