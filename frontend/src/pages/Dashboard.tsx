import React from 'react';
import { Link } from 'react-router-dom';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend as RLegend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AlertTriangle, Building2, CheckCircle2, Clock, MapPin, Users } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { AsyncBlock, Card, Meter, PageHeader, ProvenanceBadge, StatTile } from '../components/ui';
import { CHART, CATEGORICAL } from '../lib/theme';
import { LANGUAGE_LABELS, fmtCompact, fmtInt, fmtMonth, fmtNum, titleCase } from '../lib/format';

const Dashboard: React.FC = () => {
  const state = useApi(() => api.overview(), []);
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Greater Mumbai · live municipal indicators" title="Planning Dashboard"
        subtitle="Citizen feedback, infrastructure deficits and ward priorities, computed from the database. Provenance badges show which inputs are real open data and which are demonstration data." />
      <AsyncBlock state={state}>{(d) => {
        const resolvedPct = d.total_requests ? (100 * d.resolved_requests) / d.total_requests : 0;
        const cats = d.top_issue_categories.slice(0, 10).map((c) => ({ ...c, name: titleCase(c.category) }));
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <StatTile label="Population (2026 est.)" value={fmtCompact(d.population_total)} icon={<Users className="h-4 w-4" />} hint="Census 2011, projected" />
              <StatTile label="Citizen complaints" value={fmtInt(d.total_requests)} accent="marigold" icon={<MapPin className="h-4 w-4" />}
                hint={`${fmtInt(d.open_requests)} open · ${fmtInt(d.in_progress_requests)} in progress`} />
              <StatTile label="Resolved" value={`${fmtNum(resolvedPct, 0)}%`} accent="buff" icon={<CheckCircle2 className="h-4 w-4" />}
                hint={d.median_resolution_days !== null ? `median ${fmtNum(d.median_resolution_days, 1)} days to resolve` : undefined} />
              <StatTile label="Critical gaps" value={d.critical_gaps_count} accent="citrine" icon={<Building2 className="h-4 w-4" />}
                hint={`of ${d.total_infrastructure_gaps} ward-sector assessments`} />
              <StatTile label="Active hotspots" value={d.active_hotspots_count} accent="citrine" icon={<AlertTriangle className="h-4 w-4" />}
                hint={`${d.high_priority_wards_count} wards with priority ≥ 60`} />
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2" title="Complaints per month" subtitle="Received vs resolved (same month of receipt)">
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={d.monthly_trend} margin={{ top: 10, right: 10, left: -10 }}>
                    <CartesianGrid stroke={CHART.grid} vertical={false} />
                    <XAxis dataKey="month" tickFormatter={fmtMonth} tick={CHART.tick} interval={2} />
                    <YAxis tick={CHART.tick} />
                    <Tooltip {...CHART.tooltip} labelFormatter={fmtMonth} />
                    <RLegend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="count" name="Received" stroke={CATEGORICAL[0]} fill={CATEGORICAL[0]} fillOpacity={0.15} strokeWidth={2} />
                    <Area type="monotone" dataKey="resolved" name="Resolved" stroke={CATEGORICAL[1]} fill={CATEGORICAL[1]} fillOpacity={0.15} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
              <Card title="Languages" subtitle="Detected in complaint text">
                <div className="space-y-3 pt-2">
                  {d.language_distribution.sort((a, b) => b.count - a.count).map((l) => (
                    <div key={l.language}>
                      <div className="flex justify-between text-sm"><span>{LANGUAGE_LABELS[l.language] ?? l.language}</span><span className="font-semibold">{fmtInt(l.count)}</span></div>
                      <Meter value={l.count} max={d.total_requests} color="#3A5A94" />
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-line">
                  <div className="label mb-2">Data provenance</div>
                  <div className="space-y-1.5">
                    {d.data_provenance.map((p) => (
                      <div key={p.provenance} className="flex items-center justify-between text-xs">
                        <ProvenanceBadge value={p.provenance} /><span className="text-muted">{p.sources} source{p.sources > 1 ? 's' : ''} · quality {fmtNum(p.avg_quality * 100, 0)}%</span>
                      </div>
                    ))}
                  </div>
                  <Link to="/data-sources" className="text-xs text-police underline mt-2 inline-block">Data catalogue →</Link>
                </div>
              </Card>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <Card title="Issue categories" subtitle="NLP-classified primary category">
                <ResponsiveContainer width="100%" height={Math.max(220, cats.length * 26)}>
                  <BarChart data={cats} layout="vertical" margin={{ left: 20, right: 20 }}>
                    <CartesianGrid horizontal={false} stroke={CHART.grid} />
                    <XAxis type="number" tick={CHART.tick} />
                    <YAxis type="category" dataKey="name" tick={CHART.tick} width={140} />
                    <Tooltip {...CHART.tooltip} />
                    <Bar dataKey="count" name="Complaints" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <Card title="Ward priority ranking" subtitle="MCDA: complaints · deficits · density · flood exposure · forecast growth" bodyClass="p-0 pt-3">
                <div className="max-h-[420px] overflow-y-auto">
                  <table className="table-base">
                    <thead><tr><th>Ward</th><th className="text-right">Priority</th><th className="text-right">Complaints</th><th className="text-right">per 1,000</th></tr></thead>
                    <tbody>
                      {d.ward_complaint_rankings.map((w) => (
                        <tr key={w.ward_id}>
                          <td><Link className="font-semibold text-police hover:underline" to={`/gis?ward=${w.ward_id}`}>{w.ward_name}</Link></td>
                          <td className="text-right w-40">
                            <div className="flex items-center gap-2 justify-end"><span className="w-10 text-right font-semibold">{fmtNum(w.priority_score, 0)}</span>
                              <div className="w-20"><Meter value={w.priority_score} color={w.priority_score >= 60 ? '#8A3B08' : w.priority_score >= 40 ? '#E59D2C' : '#B9AE93'} /></div></div>
                          </td>
                          <td className="text-right">{fmtInt(w.complaint_count)}</td>
                          <td className="text-right text-muted">{fmtNum(w.complaints_per_1000, 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
            <p className="text-[11px] text-muted flex items-center gap-1.5"><Clock className="h-3 w-3" />Complaint records are synthetic demonstration data (real OSM places, category rates driven by real ward attributes). Replace them via Data Sources → Import.</p>
          </div>
        );
      }}</AsyncBlock>
    </div>
  );
};

export default Dashboard;
