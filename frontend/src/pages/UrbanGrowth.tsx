import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Satellite, TrendingUp, Layers, Trees, Droplets } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

export const UrbanGrowth: React.FC = () => {
  const [growthData, setGrowthData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getUrbanGrowth();
        setGrowthData(data);
      } catch (err) {
        console.error('Error loading growth data', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading || !growthData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Urban Growth & Remote Sensing</h2>
        <p className="text-sm text-slate-400">
          Multi-temporal Sentinel-2 Earth observation reflectance indices: NDVI (Vegetation), NDBI (Built-Up), and NDWI (Water Bodies) from 2020 to 2026.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>BUILT-UP EXPANSION</span>
            <Satellite className="w-4 h-4 text-brand-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">+{growthData.growth_summary.built_up_expansion_pct}%</div>
          <p className="text-[11px] text-slate-500">2020 to 2026 Built-Up Expansion (NDBI &gt; 0.05)</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>VEGETATION LOSS</span>
            <Trees className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">{growthData.growth_summary.vegetation_loss_pct}%</div>
          <p className="text-[11px] text-slate-500">Reduction in dense canopy cover (NDVI &gt; 0.3)</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>WATER BODY CHANGE</span>
            <Droplets className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{growthData.growth_summary.water_body_loss_pct}%</div>
          <p className="text-[11px] text-slate-500">Encroachment & seasonal variation (NDWI &gt; 0.1)</p>
        </div>
      </div>

      {/* Remote Sensing Time Series Chart */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Satellite Mean Spectral Index Trend (2020 - 2026)</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={growthData.satellite_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} domain={[0, 0.5]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
              />
              <Legend />
              <Line type="monotone" dataKey="mean_ndbi" name="NDBI (Built-up)" stroke="#fb923c" strokeWidth={2} />
              <Line type="monotone" dataKey="mean_ndvi" name="NDVI (Vegetation)" stroke="#10b981" strokeWidth={2} />
              <Line type="monotone" dataKey="mean_ndwi" name="NDWI (Water)" stroke="#38bdf8" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
