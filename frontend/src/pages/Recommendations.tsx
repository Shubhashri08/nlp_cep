import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ChevronDown, ChevronUp, MapPin, RefreshCw, Wand2 } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Badge, Card, Meter, PageHeader, Select, StatusBadge } from '../components/ui';
import type { Recommendation } from '../types';
import { fmtInt, fmtNum, titleCase } from '../lib/format';

const SECTORS = ['Water Supply', 'Waste Management', 'Drainage & Storm Water', 'Healthcare Capacity', 'Education', 'Public Transit Access', 'Open Space'];
const PRIORITY_COLOR: Record<string, string> = { HIGH: '#8A3B08', MEDIUM: '#A26815', LOW: '#5E6B80' };

const Recommendations: React.FC = () => {
  const { hasRole, config } = useAuth();
  const [params] = useSearchParams();
  const [wardId, setWardId] = useState(params.get('ward') ?? '');
  const [sector, setSector] = useState('');
  const [priority, setPriority] = useState('');
  const [status, setStatus] = useState('');
  const wards = useApi(() => api.wards(), []);
  const recs = useApi(() => api.recommendations({ ward_id: wardId ? Number(wardId) : undefined, sector, priority, status }), [wardId, sector, priority, status]);
  const [busy, setBusy] = useState(false);

  const regenerate = async () => { setBusy(true); try { await api.regenerateRecommendations(); recs.reload(); } finally { setBusy(false); } };
  const replace = (r: Recommendation) => recs.setData((recs.data ?? []).map((x) => (x.id === r.id ? r : x)));

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Multi-criteria decision analysis" title="Recommendations"
        subtitle="Interventions generated for every critical or high gap, scored per intervention: gap severity 35%, population affected 25%, related complaint pressure 20%, growth pressure 20%. Costs are indicative unit rates for ranking."
        actions={hasRole('PLANNER') ? <button className="btn-outline" onClick={regenerate} disabled={busy}><RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />Regenerate</button> : undefined} />
      <div className="flex flex-wrap gap-3 mb-6">
        <Select label="Ward" value={wardId} onChange={(e) => setWardId(e.target.value)}><option value="">All wards</option>
          {wards.data?.slice().sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</Select>
        <Select label="Sector" value={sector} onChange={(e) => setSector(e.target.value)}><option value="">All sectors</option>{SECTORS.map((s) => <option key={s}>{s}</option>)}</Select>
        <Select label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">All</option>{['HIGH', 'MEDIUM', 'LOW'].map((p) => <option key={p}>{p}</option>)}</Select>
        <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All</option>{['PROPOSED', 'APPROVED', 'IN_PROGRESS', 'REJECTED'].map((p) => <option key={p} value={p}>{titleCase(p)}</option>)}</Select>
      </div>
      <AsyncBlock state={recs} isEmpty={(d) => d.length === 0} empty="No recommendations match these filters.">{(list) => (
        <>
          <p className="text-sm text-muted mb-3">{list.length} interventions · total indicative cost ₹{fmtInt(list.reduce((a, r) => a + (r.estimated_cost_cr ?? 0), 0))} Cr</p>
          <div className="grid lg:grid-cols-2 gap-4">
            {list.map((r) => <RecCard key={r.id} r={r} canEdit={hasRole('PLANNER')} canBrief={hasRole('PLANNER', 'ANALYST') && config?.llm_provider !== 'none'} onChange={replace} />)}
          </div>
        </>
      )}</AsyncBlock>
    </div>
  );
};

const RecCard: React.FC<{ r: Recommendation; canEdit: boolean; canBrief: boolean; onChange: (r: Recommendation) => void }> = ({ r, canEdit, canBrief, onChange }) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const act = async (key: string, fn: () => Promise<Recommendation>) => {
    setBusy(key); setErr(null);
    try { onChange(await fn()); } catch (e) { setErr((e as Error).message); } finally { setBusy(null); }
  };
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1"><Badge color={PRIORITY_COLOR[r.priority_level]}>{r.priority_level}</Badge><Badge color="#3A5A94">{r.sector}</Badge><StatusBadge status={r.status} /></div>
          <h3 className="font-display text-lg text-police leading-snug">{r.title}</h3>
        </div>
        <div className="text-right shrink-0"><div className="font-display text-3xl text-police leading-none">{fmtNum(r.score, 0)}</div><div className="label">score</div></div>
      </div>
      <p className="text-sm text-ink/90 mt-2 leading-relaxed">{r.recommendation_text}</p>
      <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-muted">
        <span>Indicative cost <b className="text-ink">₹{fmtNum(r.estimated_cost_cr, 1)} Cr</b></span>
        <Link className="inline-flex items-center gap-1 text-police hover:underline" to={`/gis?ward=${r.ward_id}`}><MapPin className="h-3 w-3" />{r.ward_name}</Link>
      </div>
      {r.llm_brief && <div className="mt-3 text-sm bg-buff-50 border border-buff-300 rounded-lg p-3"><div className="label mb-1">Planner brief (LLM, grounded in evidence)</div>{r.llm_brief}</div>}
      <button className="mt-3 text-xs font-semibold text-police inline-flex items-center gap-1" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}Why this score & evidence</button>
      {open && (
        <div className="mt-2 space-y-3 animate-fade-in">
          {r.contributing_factors.map((f) => (
            <div key={f.factor}><div className="flex justify-between text-xs"><span>{f.factor} · <span className="text-muted">{f.value}</span></span><span className="font-semibold">{Math.round(f.weight * 100)}% weight</span></div>
              <Meter value={f.normalized_score} color="#3A5A94" /></div>
          ))}
          <div className="text-xs"><div className="label mb-1">Supporting evidence</div>
            <ul className="space-y-1">{r.supporting_evidence.map((e, i) => (
              <li key={i} className="font-mono text-[11px] bg-pearl-100 rounded px-2 py-1">{e.dataset}{e.record_id ? `#${e.record_id}` : ''} · {e.field} = {typeof e.value === 'number' ? fmtNum(e.value, 2) : String(e.value)} {e.unit ?? ''}</li>
            ))}</ul>
            <div className="text-[11px] text-muted mt-1">{r.methodology}</div>
          </div>
        </div>
      )}
      {(canEdit || canBrief) && (
        <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-line">
          {canEdit && ['APPROVED', 'IN_PROGRESS', 'REJECTED'].map((s) => (
            <button key={s} className="btn-outline text-xs py-1" disabled={!!busy || r.status === s} onClick={() => act(s, () => api.setRecommendationStatus(r.id, s))}>{titleCase(s)}</button>
          ))}
          {canBrief && <button className="btn-ghost text-xs py-1" disabled={!!busy} onClick={() => act('brief', () => api.recommendationBrief(r.id))}><Wand2 className="h-3.5 w-3.5" />{busy === 'brief' ? 'Writing…' : 'LLM brief'}</button>}
          {err && <span className="text-xs text-citrine">{err}</span>}
        </div>
      )}
    </Card>
  );
};

export default Recommendations;
