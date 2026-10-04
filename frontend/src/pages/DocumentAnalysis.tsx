import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { FileUp } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Badge, Card, ErrorState, PageHeader } from '../components/ui';
import { entityColor } from '../components/EntityText';
import type { PlanningDocument } from '../types';
import { CHART, CATEGORICAL } from '../lib/theme';
import { fmtDate, fmtInt, fmtNum, titleCase } from '../lib/format';

const SAMPLE = `Draft Ward Development Report – Eastern Suburbs

Storm Water Drainage
Low lying pockets of Kurla, Chembur and Govandi flood during every monsoon. The existing drains in L ward and M/E ward were designed for 25 mm per hour and must be upgraded to the 50 mm per hour standard recommended by BRIMSTOWAD. Two new pumping stations are proposed near the Mithi river outfall.

Solid Waste Management
The Deonar dumping ground is beyond capacity. Decentralised composting units of 20 tonnes per day are proposed in each ward, with segregated door to door collection in Govandi and Mankhurd.

Public Transport
Feeder bus routes connecting Ghatkopar metro station to residential colonies in N ward remain inadequate. The report recommends 40 new bus stops and a skywalk at Kurla station.

Health
Primary health posts in M/E ward serve more than 60,000 residents each, far above the URDPFI norm of 15,000. Five new dispensaries are proposed.`;

const DocumentAnalysis: React.FC = () => {
  const { hasRole } = useAuth();
  const docs = useApi(() => api.documents(), []);
  const [selected, setSelected] = useState<PlanningDocument | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const canUpload = hasRole('PLANNER', 'ANALYST');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = new FormData();
    if (file) form.append('file', file); else form.append('text', text);
    if (title) form.append('title', title);
    setBusy(true); setErr(null);
    try { const d = await api.uploadDocument(form); setSelected(d); docs.reload(); setFile(null); setText(''); setTitle(''); }
    catch (e2) { setErr((e2 as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Urban development reports" title="Planning Documents"
        subtitle="Upload a development plan, audit or consultant report (PDF / TXT). The system segments it into sections, classifies each by sector, extracts places and organisations, links mentioned wards to the map, and writes an executive summary." />
      <div className="grid lg:grid-cols-[380px_1fr] gap-6">
        <div className="space-y-6">
          {canUpload && (
            <Card title="Analyse a document">
              <form onSubmit={submit} className="space-y-3">
                <input className="input" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
                <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-line rounded-lg p-4 text-sm text-muted cursor-pointer hover:border-marigold">
                  <FileUp className="h-5 w-5 text-marigold" />{file ? file.name : 'Choose PDF or TXT (max 15 MB)'}
                  <input type="file" accept=".pdf,.txt,.md" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                </label>
                {!file && <>
                  <div className="text-center label">or paste text</div>
                  <textarea className="input min-h-[120px] text-xs" value={text} onChange={(e) => setText(e.target.value)} />
                  <button type="button" className="text-xs text-police underline" onClick={() => { setText(SAMPLE); setTitle('Eastern Suburbs draft report'); }}>Use sample report</button>
                </>}
                {err && <p className="text-sm text-citrine">{err}</p>}
                <button className="btn-primary w-full" disabled={busy || (!file && text.trim().split(/\s+/).length < 20)}>{busy ? 'Analysing…' : 'Analyse'}</button>
              </form>
            </Card>
          )}
          <Card title="Analysed documents" bodyClass="p-0 pt-2">
            <AsyncBlock state={docs} isEmpty={(d) => d.length === 0} empty="No documents analysed yet.">{(d) => (
              <ul className="divide-y divide-line">
                {d.map((doc) => (
                  <li key={doc.id}><button onClick={() => setSelected(doc)} className={`w-full text-left px-5 py-3 hover:bg-buff-50 ${selected?.id === doc.id ? 'bg-buff-50' : ''}`}>
                    <div className="font-semibold text-sm text-police">{doc.title}</div>
                    <div className="text-[11px] text-muted">{fmtDate(doc.created_at)} · {fmtInt(doc.text_length)} chars{doc.page_count ? ` · ${doc.page_count} pages` : ''}</div>
                  </button></li>
                ))}
              </ul>
            )}</AsyncBlock>
          </Card>
        </div>
        <div>{selected ? <DocView d={selected} /> : <Card><p className="text-sm text-muted">Select or analyse a document to see the results.</p>{!canUpload && <p className="text-xs text-muted mt-1">Uploading requires the Planner or Analyst role.</p>}</Card>}</div>
      </div>
    </div>
  );
};

const DocView: React.FC<{ d: PlanningDocument }> = ({ d }) => (
  <div className="space-y-6 animate-fade-in">
    <Card title={d.title} subtitle={`Summary · ${d.summary_method}`}>
      <p className="text-sm leading-relaxed whitespace-pre-line">{d.summary}</p>
      {d.wards_mentioned && d.wards_mentioned.length > 0 && (
        <div className="mt-4"><div className="label mb-1.5">Wards referenced</div>
          <div className="flex flex-wrap gap-2">{d.wards_mentioned.map((w) => (
            <Link key={w.ward_id} to={`/gis?ward=${w.ward_id}`}><Badge color="#1F5360">{w.ward_code} · {w.mentions}×</Badge></Link>
          ))}</div></div>
      )}
    </Card>
    <div className="grid xl:grid-cols-2 gap-6">
      <Card title="Sector focus" subtitle="Share of text by classified sector">
        {d.sector_distribution?.length ? (
          <ResponsiveContainer width="100%" height={Math.max(140, d.sector_distribution.length * 28)}>
            <BarChart data={d.sector_distribution.map((s) => ({ name: titleCase(s.category), v: s.share_pct }))} layout="vertical" margin={{ left: 10, right: 30 }}>
              <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" tick={CHART.tick} unit="%" />
              <YAxis type="category" dataKey="name" tick={CHART.tick} width={140} /><Tooltip {...CHART.tooltip} formatter={(v: number) => `${fmtNum(v, 1)}%`} />
              <Bar dataKey="v" name="Share" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} barSize={14} />
            </BarChart>
          </ResponsiveContainer>
        ) : <ErrorState message="No sections classified" />}
      </Card>
      <Card title="Key entities" bodyClass="p-5 pt-3">
        <div className="flex flex-wrap gap-1.5">{(d.entities ?? []).slice(0, 40).map((e, i) => (
          <Badge key={i} color={entityColor(e.label)} title={e.label}>{e.text}{e.count > 1 ? ` ×${e.count}` : ''}</Badge>
        ))}</div>
      </Card>
    </div>
    <Card title="Sections" bodyClass="p-0 pt-2">
      <table className="table-base">
        <thead><tr><th>Section</th><th>Sector</th><th>Key sentence</th></tr></thead>
        <tbody>{(d.sections ?? []).map((s, i) => (
          <tr key={i}><td className="font-semibold text-police whitespace-nowrap">{s.title}<div className="text-[11px] text-muted font-normal">{s.word_count} words</div></td>
            <td><Badge color="#A8490F">{titleCase(s.primary_category)} {Math.round(s.confidence * 100)}%</Badge></td><td className="text-xs">{s.summary}</td></tr>
        ))}</tbody>
      </table>
    </Card>
  </div>
);

export default DocumentAnalysis;
