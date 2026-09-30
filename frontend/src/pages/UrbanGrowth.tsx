import React from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, Legend as RLegend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { AsyncBlock, Badge, Card, Legend, PageHeader, ProvenanceBadge, StatTile } from '../components/ui';
import { CHART, CATEGORICAL, GROWTH_COLORS } from '../lib/theme';
import { fmtNum, fmtSigned, titleCase } from '../lib/format';

const UrbanGrowth: React.FC = () => {
  const state = useApi(() => api.urbanGrowth(), []);
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Remote sensing · Copernicus Sentinel-2" title="Urban Growth Patterns"
        subtitle="Dry-season median composites (Jan–Feb, 12 scenes per epoch, SCL cloud-masked, radiometrically normalised) classified into built-up, vegetation and water from NDVI / NDBI / NDWI."
        actions={<Link className="btn-outline" to="/gis">Open overlays on map</Link>} />
      <AsyncBlock state={state} isEmpty={(d) => d.satellite_series.length === 0} empty="No satellite data – run scripts.ingest.sentinel and reseed.">{(d) => {
        const s = d.growth_summary;
        const series = d.satellite_series.map((o) => ({ ...o, label: String(o.year) }));
        const wardChart = [...d.ward_growth].sort((a, b) => (b.built_up_change_pct ?? 0) - (a.built_up_change_pct ?? 0));
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatTile label={`Built-up change ${s.period ?? ''}`} value={fmtSigned(s.built_up_change_pct, 1, '%')} accent="marigold" hint={`${fmtNum(series[0]?.built_up_sq_km, 0)} → ${fmtNum(series[series.length - 1]?.built_up_sq_km, 0)} km²`} />
              <StatTile label="Vegetation change" value={fmtSigned(s.vegetation_change_pct, 1, '%')} accent="buff" hint={`${fmtNum(series[series.length - 1]?.vegetation_sq_km, 0)} km² vegetated`} />
              <StatTile label="Open-water change" value={fmtSigned(s.water_change_pct ?? null, 1, '%')} hint="NDWI > 0.05" />
              <StatTile label="Wards expanding" value={s.class_counts?.RAPID_EXPANSION ?? 0} accent="citrine" hint={`${s.class_counts?.DENSIFYING ?? 0} densifying · ${s.class_counts?.GREENING ?? 0} greening`} />
            </div>
            <div className="grid lg:grid-cols-2 gap-6">
              <Card title="City land cover by epoch" subtitle="km² of the 474 km² BMC area" actions={<ProvenanceBadge value="SENTINEL" />}>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={series} margin={{ top: 10, right: 10, left: -10 }}>
                    <CartesianGrid stroke={CHART.grid} vertical={false} /><XAxis dataKey="label" tick={CHART.tick} /><YAxis tick={CHART.tick} />
                    <Tooltip {...CHART.tooltip} formatter={(v: number) => `${fmtNum(v, 1)} km²`} /><RLegend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="built_up_sq_km" name="Built-up" fill={CATEGORICAL[2]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="vegetation_sq_km" name="Vegetation" fill={CATEGORICAL[5]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="water_sq_km" name="Water" fill={CATEGORICAL[3]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="text-[11px] text-muted mt-2">Scenes per epoch: {series.map((x) => `${x.year}: ${x.scenes}`).join(' · ')}</div>
              </Card>
              <Card title="Built-up change by ward" subtitle="% change in built-up area, first → last epoch">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={wardChart} margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                    <CartesianGrid stroke={CHART.grid} vertical={false} /><XAxis dataKey="ward_code" tick={{ ...CHART.tick, fontSize: 10 }} interval={0} angle={-45} textAnchor="end" height={40} />
                    <YAxis tick={CHART.tick} unit="%" />
                    <Tooltip {...CHART.tooltip} formatter={(v: number, _n, p: any) => [`${fmtSigned(v, 1, '%')} (${fmtSigned(p.payload.built_up_change_sq_km, 2, ' km²')})`, titleCase(p.payload.growth_class)]} />
                    <Bar dataKey="built_up_change_pct" radius={[4, 4, 0, 0]}>{wardChart.map((r) => <Cell key={r.ward_id} fill={GROWTH_COLORS[r.growth_class] ?? '#8196B6'} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
                <Legend items={Object.entries(GROWTH_COLORS).map(([k, c]) => ({ label: titleCase(k), color: c }))} />
              </Card>
            </div>
            <Card title="Ward growth profiles" bodyClass="p-0 pt-3">
              <div className="overflow-x-auto"><table className="table-base">
                <thead><tr><th>Ward</th><th>Pattern</th><th className="text-right">Built-up share</th><th className="text-right">Built-up Δ km²</th><th className="text-right">Built-up Δ %</th>
                  <th className="text-right">Vegetation Δ km²</th><th className="text-right">Complaint growth</th><th className="text-right">Density /km²</th></tr></thead>
                <tbody>{d.ward_growth.map((r) => (
                  <tr key={r.ward_id}><td><Link className="font-semibold text-police hover:underline" to={`/gis?ward=${r.ward_id}`}>{r.ward_name}</Link></td>
                    <td><Badge color={GROWTH_COLORS[r.growth_class]}>{titleCase(r.growth_class)}</Badge></td>
                    <td className="text-right">{fmtNum(r.built_up_share_pct, 1)}%</td><td className="text-right">{fmtSigned(r.built_up_change_sq_km, 2)}</td>
                    <td className="text-right">{fmtSigned(r.built_up_change_pct, 1, '%')}</td><td className="text-right">{fmtSigned(r.vegetation_change_sq_km, 2)}</td>
                    <td className="text-right">{fmtSigned(r.complaint_growth_pct, 1, '%')}</td><td className="text-right">{fmtNum(r.population_density, 0)}</td></tr>
                ))}</tbody>
              </table></div>
              <p className="text-[11px] text-muted p-4">{d.method} Mumbai is largely built-out, so changes of a few percent are within classification noise; the strongest signal is peripheral expansion (e.g. T, R/C) against greening of older wards as tree canopy matures.</p>
            </Card>
          </div>
        );
      }}</AsyncBlock>
    </div>
  );
};

export default UrbanGrowth;
