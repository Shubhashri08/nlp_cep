import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import L from 'leaflet';
import { Layers, Search } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { COMPLAINT_LEGEND, GISMap, choroplethRange } from '../components/gis/GISMap';
import { ChoroplethLegend } from '../components/gis/MapLegend';
import { WardDrawer } from '../components/gis/WardDrawer';
import { ErrorState, Legend } from '../components/ui';
import { ASSET_COLORS, SEVERITY_COLOR } from '../lib/theme';
import { titleCase } from '../lib/format';

const CATEGORY_OPTIONS = ['', 'FLOODING', 'DRAINAGE', 'WASTE_MANAGEMENT', 'WATER_SUPPLY', 'ROAD_INFRASTRUCTURE', 'TRAFFIC', 'PUBLIC_TRANSPORT',
  'STREETLIGHT', 'HEALTHCARE', 'AIR_QUALITY', 'PUBLIC_SAFETY', 'HOUSING', 'PARKS', 'ENVIRONMENT', 'EDUCATION', 'ELECTRICITY'];
const ASSET_TYPES = ['', 'HEALTHCARE', 'EDUCATION', 'BUS_STOP', 'RAIL_STATION', 'METRO_STATION', 'PARKS', 'PUBLIC_SAFETY', 'EMERGENCY', 'SANITATION', 'WATER_SUPPLY'];

const GISExplorer: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const selectedWard = params.get('ward') ? Number(params.get('ward')) : null;
  const [choroId, setChoroId] = useState('priority');
  const [showHotspots, setShowHotspots] = useState(true);
  const [showComplaints, setShowComplaints] = useState(false);
  const [showAssets, setShowAssets] = useState(false);
  const [assetType, setAssetType] = useState('HEALTHCARE');
  const [category, setCategory] = useState('');
  const [months, setMonths] = useState(12);
  const [overlayId, setOverlayId] = useState('');
  const [search, setSearch] = useState('');
  const [focus, setFocus] = useState<{ key: number; bounds: L.LatLngBoundsExpression } | null>(null);
  const [panelOpen, setPanelOpen] = useState(() => typeof window === 'undefined' || window.innerWidth >= 768);

  const manifest = useApi(() => api.layers(), []);
  const wards = useApi(() => api.wardsGeo(), []);
  const hotspots = useApi(() => api.hotspots({ category: category || undefined, months }), [category, months], showHotspots);
  const complaints = useApi(() => api.complaintPoints({ category: category || undefined, months }), [category, months], showComplaints);
  const assets = useApi(() => api.assets({ asset_type: assetType || undefined }), [assetType], showAssets);

  const spec = manifest.data?.choropleths.find((c) => c.id === choroId) ?? null;
  const range = useMemo(() => choroplethRange(wards.data, spec), [wards.data, spec]);
  const overlay = manifest.data?.raster_overlays.find((o) => o.id === overlayId);

  const selectWard = (id: number | null, fly = false) => {
    const next = new URLSearchParams(params);
    if (id) next.set('ward', String(id)); else next.delete('ward');
    setParams(next, { replace: true });
    if (fly && id && wards.data) {
      const f = wards.data.features.find((x) => x.properties.id === id);
      if (f) setFocus({ key: Date.now(), bounds: L.geoJSON(f as GeoJSON.Feature).getBounds() });
    }
  };

  // Deep link: fly to ward once polygons arrive
  useEffect(() => {
    if (selectedWard && wards.data && !focus) selectWard(selectedWard, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wards.data]);

  const matches = search.length >= 1 && wards.data
    ? wards.data.features.filter((f) => `${f.properties.ward_code} ${f.properties.name} ${f.properties.localities}`.toLowerCase().includes(search.toLowerCase())).slice(0, 6)
    : [];

  return (
    <div className="relative h-[calc(100vh-4rem)] flex">
      <div className="relative flex-1 min-w-0">
        {wards.error ? <ErrorState message={wards.error} onRetry={wards.reload} className="h-full" /> : (
          <GISMap wards={wards.data} selectedWardId={selectedWard} focus={focus}
            layers={{ choropleth: spec, hotspots: showHotspots, complaints: showComplaints, assets: showAssets, overlayUrl: overlay?.url ?? null }}
            hotspots={hotspots.data?.hotspots} complaints={complaints.data ?? []} assets={assets.data ?? []}
            overlayBounds={manifest.data?.overlay_bounds} onWardClick={(id) => selectWard(id)} />
        )}

        {/* Search */}
        <div className="absolute top-3 left-14 right-3 md:right-auto z-[500] md:w-72">
          <div className="card flex items-center gap-2 px-3 py-2">
            <Search className="h-4 w-4 text-muted" />
            <input className="flex-1 bg-transparent text-sm focus:outline-none" placeholder="Find ward or locality (e.g. Kurla, H/E)"
              value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search wards" />
          </div>
          {matches.length > 0 && (
            <div className="card mt-1 py-1">
              {matches.map((f) => (
                <button key={f.properties.id} className="block w-full text-left px-3 py-1.5 text-sm hover:bg-buff-50"
                  onClick={() => { selectWard(f.properties.id, true); setSearch(''); }}>
                  <b className="text-police">{f.properties.ward_code}</b> <span className="text-muted">{f.properties.localities}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Layer panel */}
        <div className="absolute top-16 md:top-3 right-3 z-[500] w-72 max-w-[calc(100%-4rem)] max-h-[calc(100%-5rem)] overflow-y-auto card">
          <button className="w-full flex items-center justify-between px-4 py-2.5" onClick={() => setPanelOpen((o) => !o)} aria-expanded={panelOpen}>
            <span className="flex items-center gap-2 font-display text-police"><Layers className="h-4 w-4" />Layers</span>
            <span className="text-xs text-muted">{panelOpen ? 'Hide' : 'Show'}</span>
          </button>
          {panelOpen && (
            <div className="px-4 pb-4 space-y-4 text-sm">
              <label className="block"><span className="label">Colour wards by</span>
                <select className="input mt-1 py-1.5" value={choroId} onChange={(e) => setChoroId(e.target.value)}>
                  <option value="">None (outlines)</option>
                  {manifest.data?.choropleths.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </label>
              {spec && <ChoroplethLegend spec={spec} min={range[0]} max={range[1]} />}

              <label className="block"><span className="label">Satellite overlay (Sentinel-2)</span>
                <select className="input mt-1 py-1.5" value={overlayId} onChange={(e) => setOverlayId(e.target.value)}>
                  <option value="">None</option>
                  {manifest.data?.raster_overlays.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </label>
              {overlayId.startsWith('ndvi') && <div className="flex items-center gap-2 text-[11px] text-muted"><span className="h-2.5 w-16 rounded-sm" style={{ background: 'linear-gradient(90deg,#8A3B08,#F3D58D,#2E7D32)' }} />bare / built → vegetated</div>}
              {overlayId === 'builtup_change' && <Legend items={[{ label: 'Became built-up', color: '#E59D2C' }]} />}

              <div className="space-y-2 pt-1 border-t border-line">
                <div className="label pt-2">Complaint layers</div>
                <select className="input py-1.5" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Complaint category">
                  {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c ? titleCase(c) : 'All categories'}</option>)}
                </select>
                <select className="input py-1.5" value={months} onChange={(e) => setMonths(Number(e.target.value))} aria-label="Time window">
                  {[3, 6, 12, 24, 36].map((m) => <option key={m} value={m}>Last {m} months</option>)}
                </select>
                <label className="flex items-center gap-2"><input type="checkbox" checked={showHotspots} onChange={(e) => setShowHotspots(e.target.checked)} className="accent-marigold" />
                  Hotspots (DBSCAN) {hotspots.data && <span className="text-muted text-xs">· {hotspots.data.total_hotspots}</span>}</label>
                {showHotspots && <Legend items={[{ label: 'High', color: SEVERITY_COLOR.CRITICAL }, { label: 'Medium', color: SEVERITY_COLOR.MODERATE }, { label: 'Low', color: SEVERITY_COLOR.LOW }]} />}
                <label className="flex items-center gap-2"><input type="checkbox" checked={showComplaints} onChange={(e) => setShowComplaints(e.target.checked)} className="accent-marigold" />
                  Individual complaints {complaints.data && showComplaints && <span className="text-muted text-xs">· {complaints.data.length}</span>}</label>
                {showComplaints && <Legend items={COMPLAINT_LEGEND} />}
              </div>

              <div className="space-y-2 pt-1 border-t border-line">
                <label className="flex items-center gap-2 pt-2"><input type="checkbox" checked={showAssets} onChange={(e) => setShowAssets(e.target.checked)} className="accent-marigold" />
                  Infrastructure (OSM) {assets.data && showAssets && <span className="text-muted text-xs">· {assets.data.length}</span>}</label>
                {showAssets && <select className="input py-1.5" value={assetType} onChange={(e) => setAssetType(e.target.value)} aria-label="Asset type">
                  {ASSET_TYPES.map((a) => <option key={a} value={a}>{a ? titleCase(a) : 'All types'}</option>)}
                </select>}
                {showAssets && !assetType && <Legend items={Object.entries(ASSET_COLORS).slice(0, 8).map(([k, c]) => ({ label: titleCase(k), color: c }))} />}
              </div>
              {(hotspots.error || complaints.error || assets.error) && <p className="text-xs text-citrine">{hotspots.error || complaints.error || assets.error}</p>}
            </div>
          )}
        </div>
      </div>

      {selectedWard && (
        <div className="absolute inset-y-0 right-0 z-[1100] w-full sm:w-[420px] md:static md:z-auto">
          <WardDrawer wardId={selectedWard} onClose={() => selectWard(null)} />
        </div>
      )}
    </div>
  );
};

export default GISExplorer;
