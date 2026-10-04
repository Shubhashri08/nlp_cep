import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { X } from 'lucide-react';
import { api } from '../../api/client';
import { useApi } from '../../hooks/useApi';
import { CHART, CATEGORICAL, SEVERITY_COLOR } from '../../lib/theme';
import { fmtInt, fmtMonth, fmtNum, fmtPct, titleCase } from '../../lib/format';
import { AsyncBlock, Badge, Meter, ProvenanceBadge, SeverityBadge, StatusBadge, Tabs } from '../ui';
import type { WardProfile } from '../../types';

const Row: React.FC<{ k: string; v: React.ReactNode }> = ({ k, v }) => (
  <div className="flex justify-between gap-3 py-1.5 border-b border-line/60 text-sm"><span className="text-muted">{k}</span><span className="font-semibold text-ink text-right">{v}</span></div>
);

export const WardDrawer: React.FC<{ wardId: number; onClose: () => void }> = ({ wardId, onClose }) => {
  const state = useApi(() => api.wardProfile(wardId), [wardId]);
  const [tab, setTab] = useState('overview');
  return (
    <aside className="h-full w-full bg-paper border-l border-line flex flex-col animate-fade-in">
      <div className="flex items-start justify-between p-4 border-b border-line">
        <div>
          <div className="label text-marigold-700">{state.data?.ward_info.zone_name ?? 'Ward profile'}</div>
          <h2 className="font-display text-2xl text-police leading-tight">{state.data?.ward_info.name ?? '…'}</h2>
          <div className="text-xs text-muted">{state.data?.ward_info.localities}</div>
        </div>
        <button className="btn-ghost px-2" onClick={onClose} aria-label="Close ward profile"><X className="h-5 w-5" /></button>
      </div>
      <div className="px-4"><Tabs value={tab} onChange={setTab} tabs={[
        { id: 'overview', label: 'Overview' }, { id: 'gaps', label: 'Gaps' }, { id: 'env', label: 'Land & Env' },
        { id: 'complaints', label: 'Complaints' }, { id: 'plan', label: 'Actions' }]} /></div>
      <div className="flex-1 overflow-y-auto p-4">
        <AsyncBlock state={state}>{(p) => <DrawerBody p={p} tab={tab} />}</AsyncBlock>
      </div>
    </aside>
  );
};

const DrawerBody: React.FC<{ p: WardProfile; tab: string }> = ({ p, tab }) => {
  const w = p.ward_info;
  if (tab === 'overview') return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="card p-3"><div className="label">Priority score</div><div className="font-display text-3xl text-police">{fmtNum(w.priority_score, 1)}</div><Meter value={w.priority_score} color={w.priority_score >= 60 ? '#8A3B08' : '#E59D2C'} /></div>
        <div className="card p-3"><div className="label">Growth pattern</div><div className="font-display text-xl text-police mt-1">{titleCase(w.growth_class ?? '—')}</div><div className="text-[11px] text-muted">{p.growth?.period} · Sentinel-2</div></div>
      </div>
      <div>
        <div className="label mb-1">Why this priority</div>
        {p.priority_factors.map((f) => (
          <div key={f.factor} className="py-1.5">
            <div className="flex justify-between text-xs"><span className="text-ink">{f.factor} <span className="text-muted">({f.raw_value})</span></span><span className="font-semibold">{fmtNum(f.weighted_contribution, 1)}</span></div>
            <Meter value={f.normalized_score} color="#3A5A94" />
          </div>
        ))}
      </div>
      {p.demographics && (
        <div>
          <div className="flex items-center justify-between mb-1"><div className="label">Demographics</div><ProvenanceBadge value="CENSUS" /></div>
          <Row k="Population (Census 2011)" v={fmtInt(p.demographics.population_2011)} />
          <Row k={`Estimate ${p.demographics.estimate_year}`} v={fmtInt(p.demographics.population_current_estimate)} />
          <Row k="Density" v={`${fmtInt(w.population_density)} /km²`} />
          <Row k="Households" v={fmtInt(p.demographics.households)} />
          <Row k="Literacy (7+)" v={fmtPct(p.demographics.literacy_rate)} />
          <Row k="Sex ratio (F per 1000 M)" v={fmtInt(p.demographics.sex_ratio)} />
          <Row k="Area" v={`${fmtNum(w.area_sq_km, 2)} km²`} />
        </div>
      )}
      <div>
        <div className="flex items-center justify-between mb-1"><div className="label">Facilities mapped</div><ProvenanceBadge value="OSM" /></div>
        <div className="grid grid-cols-2 gap-x-4">
          {Object.entries(p.asset_counts).filter(([k]) => k !== 'EDUCATION_SCHOOL').sort((a, b) => b[1] - a[1]).map(([k, v]) => <Row key={k} k={titleCase(k)} v={v} />)}
        </div>
      </div>
    </div>
  );

  if (tab === 'gaps') return (
    <div className="space-y-3">
      {p.infrastructure_gaps.map((g) => (
        <div key={g.id} className="card p-3">
          <div className="flex items-center justify-between"><div className="font-semibold text-police text-sm">{g.sector}</div><SeverityBadge level={g.severity} /></div>
          <div className="text-xs text-muted mt-1">{fmtNum(g.existing, 1)} available vs {fmtNum(g.required, 1)} required · {g.unit}</div>
          <div className="mt-2"><Meter value={g.deficit_pct} color={SEVERITY_COLOR[g.severity]} /></div>
          <div className="text-xs mt-1"><b>{fmtPct(g.deficit_pct)}</b> deficit</div>
          {g.norm_reference && <div className="text-[11px] text-muted mt-1">{g.norm_reference}</div>}
        </div>
      ))}
    </div>
  );

  if (tab === 'env') {
    const lu = p.land_use;
    const luRows = lu ? [['Residential', lu.residential_pct], ['Commercial', lu.commercial_pct], ['Industrial', lu.industrial_pct], ['Green / open', lu.green_pct], ['Water', lu.water_pct], ['Mixed / institutional', lu.mixed_pct], ['Unmapped', lu.unmapped_pct]] : [];
    const env = p.environmental_indicators;
    return (
      <div className="space-y-4">
        {lu && <div>
          <div className="flex items-center justify-between mb-2"><div className="label">Land use share of ward area</div><ProvenanceBadge value="OSM" /></div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={luRows.map(([k, v]) => ({ k, v }))} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid horizontal={false} stroke={CHART.grid} />
              <XAxis type="number" tick={CHART.tick} unit="%" />
              <YAxis type="category" dataKey="k" tick={CHART.tick} width={120} />
              <Tooltip {...CHART.tooltip} formatter={(v: number) => `${fmtNum(v, 1)}%`} />
              <Bar dataKey="v" radius={[0, 4, 4, 0]} barSize={12}>{luRows.map((r, i) => <Cell key={i} fill={i === 3 ? '#3F8A5A' : i === 4 ? '#5E8FD0' : i === 6 ? '#CFC6B5' : CATEGORICAL[i % 3]} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>}
        {env && <div>
          <div className="flex items-center justify-between mb-1"><div className="label">Environment</div><ProvenanceBadge value={env.provenance} /></div>
          <Row k="Flood exposure index" v={fmtNum(env.flood_risk_score, 2)} />
          <Row k="Mean elevation (DEM)" v={`${fmtNum(env.elevation_m, 1)} m`} />
          <Row k="Area below 5 m" v={fmtPct((env.low_lying_share ?? 0) * 100)} />
          <Row k="Vegetation cover (Sentinel-2)" v={fmtPct(env.vegetation_pct)} />
          <Row k="PM2.5, 12-month mean" v={`${fmtNum(env.aqi_pm25_12m_avg, 1)} µg/m³`} />
          <div className="mt-3 label">PM2.5 by month (µg/m³)</div>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={env.monthly}><CartesianGrid stroke={CHART.grid} vertical={false} />
              <XAxis dataKey="month" tickFormatter={fmtMonth} tick={CHART.tick} interval={2} /><YAxis tick={CHART.tick} width={30} />
              <Tooltip {...CHART.tooltip} labelFormatter={fmtMonth} />
              <Line dataKey="pm25" name="PM2.5" stroke="#A8490F" strokeWidth={2} dot={false} /></LineChart>
          </ResponsiveContainer>
        </div>}
        {p.transportation_indicators && <div>
          <div className="flex items-center justify-between mb-1"><div className="label">Transport</div><ProvenanceBadge value={p.transportation_indicators.provenance} /></div>
          <Row k="Road network" v={`${fmtNum(p.transportation_indicators.road_length_km, 0)} km`} />
          <Row k="Road density" v={`${fmtNum(p.transportation_indicators.road_density, 1)} km/km²`} />
          <Row k="Bus stops (OSM)" v={p.transportation_indicators.bus_stops} />
          <Row k="Rail / metro stations" v={`${p.transportation_indicators.rail_stations} / ${p.transportation_indicators.metro_stations}`} />
          <Row k="Daily PT trips (estimate)" v={fmtInt(p.transportation_indicators.daily_ridership_estimate)} />
        </div>}
      </div>
    );
  }

  if (tab === 'complaints') return (
    <div className="space-y-3">
      <div className="label">By category (all time)</div>
      <ResponsiveContainer width="100%" height={Math.max(120, p.top_complaint_categories.length * 22)}>
        <BarChart data={p.top_complaint_categories.slice(0, 8).map((c) => ({ ...c, name: titleCase(c.category) }))} layout="vertical" margin={{ left: 10, right: 20 }}>
          <XAxis type="number" tick={CHART.tick} /><YAxis type="category" dataKey="name" tick={CHART.tick} width={130} />
          <Tooltip {...CHART.tooltip} /><Bar dataKey="count" name="Complaints" fill="#3A5A94" radius={[0, 4, 4, 0]} barSize={12} />
        </BarChart>
      </ResponsiveContainer>
      <div className="label">Latest complaints</div>
      {p.recent_complaints.map((c) => (
        <div key={c.id} className="border-b border-line/70 pb-2">
          <div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-police">{titleCase(c.primary_category)}</span><StatusBadge status={c.status} /></div>
          <div className="text-sm text-ink mt-0.5">{c.original_text}</div>
          <div className="text-[11px] text-muted mt-0.5">{new Date(c.created_at).toLocaleDateString('en-IN')} · {c.request_uid}</div>
        </div>
      ))}
      <Link className="btn-outline w-full text-xs" to={`/citizen-feedback?ward=${w.id}`}>Open all complaints for this ward</Link>
    </div>
  );

  return (
    <div className="space-y-3">
      {p.recommendations.length === 0 && <div className="text-sm text-muted">No high-priority interventions generated for this ward.</div>}
      {p.recommendations.map((r) => (
        <div key={r.id} className="card p-3">
          <div className="flex items-start justify-between gap-2"><div className="font-semibold text-sm text-police">{r.title}</div><Badge color={r.priority_level === 'HIGH' ? '#8A3B08' : '#A26815'}>{r.priority_level}</Badge></div>
          <p className="text-xs text-ink/90 mt-1 leading-relaxed">{r.recommendation_text}</p>
          <div className="text-[11px] text-muted mt-1">Score {fmtNum(r.score, 1)} · est. ₹{fmtNum(r.estimated_cost_cr, 1)} Cr · {titleCase(r.status)}</div>
        </div>
      ))}
      {p.predicted_demand.length > 0 && <>
        <div className="label pt-2">Forecast complaint volume (next 12 months)</div>
        <ResponsiveContainer width="100%" height={140}>
          <LineChart data={p.predicted_demand}><CartesianGrid stroke={CHART.grid} vertical={false} />
            <XAxis dataKey="date" tickFormatter={fmtMonth} tick={CHART.tick} interval={2} /><YAxis tick={CHART.tick} width={30} />
            <Tooltip {...CHART.tooltip} labelFormatter={fmtMonth} />
            <Line dataKey="predicted_value" name="Forecast" stroke="#3A5A94" strokeWidth={2} dot={false} />
            <Line dataKey="upper" name="Upper 95%" stroke="#AEBBD1" strokeDasharray="4 3" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </>}
      <Link className="btn-primary w-full text-xs" to={`/recommendations?ward=${w.id}`}>View recommendations</Link>
    </div>
  );
};
