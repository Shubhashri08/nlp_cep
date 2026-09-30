import React, { useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Sparkles } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Badge, Card, ErrorState, Loading, PageHeader, Select } from '../components/ui';
import { EntityText, entityColor } from '../components/EntityText';
import type { NLPResult } from '../types';
import { CHART, CATEGORICAL } from '../lib/theme';
import { LANGUAGE_LABELS, fmtNum, titleCase } from '../lib/format';

const SAMPLES = [
  'Severe waterlogging near Andheri Station every monsoon, the subway is closed and potholes on SV Road are dangerous.',
  'Kachra peti bhar gayi hai near Kurla West market, 4 din se koi safai nahi, bahut badbu aa rahi hai',
  'Streetlights off along BKC for two weeks and women feel unsafe walking to the bus stop at night',
  'आमच्या भागात तीन दिवसांपासून पाणी नाही, नळाला गढूळ पाणी येत आहे',
  'Dengue cases rising in our chawl in Govandi, the dispensary has no doctor in the evening. Please send fogging.',
];

const NLPAnalytics: React.FC = () => {
  const [text, setText] = useState(SAMPLES[0]);
  const [res, setRes] = useState<NLPResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const meta = useApi(() => api.categories(), []);

  const run = async (t = text) => {
    setBusy(true); setErr(null);
    try { setRes(await api.analyze(t)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  const gold = meta.data?.metrics?.gold_set;
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="NLP pipeline" title="Text Analyzer"
        subtitle="Run any grievance or planning sentence through the live pipeline: language ID → Hinglish/Devanagari normalisation → multi-label classification → hybrid NER (OSM gazetteer + patterns) → geocoding → summary." />
      <div className="grid lg:grid-cols-[1.2fr_1fr] gap-6">
        <Card title="Input">
          <textarea className="input min-h-[130px]" value={text} onChange={(e) => setText(e.target.value)} aria-label="Text to analyse" />
          <div className="flex flex-wrap gap-2 mt-3">
            {SAMPLES.map((s, i) => <button key={i} className="btn-outline text-xs py-1" onClick={() => { setText(s); run(s); }}>Sample {i + 1}</button>)}
          </div>
          <button className="btn-primary mt-4" disabled={busy || !text.trim()} onClick={() => run()}><Sparkles className="h-4 w-4" />{busy ? 'Analysing…' : 'Analyse'}</button>
          {gold && <p className="text-[11px] text-muted mt-3">Classifier {meta.data?.model_version}: hand-written gold set micro-F1 {fmtNum(gold.micro_f1 * 100, 1)}% ({gold.samples} sentences, never seen in training).</p>}
        </Card>
        <Card title="Result">
          {busy && <Loading />}
          {err && <ErrorState message={err} />}
          {!busy && !err && !res && <p className="text-sm text-muted">Pick a sample or type text and press Analyse.</p>}
          {res && !busy && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge color="#2E4365">{LANGUAGE_LABELS[res.language] ?? res.language} · {Math.round(res.language_confidence * 100)}%</Badge>
                <Badge color="#A8490F">{titleCase(res.primary_category)}</Badge>
                {res.ward_name && <Badge color="#1F5360">{res.ward_name}</Badge>}
              </div>
              <div className="bg-pearl-100 rounded-lg p-3 text-sm"><div className="label">Summary</div>{res.summary}</div>
              <div>
                <div className="label mb-1">Category probabilities (multi-label, threshold 35%)</div>
                <ResponsiveContainer width="100%" height={Math.max(60, res.categories.length * 30)}>
                  <BarChart data={res.categories.map((c) => ({ name: titleCase(c.category), p: Math.round(c.confidence * 100) }))} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid horizontal={false} stroke={CHART.grid} />
                    <XAxis type="number" domain={[0, 100]} tick={CHART.tick} unit="%" />
                    <YAxis type="category" dataKey="name" width={140} tick={CHART.tick} />
                    <Tooltip {...CHART.tooltip} formatter={(v: number) => `${v}%`} />
                    <Bar dataKey="p" name="Probability" fill={CATEGORICAL[2]} radius={[0, 4, 4, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="text-sm">
                <div className="label mb-1">Location</div>
                {res.is_location_resolved ? <>
                  <div className="font-semibold text-police">{res.resolved_location}</div>
                  <div className="text-xs text-muted">{res.geocoding_method} · confidence {Math.round(res.geocoding_confidence * 100)}% · {res.resolved_lat?.toFixed(5)}, {res.resolved_lng?.toFixed(5)}</div>
                </> : <div className="text-muted">No resolvable place in the text (coordinates are never guessed).</div>}
              </div>
            </div>
          )}
        </Card>
      </div>
      {res && !busy && (
        <Card className="mt-6" title="Named entities" subtitle="Hover a highlight for label, confidence and source (gazetteer / pattern / lexicon)">
          <EntityText text={res.cleaned_text} entities={res.entities} />
          <div className="overflow-x-auto mt-4">
            <table className="table-base">
              <thead><tr><th>Entity</th><th>Label</th><th>Source</th><th className="text-right">Confidence</th><th>Ward</th></tr></thead>
              <tbody>{res.entities.map((e, i) => (
                <tr key={i}><td className="font-semibold">{e.text}</td><td><Badge color={entityColor(e.label)}>{e.label}</Badge></td>
                  <td className="text-xs text-muted">{e.source}</td><td className="text-right">{Math.round(e.confidence * 100)}%</td><td className="text-xs">{e.ward_code ?? '—'}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Card>
      )}
      <ClusterSummary />
    </div>
  );
};

const ClusterSummary: React.FC = () => {
  const wards = useApi(() => api.wards(), []);
  const [wardId, setWardId] = useState('');
  const [category, setCategory] = useState('FLOODING');
  const [state, setState] = useState<{ loading: boolean; error: string | null; data: Record<string, any> | null }>({ loading: false, error: null, data: null });
  const run = async () => {
    if (!wardId) return;
    setState({ loading: true, error: null, data: null });
    try { setState({ loading: false, error: null, data: await api.clusterSummary(Number(wardId), category) }); }
    catch (e) { setState({ loading: false, error: (e as Error).message, data: null }); }
  };
  return (
    <Card className="mt-6" title="Summarise a complaint cluster" subtitle="Extractive TextRank summary (LLM-abstractive when a provider is configured), traceable to source records">
      <div className="flex flex-wrap items-end gap-3">
        <Select label="Ward" value={wardId} onChange={(e) => setWardId(e.target.value)}>
          <option value="">Choose ward…</option>{wards.data?.sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </Select>
        <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          {['FLOODING', 'DRAINAGE', 'WASTE_MANAGEMENT', 'WATER_SUPPLY', 'ROAD_INFRASTRUCTURE', 'TRAFFIC', 'HEALTHCARE', 'STREETLIGHT', 'AIR_QUALITY', 'PUBLIC_SAFETY'].map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
        </Select>
        <button className="btn-secondary" disabled={!wardId || state.loading} onClick={run}>Summarise</button>
      </div>
      {state.loading && <Loading />}
      {state.error && <ErrorState message={state.error} />}
      {state.data && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="bg-pearl-100 rounded-lg p-3"><div className="label">{state.data.method}</div>{state.data.summary}</div>
          {state.data.method !== 'extractive-textrank' && <div className="text-xs text-muted">{state.data.statistics}</div>}
          <div><div className="label mb-1">Representative complaints</div><ul className="list-disc pl-5 space-y-1">{(state.data.representative_complaints ?? []).map((s: string, i: number) => <li key={i}>{s}</li>)}</ul></div>
          <div className="text-[11px] text-muted">Based on {state.data.cluster_count} records · top issues: {(state.data.top_issues ?? []).join(', ') || '—'}</div>
        </div>
      )}
    </Card>
  );
};

export default NLPAnalytics;
