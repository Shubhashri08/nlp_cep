import React, { useEffect, useMemo, useRef } from 'react';
import { CircleMarker, GeoJSON, ImageOverlay, LayersControl, MapContainer, Pane, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { GeoJSON as LGeoJSON, Layer, LeafletMouseEvent, PathOptions } from 'leaflet';
import L from 'leaflet';
import type { Asset, ChoroplethSpec, ComplaintPoint, Hotspot, WardFeatureCollection, WardFeatureProps } from '../../types';
import { ASSET_COLORS, BRAND, CATEGORICAL, GROWTH_COLORS, RAMPS, SEVERITY_COLOR, rampColor } from '../../lib/theme';
import { fmtInt, fmtNum, titleCase } from '../../lib/format';

export const MUMBAI_CENTER: [number, number] = [19.075, 72.885];

/** Keeps Leaflet's size in sync with its container (drawer open/close, window resize). */
const SizeSync: React.FC = () => {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    const ro = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);
  return null;
};

/** Pans to a ward only when the focus target changes (not on every re-render). */
const FocusController: React.FC<{ target: { key: number; bounds: L.LatLngBoundsExpression } | null }> = ({ target }) => {
  const map = useMap();
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (target && target.key !== last.current) {
      last.current = target.key;
      map.flyToBounds(target.bounds, { padding: [40, 40], maxZoom: 14, duration: 0.6 });
    }
  }, [target, map]);
  return null;
};

export interface MapLayers {
  choropleth: ChoroplethSpec | null;
  hotspots: boolean;
  complaints: boolean;
  assets: boolean;
  overlayUrl: string | null;
}

interface Props {
  wards: WardFeatureCollection | null;
  layers: MapLayers;
  hotspots?: Hotspot[];
  complaints?: ComplaintPoint[];
  assets?: Asset[];
  overlayBounds?: [[number, number], [number, number]] | null;
  selectedWardId?: number | null;
  focus?: { key: number; bounds: L.LatLngBoundsExpression } | null;
  onWardClick?: (id: number) => void;
}

const categoryColor = (() => {
  const cache: Record<string, string> = {};
  const order = ['FLOODING', 'DRAINAGE', 'WASTE_MANAGEMENT', 'WATER_SUPPLY', 'ROAD_INFRASTRUCTURE', 'TRAFFIC'];
  return (c: string) => {
    if (!cache[c]) {
      const i = order.indexOf(c);
      cache[c] = i >= 0 ? CATEGORICAL[i] : '#8C8577';
    }
    return cache[c];
  };
})();
export const COMPLAINT_LEGEND = ['FLOODING', 'DRAINAGE', 'WASTE_MANAGEMENT', 'WATER_SUPPLY', 'ROAD_INFRASTRUCTURE', 'TRAFFIC']
  .map((c) => ({ label: titleCase(c), color: categoryColor(c) })).concat([{ label: 'Other', color: '#8C8577' }]);

export function choroplethRange(wards: WardFeatureCollection | null, spec: ChoroplethSpec | null): [number, number] {
  if (!wards || !spec || spec.ramp === 'categorical') return [0, 1];
  const vals = wards.features.map((f) => f.properties[spec.property] as number).filter((v) => typeof v === 'number');
  return vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
}

export const GISMap: React.FC<Props> = ({ wards, layers, hotspots = [], complaints = [], assets = [], overlayBounds, selectedWardId, focus, onWardClick }) => {
  const spec = layers.choropleth;
  const [min, max] = useMemo(() => choroplethRange(wards, spec), [wards, spec]);
  const canvas = useMemo(() => L.canvas({ padding: 0.3 }), []);

  const style = (feature?: GeoJSON.Feature): PathOptions => {
    const p = feature?.properties as WardFeatureProps;
    const selected = p?.id === selectedWardId;
    let fill = '#F1E7D6';
    if (spec) {
      const v = p?.[spec.property];
      fill = spec.ramp === 'categorical' ? (GROWTH_COLORS[String(v)] ?? '#E7E1D6') : rampColor(v as number, min, max, RAMPS[spec.ramp]);
    }
    return {
      color: selected ? BRAND.marigold : BRAND.police, weight: selected ? 3.5 : 1.2, opacity: 0.9,
      fillColor: fill, fillOpacity: spec ? (layers.overlayUrl ? 0.35 : 0.72) : 0.08,
    };
  };

  const onEachFeature = (feature: GeoJSON.Feature, layer: Layer) => {
    const p = feature.properties as WardFeatureProps;
    const value = spec ? p[spec.property] : null;
    layer.bindTooltip(
      `<div style="font-weight:700;color:#2E4365">${p.ward_code} Ward</div><div style="font-size:11px;color:#5E6B80">${p.localities ?? ''}</div>` +
      (spec ? `<div style="margin-top:3px;font-size:12px">${spec.label}: <b>${typeof value === 'number' ? fmtNum(value, 2) : titleCase(String(value ?? '—'))}</b> ${spec.unit}</div>` : ''),
      { sticky: true },
    );
    layer.on({
      click: () => onWardClick?.(p.id),
      mouseover: (e: LeafletMouseEvent) => (e.target as L.Path).setStyle({ weight: 3, color: BRAND.marigold }),
      mouseout: (e: LeafletMouseEvent) => (e.target as L.Path).setStyle(style(feature)),
    });
  };

  // Key changes only when styling inputs change – not on every render
  const geoKey = `${spec?.id ?? 'none'}-${selectedWardId ?? 'x'}-${layers.overlayUrl ? 'ov' : ''}-${wards?.features.length ?? 0}`;

  return (
    <MapContainer center={MUMBAI_CENTER} zoom={11} minZoom={10} maxZoom={18} className="h-full w-full" preferCanvas>
      <SizeSync />
      <FocusController target={focus ?? null} />
      <LayersControl position="bottomleft">
        <LayersControl.BaseLayer checked name="Light (Esri)">
          <TileLayer attribution='Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors' maxZoom={16}
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}" />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="OpenStreetMap">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' maxZoom={19}
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Satellite (Esri)">
          <TileLayer attribution='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics' maxZoom={18}
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
        </LayersControl.BaseLayer>
      </LayersControl>
      {layers.overlayUrl && overlayBounds && (
        <ImageOverlay url={layers.overlayUrl} bounds={overlayBounds} opacity={0.85} zIndex={250}
          attribution="Contains modified Copernicus Sentinel data" />
      )}
      {wards && <GeoJSON key={geoKey} data={wards as GeoJSON.GeoJsonObject} style={style} onEachFeature={onEachFeature} ref={(r: LGeoJSON | null) => r?.bringToBack()} />}

      <Pane name="points" style={{ zIndex: 450 }}>
        {layers.assets && assets.map((a) => (
          <CircleMarker key={`a${a.id}`} center={[a.latitude, a.longitude]} radius={3.5} renderer={canvas}
            pathOptions={{ color: '#fff', weight: 0.8, fillColor: ASSET_COLORS[a.asset_type] ?? '#5E6B80', fillOpacity: 0.95 }}>
            <Popup><h4>{a.name}</h4><div>{titleCase(a.asset_type)}{a.subtype ? ` · ${titleCase(a.subtype)}` : ''}</div>
              <div style={{ color: '#5E6B80', fontSize: 11, marginTop: 4 }}>Source: {a.provenance}</div></Popup>
          </CircleMarker>
        ))}
        {layers.complaints && complaints.map((c) => (
          <CircleMarker key={`c${c.id}`} center={[c.lat, c.lng]} radius={3} renderer={canvas}
            pathOptions={{ color: categoryColor(c.category), weight: 1, fillColor: categoryColor(c.category), fillOpacity: 0.55 }}>
            <Popup><h4>{titleCase(c.category)}</h4><div>{c.summary}</div>
              <div style={{ color: '#5E6B80', fontSize: 11, marginTop: 4 }}>{c.date} · {titleCase(c.status)} · #{c.id}</div></Popup>
          </CircleMarker>
        ))}
      </Pane>
      <Pane name="hotspots" style={{ zIndex: 460 }}>
        {layers.hotspots && hotspots.map((h) => (
          <CircleMarker key={`h${h.cluster_id}-${h.category}`} center={[h.center_lat, h.center_lng]}
            radius={Math.max(6, Math.min(18, Math.sqrt(h.point_count) * 2))}
            pathOptions={{ color: '#fff', weight: 2, fillColor: SEVERITY_COLOR[h.severity_level === 'HIGH' ? 'CRITICAL' : h.severity_level], fillOpacity: 0.8 }}>
            <Tooltip direction="top">{titleCase(h.category)} · {h.point_count} complaints</Tooltip>
            <Popup>
              <h4>{titleCase(h.category)} hotspot</h4>
              <div><b>{h.point_count}</b> complaints within ~{fmtInt(h.radius_meters)} m · severity <b>{titleCase(h.severity_level)}</b></div>
              <div style={{ marginTop: 6, fontSize: 12 }}>
                {Object.entries(h.category_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => <div key={k}>{titleCase(k)}: {v}</div>)}
              </div>
              {h.sample_complaints.length > 0 && <ul style={{ marginTop: 6, paddingLeft: 16, fontSize: 12, color: '#5E6B80' }}>
                {h.sample_complaints.slice(0, 3).map((s, i) => <li key={i}>{s}</li>)}</ul>}
            </Popup>
          </CircleMarker>
        ))}
      </Pane>
    </MapContainer>
  );
};
