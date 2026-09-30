import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Card, Legend, PageHeader, SeverityBadge } from '../components/ui';
import type { GapRecord } from '../types';
import { CHART, SEVERITY_COLOR } from '../lib/theme';
import { fmtNum } from '../lib/format';

const SECTORS = ['Water Supply', 'Waste Management', 'Drainage & Storm Water', 'Healthcare Capacity', 'Education', 'Public Transit Access', 'Open Space'];

const InfrastructureGaps: React.FC = () => {
  const { hasRole } = useAuth();
  const state = useApi(() => api.gaps(), []);
  const [sector, setSector] = useState('Water Supply');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const recompute = async () => {
    setBusy(true); setMsg(null);
    try { const r = await api.recomputeGaps(); setMsg(`Recomputed ${r.gaps} gap assessments and ${r.recommendations} recommendations.`); state.reload(); }
    catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Supply vs norm-based demand" title="Infrastructure Gaps"
        subtitle="Each ward is benchmarked against CPHEEO, MoHUA, URDPFI and BRIMSTOWAD norms using Census population, OSM facilities and Sentinel-2 land cover. Evidence and caveats travel with every number."
        actions={hasRole('PLANNER', 'ANALYST') ? <button className="btn-outline" onClick={recompute} disabled={busy}><RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />Recompute</button> : undefined} />
      {msg && <p className="text-sm text-police mb-4">{msg}</p>}
      <AsyncBlock state={state} isEmpty={(d) => d.length === 0} empty="No gap assessments yet – run the seed or Recompute.">{(gaps) => <GapsBody gaps={gaps} sector={sector} setSector={setSector} />}</AsyncBlock>
    </div>
  );
};

const GapsBody: React.FC<{ gaps: GapRecord[]; sector: string; setSector: (s: string) => void }> = ({ gaps, sector, setSector }) => {
  const wards = useMemo(() => Array.from(new Set(gaps.map((g) => g.ward_code))).sort(), [gaps]);
  const grid = useMemo(() => {
    const m: Record<string, Record<string, GapRecord>> = {};
    gaps.forEach((g) => { (m[g.ward_code] ??= {})[g.sector] = g; });
    return m;
  }, [gaps]);
  const sectors = SECTORS.filter((s) => gaps.some((g) => g.sector === s));
  const rows = gaps.filter((g) => g.sector === sector).sort((a, b) => b.deficit_percentage - a.deficit_percentage);
  const sample = rows[0];
  const counts = gaps.reduce<Record<string, number>>((acc, g) => ({ ...acc, [g.severity]: (acc[g.severity] ?? 0) + 1 }), {});

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {(['CRITICAL', 'HIGH', 'MODERATE', 'LOW'] as const).map((s) => (
          <div key={s} className="card p-4"><div className="flex items-center justify-between"><SeverityBadge level={s} /></div>
            <div className="font-display text-3xl text-police mt-2">{counts[s] ?? 0}</div><div className="text-xs text-muted">ward-sector assessments</div></div>
        ))}
      </div>

      <Card title="Deficit matrix" subtitle="Deficit % by ward and sector – click a column to inspect a sector" bodyClass="p-0 pt-3">
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead><tr><th>Ward</th>{sectors.map((s) => (
              <th key={s} className={`text-center cursor-pointer ${s === sector ? 'text-marigold-700' : ''}`} onClick={() => setSector(s)}>{s.replace(' & Storm Water', '').replace(' Capacity', '')}</th>
            ))}</tr></thead>
            <tbody>{wards.map((w) => (
              <tr key={w}><td className="font-semibold text-police whitespace-nowrap">{w}</td>
                {sectors.map((s) => {
                  const g = grid[w]?.[s];
                  return <td key={s} className="text-center p-1">
                    {g ? <div title={`${g.sector}: ${fmtNum(g.deficit_percentage, 1)}% deficit (${g.severity})`} className="rounded-md py-1.5 text-xs font-semibold"
                      style={{ background: `${SEVERITY_COLOR[g.severity]}${g.severity === 'LOW' ? '33' : '26'}`, color: SEVERITY_COLOR[g.severity] === '#B9AE93' ? '#5E6B80' : SEVERITY_COLOR[g.severity] }}>
                      {fmtNum(g.deficit_percentage, 0)}%</div> : <span className="text-muted">—</span>}
                  </td>;
                })}
              </tr>
            ))}</tbody>
          </table>
        </div>
        <Legend className="p-4" items={(['CRITICAL', 'HIGH', 'MODERATE', 'LOW'] as const).map((s) => ({ label: s, color: SEVERITY_COLOR[s] }))} />
      </Card>

      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
        <Card title={`${sector}: deficit by ward`} subtitle={sample?.unit}>
          <ResponsiveContainer width="100%" height={Math.max(260, rows.length * 22)}>
            <BarChart data={rows} layout="vertical" margin={{ left: 10, right: 30 }}>
              <CartesianGrid horizontal={false} stroke={CHART.grid} />
              <XAxis type="number" tick={CHART.tick} unit="%" domain={[0, 100]} />
              <YAxis type="category" dataKey="ward_code" tick={CHART.tick} width={40} />
              <Tooltip {...CHART.tooltip} formatter={(v: number, _n, p: any) => [`${fmtNum(v, 1)}% (${fmtNum(p.payload.existing_capacity, 1)} of ${fmtNum(p.payload.required_capacity, 1)})`, 'Deficit']} />
              <Bar dataKey="deficit_percentage" radius={[0, 4, 4, 0]} barSize={12}>{rows.map((r) => <Cell key={r.id} fill={SEVERITY_COLOR[r.severity]} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Method & evidence">
          {sample && <div className="space-y-3 text-sm">
            <div><div className="label">Norm</div><div>{sample.norm_reference}</div></div>
            <div><div className="label">Inputs (worst ward: {sample.ward_code})</div>
              <pre className="text-[11px] bg-pearl-100 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(sample.evidence, null, 1)}</pre></div>
            <div className="overflow-y-auto max-h-64">
              <table className="table-base"><thead><tr><th>Ward</th><th className="text-right">Existing</th><th className="text-right">Required</th><th>Severity</th></tr></thead>
                <tbody>{rows.map((r) => <tr key={r.id}><td><Link className="text-police font-semibold hover:underline" to={`/gis?ward=${r.ward_id}`}>{r.ward_code}</Link></td>
                  <td className="text-right">{fmtNum(r.existing_capacity, 1)}</td><td className="text-right">{fmtNum(r.required_capacity, 1)}</td><td><SeverityBadge level={r.severity} /></td></tr>)}</tbody></table>
            </div>
          </div>}
        </Card>
      </div>
    </div>
  );
};

export default InfrastructureGaps;
