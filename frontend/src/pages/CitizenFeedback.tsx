import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Plus, Search, X } from 'lucide-react';
import { api } from '../api/client';
import { useApi, useDebounced } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Badge, Card, EmptyState, ErrorState, Loading, PageHeader, ProvenanceBadge, Select, StatusBadge } from '../components/ui';
import { EntityText } from '../components/EntityText';
import type { CitizenRequest, RequestStatus, SemanticResult } from '../types';
import { LANGUAGE_LABELS, fmtDate, fmtNum, titleCase } from '../lib/format';

const CATEGORIES = ['FLOODING', 'DRAINAGE', 'WASTE_MANAGEMENT', 'WATER_SUPPLY', 'ROAD_INFRASTRUCTURE', 'TRAFFIC', 'PUBLIC_TRANSPORT', 'STREETLIGHT',
  'ELECTRICITY', 'PUBLIC_SAFETY', 'HEALTHCARE', 'EDUCATION', 'PARKS', 'ENVIRONMENT', 'AIR_QUALITY', 'HOUSING', 'OTHER'];
const STATUSES: RequestStatus[] = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
const PAGE = 25;

const CitizenFeedback: React.FC = () => {
  const { hasRole } = useAuth();
  const [params] = useSearchParams();
  const [wardId, setWardId] = useState(params.get('ward') ?? '');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [language, setLanguage] = useState('');
  const [q, setQ] = useState('');
  const dq = useDebounced(q, 350);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<CitizenRequest | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [semQuery, setSemQuery] = useState('');
  const [sem, setSem] = useState<{ loading: boolean; error: string | null; results: SemanticResult[] | null }>({ loading: false, error: null, results: null });

  const wards = useApi(() => api.wards(), []);
  const list = useApi(() => api.complaints({ ward_id: wardId ? Number(wardId) : undefined, category, status, language, q: dq, limit: PAGE, offset }),
    [wardId, category, status, language, dq, offset]);

  const resetPage = <T,>(fn: (v: T) => void) => (v: T) => { setOffset(0); fn(v); };

  const runSemantic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (semQuery.trim().length < 2) return;
    setSem({ loading: true, error: null, results: null });
    try {
      setSem({ loading: false, error: null, results: await api.semanticSearch({ query: semQuery, top_k: 10, ward_id: wardId ? Number(wardId) : undefined }) });
    } catch (err) { setSem({ loading: false, error: (err as Error).message, results: null }); }
  };

  const updateStatus = async (id: number, s: RequestStatus) => {
    const updated = await api.setComplaintStatus(id, s);
    setSelected(updated);
    list.reload();
  };

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Grievance redressal" title="Citizen Feedback"
        subtitle="Every complaint is processed by the NLP pipeline: language detection, multi-label classification, entity extraction, geocoding and semantic embedding."
        actions={hasRole('PLANNER', 'ANALYST') ? <button className="btn-primary" onClick={() => setShowNew(true)}><Plus className="h-4 w-4" />Log complaint</button> : undefined} />

      <Card className="mb-6" title="Semantic search" subtitle="Finds complaints by meaning (64-d LSA embeddings), not just keywords">
        <form onSubmit={runSemantic} className="flex gap-2">
          <input className="input" placeholder='e.g. "sewage smell near the station" or "paani nahi aata"' value={semQuery} onChange={(e) => setSemQuery(e.target.value)} />
          <button className="btn-secondary" disabled={sem.loading}><Search className="h-4 w-4" />Search</button>
        </form>
        {sem.loading && <Loading />}
        {sem.error && <ErrorState message={sem.error} />}
        {sem.results && (sem.results.length === 0 ? <EmptyState message="No semantically similar complaints." /> : (
          <div className="mt-3 divide-y divide-line">
            {sem.results.map((r) => (
              <div key={r.id} className="py-2 flex items-start gap-3">
                <span className="font-mono text-xs text-marigold-700 w-12 shrink-0 pt-0.5">{fmtNum(r.similarity_score * 100, 0)}%</span>
                <div className="flex-1 text-sm">{r.text}<div className="text-[11px] text-muted">{titleCase(r.primary_category)} · {r.ward_name ?? 'unassigned'} · {fmtDate(r.created_at)}</div></div>
                {r.status && <StatusBadge status={r.status} />}
              </div>
            ))}
          </div>
        ))}
      </Card>

      <Card bodyClass="p-0">
        <div className="flex flex-wrap items-end gap-3 p-4 border-b border-line">
          <label className="flex-1 min-w-[180px]"><span className="label">Text contains</span>
            <input className="input mt-1 py-1.5" value={q} onChange={(e) => { setOffset(0); setQ(e.target.value); }} placeholder="keyword" /></label>
          <Select label="Ward" value={wardId} onChange={(e) => resetPage(setWardId)(e.target.value)}>
            <option value="">All wards</option>{wards.data?.sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
          <Select label="Category" value={category} onChange={(e) => resetPage(setCategory)(e.target.value)}>
            <option value="">All</option>{CATEGORIES.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
          </Select>
          <Select label="Status" value={status} onChange={(e) => resetPage(setStatus)(e.target.value)}>
            <option value="">All</option>{STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
          </Select>
          <Select label="Language" value={language} onChange={(e) => resetPage(setLanguage)(e.target.value)}>
            <option value="">All</option>{Object.entries(LANGUAGE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>
        <AsyncBlock state={list} isEmpty={(d) => d.items.length === 0} empty="No complaints match these filters.">{(d) => (
          <>
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead><tr><th>ID</th><th>Complaint</th><th>Category</th><th>Ward</th><th>Lang</th><th>Status</th><th>Date</th></tr></thead>
                <tbody>
                  {d.items.map((r) => (
                    <tr key={r.id} className="cursor-pointer" onClick={() => setSelected(r)}>
                      <td className="font-mono text-[11px] text-muted whitespace-nowrap">{r.request_uid}</td>
                      <td className="max-w-md"><div className="line-clamp-2">{r.original_text}</div>
                        <div className="text-[11px] text-muted mt-0.5 line-clamp-1">{r.summary}</div></td>
                      <td><div className="flex flex-wrap gap-1">{r.categories.slice(0, 2).map((c) => <Badge key={c.category} color="#3A5A94">{titleCase(c.category)} {Math.round(c.confidence * 100)}%</Badge>)}</div></td>
                      <td className="whitespace-nowrap text-xs">{r.ward_name?.split(' (')[0] ?? '—'}</td>
                      <td className="text-xs">{LANGUAGE_LABELS[r.language] ?? r.language}</td>
                      <td><StatusBadge status={r.status} /></td>
                      <td className="text-xs whitespace-nowrap text-muted">{fmtDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between p-3 text-sm">
              <span className="text-muted">{offset + 1}–{Math.min(offset + PAGE, d.total)} of {d.total.toLocaleString('en-IN')}</span>
              <div className="flex gap-2">
                <button className="btn-outline px-2 py-1" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></button>
                <button className="btn-outline px-2 py-1" disabled={offset + PAGE >= d.total} onClick={() => setOffset(offset + PAGE)} aria-label="Next page"><ChevronRight className="h-4 w-4" /></button>
              </div>
            </div>
          </>
        )}</AsyncBlock>
      </Card>

      {selected && <ComplaintDetail r={selected} onClose={() => setSelected(null)} canEdit={hasRole('PLANNER')} onStatus={updateStatus} />}
      {showNew && <NewComplaint onClose={() => setShowNew(false)} onCreated={(r) => { setShowNew(false); setSelected(r); list.reload(); }} />}
    </div>
  );
};

const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({ title, onClose, children }) => (
  <div className="fixed inset-0 z-[1000] bg-police-900/40 flex items-center justify-center p-4" onClick={onClose}>
    <div className="card w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fade-in" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
      <div className="flex items-center justify-between p-4 border-b border-line"><h3 className="font-display text-xl text-police">{title}</h3>
        <button className="btn-ghost px-2" onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button></div>
      <div className="p-5">{children}</div>
    </div>
  </div>
);

const ComplaintDetail: React.FC<{ r: CitizenRequest; onClose: () => void; canEdit: boolean; onStatus: (id: number, s: RequestStatus) => Promise<void> }> = ({ r, onClose, canEdit, onStatus }) => {
  const [err, setErr] = useState<string | null>(null);
  return (
    <Modal title={r.request_uid ?? `#${r.id}`} onClose={onClose}>
      <div className="flex flex-wrap gap-2 mb-3"><StatusBadge status={r.status} /><ProvenanceBadge value={r.provenance} /><Badge>{LANGUAGE_LABELS[r.language] ?? r.language} · {Math.round(r.language_confidence * 100)}%</Badge></div>
      <EntityText text={r.cleaned_text ?? r.original_text} entities={r.entities} />
      <div className="mt-3 text-sm bg-pearl-100 rounded-lg p-3"><span className="label">Summary</span><div>{r.summary}</div></div>
      <div className="grid sm:grid-cols-2 gap-4 mt-4 text-sm">
        <div><div className="label mb-1">Classification</div>
          {r.categories.map((c) => <div key={c.category} className="flex justify-between"><span>{titleCase(c.category)}</span><span className="font-semibold">{Math.round(c.confidence * 100)}%</span></div>)}
          <div className="text-[11px] text-muted mt-1">{r.model_version}</div></div>
        <div><div className="label mb-1">Location</div>
          <div>{r.address ?? '—'}</div><div className="text-muted text-xs">{r.ward_name ?? 'No ward'} · {r.geocoding_method ?? 'NONE'} · {Math.round((r.geocoding_confidence ?? 0) * 100)}%</div>
          {r.latitude && <div className="font-mono text-[11px] text-muted">{r.latitude.toFixed(5)}, {r.longitude?.toFixed(5)}</div>}</div>
      </div>
      <div className="text-xs text-muted mt-3">Received {fmtDate(r.created_at)} via {r.source}{r.resolved_at ? ` · resolved ${fmtDate(r.resolved_at)}` : ''}</div>
      {canEdit && (
        <div className="mt-4 pt-4 border-t border-line flex flex-wrap gap-2 items-center">
          <span className="label">Set status</span>
          {STATUSES.map((s) => <button key={s} disabled={s === r.status} className="btn-outline text-xs py-1" onClick={() => onStatus(r.id, s).catch((e) => setErr(e.message))}>{titleCase(s)}</button>)}
          {err && <span className="text-xs text-citrine">{err}</span>}
        </div>
      )}
    </Modal>
  );
};

const NewComplaint: React.FC<{ onClose: () => void; onCreated: (r: CitizenRequest) => void }> = ({ onClose, onCreated }) => {
  const [text, setText] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [source, setSource] = useState('Ward Office');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      onCreated(await api.createComplaint({ text, source, latitude: lat ? Number(lat) : undefined, longitude: lng ? Number(lng) : undefined }));
    } catch (e2) { setErr((e2 as Error).message); } finally { setBusy(false); }
  };
  return (
    <Modal title="Log a citizen complaint" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block"><span className="label">Complaint text (English, Hindi, Marathi or Hinglish)</span>
          <textarea className="input mt-1 min-h-[110px]" required minLength={5} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Gatar ka paani ghar mein aa raha hai near Kurla station, 3 din se" /></label>
        <div className="grid grid-cols-3 gap-3">
          <label><span className="label">Latitude (optional)</span><input className="input mt-1" value={lat} onChange={(e) => setLat(e.target.value)} inputMode="decimal" /></label>
          <label><span className="label">Longitude (optional)</span><input className="input mt-1" value={lng} onChange={(e) => setLng(e.target.value)} inputMode="decimal" /></label>
          <Select label="Channel" value={source} onChange={(e) => setSource(e.target.value)} className="mt-0">
            {['Ward Office', '1916 Helpline', 'MyBMC App', 'Web Portal', 'Twitter / X'].map((s) => <option key={s}>{s}</option>)}
          </Select>
        </div>
        <p className="text-[11px] text-muted">Without coordinates the location is resolved from place names in the text (OSM gazetteer, then bounded Nominatim).</p>
        {err && <p className="text-sm text-citrine">{err}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={busy}>{busy ? 'Processing…' : 'Submit'}</button></div>
      </form>
    </Modal>
  );
};

export default CitizenFeedback;
