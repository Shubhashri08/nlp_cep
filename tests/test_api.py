from backend.app.llm.providers import LLMProvider, set_llm


def test_health(client):
    assert client.get("/health").json()["status"] == "HEALTHY"


def test_endpoints_require_auth(client):
    for path in ["/api/v1/wards", "/api/v1/analytics/overview", "/api/v1/citizen-requests", "/api/v1/audit"]:
        assert client.get(path).status_code == 401, path


def test_invalid_token_rejected(client):
    r = client.get("/api/v1/wards", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_demo_login_disabled_by_default(client):
    assert client.post("/api/v1/auth/demo-login", json={"role": "ADMIN"}).status_code == 404


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", data={"username": "admin@test.gov.in", "password": "nope"})
    assert r.status_code == 401


def test_rbac(client, viewer_headers, admin_headers):
    assert client.get("/api/v1/audit", headers=viewer_headers).status_code == 403
    assert client.get("/api/v1/audit", headers=admin_headers).status_code == 200
    r = client.post("/api/v1/scenarios", headers=viewer_headers, json={"title": "x" * 5, "parameters": {"new_schools": 2}})
    assert r.status_code == 403


def test_wards_and_geojson(client, viewer_headers):
    wards = client.get("/api/v1/wards", headers=viewer_headers).json()
    assert {w["ward_code"] for w in wards} == {"H/E", "K/W", "M/E"}
    fc = client.get("/api/v1/wards/geojson/all", headers=viewer_headers).json()
    assert fc["type"] == "FeatureCollection" and fc["features"][0]["geometry"]["type"] in ("Polygon", "MultiPolygon")
    prof = client.get(f"/api/v1/wards/{wards[0]['id']}/profile", headers=viewer_headers).json()
    assert prof["demographics"]["population_2011"] > 100_000
    assert prof["infrastructure_gaps"] and prof["priority_factors"]


def test_overview_is_computed(client, viewer_headers):
    d = client.get("/api/v1/analytics/overview", headers=viewer_headers).json()
    assert 450 <= d["total_requests"] <= 560
    assert sum(c["count"] for c in d["top_issue_categories"]) == d["total_requests"]
    assert d["open_requests"] + d["in_progress_requests"] + d["resolved_requests"] <= d["total_requests"]
    assert d["monthly_trend"] and d["language_distribution"]


def test_nlp_analyze(client, viewer_headers):
    r = client.post("/api/v1/nlp/analyze", headers=viewer_headers,
                    json={"text": "Waterlogging and potholes near Bandra Station on Linking Road"})
    assert r.status_code == 200
    res = r.json()
    assert res["primary_category"] in ("FLOODING", "ROAD_INFRASTRUCTURE")
    assert res["is_location_resolved"] and res["geocoding_method"] == "GAZETTEER"


def test_create_and_update_complaint(client, planner_headers):
    r = client.post("/api/v1/citizen-requests", headers=planner_headers,
                    json={"text": "Garbage bins overflowing near Kalina for a week", "latitude": 19.075, "longitude": 72.86})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["request_uid"].startswith("CR-") and body["ward_name"]
    r2 = client.patch(f"/api/v1/citizen-requests/{body['id']}/status", headers=planner_headers, json={"status": "RESOLVED"})
    assert r2.json()["status"] == "RESOLVED" and r2.json()["resolved_at"]


def test_semantic_search(client, viewer_headers):
    r = client.post("/api/v1/citizen-requests/search/semantic", headers=viewer_headers, json={"query": "garbage not collected", "top_k": 5})
    res = r.json()
    assert len(res) == 5 and res[0]["similarity_score"] >= res[-1]["similarity_score"]
    assert sum(x["primary_category"] == "WASTE_MANAGEMENT" for x in res) >= 3


def test_forecast_uses_db_history(client, viewer_headers):
    r = client.get("/api/v1/predictions/forecast?target_metric=water_demand_mld&horizon_months=6", headers=viewer_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["forecast"]) == 6 and len(d["historical_data"]) == 30
    assert d["metrics"]["mape_pct"] < 20
    assert client.get("/api/v1/predictions/forecast?target_metric=bogus", headers=viewer_headers).status_code == 422


def test_infrastructure_demand_projection(client, viewer_headers):
    d = client.get("/api/v1/predictions/infrastructure-demand?target_year=2036", headers=viewer_headers).json()
    assert d["city_totals"]["population_projected"] > sum(w["population_current"] for w in d["wards"])


def test_scenarios_create_and_compare(client, planner_headers):
    base = client.get("/api/v1/scenarios/baseline", headers=planner_headers).json()
    assert base["total_population"] > 1_000_000 and base["health_facilities"] > 0
    ids = []
    for title, params in [("Drain upgrade", {"drainage_upgrade_pct": 50}), ("More clinics", {"new_health_facilities": 25})]:
        r = client.post("/api/v1/scenarios", headers=planner_headers, json={"title": title, "parameters": params})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    cmp = client.post("/api/v1/scenarios/compare", headers=planner_headers, json={"scenario_ids": ids}).json()
    assert len(cmp["ranking"]) == 2 and cmp["narrative"]


def test_recommendations_ranked(client, viewer_headers):
    recs = client.get("/api/v1/recommendations", headers=viewer_headers).json()
    assert recs
    assert recs == sorted(recs, key=lambda r: -r["score"])
    assert len({r["score"] for r in recs}) > 1  # scores are per-intervention, not copied ward priority


def test_growth_and_gaps(client, viewer_headers):
    g = client.get("/api/v1/analytics/urban-growth", headers=viewer_headers).json()
    assert len(g["ward_growth"]) == 3 and all(r["growth_class"] for r in g["ward_growth"])
    gaps = client.get("/api/v1/analytics/infrastructure-gaps", headers=viewer_headers).json()
    assert {x["sector"] for x in gaps} >= {"Healthcare Capacity", "Water Supply", "Drainage & Storm Water"}


def test_document_analysis(client, analyst_headers):
    text = ("Development Plan Report\n\nStorm Water Drainage\nThe low lying areas of Kurla and Bandra East flood every monsoon. "
            "Drains in H/E ward must be widened to handle 50 mm per hour rainfall. Pumping stations are proposed.\n\n"
            "Solid Waste\nGarbage collection in M/E ward near Deonar needs decentralised processing. Waste bins overflow daily.")
    r = client.post("/api/v1/nlp/documents", headers=analyst_headers, data={"text": text, "title": "Test plan"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["summary"] and d["sector_distribution"]
    assert {w["ward_code"] for w in d["wards_mentioned"]} & {"H/E", "M/E"}


def test_assistant_rule_fallback(client, viewer_headers):
    d = client.post("/api/v1/assistant/query", headers=viewer_headers,
                    json={"question": "Which wards have the most flooding complaints?"}).json()
    assert d["provider"] == "rules" and d["intent"] == "COMPLAINT_ANALYSIS"
    assert d["evidence_sources"] and "SELECT" in d["evidence_sources"][0]["query_executed"].upper()


class FakeToolLLM(LLMProvider):
    """Simulates a tool-calling model: requests infrastructure_gaps, then answers from the result."""
    name, model, available = "fake", "fake-1", True

    def run_tools(self, system, question, tools, executor, max_steps=5):
        assert any(t.name == "infrastructure_gaps" for t in tools)
        res = executor("infrastructure_gaps", {"severity": "CRITICAL", "limit": 3})
        top = res["rows"][0] if res["rows"] else None
        return (f"Largest critical gap: {top['sector']} in {top['ward_code']}" if top else "No critical gaps"), \
            [{"tool": "infrastructure_gaps", "arguments": {}, "result": res}]


def test_assistant_llm_tool_loop(client, viewer_headers):
    set_llm(FakeToolLLM())
    try:
        d = client.post("/api/v1/assistant/query", headers=viewer_headers, json={"question": "What are the critical gaps?"}).json()
    finally:
        set_llm(None)
    assert d["provider"] == "fake" and "infrastructure_gaps" in d["intent"]
    assert d["evidence_sources"][0]["table_name"].startswith("infrastructure_gaps")
    assert d["structured_findings"]
