from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.models.entities import RequestStatus, UserRole

ORM = ConfigDict(from_attributes=True)


# --- Auth ---------------------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    email: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    model_config = ORM
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class DemoLoginRequest(BaseModel):
    role: UserRole


# --- NLP -----------------------------------------------------------------------------------------
class EntityItem(BaseModel):
    text: str
    label: str
    confidence: float
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    source: Optional[str] = None
    ward_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class CategoryScore(BaseModel):
    category: str
    confidence: float


class NLPAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class NLPAnalysisResult(BaseModel):
    original_text: str
    cleaned_text: str
    language: str
    language_confidence: float
    primary_category: str
    confidence: float
    categories: List[CategoryScore]
    entities: List[EntityItem]
    summary: str
    resolved_location: Optional[str] = None
    resolved_lat: Optional[float] = None
    resolved_lng: Optional[float] = None
    geocoding_confidence: float = 0.0
    geocoding_method: str = "NONE"
    is_location_resolved: bool = False
    ward_id: Optional[int] = None
    ward_name: Optional[str] = None
    model_version: str


class CitizenRequestCreate(BaseModel):
    text: str = Field(min_length=5, max_length=5000)
    source: Optional[str] = "Web Portal"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    ward_id: Optional[int] = None


class CitizenRequestResponse(BaseModel):
    model_config = ORM
    id: int
    request_uid: Optional[str]
    original_text: str
    cleaned_text: Optional[str]
    language: str
    language_confidence: float
    primary_category: str
    categories: List[Dict[str, Any]]
    confidence: float
    model_version: str
    entities: List[Dict[str, Any]]
    summary: Optional[str]
    raw_location_text: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    geocoding_confidence: float
    geocoding_method: Optional[str] = None
    is_location_resolved: bool
    address: Optional[str]
    ward_id: Optional[int]
    ward_name: Optional[str] = None
    source: str
    provenance: Optional[str] = None
    status: RequestStatus
    cluster_id: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime] = None


class CitizenRequestPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[CitizenRequestResponse]


class StatusUpdate(BaseModel):
    status: RequestStatus


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(10, ge=1, le=50)
    category: Optional[str] = None
    ward_id: Optional[int] = None


class SemanticSearchResult(BaseModel):
    id: int
    request_uid: Optional[str]
    text: str
    primary_category: str
    similarity_score: float
    ward_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    status: Optional[str] = None
    created_at: datetime


# --- Wards / GIS ------------------------------------------------------------------------------------
class WardSummary(BaseModel):
    id: int
    ward_code: str
    name: str
    localities: Optional[str] = None
    zone_name: Optional[str] = None
    area_sq_km: float
    population: int
    population_density: float
    center_lat: float
    center_lng: float
    priority_score: float
    growth_class: Optional[str] = None
    mean_elevation_m: Optional[float] = None
    low_lying_share: Optional[float] = None
    total_complaints: int
    open_complaints: int = 0
    critical_gaps_count: int


class WardProfile(BaseModel):
    ward_info: WardSummary
    boundary_geojson: Dict[str, Any]
    priority_factors: List[Dict[str, Any]] = []
    demographics: Optional[Dict[str, Any]] = None
    asset_counts: Dict[str, int] = {}
    infrastructure_gaps: List[Dict[str, Any]] = []
    environmental_indicators: Optional[Dict[str, Any]] = None
    transportation_indicators: Optional[Dict[str, Any]] = None
    land_use: Optional[Dict[str, Any]] = None
    satellite: List[Dict[str, Any]] = []
    growth: Optional[Dict[str, Any]] = None
    top_complaint_categories: List[Dict[str, Any]] = []
    recent_complaints: List[CitizenRequestResponse] = []
    recommendations: List[Dict[str, Any]] = []
    predicted_demand: List[Dict[str, Any]] = []


# --- Analytics ---------------------------------------------------------------------------------------
class DashboardOverview(BaseModel):
    total_requests: int
    open_requests: int
    in_progress_requests: int
    resolved_requests: int
    median_resolution_days: Optional[float]
    high_priority_wards_count: int
    total_infrastructure_gaps: int
    critical_gaps_count: int
    avg_quality_score: float
    top_issue_categories: List[Dict[str, Any]]
    ward_complaint_rankings: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]
    language_distribution: List[Dict[str, Any]]
    active_hotspots_count: int
    population_total: int
    data_provenance: List[Dict[str, Any]]


# --- Forecasting ---------------------------------------------------------------------------------------
class ForecastPoint(BaseModel):
    date: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    target_metric: str
    metric_label: str
    unit: str
    ward_id: Optional[int]
    ward_name: Optional[str]
    model_name: str
    model_version: str
    historical_data: List[Dict[str, Any]]
    forecast: List[ForecastPoint]
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    provenance: str
    generated_at: datetime


# --- Scenarios -------------------------------------------------------------------------------------------
class ScenarioCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    ward_ids: Optional[List[int]] = None
    parameters: Dict[str, float] = Field(
        ..., json_schema_extra={"example": {"transit_capacity_delta_pct": 25.0, "drainage_upgrade_pct": 40.0,
                                            "population_growth_rate_pct": 8.0, "new_health_facilities": 20}})


class ScenarioResponse(BaseModel):
    model_config = ORM
    id: int
    title: str
    description: str
    scope_ward_ids: Optional[List[int]] = None
    parameters: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    simulated_metrics: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    assumptions: List[str]
    score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    capital_cost_cr: Optional[float] = None
    evidence_status: str
    created_at: datetime


class ScenarioCompareRequest(BaseModel):
    scenario_ids: List[int] = Field(min_length=2, max_length=4)
    narrative: bool = True


# --- Recommendations -----------------------------------------------------------------------------------------
class RecommendationResponse(BaseModel):
    id: int
    ward_id: int
    ward_name: str
    ward_code: str
    sector: str
    title: str
    recommendation_text: str
    priority_level: str
    score: float
    estimated_cost_cr: Optional[float] = None
    contributing_factors: List[Dict[str, Any]]
    supporting_evidence: List[Dict[str, Any]]
    methodology: str
    status: str
    llm_brief: Optional[str] = None
    created_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(PROPOSED|APPROVED|REJECTED|IN_PROGRESS)$")


# --- Assistant -------------------------------------------------------------------------------------------------
class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    context_ward_id: Optional[int] = None


class EvidenceSource(BaseModel):
    table_name: str
    record_ids: List[int]
    description: str
    query_executed: str
    timestamp: str


class AssistantQueryResponse(BaseModel):
    question: str
    intent: str
    grounded_answer: str
    structured_findings: List[Dict[str, Any]]
    evidence_sources: List[EvidenceSource]
    suggested_actions: List[str]
    confidence: float
    provider: str = "rules"
    model: Optional[str] = None


# --- Documents ----------------------------------------------------------------------------------------------------
class PlanningDocumentResponse(BaseModel):
    model_config = ORM
    id: int
    title: str
    filename: Optional[str]
    text_length: int
    page_count: Optional[int]
    summary: Optional[str]
    summary_method: Optional[str]
    key_sentences: Optional[List[str]]
    sector_distribution: Optional[List[Dict[str, Any]]]
    sections: Optional[List[Dict[str, Any]]]
    entities: Optional[List[Dict[str, Any]]]
    wards_mentioned: Optional[List[Dict[str, Any]]]
    created_at: datetime
