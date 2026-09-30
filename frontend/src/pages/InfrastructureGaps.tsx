import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { InfrastructureGapItem } from '../types';
import { Network, AlertTriangle, CheckCircle2, ShieldAlert, FileSpreadsheet } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export const InfrastructureGaps: React.FC = () => {
  const [gaps, setGaps] = useState<InfrastructureGapItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedSector, setSelectedSector] = useState<string>('');

  useEffect(() => {
    async function loadGaps() {
      try {
        setLoading(true);
        const data = await api.getInfrastructureGaps();
        setGaps(data);
      } catch (err) {
        console.error('Failed to load gaps', err);
      } finally {
        setLoading(false);
      }
    }
    loadGaps();
  }, []);

  const filteredGaps = selectedSector ? gaps.filter(g => g.sector.includes(selectedSector)) : gaps;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Infrastructure Gap Analysis</h2>
          <p className="text-sm text-slate-400">
            Comparing verified population demand against existing municipal infrastructure capacities using CPHEEO & URDPFI standards.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
          >
            <option value="">All Sectors</option>
            <option value="Water">Water Supply (135 LPCD)</option>
            <option value="Drainage">Drainage & Storm Water</option>
            <option value="Waste">Waste Management (0.45 kg/capita)</option>
            <option value="Healthcare">Healthcare (WHO / IPHS Beds)</option>
          </select>
        </div>
      </div>

      {/* Deficit Percentage Chart */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Infrastructure Deficit Percentage by Ward & Sector</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={filteredGaps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="ward_name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                formatter={(val: any) => [`${val}% Deficit`, 'Deficit Rate']}
              />
              <Bar dataKey="deficit_percentage" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Gaps Breakdown Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 bg-slate-950/40">
          <h3 className="text-sm font-bold text-slate-200">Deficit Records & Traceable Benchmarks</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="p-3">WARD</th>
                <th className="p-3">SECTOR</th>
                <th className="p-3">REQUIRED DEMAND</th>
                <th className="p-3">EXISTING CAPACITY</th>
                <th className="p-3">DEFICIT AMOUNT</th>
                <th className="p-3">DEFICIT %</th>
                <th className="p-3">SEVERITY</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {filteredGaps.map((g) => (
                <tr key={g.id} className="hover:bg-slate-800/40 transition">
                  <td className="p-3 font-semibold text-slate-100">{g.ward_name}</td>
                  <td className="p-3 text-slate-200">{g.sector}</td>
                  <td className="p-3 font-mono">{g.required_capacity} {g.unit}</td>
                  <td className="p-3 font-mono text-slate-400">{g.existing_capacity} {g.unit}</td>
                  <td className="p-3 font-mono font-bold text-rose-400">{g.deficit_amount} {g.unit}</td>
                  <td className="p-3 font-mono font-bold">{g.deficit_percentage}%</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        g.severity === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : g.severity === 'HIGH'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {g.severity}
                    </span>
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
