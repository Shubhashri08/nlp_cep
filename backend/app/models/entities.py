import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, Date,
    ForeignKey, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base


def _now():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    PLANNER = "PLANNER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class Provenance(str, enum.Enum):
    """Where a record came from. Surfaced in the UI so synthetic data is never mistaken for real data."""
    OSM = "OSM"                  # OpenStreetMap (ODbL)
    CENSUS = "CENSUS"            # Census of India 2011 (ORGI)
    SENTINEL = "SENTINEL"        # Copernicus Sentinel-2 L2A (via Microsoft Planetary Computer)
    DERIVED = "DERIVED"          # Computed from other records by this system
    ESTIMATED = "ESTIMATED"      # Modelled estimate from real inputs (documented method)
    SYNTHETIC = "SYNTHETIC"      # Generated for demonstration (no open source available)
    IMPORTED = "IMPORTED"        # Uploaded by a user
    CITIZEN = "CITIZEN"          # Submitted through the app


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now)

    wards = relationship("Ward", back_populates="zone")


class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    ward_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g. "H/E"
    name = Column(String(100), nullable=False)
    localities = Column(String(255), nullable=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    osm_relation_id = Column(Integer, nullable=True)
    area_sq_km = Column(Float, nullable=False)
    population = Column(Integer, nullable=False)          # current (projected) population
    population_density = Column(Float, nullable=False)    # persons / km²
    boundary_geojson = Column(JSON, nullable=False)       # GeoJSON Polygon / MultiPolygon
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    priority_score = Column(Float, default=0.0)
    priority_factors = Column(JSON, nullable=True)
    growth_class = Column(String(40), nullable=True)
    mean_elevation_m = Column(Float, nullable=True)        # Copernicus DEM GLO-30
    low_lying_share = Column(Float, nullable=True)         # share of ward area below 5 m elevation
    boundary_source = Column(String(30), default=Provenance.OSM.value)
    created_at = Column(DateTime, default=_now)

    zone = relationship("Zone", back_populates="wards")
    citizen_requests = relationship("CitizenRequest", back_populates="ward")
    infrastructure_assets = relationship("InfrastructureAsset", back_populates="ward")
    demographics = relationship("DemographicData", back_populates="ward")
    transport_data = relationship("TransportationData", back_populates="ward")
    environmental_data = relationship("EnvironmentalData", back_populates="ward")
    recommendations = relationship("Recommendation", back_populates="ward")


class RequestStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CitizenRequest(Base):
    __tablename__ = "citizen_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_uid = Column(String(100), unique=True, index=True, nullable=True)
    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    language = Column(String(20), default="en")
    language_confidence = Column(Float, default=1.0)

    primary_category = Column(String(100), index=True, nullable=False)
    categories = Column(JSON, default=list)
    confidence = Column(Float, default=0.0)
    model_version = Column(String(50), default="")

    entities = Column(JSON, default=list)
    summary = Column(Text, nullable=True)

    raw_location_text = Column(String(255), nullable=True)
    latitude = Column(Float, index=True, nullable=True)
    longitude = Column(Float, index=True, nullable=True)
    geocoding_confidence = Column(Float, default=0.0)
    geocoding_method = Column(String(40), nullable=True)  # USER_GPS | GAZETTEER | NOMINATIM | NONE
    is_location_resolved = Column(Boolean, default=False)
    address = Column(String(255), nullable=True)

    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True, index=True)
    source = Column(String(50), default="Web Portal")
    provenance = Column(String(20), default=Provenance.CITIZEN.value)
    status = Column(Enum(RequestStatus), default=RequestStatus.OPEN, index=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=_now, index=True)
    resolved_at = Column(DateTime, nullable=True)

    ward = relationship("Ward", back_populates="citizen_requests")
    embedding = relationship("RequestEmbedding", back_populates="request", uselist=False)


class RequestEmbedding(Base):
    __tablename__ = "request_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("citizen_requests.id"), unique=True, nullable=False)
    embedding_vector = Column(JSON, nullable=False)
    embedding_model = Column(String(100), default="tfidf-lsa")
    created_at = Column(DateTime, default=_now)

    request = relationship("CitizenRequest", back_populates="embedding")


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_uid = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    asset_type = Column(String(100), index=True, nullable=False)  # HEALTHCARE, EDUCATION, BUS_STOP, RAIL_STATION, ...
    subtype = Column(String(100), nullable=True)                  # hospital, clinic, school, college, ...
    capacity = Column(Float, nullable=True)
    capacity_unit = Column(String(50), nullable=True)
    capacity_estimated = Column(Boolean, default=True)
    current_load = Column(Float, default=0.0)
    condition_score = Column(Float, nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    osm_id = Column(String(40), nullable=True)
    provenance = Column(String(20), default=Provenance.OSM.value)
    last_inspected = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)

    ward = relationship("Ward", back_populates="infrastructure_assets")


class InfrastructureGap(Base):
    __tablename__ = "infrastructure_gaps"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    sector = Column(String(100), nullable=False)
    required_capacity = Column(Float, nullable=False)
    existing_capacity = Column(Float, nullable=False)
    deficit_amount = Column(Float, nullable=False)
    deficit_percentage = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # CRITICAL, HIGH, MODERATE, LOW
    complaint_density = Column(Float, default=0.0)
    norm_reference = Column(String(255), nullable=True)
    evidence = Column(JSON, nullable=True)
    assessment_date = Column(DateTime, default=_now)


class DemographicData(Base):
    __tablename__ = "demographic_data"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    census_year = Column(Integer, nullable=False)
    total_population = Column(Integer, nullable=False)
    male_population = Column(Integer, nullable=False)
    female_population = Column(Integer, nullable=False)
    households = Column(Integer, nullable=False)
    literacy_rate = Column(Float, nullable=False)
    child_population_0_6 = Column(Integer, nullable=True)
    workers = Column(Integer, nullable=True)
    sc_population = Column(Integer, nullable=True)
    st_population = Column(Integer, nullable=True)
    sex_ratio = Column(Float, nullable=True)  # females per 1000 males
    median_income = Column(Float, nullable=True)
    growth_rate_percent = Column(Float, default=0.0)  # annual
    provenance = Column(String(20), default=Provenance.CENSUS.value)
    created_at = Column(DateTime, default=_now)

    ward = relationship("Ward", back_populates="demographics")


class TransportationData(Base):
    __tablename__ = "transportation_data"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    road_length_km = Column(Float, nullable=False)
    road_density_km_per_sq_km = Column(Float, nullable=False)
    road_km_by_class = Column(JSON, nullable=True)
    bus_stops_count = Column(Integer, nullable=False)
    rail_stations_count = Column(Integer, default=0)
    metro_stations_count = Column(Integer, default=0)
    daily_transit_ridership = Column(Integer, nullable=False)
    avg_peak_congestion_index = Column(Float, nullable=False)  # 1.0 (free flow) to 3.0 (gridlock)
    provenance = Column(String(40), default=Provenance.OSM.value)
    created_at = Column(DateTime, default=_now)

    ward = relationship("Ward", back_populates="transport_data")


class EnvironmentalData(Base):
    __tablename__ = "environmental_data"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, default=_now, index=True)
    rainfall_mm = Column(Float, nullable=False)
    aqi_pm25 = Column(Float, nullable=False)
    aqi_pm10 = Column(Float, nullable=False)
    avg_temperature_c = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=False)
    flood_risk_score = Column(Float, nullable=False)  # 0.0 to 1.0
    vegetation_coverage_pct = Column(Float, nullable=False)
    provenance = Column(String(20), default=Provenance.SYNTHETIC.value)

    ward = relationship("Ward", back_populates="environmental_data")


class LandUseData(Base):
    __tablename__ = "land_use_data"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    residential_pct = Column(Float, nullable=False)
    commercial_pct = Column(Float, nullable=False)
    industrial_pct = Column(Float, nullable=False)
    agricultural_pct = Column(Float, nullable=False)
    forest_green_pct = Column(Float, nullable=False)
    waterbody_pct = Column(Float, nullable=False)
    mixed_use_pct = Column(Float, nullable=False)
    unmapped_pct = Column(Float, default=0.0)
    building_count = Column(Integer, nullable=True)
    provenance = Column(String(20), default=Provenance.OSM.value)
    created_at = Column(DateTime, default=_now)


class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True, index=True)  # NULL = whole city
    observation_date = Column(DateTime, nullable=False, index=True)
    satellite_name = Column(String(100), default="Sentinel-2 L2A")
    scene_id = Column(String(200), nullable=True)
    spatial_resolution_m = Column(Float, default=10.0)
    coverage_area_sq_km = Column(Float, nullable=False)
    mean_ndvi = Column(Float, nullable=False)
    mean_ndbi = Column(Float, nullable=False)
    mean_ndwi = Column(Float, nullable=False)
    built_up_area_sq_km = Column(Float, nullable=False)
    vegetation_area_sq_km = Column(Float, nullable=False)
    water_area_sq_km = Column(Float, nullable=False)
    cloud_cover_pct = Column(Float, nullable=True)
    provenance = Column(String(20), default=Provenance.SENTINEL.value)
    raster_file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now)


class UrbanGrowth(Base):
    __tablename__ = "urban_growth"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    period_start_year = Column(Integer, nullable=True)
    built_up_area_sq_km = Column(Float, nullable=False)
    built_up_change_sq_km = Column(Float, default=0.0)
    vegetation_loss_sq_km = Column(Float, nullable=False)
    water_body_change_sq_km = Column(Float, nullable=False)
    population_cagr_pct = Column(Float, default=0.0)
    complaint_growth_pct = Column(Float, default=0.0)
    annual_growth_rate_pct = Column(Float, nullable=False)
    growth_class = Column(String(40), nullable=True)
    evidence = Column(String(20), default=Provenance.ESTIMATED.value)
    created_at = Column(DateTime, default=_now)


class ServiceDemandRecord(Base):
    """Monthly observed demand per ward and metric (history used by the forecaster)."""
    __tablename__ = "service_demand_records"
    __table_args__ = (UniqueConstraint("ward_id", "metric", "month", name="uq_demand_ward_metric_month"),)

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    metric = Column(String(60), nullable=False, index=True)  # water_demand_mld, waste_generation_tpd, transit_ridership, complaint_volume
    month = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False)
    provenance = Column(String(20), default=Provenance.SYNTHETIC.value)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    target_metric = Column(String(100), nullable=False, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True, index=True)
    target_date = Column(DateTime, nullable=False)
    predicted_value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    confidence_level = Column(Float, default=0.95)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    input_features = Column(JSON, nullable=False)
    feature_importance = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=_now)


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scope_ward_ids = Column(JSON, nullable=True)  # None = city-wide
    parameters = Column(JSON, nullable=False)
    baseline_metrics = Column(JSON, nullable=False)
    simulated_metrics = Column(JSON, nullable=False)
    delta_metrics = Column(JSON, nullable=False)
    assumptions = Column(JSON, nullable=False)
    score = Column(Float, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    capital_cost_cr = Column(Float, nullable=True)
    evidence_status = Column(String(50), default="ESTIMATED_FROM_DATA")
    created_at = Column(DateTime, default=_now)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    sector = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    priority_level = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    score = Column(Float, nullable=False)
    contributing_factors = Column(JSON, nullable=False)
    supporting_evidence = Column(JSON, nullable=False)
    methodology = Column(String(255), default="Multi-Criteria Decision Analysis (MCDA)")
    estimated_cost_cr = Column(Float, nullable=True)
    llm_brief = Column(Text, nullable=True)
    status = Column(String(30), default="PROPOSED")  # PROPOSED, APPROVED, REJECTED, IN_PROGRESS
    created_at = Column(DateTime, default=_now)

    ward = relationship("Ward", back_populates="recommendations")


class PlanningDocument(Base):
    """Uploaded urban development report / plan analysed by the NLP pipeline."""
    __tablename__ = "planning_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    text_length = Column(Integer, default=0)
    page_count = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    summary_method = Column(String(40), nullable=True)
    key_sentences = Column(JSON, nullable=True)
    sector_distribution = Column(JSON, nullable=True)
    sections = Column(JSON, nullable=True)
    entities = Column(JSON, nullable=True)
    wards_mentioned = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now)


class GeocodeCacheEntry(Base):
    __tablename__ = "geocode_cache"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    confidence = Column(Float, default=0.0)
    address = Column(String(500), nullable=True)
    method = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=_now)


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(200), nullable=False)
    provider = Column(String(200), nullable=False)
    dataset_type = Column(String(100), nullable=False)
    provenance = Column(String(20), default=Provenance.OSM.value)
    source_url = Column(String(500), nullable=True)
    license = Column(String(100), nullable=False)
    date_collected = Column(DateTime, nullable=False)
    geographic_scope = Column(String(200), nullable=False)
    update_frequency = Column(String(100), nullable=False)
    schema_info = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    quality_score = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=_now)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id = Column(Integer, primary_key=True, index=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    total_records = Column(Integer, nullable=False)
    completeness_score = Column(Float, nullable=False)
    duplicate_rate = Column(Float, nullable=False)
    missing_values_count = Column(Integer, nullable=False)
    geographic_validity_rate = Column(Float, nullable=False)
    freshness_days = Column(Integer, nullable=False)
    consistency_score = Column(Float, nullable=False)
    overall_quality_score = Column(Float, nullable=False)
    assessed_at = Column(DateTime, default=_now)


class ModelRegistry(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    training_dataset = Column(String(200), nullable=False)
    training_date = Column(DateTime, default=_now)
    parameters = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    status = Column(String(50), default="ACTIVE")
    artifact_path = Column(String(255), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=_now, index=True)
