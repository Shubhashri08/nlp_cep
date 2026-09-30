from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from backend.app.models.entities import UserRole, RequestStatus

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    email: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.VIEWER

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- NLP & Citizen Request Schemas ---
class EntityItem(BaseModel):
    text: str
    label: str
    confidence: float
    start_char: Optional[int] = None
    end_char: Optional[int] = None

class CategoryScore(BaseModel):
    category: str
    confidence: float

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
    is_location_resolved: bool = False
    model_version: str

class CitizenRequestCreate(BaseModel):
    text: str
    source: Optional[str] = "Web Portal"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    ward_id: Optional[int] = None

class CitizenRequestResponse(BaseModel):
    id: int
    request_uid: str
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
    is_location_resolved: bool
    address: Optional[str]
    ward_id: Optional[int]
    ward_name: Optional[str] = None
    source: str
    status: RequestStatus
    cluster_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class BulkIngestResponse(BaseModel):
    total_processed: int
    successful_ingestions: int
    failed_ingestions: int
    quality_score: float
    categories_distribution: Dict[str, int]
    resolved_locations_count: int

# --- Semantic Search Schema ---
class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    category: Optional[str] = None
    ward_id: Optional[int] = None

class SemanticSearchResult(BaseModel):
    id: int
    request_uid: str
    text: str
    primary_category: str
    similarity_score: float
    ward_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime

# --- GIS & Ward Schemas ---
class WardSummary(BaseModel):
    id: int
    ward_code: str
    name: str
    zone_name: Optional[str] = None
    area_sq_km: float
    population: int
    population_density: float
    center_lat: float
    center_lng: float
    priority_score: float
    total_complaints: int
    critical_gaps_count: int

class WardProfile(BaseModel):
    ward_info: WardSummary
    boundary_geojson: Dict[str, Any]
    demographics: Optional[Dict[str, Any]] = None
    infrastructure_assets: List[Dict[str, Any]] = []
    infrastructure_gaps: List[Dict[str, Any]] = []
    environmental_indicators: Optional[Dict[str, Any]] = None
    transportation_indicators: Optional[Dict[str, Any]] = None
    land_use: Optional[Dict[str, Any]] = None
    top_complaint_categories: List[Dict[str, Any]] = []
    recent_complaints: List[CitizenRequestResponse] = []
    recommendations: List[Dict[str, Any]] = []
    predicted_demand: List[Dict[str, Any]] = []

class HotspotCluster(BaseModel):
    cluster_id: int
    category: str
    center_lat: float
    center_lng: float
    radius_meters: float
    point_count: int
    density_score: float
    severity_level: str  # HIGH, MEDIUM, LOW
    sample_complaints: List[str]

# --- Analytics Schemas ---
class DashboardOverview(BaseModel):
    total_requests: int
    open_requests: int
    in_progress_requests: int
    resolved_requests: int
    high_priority_wards_count: int
    total_infrastructure_gaps: int
    avg_quality_score: float
    top_issue_categories: List[Dict[str, Any]]
    ward_complaint_rankings: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]
    active_hotspots_count: int

# --- Forecasting & Prediction Schemas ---
class ForecastRequest(BaseModel):
    ward_id: Optional[int] = None
    target_metric: str = "complaint_volume"  # complaint_volume, water_demand, waste_volume, transit_ridership
    horizon_months: int = 12

class ForecastPoint(BaseModel):
    date: str
    predicted_value: float
    lower_bound: float
    upper_bound: float

class ForecastResponse(BaseModel):
    target_metric: str
    ward_id: Optional[int]
    ward_name: Optional[str]
    model_name: str
    model_version: str
    historical_data: List[Dict[str, Any]]
    forecast: List[ForecastPoint]
    metrics: Dict[str, float]  # MAE, RMSE, R2
    feature_importance: Dict[str, float]
    generated_at: datetime

# --- Scenario Analysis Schemas ---
class ScenarioCreateRequest(BaseModel):
    title: str
    description: str
    parameters: Dict[str, Any] = Field(
        ..., 
        example={
            "transit_capacity_delta_pct": 25.0,
            "drainage_upgrade_investment_cr": 50.0,
            "population_growth_rate_pct": 8.0,
            "waste_processing_expansion_pct": 20.0
        }
    )

class ScenarioResponse(BaseModel):
    id: int
    title: str
    description: str
    parameters: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    simulated_metrics: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    assumptions: List[str]
    evidence_status: str
    created_at: datetime

# --- Recommendations Schema ---
class RecommendationResponse(BaseModel):
    id: int
    ward_id: int
    ward_name: str
    sector: str
    title: str
    recommendation_text: str
    priority_level: str
    score: float
    contributing_factors: List[Dict[str, Any]]
    supporting_evidence: List[Dict[str, Any]]
    methodology: str
    created_at: datetime

# --- AI Planning Assistant Schemas ---
class AssistantQueryRequest(BaseModel):
    question: str
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
