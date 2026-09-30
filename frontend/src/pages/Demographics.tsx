import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { WardSummary } from '../types';
import { Users, PieChart as PieIcon, MapPin, Building } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export const Demographics: React.FC = () => {
  const [wards, setWards] = useState<WardSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getWards();
        setWards(data);
      } catch (err) {
        console.error('Error loading wards', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Demographic & Land-Use Profiles</h2>
        <p className="text-sm text-slate-400">
          Census of India municipal ward demographics, population density distributions, and Master Plan land-use zoning.
        </p>
      </div>

      {/* Population Density Chart */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Ward Population Density (Persons / km²)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={wards}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                formatter={(val: any) => [`${val.toLocaleString()} persons/km²`, 'Density']}
              />
              <Bar dataKey="population_density" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Ward Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {wards.map((w) => (
          <div key={w.id} className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-brand-400">{w.ward_code}</span>
              <span className="text-[10px] text-slate-500 font-medium">{w.area_sq_km} km²</span>
            </div>
            <div>
              <h4 className="font-bold text-slate-100 text-sm">{w.name}</h4>
              <p className="text-xs text-slate-400">{w.zone_name}</p>
            </div>
            <div className="pt-2 border-t border-slate-800 space-y-1 text-xs text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Population:</span>
                <span className="font-mono font-semibold">{w.population.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Density:</span>
                <span className="font-mono">{w.population_density.toFixed(0)}/km²</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Complaints:</span>
                <span className="font-mono text-amber-400">{w.total_complaints}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
