import React, { useMemo, useState } from 'react';
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend as RLegend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Card, PageHeader, ProvenanceBadge, Select, StatTile } from '../components/ui';
import { CHART, CATEGORICAL } from '../lib/theme';
import { fmtCompact, fmtInt, fmtMonth, fmtNum, fmtSigned } from '../lib/format';

const Predictions: React.FC = () => {
  const { hasRole } = useAuth();
  const metrics = useApi(() => api.forecastMetrics(), []);
  const wards = useApi(() => api.wards(), []);
  const [metric, setMetric] = useState('complaint_volume');
  const [wardId, setWardId] = useState('');
  const [horizon, setHorizon] = useState(12);
  const [year, setYear] = useState(2031);
  const fc = useApi(() => api.forecast({ target_metric: metric, ward_id: wardId ? Number(wardId) : undefined, horizon_months: horizon }), [metric, wardId, horizon]);
  const demand = useApi(() => api.infraDemand(year), [year]);
  const [busy, setBusy] = useState(false);

  const retrain = async () => { setBusy(true); try { await api.retrain(); metrics.reload(); fc.reload(); } finally { setBusy(false); } };

  const chartData = useMemo(() => {
    if (!fc.data) return [];
    const hist = fc.data.historical_data.slice(-24).map((h) => ({ date: h.date, actual: h.actual_value }));
    const last = hist[hist.length - 1];
    const fut = fc.data.forecast.map((p) => ({ date: p.date, forecast: p.predicted_value, band: [p.lower_bound, p.upper_bound] as [number, number] }));
    // Join the forecast line to the last observation so there is no visual gap
    if (last) Object.assign(last, { forecast: last.actual, band: [last.actual, last.actual] });
    return [...hist, ...fut];
  }, [fc.data]);

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Predictive analytics" title="Demand Forecasts"
        subtitle="Gradient-boosted panel models trained on the monthly history of every ward (lags, seasonality, monsoon, trend, density), back-tested on the last 6 months and compared with a seasonal-naive baseline."
        actions={hasRole('ANALYST') ? <button className="btn-outline" onClick={retrain} disabled={busy}><RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />Retrain</button> : undefined} />

      <div className="flex flex-wrap gap-3 mb-6">
        <Select label="Metric" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {(metrics.data ?? []).map((m) => <option key={m.id} value={m.id} disabled={!m.trained}>{m.label} ({m.unit})</option>)}
        </Select>
        <Select label="Scope" value={wardId} onChange={(e) => setWardId(e.target.value)}>
          <option value="">All wards (city total)</option>
          {wards.data?.slice().sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </Select>
        <Select label="Horizon" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
          {[6, 12, 18, 24].map((h) => <option key={h} value={h}>{h} months</option>)}
        </Select>
      </div>

      <AsyncBlock state={fc}>{(d) => {
        const hist = d.historical_data.slice(-12).map((h) => h.actual_value);
        const avgHist = hist.reduce((a, b) => a + b, 0) / Math.max(1, hist.length);
        const avgFc = d.forecast.reduce((a, p) => a + p.predicted_value, 0) / Math.max(1, d.forecast.length);
        const imp = Object.entries(d.feature_importance).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ name: k.replace(/_/g, ' '), v: v * 100 }));
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatTile label="Next-period average" value={fmtCompact(avgFc)} hint={`${d.unit} · vs ${fmtCompact(avgHist)} last 12 months`} accent="marigold" />
              <StatTile label="Expected change" value={fmtSigned(avgHist ? (100 * (avgFc - avgHist)) / avgHist : null, 1, '%')} />
              <StatTile label="Back-test MAPE" value={`${fmtNum(d.metrics.mape_pct, 1)}%`} hint={`seasonal-naive ${fmtNum(d.metrics.seasonal_naive_mape_pct, 1)}%`} accent="buff" />
              <StatTile label="Back-test R²" value={fmtNum(d.metrics.r2_score, 3)} hint={`${d.metrics.test_samples} held-out ward-months`} />
            </div>
            <Card title={`${d.metric_label} — ${d.ward_name}`} subtitle="Observed history, forecast and 95% prediction interval" actions={<ProvenanceBadge value={d.provenance.split(' ')[0]} />}>
              <ResponsiveContainer width="100%" height={340}>
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0 }}>
                  <CartesianGrid stroke={CHART.grid} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={fmtMonth} tick={CHART.tick} interval={2} />
                  <YAxis tick={CHART.tick} tickFormatter={fmtCompact} width={55} />
                  <Tooltip {...CHART.tooltip} labelFormatter={fmtMonth}
                    formatter={(v: number | number[], n: string) => Array.isArray(v) ? [`${fmtNum(v[0], 1)} – ${fmtNum(v[1], 1)}`, n] : [fmtNum(v, 1), n]} />
                  <RLegend wrapperStyle={{ fontSize: 12 }} />
                  <Area dataKey="band" name="95% interval" stroke="none" fill={CATEGORICAL[1]} fillOpacity={0.22} isAnimationActive={false} />
                  <Line dataKey="actual" name="Observed" stroke={CATEGORICAL[0]} strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line dataKey="forecast" name="Forecast" stroke={CATEGORICAL[2]} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </Card>
            <div className="grid lg:grid-cols-2 gap-6">
              <Card title="What drives the model" subtitle="Gradient-boosting feature importance">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={imp} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid horizontal={false} stroke={CHART.grid} /><XAxis type="number" tick={CHART.tick} unit="%" />
                    <YAxis type="category" dataKey="name" tick={CHART.tick} width={100} /><Tooltip {...CHART.tooltip} formatter={(v: number) => `${fmtNum(v, 1)}%`} />
                    <Bar dataKey="v" name="Importance" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} barSize={12} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <Card title="Model back-test by metric" bodyClass="p-0 pt-3">
                <table className="table-base"><thead><tr><th>Metric</th><th className="text-right">MAPE</th><th className="text-right">Naive MAPE</th><th className="text-right">R²</th></tr></thead>
                  <tbody>{(metrics.data ?? []).map((m) => <tr key={m.id}><td>{m.label}</td><td className="text-right">{fmtNum(m.backtest?.mape_pct, 2)}%</td>
                    <td className="text-right text-muted">{fmtNum(m.backtest?.seasonal_naive_mape_pct, 2)}%</td><td className="text-right">{fmtNum(m.backtest?.r2_score, 3)}</td></tr>)}</tbody></table>
                <p className="text-[11px] text-muted p-4">Water, waste and ridership histories are synthetic demonstration series; complaint volume is aggregated from complaint records.</p>
              </Card>
            </div>
          </div>
        );
      }}</AsyncBlock>

      <Card className="mt-6" title="Future infrastructure requirements" subtitle="Norm-based needs from Census population projections"
        actions={<Select value={year} onChange={(e) => setYear(Number(e.target.value))} aria-label="Target year">{[2031, 2036, 2041].map((y) => <option key={y}>{y}</option>)}</Select>} bodyClass="p-0 pt-3">
        <AsyncBlock state={demand}>{(d) => (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 px-5 pb-4">
              {[['Population', fmtCompact(d.city_totals.population_projected)], ['Water needed', `${fmtInt(d.city_totals.water_required_mld)} MLD`],
                ['Extra water', `${fmtInt(d.city_totals.additional_water_mld)} MLD`], ['Extra health facilities', fmtInt(d.city_totals.additional_health_facilities)],
                ['Extra schools', fmtInt(d.city_totals.additional_schools)]].map(([l, v]) => (
                <div key={l} className="bg-pearl-100 rounded-lg p-3"><div className="label">{l}</div><div className="font-display text-xl text-police">{v}</div></div>
              ))}
            </div>
            <div className="overflow-x-auto max-h-[420px]"><table className="table-base">
              <thead><tr><th>Ward</th><th className="text-right">Population {d.target_year}</th><th className="text-right">Water req. MLD</th><th className="text-right">+Water</th>
                <th className="text-right">Waste TPD</th><th className="text-right">+Health</th><th className="text-right">+Schools</th><th className="text-right">Open space need ha</th></tr></thead>
              <tbody>{d.wards.map((w) => (
                <tr key={w.ward_id}><td className="font-semibold text-police">{w.ward_code}</td><td className="text-right">{fmtInt(w.population_projected)}</td>
                  <td className="text-right">{fmtNum(w.water_required_mld, 1)}</td><td className="text-right">{fmtNum(w.additional_water_mld, 1)}</td><td className="text-right">{fmtNum(w.waste_generated_tpd, 0)}</td>
                  <td className="text-right">{w.additional_health_facilities}</td><td className="text-right">{w.additional_schools}</td>
                  <td className="text-right">{fmtNum(w.open_space_required_ha, 0)} <span className="text-muted">(has {fmtNum(w.open_space_existing_ha, 0)})</span></td></tr>
              ))}</tbody>
            </table></div>
            <p className="text-[11px] text-muted p-4">{d.method}.</p>
          </>
        )}</AsyncBlock>
      </Card>
    </div>
  );
};

export default Predictions;
