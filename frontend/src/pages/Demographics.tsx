import React, { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend as RLegend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { AsyncBlock, Card, PageHeader, ProvenanceBadge, Tabs } from '../components/ui';
import { CHART, CATEGORICAL } from '../lib/theme';
import { fmtCompact, fmtInt, fmtNum } from '../lib/format';

const LU_KEYS: { key: string; label: string; color: string }[] = [
  { key: 'residential', label: 'Residential', color: CATEGORICAL[0] },
  { key: 'commercial', label: 'Commercial', color: CATEGORICAL[1] },
  { key: 'industrial', label: 'Industrial', color: CATEGORICAL[2] },
  { key: 'green', label: 'Green / open', color: CATEGORICAL[5] },
  { key: 'water', label: 'Water', color: CATEGORICAL[3] },
  { key: 'mixed', label: 'Institutional / mixed', color: CATEGORICAL[4] },
  { key: 'unmapped', label: 'Not tagged in OSM', color: '#D9D1C3' },
];

const Demographics: React.FC = () => {
  const state = useApi(() => api.demographics(), []);
  const [tab, setTab] = useState('population');
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Census of India 2011 · OpenStreetMap" title="Demographics & Land Use"
        subtitle="Ward-level Primary Census Abstract aggregated to the 24 BMC wards (total 1,24,42,373), projected to 2026 with the 2001–11 city growth rate, alongside OSM land-use shares." />
      <AsyncBlock state={state} isEmpty={(d) => d.length === 0} empty="No demographic data.">{(rows) => {
        const byDensity = [...rows].sort((a, b) => b.density - a.density);
        return (
          <div className="space-y-6">
            <Tabs value={tab} onChange={setTab} tabs={[{ id: 'population', label: 'Population & density' }, { id: 'social', label: 'Social indicators' }, { id: 'landuse', label: 'Land use' }]} />
            {tab === 'population' && (
              <div className="grid lg:grid-cols-2 gap-6">
                <Card title="Population density" subtitle="Persons per km², 2026 estimate">
                  <ResponsiveContainer width="100%" height={560}>
                    <BarChart data={byDensity} layout="vertical" margin={{ left: 5, right: 30 }}>
                      <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" tick={CHART.tick} tickFormatter={fmtCompact} />
                      <YAxis type="category" dataKey="ward_code" tick={CHART.tick} width={40} />
                      <Tooltip {...CHART.tooltip} formatter={(v: number) => [`${fmtInt(v)} /km²`, 'Density']} />
                      <Bar dataKey="density" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} barSize={14} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
                <Card title="Population by ward" subtitle="Census 2011 vs 2026 projection">
                  <ResponsiveContainer width="100%" height={560}>
                    <BarChart data={[...rows].sort((a, b) => b.population_current - a.population_current)} layout="vertical" margin={{ left: 5, right: 30 }}>
                      <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" tick={CHART.tick} tickFormatter={fmtCompact} />
                      <YAxis type="category" dataKey="ward_code" tick={CHART.tick} width={40} />
                      <Tooltip {...CHART.tooltip} formatter={(v: number) => fmtInt(v)} /><RLegend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="population_2011" name="Census 2011" fill={CATEGORICAL[3]} radius={[0, 4, 4, 0]} barSize={7} />
                      <Bar dataKey="population_current" name="2026 estimate" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} barSize={7} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>
            )}
            {tab === 'social' && (
              <Card title="Census 2011 social indicators" actions={<ProvenanceBadge value="CENSUS" />} bodyClass="p-0 pt-3">
                <div className="overflow-x-auto"><table className="table-base">
                  <thead><tr><th>Ward</th><th className="text-right">Population 2011</th><th className="text-right">Households</th><th className="text-right">HH size</th>
                    <th className="text-right">Literacy %</th><th className="text-right">Sex ratio</th><th className="text-right">Age 0–6 %</th><th className="text-right">Workers %</th><th className="text-right">SC %</th><th className="text-right">ST %</th></tr></thead>
                  <tbody>{rows.map((r) => (
                    <tr key={r.ward_id}><td className="font-semibold text-police">{r.ward_name}</td><td className="text-right">{fmtInt(r.population_2011)}</td><td className="text-right">{fmtInt(r.households)}</td>
                      <td className="text-right">{fmtNum(r.avg_household_size, 2)}</td><td className="text-right">{fmtNum(r.literacy_rate, 1)}</td><td className="text-right">{fmtInt(r.sex_ratio)}</td>
                      <td className="text-right">{fmtNum(r.children_0_6_pct, 1)}</td><td className="text-right">{fmtNum(r.workers_pct, 1)}</td><td className="text-right">{fmtNum(r.sc_pct, 1)}</td><td className="text-right">{fmtNum(r.st_pct, 2)}</td></tr>
                  ))}</tbody>
                </table></div>
              </Card>
            )}
            {tab === 'landuse' && (
              <Card title="Land-use composition" subtitle="Share of ward area covered by OSM landuse / leisure / natural polygons" actions={<ProvenanceBadge value="OSM" />}>
                <ResponsiveContainer width="100%" height={600}>
                  <BarChart data={rows.filter((r) => r.land_use).map((r) => ({ ward: r.ward_code, ...r.land_use }))} layout="vertical" stackOffset="expand" margin={{ left: 5, right: 20 }} barCategoryGap={4}>
                    <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={CHART.tick} />
                    <YAxis type="category" dataKey="ward" tick={CHART.tick} width={40} />
                    <Tooltip {...CHART.tooltip} formatter={(v: number) => `${fmtNum(v, 1)}%`} /><RLegend wrapperStyle={{ fontSize: 12 }} />
                    {LU_KEYS.map((k) => <Bar key={k.key} dataKey={k.key} name={k.label} stackId="a" fill={k.color} stroke="#FCFAF6" strokeWidth={1} />)}
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-[11px] text-muted mt-2">"Not tagged" is area without a land-use polygon in OSM (mostly dense built fabric); it is shown, not hidden, to make data completeness visible.</p>
              </Card>
            )}
          </div>
        );
      }}</AsyncBlock>
    </div>
  );
};

export default Demographics;
