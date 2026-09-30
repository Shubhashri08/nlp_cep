import {
  DashboardOverview, WardSummary, WardProfile, CitizenRequest,
  NLPAnalysisResult, Hotspot, InfrastructureGapItem, ForecastResponse,
  ScenarioResponse, RecommendationItem, AssistantQueryResponse,
  DataSourceItem, ModelRegistryItem
} from '../types';

const BASE_URL = '/api/v1';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('dss_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(formData: FormData) {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error('Invalid email or password');
    }
    return response.json();
  },

  async getMe() {
    return request<any>('/auth/me');
  },

  // Analytics & Dashboard
  async getDashboardOverview(): Promise<DashboardOverview> {
    return request<DashboardOverview>('/analytics/overview');
  },

  async getInfrastructureGaps(): Promise<InfrastructureGapItem[]> {
    return request<InfrastructureGapItem[]>('/analytics/infrastructure-gaps');
  },

  async getUrbanGrowth() {
    return request<any>('/analytics/urban-growth');
  },

  // Wards
  async getWards(): Promise<WardSummary[]> {
    return request<WardSummary[]>('/wards');
  },

  async getWardProfile(wardId: number): Promise<WardProfile> {
    return request<WardProfile>(`/wards/${wardId}/profile`);
  },

  async getWardsGeoJSON() {
    return request<any>('/wards/geojson/all');
  },

  // Citizen Requests
  async getCitizenRequests(params?: {
    ward_id?: number;
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<CitizenRequest[]> {
    const query = new URLSearchParams();
    if (params?.ward_id) query.append('ward_id', params.ward_id.toString());
    if (params?.category) query.append('category', params.category);
    if (params?.status) query.append('status', params.status);
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset) query.append('offset', params.offset.toString());
    return request<CitizenRequest[]>(`/citizen-requests?${query.toString()}`);
  },

  async createCitizenRequest(data: {
    text: string;
    source?: string;
    latitude?: number;
    longitude?: number;
    address?: string;
    ward_id?: number;
  }): Promise<CitizenRequest> {
    return request<CitizenRequest>('/citizen-requests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async semanticSearch(query: string, category?: string, ward_id?: number): Promise<any[]> {
    return request<any[]>('/citizen-requests/search/semantic', {
      method: 'POST',
      body: JSON.stringify({ query, category, ward_id, top_k: 10 }),
    });
  },

  // NLP
  async analyzeNLP(text: string, contextCity: string = 'Mumbai'): Promise<NLPAnalysisResult> {
    return request<NLPAnalysisResult>('/nlp/analyze', {
      method: 'POST',
      body: JSON.stringify({ text, context_city: contextCity }),
    });
  },

  async getNlpCategories() {
    return request<{ total_categories: number; categories: string[] }>('/nlp/categories');
  },

  // GIS
  async getHotspots(eps_km: number = 1.0, category?: string): Promise<{ total_hotspots: number; hotspots: Hotspot[] }> {
    const query = new URLSearchParams({ eps_km: eps_km.toString() });
    if (category) query.append('category', category);
    return request<{ total_hotspots: number; hotspots: Hotspot[] }>(`/gis/hotspots?${query.toString()}`);
  },

  async getInfrastructureAssets(assetType?: string, wardId?: number) {
    const query = new URLSearchParams();
    if (assetType) query.append('asset_type', assetType);
    if (wardId) query.append('ward_id', wardId.toString());
    return request<any[]>(`/gis/infrastructure?${query.toString()}`);
  },

  // Predictions & Forecasting
  async getForecast(wardId?: number, horizonMonths: number = 12): Promise<ForecastResponse> {
    const query = new URLSearchParams({ horizon_months: horizonMonths.toString() });
    if (wardId) query.append('ward_id', wardId.toString());
    return request<ForecastResponse>(`/predictions/forecast?${query.toString()}`);
  },

  // Scenarios
  async getScenarios(): Promise<ScenarioResponse[]> {
    return request<ScenarioResponse[]>('/scenarios');
  },

  async createScenario(data: {
    title: string;
    description: string;
    parameters: Record<string, any>;
  }): Promise<ScenarioResponse> {
    return request<ScenarioResponse>('/scenarios', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Recommendations
  async getRecommendations(wardId?: number, sector?: string, priority?: string): Promise<RecommendationItem[]> {
    const query = new URLSearchParams();
    if (wardId) query.append('ward_id', wardId.toString());
    if (sector) query.append('sector', sector);
    if (priority) query.append('priority', priority);
    return request<RecommendationItem[]>(`/recommendations?${query.toString()}`);
  },

  // AI Planning Assistant
  async queryAssistant(question: string, contextWardId?: number): Promise<AssistantQueryResponse> {
    return request<AssistantQueryResponse>('/assistant/query', {
      method: 'POST',
      body: JSON.stringify({ question, context_ward_id: contextWardId }),
    });
  },

  // Data Sources & Quality
  async getDataSources(): Promise<DataSourceItem[]> {
    return request<DataSourceItem[]>('/data-sources');
  },

  // Models
  async getRegisteredModels(): Promise<ModelRegistryItem[]> {
    return request<ModelRegistryItem[]>('/models');
  },

  // Audit Logs
  async getAuditLogs(limit: number = 50) {
    return request<any[]>(`/audit?limit=${limit}`);
  },
};
