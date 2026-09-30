export type Role = 'ADMIN' | 'PLANNER' | 'ANALYST' | 'VIEWER';
export type RequestStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
export type Severity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export interface User { id: number; email: string; full_name: string; role: Role; is_active: boolean; created_at: string; }
export interface TokenResponse { access_token: string; token_type: string; role: Role; user_id: number; full_name: string; email: string; }
export interface PublicConfig { demo_mode: boolean; llm_provider: string; llm_model: string | null; city: string; version: string; }

export interface Entity {
  text: string; label: string; confidence: number; start_char?: number; end_char?: number;
  source?: string; ward_code?: string | null; lat?: number | null; lng?: number | null;
}
export interface CategoryScore { category: string; confidence: number; }

export interface CitizenRequest {
  id: number; request_uid: string | null; original_text: string; cleaned_text: string | null; language: string;
  language_confidence: number; primary_category: string; categories: CategoryScore[]; confidence: number; model_version: string;
  entities: Entity[]; summary: string | null; raw_location_text: string | null; latitude: number | null; longitude: number | null;
  geocoding_confidence: number; geocoding_method: string | null; is_location_resolved: boolean; address: string | null;
  ward_id: number | null; ward_name: string | null; source: string; provenance: string | null; status: RequestStatus;
  cluster_id: number | null; created_at: string; resolved_at: string | null;
}
export interface Page<T> { total: number; limit: number; offset: number; items: T[]; }

export interface SemanticResult {
  id: number; request_uid: string | null; text: string; primary_category: string; similarity_score: number;
  ward_name: string | null; latitude: number | null; longitude: number | null; status: string | null; created_at: string;
}

export interface NLPResult {
  original_text: string; cleaned_text: string; language: string; language_confidence: number; primary_category: string;
  confidence: number; categories: CategoryScore[]; entities: Entity[]; summary: string; resolved_location: string | null;
  resolved_lat: number | null; resolved_lng: number | null; geocoding_confidence: number; geocoding_method: string;
  is_location_resolved: boolean; ward_id: number | null; ward_name: string | null; model_version: string;
}

export interface WardSummary {
  id: number; ward_code: string; name: string; localities: string | null; zone_name: string | null; area_sq_km: number;
  population: number; population_density: number; center_lat: number; center_lng: number; priority_score: number;
  growth_class: string | null; mean_elevation_m: number | null; low_lying_share: number | null;
  total_complaints: number; open_complaints: number; critical_gaps_count: number;
}

export interface PriorityFactor { factor: string; weight: number; raw_value: string; normalized_score: number; weighted_contribution: number; }
export interface GapRow {
  id: number; sector: string; required: number; existing: number; deficit: number; deficit_pct: number; unit: string;
  severity: Severity; norm_reference: string | null; evidence: Record<string, unknown> | null;
}
export interface WardProfile {
  ward_info: WardSummary;
  boundary_geojson: GeoJSON.Geometry;
  priority_factors: PriorityFactor[];
  demographics: Record<string, any> | null;
  asset_counts: Record<string, number>;
  infrastructure_gaps: GapRow[];
  environmental_indicators: (Record<string, any> & { monthly: { month: string; rainfall_mm: number; pm25: number; flood_risk: number }[] }) | null;
  transportation_indicators: Record<string, any> | null;
  land_use: Record<string, any> | null;
  satellite: { year: number; date: string; mean_ndvi: number; mean_ndbi: number; mean_ndwi: number; built_up_sq_km: number; vegetation_sq_km: number; water_sq_km: number }[];
  growth: Record<string, any> | null;
  top_complaint_categories: { category: string; count: number }[];
  recent_complaints: CitizenRequest[];
  recommendations: { id: number; sector: string; title: string; recommendation_text: string; priority_level: string; score: number; estimated_cost_cr: number | null; status: string }[];
  predicted_demand: { metric: string; date: string; predicted_value: number; lower: number; upper: number }[];
}

export interface WardFeatureProps {
  id: number; ward_code: string; name: string; localities: string; population: number; density: number; area_sq_km: number;
  priority_score: number; total_complaints: number; complaints_per_1000: number; critical_gaps: number; mean_deficit_pct: number;
  residential_pct: number | null; commercial_pct: number | null; industrial_pct: number | null; green_pct: number | null; water_pct: number | null;
  road_density: number | null; bus_stops: number | null; congestion_index: number | null; flood_risk: number | null; pm25: number | null;
  elevation_m: number | null; low_lying_share: number | null; growth_class: string | null; built_up_change_sq_km: number | null;
  center_lat: number; center_lng: number; [k: string]: unknown;
}
export type WardFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Geometry, WardFeatureProps>;

export interface ChoroplethSpec { id: string; property: string; label: string; ramp: 'severity' | 'density' | 'green' | 'categorical'; unit: string; }
export interface LayersManifest {
  vector_layers: { id: string; name: string; endpoint: string }[];
  choropleths: ChoroplethSpec[];
  raster_overlays: { id: string; name: string; url: string }[];
  overlay_bounds: [[number, number], [number, number]] | null;
}

export interface Hotspot {
  cluster_id: number; category: string; center_lat: number; center_lng: number; radius_meters: number; point_count: number;
  density_score: number; severity_level: 'HIGH' | 'MEDIUM' | 'LOW'; sample_complaints: string[]; category_breakdown: Record<string, number>; ward_ids: number[];
}
export interface ComplaintPoint { id: number; lat: number; lng: number; category: string; status: RequestStatus; summary: string | null; date: string; }
export interface Asset {
  id: number; uid: string; name: string; asset_type: string; subtype: string | null; capacity: number | null; unit: string | null;
  ward_id: number; latitude: number; longitude: number; provenance: string;
}

export interface DashboardOverview {
  total_requests: number; open_requests: number; in_progress_requests: number; resolved_requests: number;
  median_resolution_days: number | null; high_priority_wards_count: number; total_infrastructure_gaps: number; critical_gaps_count: number;
  avg_quality_score: number; top_issue_categories: { category: string; count: number }[];
  ward_complaint_rankings: { ward_id: number; ward_name: string; ward_code: string; priority_score: number; complaint_count: number; complaints_per_1000: number }[];
  monthly_trend: { month: string; count: number; resolved: number }[]; language_distribution: { language: string; count: number }[];
  active_hotspots_count: number; population_total: number; data_provenance: { provenance: string; sources: number; avg_quality: number }[];
}

export interface GapRecord {
  id: number; ward_id: number; ward_name: string; ward_code: string; sector: string; required_capacity: number; existing_capacity: number;
  deficit_amount: number; deficit_percentage: number; unit: string; severity: Severity; complaint_density: number;
  norm_reference: string | null; evidence: Record<string, any> | null;
}

export interface GrowthRow {
  ward_id: number; ward_code: string; ward_name: string; period: string; built_up_start_sq_km: number; built_up_end_sq_km: number;
  built_up_change_sq_km: number; built_up_change_pct: number | null; built_up_share_pct: number; vegetation_change_sq_km: number;
  water_change_sq_km: number; annual_built_up_growth_pct: number; complaint_growth_pct: number; population_density: number;
  growth_class: string; evidence: string;
}
export interface UrbanGrowthResponse {
  satellite_series: { date: string; year: number; satellite: string; scenes: number; mean_ndvi: number; mean_ndbi: number; mean_ndwi: number;
    built_up_sq_km: number; vegetation_sq_km: number; water_sq_km: number; cloud_cover_pct: number | null }[];
  ward_growth: GrowthRow[];
  growth_summary: { period?: string; built_up_change_pct?: number; vegetation_change_pct?: number; water_change_pct?: number | null; class_counts?: Record<string, number> };
  method: string;
}

export interface DemographicRow {
  ward_id: number; ward_code: string; ward_name: string; area_sq_km: number; population_2011: number; population_current: number; density: number;
  households: number; avg_household_size: number; literacy_rate: number; sex_ratio: number; children_0_6_pct: number; workers_pct: number;
  sc_pct: number; st_pct: number; land_use: Record<string, number> | null;
}

export interface ForecastPoint { date: string; predicted_value: number; lower_bound: number; upper_bound: number; }
export interface ForecastResponse {
  target_metric: string; metric_label: string; unit: string; ward_id: number | null; ward_name: string | null; model_name: string; model_version: string;
  historical_data: { date: string; actual_value: number }[]; forecast: ForecastPoint[]; metrics: Record<string, number>;
  feature_importance: Record<string, number>; provenance: string; generated_at: string;
}
export interface MetricInfo { id: string; label: string; unit: string; trained: boolean; backtest: Record<string, number> | null; }
export interface InfraDemand { target_year: number; method: string; wards: Record<string, any>[]; city_totals: Record<string, number>; }

export interface Lever { label: string; unit: string; min: number; max: number; default: number; }
export interface ScoreBreakdown {
  baseline_score: number; simulated_score: number; score_change: number; weights: Record<string, number>;
  baseline_criteria: Record<string, number>; simulated_criteria: Record<string, number>; score_gain_per_100cr: number | null;
}
export interface SimulationResult {
  parameters: Record<string, number>; baseline_metrics: Record<string, any>; simulated_metrics: Record<string, any>;
  delta_metrics: Record<string, number>; assumptions: string[]; score: number; score_breakdown: ScoreBreakdown;
  capital_cost_cr: number; evidence_status: string;
}
export interface Scenario {
  id: number; title: string; description: string; scope_ward_ids: number[] | null; parameters: Record<string, number>;
  baseline_metrics: Record<string, any>; simulated_metrics: Record<string, any>; delta_metrics: Record<string, number>;
  assumptions: string[]; score: number | null; score_breakdown: ScoreBreakdown | null; capital_cost_cr: number | null;
  evidence_status: string; created_at: string;
}
export interface ScenarioComparison {
  metrics_table: Record<string, any>[]; ranking: { id: number; title: string; score: number; capital_cost_cr: number; score_change: number; score_gain_per_100cr: number | null }[];
  criteria: Record<string, Record<string, number>>; weights: Record<string, number>; scenarios: { id: number; title: string; parameters: Record<string, number>; scope_ward_ids: number[] | null }[];
  warning: string | null; narrative: string | null;
}

export interface Recommendation {
  id: number; ward_id: number; ward_name: string; ward_code: string; sector: string; title: string; recommendation_text: string;
  priority_level: 'HIGH' | 'MEDIUM' | 'LOW'; score: number; estimated_cost_cr: number | null;
  contributing_factors: { factor: string; weight: number; value: string; normalized_score: number }[];
  supporting_evidence: Record<string, any>[]; methodology: string; status: string; llm_brief: string | null; created_at: string;
}

export interface EvidenceSource { table_name: string; record_ids: number[]; description: string; query_executed: string; timestamp: string; }
export interface AssistantResponse {
  question: string; intent: string; grounded_answer: string; structured_findings: Record<string, any>[];
  evidence_sources: EvidenceSource[]; suggested_actions: string[]; confidence: number; provider: string; model: string | null;
}

export interface PlanningDocument {
  id: number; title: string; filename: string | null; text_length: number; page_count: number | null; summary: string | null;
  summary_method: string | null; key_sentences: string[] | null; sector_distribution: { category: string; share_pct: number }[] | null;
  sections: { title: string; word_count: number; primary_category: string; confidence: number; summary: string }[] | null;
  entities: { text: string; label: string; count: number; ward_code: string | null; lat: number | null; lng: number | null }[] | null;
  wards_mentioned: { ward_code: string; ward_id: number; ward_name: string; mentions: number }[] | null; created_at: string;
}

export interface DataSource {
  id: number; source_name: string; provider: string; dataset_type: string; provenance: string; source_url: string | null; license: string;
  date_collected: string; geographic_scope: string; update_frequency: string; schema_info: Record<string, any>; notes: string | null;
  quality_score: number; quality_report: Record<string, number> | null;
}
export interface ModelInfo {
  id: number; model_name: string; model_type: string; version: string; training_dataset: string; training_date: string;
  parameters: Record<string, any>; metrics: Record<string, any>; status: string;
}
export interface AuditEntry {
  id: number; user_id: number | null; user_email: string | null; action: string; resource_type: string; resource_id: string | null;
  details: Record<string, any> | null; ip_address: string | null; timestamp: string;
}
