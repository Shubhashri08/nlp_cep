export type UserRole = 'ADMIN' | 'PLANNER' | 'ANALYST' | 'VIEWER';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  role: UserRole | null;
}

export interface WardSummary {
  id: number;
  ward_code: string;
  name: string;
  zone_name?: string;
  area_sq_km: number;
  population: number;
  population_density: number;
  center_lat: number;
  center_lng: number;
  priority_score: number;
  total_complaints: number;
  critical_gaps_count: number;
}

export interface WardProfile {
  ward_info: WardSummary;
  boundary_geojson: any;
  demographics?: {
    total_population: number;
    households: number;
    literacy_rate: number;
    growth_rate_percent: number;
  };
  infrastructure_assets: Array<{
    id: number;
    name: string;
    type: string;
    capacity: number;
    unit: string;
    lat: number;
    lng: number;
  }>;
  infrastructure_gaps: Array<{
    id: number;
    sector: string;
    required: number;
    existing: number;
    deficit: number;
    deficit_pct: number;
    unit: string;
    severity: string;
  }>;
  environmental_indicators?: {
    rainfall_mm: number;
    aqi_pm25: number;
    flood_risk_score: number;
    elevation_m: number;
    vegetation_pct: number;
  };
  transportation_indicators?: {
    road_length_km: number;
    road_density: number;
    bus_stops: number;
    daily_ridership: number;
    congestion_index: number;
  };
  land_use?: {
    residential_pct: number;
    commercial_pct: number;
    industrial_pct: number;
    green_pct: number;
    water_pct: number;
  };
  top_complaint_categories: Array<{ category: string; count: number }>;
  recent_complaints: CitizenRequest[];
  recommendations: Array<{
    id: number;
    sector: string;
    title: string;
    recommendation_text: string;
    priority_level: string;
    score: number;
    contributing_factors: any[];
    supporting_evidence: any[];
  }>;
  predicted_demand: Array<{
    metric: string;
    date: string;
    predicted_value: number;
    lower: number;
    upper: number;
  }>;
}

export interface CitizenRequest {
  id: number;
  request_uid: string;
  original_text: string;
  cleaned_text?: string;
  language: string;
  language_confidence: number;
  primary_category: string;
  categories: Array<{ category: string; confidence: number }>;
  confidence: number;
  model_version: string;
  entities: Array<{ text: string; label: string; confidence: number }>;
  summary?: string;
  raw_location_text?: string;
  latitude?: number;
  longitude?: number;
  geocoding_confidence: number;
  is_location_resolved: boolean;
  address?: string;
  ward_id?: number;
  ward_name?: string;
  source: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
  cluster_id?: number;
  created_at: string;
}

export interface NLPAnalysisResult {
  original_text: string;
  cleaned_text: string;
  language: string;
  language_confidence: number;
  primary_category: string;
  confidence: number;
  categories: Array<{ category: string; confidence: number }>;
  entities: Array<{ text: string; label: string; confidence: number }>;
  summary: string;
  resolved_location?: string;
  resolved_lat?: number;
  resolved_lng?: number;
  geocoding_confidence: number;
  is_location_resolved: boolean;
  model_version: string;
}

export interface DashboardOverview {
  total_requests: number;
  open_requests: number;
  in_progress_requests: number;
  resolved_requests: number;
  high_priority_wards_count: number;
  total_infrastructure_gaps: number;
  avg_quality_score: number;
  top_issue_categories: Array<{ category: string; count: number }>;
  ward_complaint_rankings: Array<{
    ward_name: string;
    ward_code: string;
    priority_score: number;
    complaint_count: number;
  }>;
  monthly_trend: Array<{
    month: string;
    count: number;
    resolved: number;
  }>;
  active_hotspots_count: number;
}

export interface Hotspot {
  cluster_id: number;
  category: string;
  center_lat: number;
  center_lng: number;
  radius_meters: number;
  point_count: number;
  density_score: number;
  severity_level: 'HIGH' | 'MEDIUM' | 'LOW';
  sample_complaints: string[];
}

export interface InfrastructureGapItem {
  id: number;
  ward_id: number;
  ward_name: string;
  ward_code: string;
  sector: string;
  required_capacity: number;
  existing_capacity: number;
  deficit_amount: number;
  deficit_percentage: number;
  unit: string;
  severity: string;
  complaint_density: number;
}

export interface ForecastPoint {
  date: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  target_metric: string;
  ward_id?: number;
  ward_name?: string;
  model_name: string;
  model_version: string;
  historical_data: Array<{ date: string; actual_value: number }>;
  forecast: ForecastPoint[];
  metrics: { mae: number; rmse: number; r2_score: number; test_samples?: number };
  feature_importance: Record<string, number>;
  generated_at: string;
}

export interface ScenarioResponse {
  id: number;
  title: string;
  description: string;
  parameters: Record<string, any>;
  baseline_metrics: Record<string, any>;
  simulated_metrics: Record<string, any>;
  delta_metrics: Record<string, any>;
  assumptions: string[];
  evidence_status: string;
  created_at: string;
}

export interface RecommendationItem {
  id: number;
  ward_id: number;
  ward_name: string;
  sector: string;
  title: string;
  recommendation_text: string;
  priority_level: string;
  score: number;
  contributing_factors: Array<{ factor: string; raw_value: string; weighted_contribution: number }>;
  supporting_evidence: any[];
  methodology: string;
  created_at: string;
}

export interface AssistantQueryResponse {
  question: string;
  intent: string;
  grounded_answer: string;
  structured_findings: any[];
  evidence_sources: Array<{
    table_name: string;
    record_ids: number[];
    description: string;
    query_executed: string;
    timestamp: string;
  }>;
  suggested_actions: string[];
  confidence: number;
}

export interface DataSourceItem {
  id: number;
  source_name: string;
  provider: string;
  dataset_type: string;
  source_url?: string;
  license: string;
  date_collected: string;
  geographic_scope: string;
  update_frequency: string;
  quality_score: number;
  quality_report?: {
    total_records: number;
    completeness_score: number;
    duplicate_rate: number;
    missing_values_count: number;
    geographic_validity_rate: number;
    freshness_days: number;
    consistency_score: number;
    overall_quality_score: number;
  };
}

export interface ModelRegistryItem {
  id: number;
  model_name: string;
  model_type: string;
  version: string;
  training_dataset: string;
  training_date: string;
  parameters: Record<string, any>;
  metrics: Record<string, any>;
  status: string;
}
