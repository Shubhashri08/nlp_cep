import React, { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend as RLegend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { GitCompare, Save, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { useApi, useDebounced } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Card, ErrorState, Loading, PageHeader, StatTile } from '../components/ui';
import type { Scenario, ScenarioComparison, SimulationResult } from '../types';
import { CHART, CATEGORICAL } from '../lib/theme';
import { fmtDate, fmtInt, fmtNum, fmtSigned, titleCase } from '../lib/format';

const KEY_METRICS: { key: string; label: string; better: 'up' | 'down'; digits?: number }[] = [
  { key: 'total_population', label: 'Population', better: 'up', digits: 0 },
  { key: 'daily_transit_ridership', label: 'Daily PT trips', better: 'up', digits: 0 },
  { key: 'avg_peak_congestion_index', label: 'Congestion index', better: 'down', digits: 2 },
  { key: 'flood_risk_score', label: 'Flood exposure', better: 'down', digits: 3 },
  { key: 'monthly_flood_complaints', label: 'Flood complaints / month', better: 'down', digits: 1 },
  { key: 'water_gap_mld', label: 'Water gap (MLD)', better: 'down', digits: 1 },
  { key: 'uncollected_waste_pct', label: 'Unprocessed waste %', better: 'down', digits: 1 },
  { key: 'residents_per_health_facility', label: 'Residents / health facility', better: 'down', digits: 0 },
  { key: 'residents_per_school', label: 'Residents / school', better: 'down', digits: 0 },
  { key: 'open_space_sqm_per_capita', label: 'Open space m² / capita', better: 'up', digits: 2 },
];
const CRIT_LABEL: Record<string, string> = {
  water_adequacy: 'Water', waste_adequacy: 'Waste', health_adequacy: 'Health', education_adequacy: 'Schools',
  drainage_adequacy: 'Drainage', mobility: 'Mobility', flood_safety: 'Flood safety', open_space: 'Open space',
};

const ScenarioStudio: React.FC = () => {
  const { hasRole } = useAuth();
  const levers = useApi(() => api.levers(), []);
  const wards = useApi(() => api.wards(), []);
  const saved = useApi(() => api.scenarios(), []);
  const [params, setParams] = useState<Record<string, number>>({});
  const [scope, setScope] = useState<number[]>([]);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [preview, setPreview] = useState<{ loading: boolean; error: string | null; data: SimulationResult | null }>({ loading: false, error: null, data: null });
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const dParams = useDebounced(params, 350);
  const dScope = useDebounced(scope, 350);

  useEffect(() => {
    let alive = true;
    setPreview((p) => ({ ...p, loading: true, error: null }));
    api.previewScenario({ title: 'preview', parameters: dParams, ward_ids: dScope.length ? dScope : null })
      .then((d) => alive && setPreview({ loading: false, error: null, data: d }))
      .catch((e) => alive && setPreview({ loading: false, error: e.message, data: null }));
    return () => { alive = false; };
  }, [dParams, dScope]);

  const save = async () => {
    setMsg(null);
    try {
      await api.createScenario({ title: title || 'Untitled scenario', description: desc, parameters: params, ward_ids: scope.length ? scope : null });
      setMsg('Scenario saved.'); setTitle(''); setDesc(''); saved.reload();
    } catch (e) { setMsg((e as Error).message); }
  };
  const runCompare = async () => {
    setMsg(null);
    try { setComparison(await api.compareScenarios(compareIds)); } catch (e) { setMsg((e as Error).message); }
  };
  const remove = async (id: number) => { await api.deleteScenario(id).catch((e) => setMsg(e.message)); setCompareIds((c) => c.filter((x) => x !== id)); saved.reload(); };
  const load = (s: Scenario) => { setParams(s.parameters); setScope(s.scope_ward_ids ?? []); setTitle(`${s.title} (copy)`); setDesc(s.description); window.scrollTo({ top: 0, behavior: 'smooth' }); };

  const sim = preview.data;
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="What-if analysis" title="Scenario Studio"
        subtitle="Adjust planning levers and see their modelled effect on a baseline aggregated from the database for the chosen wards. Every effect cites its elasticity or norm, and each scenario is scored on an 8-criterion service-adequacy index." />
      <div className="grid xl:grid-cols-[360px_1fr] gap-6">
        <Card title="Levers">
          <AsyncBlock state={levers}>{(l) => (
            <div className="space-y-4">
              <label className="block"><span className="label">Spatial scope</span>
                <select multiple className="input mt-1 h-24 text-xs" value={scope.map(String)} onChange={(e) => setScope(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}>
                  {wards.data?.slice().sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
                <span className="text-[11px] text-muted">{scope.length ? `${scope.length} ward(s) selected` : 'None selected = whole city'} · Ctrl/Cmd-click for multiple</span>
              </label>
              {Object.entries(l.levers).map(([k, lv]) => {
                const v = params[k] ?? lv.default;
                const step = lv.max > 200 ? 10 : lv.max > 50 ? 5 : 1;
                return (
                  <label key={k} className="block">
                    <div className="flex justify-between text-sm"><span className="text-ink">{lv.label}</span><span className="font-semibold text-police">{fmtNum(v, 0)} {lv.unit}</span></div>
                    <input type="range" min={lv.min} max={lv.max} step={step} value={v} className="w-full accent-marigold"
                      onChange={(e) => setParams((p) => ({ ...p, [k]: Number(e.target.value) }))} />
                  </label>
                );
              })}
              <button className="btn-ghost text-xs" onClick={() => setParams({})}>Reset levers</button>
              {hasRole('PLANNER') && (
                <div className="pt-3 border-t border-line space-y-2">
                  <input className="input" placeholder="Scenario title" value={title} onChange={(e) => setTitle(e.target.value)} />
                  <textarea className="input text-xs" placeholder="Description / rationale" value={desc} onChange={(e) => setDesc(e.target.value)} />
                  <button className="btn-primary w-full" onClick={save} disabled={title.trim().length < 3}><Save className="h-4 w-4" />Save scenario</button>
                </div>
              )}
              {msg && <p className="text-xs text-police">{msg}</p>}
            </div>
          )}</AsyncBlock>
        </Card>

        <div className="space-y-6">
          {preview.error && <ErrorState message={preview.error} />}
          {!sim && preview.loading && <Loading label="Simulating…" />}
          {sim && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatTile label="Service adequacy score" value={fmtNum(sim.score_breakdown.simulated_score, 1)} accent="marigold" hint={`baseline ${fmtNum(sim.score_breakdown.baseline_score, 1)}`} />
                <StatTile label="Score change" value={fmtSigned(sim.score_breakdown.score_change, 2)} accent={sim.score_breakdown.score_change >= 0 ? 'buff' : 'citrine'} />
                <StatTile label="Indicative capital cost" value={`₹${fmtInt(sim.capital_cost_cr)} Cr`} accent="police" />
                <StatTile label="Points per ₹100 Cr" value={sim.score_breakdown.score_gain_per_100cr !== null ? fmtNum(sim.score_breakdown.score_gain_per_100cr, 2) : '—'} hint="cost-effectiveness" />
              </div>
              <div className="grid lg:grid-cols-2 gap-6">
                <Card title="Baseline → simulated" subtitle={`Scope: ${sim.baseline_metrics.scope}`} bodyClass="p-0 pt-3">
                  <table className="table-base"><thead><tr><th>Indicator</th><th className="text-right">Baseline</th><th className="text-right">Scenario</th><th className="text-right">Change</th></tr></thead>
                    <tbody>{KEY_METRICS.map((m) => {
                      const b = sim.baseline_metrics[m.key] as number; const s = sim.simulated_metrics[m.key] as number;
                      const delta = s - b; const good = m.better === 'up' ? delta > 0 : delta < 0;
                      return <tr key={m.key}><td>{m.label}</td><td className="text-right">{fmtNum(b, m.digits)}</td><td className="text-right font-semibold">{fmtNum(s, m.digits)}</td>
                        <td className="text-right font-semibold" style={{ color: Math.abs(delta) < 1e-9 ? '#5E6B80' : good ? '#3F8A5A' : '#8A3B08' }}>{Math.abs(delta) < 1e-9 ? '—' : fmtSigned(delta, m.digits)}</td></tr>;
                    })}</tbody></table>
                </Card>
                <Card title="Adequacy by criterion" subtitle="0–100, weights shown in tooltip">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={Object.keys(sim.score_breakdown.weights).map((k) => ({ name: CRIT_LABEL[k], baseline: sim.score_breakdown.baseline_criteria[k], scenario: sim.score_breakdown.simulated_criteria[k], w: sim.score_breakdown.weights[k] }))}
                      layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" domain={[0, 100]} tick={CHART.tick} />
                      <YAxis type="category" dataKey="name" tick={CHART.tick} width={85} />
                      <Tooltip {...CHART.tooltip} formatter={(v: number, n: string, p: any) => [`${fmtNum(v, 1)} (weight ${Math.round(p.payload.w * 100)}%)`, n]} />
                      <RLegend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="baseline" name="Baseline" fill={CATEGORICAL[3]} radius={[0, 4, 4, 0]} barSize={7} />
                      <Bar dataKey="scenario" name="Scenario" fill={CATEGORICAL[1]} radius={[0, 4, 4, 0]} barSize={7} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>
              <Card title="Assumptions & evidence">
                <ul className="list-disc pl-5 space-y-1 text-sm">{sim.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
                <p className="text-[11px] text-muted mt-2">{sim.evidence_status}</p>
              </Card>
            </>
          )}
        </div>
      </div>

      <Card className="mt-6" title="Saved scenarios" subtitle="Tick 2–4 to compare"
        actions={<button className="btn-secondary text-xs" disabled={compareIds.length < 2 || compareIds.length > 4} onClick={runCompare}><GitCompare className="h-4 w-4" />Compare ({compareIds.length})</button>} bodyClass="p-0 pt-3">
        <AsyncBlock state={saved} isEmpty={(d) => d.length === 0} empty="No saved scenarios yet.">{(list) => (
          <table className="table-base"><thead><tr><th></th><th>Scenario</th><th>Levers</th><th className="text-right">Score</th><th className="text-right">Cost ₹ Cr</th><th>Created</th><th></th></tr></thead>
            <tbody>{list.map((s) => (
              <tr key={s.id}>
                <td><input type="checkbox" className="accent-marigold" checked={compareIds.includes(s.id)} aria-label={`Compare ${s.title}`}
                  onChange={(e) => setCompareIds((c) => e.target.checked ? [...c, s.id] : c.filter((x) => x !== s.id))} /></td>
                <td><button className="font-semibold text-police hover:underline text-left" onClick={() => load(s)}>{s.title}</button><div className="text-[11px] text-muted">{s.description}</div></td>
                <td className="text-xs">{Object.entries(s.parameters).map(([k, v]) => `${titleCase(k)}: ${v}`).join(' · ')}</td>
                <td className="text-right font-semibold">{fmtNum(s.score, 1)}<div className="text-[11px] text-muted font-normal">{fmtSigned(s.score_breakdown?.score_change, 2)}</div></td>
                <td className="text-right">{fmtInt(s.capital_cost_cr)}</td><td className="text-xs text-muted">{fmtDate(s.created_at)}</td>
                <td>{hasRole('PLANNER') && <button className="btn-ghost px-2" onClick={() => remove(s.id)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>}</td>
              </tr>
            ))}</tbody></table>
        )}</AsyncBlock>
      </Card>

      {comparison && <ComparisonView c={comparison} />}
    </div>
  );
};

const ComparisonView: React.FC<{ c: ScenarioComparison }> = ({ c }) => {
  const ids = c.scenarios.map((s) => String(s.id));
  const title = (id: string) => c.scenarios.find((s) => String(s.id) === id)?.title ?? id;
  const critData = useMemo(() => Object.keys(c.weights).map((k) => ({ name: CRIT_LABEL[k], ...Object.fromEntries(ids.map((id) => [id, c.criteria[id]?.[k] ?? 0])) })), [c]);
  return (
    <Card className="mt-6 animate-fade-in" title="Scenario comparison" subtitle={c.warning ?? 'Same baseline scope'}>
      {c.narrative && <p className="text-sm bg-buff-50 border border-buff-300 rounded-lg p-3 mb-4">{c.narrative}</p>}
      <div className="grid lg:grid-cols-2 gap-6">
        <div>
          <div className="label mb-2">Ranking</div>
          <table className="table-base"><thead><tr><th>#</th><th>Scenario</th><th className="text-right">Score</th><th className="text-right">Δ</th><th className="text-right">₹ Cr</th><th className="text-right">pts / ₹100 Cr</th></tr></thead>
            <tbody>{c.ranking.map((r, i) => <tr key={r.id}><td>{i + 1}</td><td className="font-semibold text-police">{r.title}</td><td className="text-right">{fmtNum(r.score, 1)}</td>
              <td className="text-right">{fmtSigned(r.score_change, 2)}</td><td className="text-right">{fmtInt(r.capital_cost_cr)}</td><td className="text-right">{fmtNum(r.score_gain_per_100cr, 2)}</td></tr>)}</tbody></table>
          <div className="label mt-5 mb-2">Key indicators</div>
          <div className="overflow-x-auto"><table className="table-base"><thead><tr><th>Indicator</th><th className="text-right">Baseline</th>{ids.map((id) => <th key={id} className="text-right">{title(id)}</th>)}</tr></thead>
            <tbody>{c.metrics_table.map((row) => <tr key={row.metric}><td>{titleCase(row.metric)}</td><td className="text-right text-muted">{fmtNum(row.baseline, 2)}</td>
              {ids.map((id) => <td key={id} className="text-right">{fmtNum(row[id], 2)}</td>)}</tr>)}</tbody></table></div>
        </div>
        <div>
          <div className="label mb-2">Adequacy criteria (0–100)</div>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={critData} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" domain={[0, 100]} tick={CHART.tick} />
              <YAxis type="category" dataKey="name" tick={CHART.tick} width={85} /><Tooltip {...CHART.tooltip} formatter={(v: number) => fmtNum(v, 1)} />
              <RLegend wrapperStyle={{ fontSize: 12 }} />
              {ids.map((id, i) => <Bar key={id} dataKey={id} name={title(id)} fill={CATEGORICAL[i]} radius={[0, 4, 4, 0]} barSize={6} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
};

export default ScenarioStudio;
