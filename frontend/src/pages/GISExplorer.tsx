import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { GISMap } from '../components/gis/GISMap';
import { WardProfile, Hotspot } from '../types';
import {
  Layers, MapPin, Eye, AlertTriangle, ShieldCheck,
  Building, Droplets, Users, X, Info
} from 'lucide-react';

export const GISExplorer: React.FC = () => {
  const [wardsGeoJSON, setWardsGeoJSON] = useState<any>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [complaints, setComplaints] = useState<any[]>([]);
  const [infrastructure, setInfrastructure] = useState<any[]>([]);
  const [selectedWardProfile, setSelectedWardProfile] = useState<WardProfile | null>(null);
  const [selectedWardId, setSelectedWardId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Layer visibility state
  const [layers, setLayers] = useState({
    wards: true,
    hotspots: true,
    complaints: true,
    infrastructure: false,
  });

  const [categoryFilter, setCategoryFilter] = useState<string>('');

  useEffect(() => {
    async function loadGISData() {
      try {
        setLoading(true);
        const [geo, hs, comp, infra] = await Promise.all([
          api.getWardsGeoJSON(),
          api.getHotspots(1.0, categoryFilter || undefined),
          api.getCitizenRequests({ limit: 100 }),
          api.getInfrastructureAssets()
        ]);
        setWardsGeoJSON(geo);
        setHotspots(hs.hotspots);
        setComplaints(comp);
        setInfrastructure(infra);
      } catch (err) {
        console.error('Error loading GIS layers', err);
      } finally {
        setLoading(false);
      }
    }
    loadGISData();
  }, [categoryFilter]);

  const handleSelectWard = async (wardId: number) => {
    setSelectedWardId(wardId);
    try {
      const profile = await api.getWardProfile(wardId);
      setSelectedWardProfile(profile);
    } catch (err) {
      console.error('Failed to load ward profile', err);
    }
  };

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col space-y-3">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900 border border-slate-800 p-3 rounded-xl">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-brand-400" />
          <h2 className="text-base font-bold text-slate-100">Interactive Municipal GIS Explorer</h2>
          <span className="text-xs text-slate-400 hidden sm:inline">• PostGIS Vector Layers & DBSCAN Clustering</span>
        </div>

        {/* Layer Toggles & Category Filter */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => setLayers(p => ({ ...p, wards: !p.wards }))}
            className={`px-2.5 py-1 rounded-lg border font-medium transition ${
              layers.wards ? 'bg-brand-500/20 border-brand-500/40 text-brand-300' : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            Wards
          </button>
          <button
            onClick={() => setLayers(p => ({ ...p, hotspots: !p.hotspots }))}
            className={`px-2.5 py-1 rounded-lg border font-medium transition ${
              layers.hotspots ? 'bg-rose-500/20 border-rose-500/40 text-rose-300' : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            Hotspots ({hotspots.length})
          </button>
          <button
            onClick={() => setLayers(p => ({ ...p, complaints: !p.complaints }))}
            className={`px-2.5 py-1 rounded-lg border font-medium transition ${
              layers.complaints ? 'bg-amber-500/20 border-amber-500/40 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            Complaints ({complaints.length})
          </button>
          <button
            onClick={() => setLayers(p => ({ ...p, infrastructure: !p.infrastructure }))}
            className={`px-2.5 py-1 rounded-lg border font-medium transition ${
              layers.infrastructure ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            Assets ({infrastructure.length})
          </button>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none"
          >
            <option value="">All Categories</option>
            <option value="FLOODING">Flooding</option>
            <option value="DRAINAGE">Drainage</option>
            <option value="ROAD_INFRASTRUCTURE">Roads</option>
            <option value="WASTE_MANAGEMENT">Waste</option>
            <option value="WATER_SUPPLY">Water</option>
            <option value="TRAFFIC">Traffic</option>
          </select>
        </div>
      </div>

      {/* Main Map & Drawer Split View */}
      <div className="flex-1 flex gap-4 min-h-0 relative">
        <div className="flex-1 h-full min-h-0">
          {loading ? (
            <div className="w-full h-full flex items-center justify-center bg-slate-900 rounded-xl border border-slate-800">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
            </div>
          ) : (
            <GISMap
              wardsGeoJSON={wardsGeoJSON}
              hotspots={hotspots}
              complaints={complaints}
              infrastructure={infrastructure}
              selectedWardId={selectedWardId}
              onSelectWard={handleSelectWard}
              layersVisible={layers}
            />
          )}
        </div>

        {/* Slide-in Ward Profile Drawer */}
        {selectedWardProfile && (
          <div className="w-96 bg-slate-900 border border-slate-800 rounded-xl flex flex-col h-full shadow-2xl z-10 overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div>
                <h3 className="text-sm font-bold text-slate-100">{selectedWardProfile.ward_info.name}</h3>
                <span className="text-xs text-brand-400 font-mono">{selectedWardProfile.ward_info.ward_code}</span>
              </div>
              <button
                onClick={() => setSelectedWardProfile(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs">
              {/* Quick Metrics */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <div className="text-slate-500 font-medium">Population</div>
                  <div className="text-base font-bold text-slate-200">{selectedWardProfile.ward_info.population.toLocaleString()}</div>
                  <div className="text-[10px] text-slate-400">{selectedWardProfile.ward_info.population_density.toFixed(0)} / km²</div>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <div className="text-slate-500 font-medium">Priority Score</div>
                  <div className="text-base font-bold text-rose-400">{selectedWardProfile.ward_info.priority_score.toFixed(1)} / 100</div>
                  <div className="text-[10px] text-slate-400">{selectedWardProfile.ward_info.total_complaints} complaints</div>
                </div>
              </div>

              {/* Verified Infrastructure Gaps */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-300">Infrastructure Deficits</span>
                  <span className="text-[10px] text-slate-500">URDPFI Norms</span>
                </div>
                {selectedWardProfile.infrastructure_gaps.length === 0 ? (
                  <div className="p-2 bg-slate-950 rounded text-slate-500 text-[11px]">No critical deficits detected.</div>
                ) : (
                  selectedWardProfile.infrastructure_gaps.map((gap, i) => (
                    <div key={i} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between font-semibold text-slate-200">
                        <span>{gap.sector}</span>
                        <span className="text-rose-400 font-bold">{gap.deficit_pct}% deficit</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Required: {gap.required} {gap.unit} | Existing: {gap.existing} {gap.unit}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Environmental Risk */}
              {selectedWardProfile.environmental_indicators && (
                <div className="space-y-2">
                  <span className="font-bold text-slate-300">Environmental & Climate</span>
                  <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1 text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Flood Vulnerability:</span>
                      <span className="font-bold text-amber-400">
                        {(selectedWardProfile.environmental_indicators.flood_risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Air Quality PM2.5:</span>
                      <span className="font-mono">{selectedWardProfile.environmental_indicators.aqi_pm25} µg/m³</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Elevation:</span>
                      <span>{selectedWardProfile.environmental_indicators.elevation_m} meters</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div className="space-y-2">
                <span className="font-bold text-slate-300">Planning Recommendations</span>
                {selectedWardProfile.recommendations.map((r, i) => (
                  <div key={i} className="p-2.5 bg-brand-950/40 border border-brand-800/40 rounded-lg space-y-1">
                    <div className="font-bold text-brand-300">{r.title}</div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">{r.recommendation_text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
