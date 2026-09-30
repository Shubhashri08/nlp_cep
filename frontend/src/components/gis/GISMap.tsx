import React, { useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, Circle, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Hotspot } from '../../types';

// Fix Leaflet marker icon asset issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface GISMapProps {
  wardsGeoJSON?: any;
  hotspots?: Hotspot[];
  complaints?: any[];
  infrastructure?: any[];
  selectedWardId?: number | null;
  onSelectWard?: (wardId: number) => void;
  layersVisible?: {
    wards: boolean;
    hotspots: boolean;
    complaints: boolean;
    infrastructure: boolean;
  };
}

function MapViewController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

export const GISMap: React.FC<GISMapProps> = ({
  wardsGeoJSON,
  hotspots = [],
  complaints = [],
  infrastructure = [],
  selectedWardId,
  onSelectWard,
  layersVisible = { wards: true, hotspots: true, complaints: true, infrastructure: false },
}) => {
  const defaultCenter: [number, number] = [19.0760, 72.8777]; // Mumbai coordinates

  const getWardStyle = (feature: any) => {
    const isSelected = selectedWardId === feature.properties.id;
    const score = feature.properties.priority_score || 0;
    
    // Color scale based on priority score
    let fillColor = '#3b82f6'; // Low (Blue)
    if (score >= 60) fillColor = '#ef4444'; // Critical (Red)
    else if (score >= 40) fillColor = '#f59e0b'; // Moderate (Amber)
    else if (score >= 20) fillColor = '#10b981'; // Green

    return {
      fillColor,
      weight: isSelected ? 3 : 1.5,
      opacity: 1,
      color: isSelected ? '#ffffff' : '#64748b',
      dashArray: isSelected ? '' : '3',
      fillOpacity: isSelected ? 0.65 : 0.35,
    };
  };

  const onEachWard = (feature: any, layer: L.Layer) => {
    layer.on({
      click: () => {
        if (onSelectWard) onSelectWard(feature.properties.id);
      },
    });
    layer.bindTooltip(`
      <div class="font-sans text-xs">
        <strong>${feature.properties.name}</strong><br/>
        Pop: ${feature.properties.population?.toLocaleString()}<br/>
        Priority Score: <strong>${feature.properties.priority_score?.toFixed(1)}/100</strong>
      </div>
    `, { sticky: true });
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'FLOODING':
      case 'DRAINAGE': return '#38bdf8';
      case 'ROAD_INFRASTRUCTURE':
      case 'TRAFFIC': return '#fb923c';
      case 'WASTE_MANAGEMENT': return '#a855f7';
      case 'WATER_SUPPLY': return '#0284c7';
      case 'PUBLIC_SAFETY': return '#ef4444';
      default: return '#94a3b8';
    }
  };

  return (
    <div className="w-full h-full relative rounded-xl overflow-hidden border border-slate-800 shadow-inner">
      <MapContainer
        center={defaultCenter}
        zoom={11}
        scrollWheelZoom={true}
        className="w-full h-full bg-slate-950"
      >
        <MapViewController center={defaultCenter} zoom={11} />
        
        {/* Dark Matter CartoDB / OSM Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Wards Boundary Polygons Layer */}
        {layersVisible.wards && wardsGeoJSON && (
          <GeoJSON
            key={JSON.stringify(wardsGeoJSON)}
            data={wardsGeoJSON}
            style={getWardStyle}
            onEachFeature={onEachWard}
          />
        )}

        {/* Hotspot Circles (DBSCAN) Layer */}
        {layersVisible.hotspots &&
          hotspots.map((h, i) => (
            <Circle
              key={`hotspot-${i}`}
              center={[h.center_lat, h.center_lng]}
              radius={h.radius_meters}
              pathOptions={{
                color: h.severity_level === 'HIGH' ? '#ef4444' : '#f59e0b',
                fillColor: getCategoryColor(h.category),
                fillOpacity: 0.35,
                weight: 2,
              }}
            >
              <Popup>
                <div className="text-xs space-y-1 font-sans">
                  <div className="font-bold text-slate-900 flex items-center justify-between">
                    <span>HOTSPOT: {h.category}</span>
                    <span className="px-1.5 py-0.5 bg-rose-100 text-rose-700 rounded font-semibold text-[10px]">
                      {h.severity_level}
                    </span>
                  </div>
                  <div className="text-slate-700">Reports: <strong>{h.point_count} complaints</strong></div>
                  <div className="text-slate-700">Radius: <strong>{h.radius_meters}m</strong></div>
                  <div className="text-slate-700">Density Score: <strong>{h.density_score}</strong></div>
                </div>
              </Popup>
            </Circle>
          ))}

        {/* Geocoded Complaints Point Markers Layer */}
        {layersVisible.complaints &&
          complaints.map((c) => {
            if (!c.latitude || !c.longitude) return null;
            return (
              <Circle
                key={`complaint-${c.id}`}
                center={[c.latitude, c.longitude]}
                radius={80}
                pathOptions={{
                  color: getCategoryColor(c.primary_category),
                  fillColor: getCategoryColor(c.primary_category),
                  fillOpacity: 0.85,
                  weight: 1,
                }}
              >
                <Popup>
                  <div className="text-xs font-sans max-w-[220px]">
                    <div className="font-semibold text-slate-900 mb-1">{c.primary_category}</div>
                    <p className="text-slate-600 italic text-[11px] mb-1">"{c.original_text}"</p>
                    <div className="text-slate-500 text-[10px]">Location: {c.address || `${c.latitude}, ${c.longitude}`}</div>
                    <div className="text-slate-500 text-[10px]">Status: {c.status}</div>
                  </div>
                </Popup>
              </Circle>
            );
          })}

        {/* Infrastructure Assets Layer */}
        {layersVisible.infrastructure &&
          infrastructure.map((asset) => (
            <Circle
              key={`asset-${asset.id}`}
              center={[asset.latitude, asset.longitude]}
              radius={120}
              pathOptions={{
                color: '#10b981',
                fillColor: '#059669',
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Popup>
                <div className="text-xs font-sans">
                  <div className="font-bold text-emerald-800">{asset.name}</div>
                  <div className="text-slate-700">Sector: {asset.asset_type}</div>
                  <div className="text-slate-700">Capacity: {asset.capacity} {asset.unit}</div>
                </div>
              </Popup>
            </Circle>
          ))}
      </MapContainer>
    </div>
  );
};
