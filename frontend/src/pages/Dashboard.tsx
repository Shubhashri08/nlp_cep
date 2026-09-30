import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DashboardOverview } from '../types';
import {
  Users, AlertCircle, CheckCircle2, TrendingUp,
  Layers, ShieldAlert, FileText, ArrowUpRight
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  Tooltip, PieChart, Pie, Cell, AreaChart, Area, CartesianGrid
} from 'recharts';
import { Link } from 'react-router-dom';

const COLORS = ['#38bdf8', '#fb923c', '#a855f7', '#0284c7', '#ef4444', '#10b981', '#f59e0b', '#64748b'];

export const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getDashboardOverview();
        setOverview(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard metrics');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl">
        Error loading dashboard: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Title & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Executive Planning Dashboard</h2>
          <p className="text-sm text-slate-400">
            Real-time urban intelligence, citizen feedback NLP synthesis, and infrastructure priority metrics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/ai-assistant"
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-emerald-600 hover:from-brand-500 hover:to-emerald-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-brand-500/20 transition"
          >
            Ask AI Planning Assistant
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Main KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">TOTAL GRIEVANCES</span>
            <div className="p-2 bg-brand-500/10 text-brand-400 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-100">{overview.total_requests}</div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="text-emerald-400 font-medium">{overview.resolved_requests} Resolved</span>
            <span>•</span>
            <span className="text-amber-400 font-medium">{overview.open_requests} Open</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">HIGH PRIORITY WARDS</span>
            <div className="p-2 bg-rose-500/10 text-rose-400 rounded-lg">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-rose-400">{overview.high_priority_wards_count}</div>
          <p className="text-xs text-slate-400">MCDA score &ge; 50/100 requiring immediate budget intervention</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">INFRASTRUCTURE GAPS</span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-amber-400">{overview.total_infrastructure_gaps}</div>
          <p className="text-xs text-slate-400">Verified capacity deficits across water, drainage, and waste</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">DATA QUALITY INDEX</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">{(overview.avg_quality_score * 100).toFixed(1)}%</div>
          <p className="text-xs text-slate-400">100% verified spatial boundaries and provenance audit</p>
        </div>
      </div>

      {/* Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issue Categories Breakdown */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200">Grievances by Category</h3>
            <span className="text-xs text-slate-500">NLP Multi-Class</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={overview.top_issue_categories}
                  dataKey="count"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={45}
                  paddingAngle={4}
                >
                  {overview.top_issue_categories.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {overview.top_issue_categories.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }}></span>
                <span className="text-slate-300 truncate">{c.category.replace('_', ' ')}</span>
                <span className="text-slate-500 ml-auto font-mono">{c.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Monthly Grievance & Resolution Trend */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200">6-Month Grievance & Resolution Volume</h3>
            <span className="text-xs text-slate-500">Historical Time Series</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview.monthly_trend}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="count" name="Total Received" stroke="#0ea5e9" fillOpacity={1} fill="url(#colorCount)" />
                <Area type="monotone" dataKey="resolved" name="Resolved" stroke="#10b981" fillOpacity={1} fill="url(#colorResolved)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Peak seasonal influx correlates with monsoon flooding</span>
            <Link to="/predictions" className="text-brand-400 hover:underline">View 12-Month Forecast &rarr;</Link>
          </div>
        </div>
      </div>

      {/* Ward Priority Rankings Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-200">Ward Priority Scoring & Action Matrix</h3>
            <p className="text-xs text-slate-400">Calculated via Multi-Criteria Decision Analysis (MCDA)</p>
          </div>
          <Link to="/recommendations" className="text-xs text-brand-400 hover:underline">
            Inspect Recommendations &rarr;
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="p-3">WARD</th>
                <th className="p-3">CODE</th>
                <th className="p-3">GRIEVANCES</th>
                <th className="p-3">PRIORITY SCORE</th>
                <th className="p-3">LEVEL</th>
                <th className="p-3">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {overview.ward_complaint_rankings.map((w, idx) => (
                <tr key={idx} className="hover:bg-slate-800/50 transition">
                  <td className="p-3 font-semibold text-slate-100">{w.ward_name}</td>
                  <td className="p-3 font-mono text-slate-400">{w.ward_code}</td>
                  <td className="p-3 font-mono">{w.complaint_count}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            w.priority_score >= 60 ? 'bg-rose-500' : w.priority_score >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, w.priority_score)}%` }}
                        ></div>
                      </div>
                      <span className="font-mono font-bold">{w.priority_score.toFixed(1)}</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        w.priority_score >= 60
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : w.priority_score >= 40
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {w.priority_score >= 60 ? 'HIGH' : w.priority_score >= 40 ? 'MEDIUM' : 'LOW'}
                    </span>
                  </td>
                  <td className="p-3">
                    <Link
                      to={`/gis?ward=${w.ward_code}`}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-brand-400 rounded text-[11px] font-medium transition"
                    >
                      View on Map
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
