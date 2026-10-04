import type {
  Asset, AssistantResponse, AuditEntry, CitizenRequest, ComplaintPoint, DashboardOverview, DataSource, DemographicRow,
  ForecastResponse, GapRecord, Hotspot, InfraDemand, LayersManifest, Lever, MetricInfo, ModelInfo, NLPResult, Page,
  PlanningDocument, PublicConfig, Recommendation, RequestStatus, Role, Scenario, ScenarioComparison, SemanticResult,
  SimulationResult, TokenResponse, UrbanGrowthResponse, User, WardFeatureCollection, WardProfile, WardSummary,
} from '../types';

export const API_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`;
const TOKEN_KEY = 'dss_token';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

let unauthorizedHandler: (() => void) | null = null;
export const onUnauthorized = (fn: () => void) => { unauthorizedHandler = fn; };

export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set: (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } },
};

function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ');
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (auth && token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, 'Cannot reach the API server. Is the backend running on port 8000?');
  }
  if (res.status === 401 && auth) {
    tokenStore.clear();
    unauthorizedHandler?.();
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { msg = detailToMessage((await res.json()).detail, msg); } catch { /* non-JSON */ }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, unknown>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    if (Array.isArray(v)) v.forEach((x) => p.append(k, String(x)));
    else p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};
const post = <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T,>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });

export const api = {
  // auth
  config: () => request<PublicConfig>('/auth/config', {}, false),
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: new URLSearchParams({ username: email, password }) }, false),
  demoLogin: (role: Role) => request<TokenResponse>('/auth/demo-login', { method: 'POST', body: JSON.stringify({ role }) }, false),
  me: () => request<User>('/auth/me'),
  users: () => request<User[]>('/auth/users'),
  createUser: (u: { email: string; password: string; full_name: string; role: Role }) => post<User>('/auth/users', u),

  // wards & GIS
  wards: () => request<WardSummary[]>('/wards'),
  wardsGeo: () => request<WardFeatureCollection>('/wards/geojson/all'),
  wardProfile: (id: number) => request<WardProfile>(`/wards/${id}/profile`),
  layers: () => request<LayersManifest>('/gis/layers'),
  hotspots: (p: { category?: string; months?: number; eps_km?: number; min_samples?: number } = {}) =>
    request<{ total_hotspots: number; points_considered: number; hotspots: Hotspot[] }>(`/gis/hotspots${qs(p)}`),
  assets: (p: { asset_type?: string; ward_id?: number } = {}) => request<Asset[]>(`/gis/infrastructure${qs(p)}`),
  complaintPoints: (p: { category?: string; status?: string; months?: number } = {}) => request<ComplaintPoint[]>(`/citizen-requests/points${qs(p)}`),

  // citizen feedback
  complaints: (p: { ward_id?: number; category?: string; status?: string; language?: string; q?: string; limit?: number; offset?: number }) =>
    request<Page<CitizenRequest>>(`/citizen-requests${qs(p)}`),
  complaint: (id: number) => request<CitizenRequest>(`/citizen-requests/${id}`),
  createComplaint: (b: { text: string; source?: string; latitude?: number; longitude?: number; ward_id?: number }) => post<CitizenRequest>('/citizen-requests', b),
  setComplaintStatus: (id: number, status: RequestStatus) => patch<CitizenRequest>(`/citizen-requests/${id}/status`, { status }),
  semanticSearch: (b: { query: string; top_k?: number; category?: string; ward_id?: number }) => post<SemanticResult[]>('/citizen-requests/search/semantic', b),

  // NLP
  analyze: (text: string) => post<NLPResult>('/nlp/analyze', { text }),
  categories: () => request<{ categories: string[]; model_version: string; metrics: Record<string, any> }>('/nlp/categories'),
  clusterSummary: (ward_id: number, category: string) => request<Record<string, any>>(`/nlp/cluster-summary${qs({ ward_id, category })}`),
  documents: () => request<PlanningDocument[]>('/nlp/documents'),
  document: (id: number) => request<PlanningDocument>(`/nlp/documents/${id}`),
  uploadDocument: (form: FormData) => request<PlanningDocument>('/nlp/documents', { method: 'POST', body: form }),

  // analytics
  overview: () => request<DashboardOverview>('/analytics/overview'),
  gaps: (p: { sector?: string; severity?: string } = {}) => request<GapRecord[]>(`/analytics/infrastructure-gaps${qs(p)}`),
  recomputeGaps: () => post<{ gaps: number; recommendations: number }>('/analytics/infrastructure-gaps/recompute'),
  urbanGrowth: () => request<UrbanGrowthResponse>('/analytics/urban-growth'),
  demographics: () => request<DemographicRow[]>('/analytics/demographics'),

  // forecasting
  forecastMetrics: () => request<MetricInfo[]>('/predictions/metrics'),
  forecast: (p: { target_metric: string; ward_id?: number; horizon_months?: number }) => request<ForecastResponse>(`/predictions/forecast${qs(p)}`),
  infraDemand: (target_year: number) => request<InfraDemand>(`/predictions/infrastructure-demand${qs({ target_year })}`),
  retrain: () => post<{ metrics: Record<string, any> }>('/predictions/retrain'),

  // scenarios
  levers: () => request<{ levers: Record<string, Lever>; criteria_weights: Record<string, number> }>('/scenarios/levers'),
  scenarios: () => request<Scenario[]>('/scenarios'),
  previewScenario: (b: { title: string; parameters: Record<string, number>; ward_ids?: number[] | null }) => post<SimulationResult>('/scenarios/preview', b),
  createScenario: (b: { title: string; description: string; parameters: Record<string, number>; ward_ids?: number[] | null }) => post<Scenario>('/scenarios', b),
  deleteScenario: (id: number) => request<void>(`/scenarios/${id}`, { method: 'DELETE' }),
  compareScenarios: (ids: number[]) => post<ScenarioComparison>('/scenarios/compare', { scenario_ids: ids, narrative: true }),

  // recommendations
  recommendations: (p: { ward_id?: number; sector?: string; priority?: string; status?: string } = {}) => request<Recommendation[]>(`/recommendations${qs(p)}`),
  setRecommendationStatus: (id: number, status: string) => patch<Recommendation>(`/recommendations/${id}/status`, { status }),
  regenerateRecommendations: () => post<{ count: number }>('/recommendations/regenerate'),
  recommendationBrief: (id: number) => post<Recommendation>(`/recommendations/${id}/brief`),

  // assistant
  assistantStatus: () => request<{ provider: string; model: string | null; llm_available: boolean; mode: string }>('/assistant/status'),
  ask: (question: string, context_ward_id?: number) => post<AssistantResponse>('/assistant/query', { question, context_ward_id }),

  // governance
  dataSources: () => request<DataSource[]>('/data-sources'),
  importData: (form: FormData) => request<Record<string, any>>('/data-sources/import', { method: 'POST', body: form }),
  models: () => request<ModelInfo[]>('/models'),
  audit: (limit = 100) => request<AuditEntry[]>(`/audit${qs({ limit })}`),
};
