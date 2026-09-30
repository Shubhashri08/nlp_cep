import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, 
    ForeignKey, Enum, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    PLANNER = "PLANNER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    wards = relationship("Ward", back_populates="zone")

class Ward(Base):
    __tablename__ = "wards"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    area_sq_km = Column(Float, nullable=False)
    population = Column(Integer, nullable=False)
    population_density = Column(Float, nullable=False)  # pop / area_sq_km
    boundary_geojson = Column(JSON, nullable=False)  # GeoJSON Polygon/MultiPolygon
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    priority_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
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
    request_uid = Column(String(100), unique=True, index=True, nullable=False)
    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    language = Column(String(20), default="en")
    language_confidence = Column(Float, default=1.0)
    
    # Classification results
    primary_category = Column(String(100), index=True, nullable=False)
    categories = Column(JSON, default=list)  # Multi-label list with confidence scores
    confidence = Column(Float, default=0.0)
    model_version = Column(String(50), default="v1.0-tfidf-logreg")
    
    # NLP details
    entities = Column(JSON, default=list)  # Extracted entities [{text, label, confidence}]
    summary = Column(Text, nullable=True)
    
    # Geospatial details
    raw_location_text = Column(String(255), nullable=True)
    latitude = Column(Float, index=True, nullable=True)
    longitude = Column(Float, index=True, nullable=True)
    geocoding_confidence = Column(Float, default=0.0)
    is_location_resolved = Column(Boolean, default=False)
    address = Column(String(255), nullable=True)
    
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    source = Column(String(50), default="Mobile App")  # Mobile App, Web Portal, Call Center, Ward Office
    status = Column(Enum(RequestStatus), default=RequestStatus.OPEN, index=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    ward = relationship("Ward", back_populates="citizen_requests")
    embedding = relationship("RequestEmbedding", back_populates="request", uselist=False)

class RequestEmbedding(Base):
    __tablename__ = "request_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("citizen_requests.id"), unique=True, nullable=False)
    embedding_vector = Column(JSON, nullable=False)  # Stored as float list (or pgvector in postgis)
    embedding_model = Column(String(100), default="sentence-transformers/all-MiniLM-L6-v2")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    request = relationship("CitizenRequest", back_populates="embedding")

class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_uid = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    asset_type = Column(String(100), index=True, nullable=False)  # WATER_SUPPLY, DRAINAGE, WASTE_MANAGEMENT, HEALTHCARE, EDUCATION, ROAD, STREETLIGHT
    capacity = Column(Float, nullable=False)
    capacity_unit = Column(String(50), nullable=False)  # MLD, tons/day, beds, students, lanes, etc.
    current_load = Column(Float, default=0.0)
    condition_score = Column(Float, default=1.0)  # 0.0 to 1.0 (1.0 = excellent)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    last_inspected = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    ward = relationship("Ward", back_populates="infrastructure_assets")

class InfrastructureGap(Base):
    __tablename__ = "infrastructure_gaps"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    sector = Column(String(100), nullable=False)  # Water, Drainage, Waste, Health, Education, Transit
    required_capacity = Column(Float, nullable=False)
    existing_capacity = Column(Float, nullable=False)
    deficit_amount = Column(Float, nullable=False)
    deficit_percentage = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # CRITICAL, HIGH, MODERATE, LOW
    complaint_density = Column(Float, default=0.0)  # Complaints / sq km
    assessment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DemographicData(Base):
    __tablename__ = "demographic_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    census_year = Column(Integer, nullable=False)
    total_population = Column(Integer, nullable=False)
    male_population = Column(Integer, nullable=False)
    female_population = Column(Integer, nullable=False)
    households = Column(Integer, nullable=False)
    literacy_rate = Column(Float, nullable=False)
    median_income = Column(Float, nullable=True)
    growth_rate_percent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    ward = relationship("Ward", back_populates="demographics")

class TransportationData(Base):
    __tablename__ = "transportation_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    road_length_km = Column(Float, nullable=False)
    road_density_km_per_sq_km = Column(Float, nullable=False)
    bus_stops_count = Column(Integer, nullable=False)
    metro_stations_count = Column(Integer, default=0)
    daily_transit_ridership = Column(Integer, nullable=False)
    avg_peak_congestion_index = Column(Float, nullable=False)  # 1.0 (free flow) to 3.0 (gridlock)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    ward = relationship("Ward", back_populates="transport_data")

class EnvironmentalData(Base):
    __tablename__ = "environmental_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    rainfall_mm = Column(Float, nullable=False)
    aqi_pm25 = Column(Float, nullable=False)
    aqi_pm10 = Column(Float, nullable=False)
    avg_temperature_c = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=False)
    flood_risk_score = Column(Float, nullable=False)  # 0.0 to 1.0
    vegetation_coverage_pct = Column(Float, nullable=False)
    
    ward = relationship("Ward", back_populates="environmental_data")

class LandUseData(Base):
    __tablename__ = "land_use_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    year = Column(Integer, nullable=False)
    residential_pct = Column(Float, nullable=False)
    commercial_pct = Column(Float, nullable=False)
    industrial_pct = Column(Float, nullable=False)
    agricultural_pct = Column(Float, nullable=False)
    forest_green_pct = Column(Float, nullable=False)
    waterbody_pct = Column(Float, nullable=False)
    mixed_use_pct = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    observation_date = Column(DateTime, nullable=False, index=True)
    satellite_name = Column(String(100), default="Sentinel-2 / Landsat-8")
    spatial_resolution_m = Column(Float, default=10.0)
    coverage_area_sq_km = Column(Float, nullable=False)
    mean_ndvi = Column(Float, nullable=False)  # Normalized Difference Vegetation Index
    mean_ndbi = Column(Float, nullable=False)  # Normalized Difference Built-up Index
    mean_ndwi = Column(Float, nullable=False)  # Normalized Difference Water Index
    built_up_area_sq_km = Column(Float, nullable=False)
    vegetation_area_sq_km = Column(Float, nullable=False)
    water_area_sq_km = Column(Float, nullable=False)
    raster_file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UrbanGrowth(Base):
    __tablename__ = "urban_growth"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    year = Column(Integer, nullable=False)
    built_up_area_sq_km = Column(Float, nullable=False)
    vegetation_loss_sq_km = Column(Float, nullable=False)
    water_body_change_sq_km = Column(Float, nullable=False)
    annual_growth_rate_pct = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    target_metric = Column(String(100), nullable=False)  # e.g., "monthly_complaints_water", "population_2028", "transit_demand"
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    target_date = Column(DateTime, nullable=False)
    predicted_value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    confidence_level = Column(Float, default=0.95)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    input_features = Column(JSON, nullable=False)
    feature_importance = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parameters = Column(JSON, nullable=False)  # e.g. {"transit_capacity_delta_pct": 20, "drainage_upgrade_ward_ids": [1, 3]}
    baseline_metrics = Column(JSON, nullable=False)
    simulated_metrics = Column(JSON, nullable=False)
    delta_metrics = Column(JSON, nullable=False)
    assumptions = Column(JSON, nullable=False)
    evidence_status = Column(String(50), default="ESTIMATED_FROM_DATA")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    sector = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    priority_level = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    score = Column(Float, nullable=False)  # Multi-factor score
    contributing_factors = Column(JSON, nullable=False)
    supporting_evidence = Column(JSON, nullable=False)  # Traceable data points
    methodology = Column(String(255), default="Multi-Criteria Decision Analysis (MCDA)")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    ward = relationship("Ward", back_populates="recommendations")

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(200), nullable=False)
    provider = Column(String(200), nullable=False)
    dataset_type = Column(String(100), nullable=False)  # GeoJSON, CSV, Satellite, Census, Sensor
    source_url = Column(String(500), nullable=True)
    license = Column(String(100), nullable=False)
    date_collected = Column(DateTime, nullable=False)
    geographic_scope = Column(String(200), nullable=False)
    update_frequency = Column(String(100), nullable=False)
    schema_info = Column(JSON, nullable=False)
    quality_score = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ModelRegistry(Base):
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(100), nullable=False)  # NLP_CLASSIFIER, NER, DEMAND_FORECASTER, KDE_HOTSPOT
    version = Column(String(50), nullable=False)
    training_dataset = Column(String(200), nullable=False)
    training_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    parameters = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)  # accuracy, precision, recall, f1, mae, rmse, r2, confusion_matrix
    status = Column(String(50), default="ACTIVE")  # ACTIVE, ARCHIVED, STAGING
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
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
