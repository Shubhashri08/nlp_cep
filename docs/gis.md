# GIS & remote sensing

## Remote sensing (`scripts/ingest/sentinel.py`, `backend/app/gis/remote_sensing.py`)

1. Planetary Computer STAC search: `sentinel-2-l2a`, window Jan–Feb of 2019 / 2022 / 2026, cloud < 10 %, three distinct dates per MGRS tile (tiles 42QZF, 42QZG, 43QBA, 43QBB).
2. Bands B03, B04, B08, B11 and SCL, warped to an EPSG:4326 grid at 0.0003° (≈33 m). Baseline ≥ 04.00 offset (−1000 DN) corrected.
3. SCL mask excludes no-data, saturated, cloud shadow, medium / high cloud, cirrus and snow. Per-pixel median composite.
4. **PIF radiometric normalisation** (Schott 1988): per-band linear fit onto the 2019 reference, using pixels whose NDVI percentile rank changed by less than 1 %.
5. Indices: NDVI, NDBI, NDWI (McFeeters). Classes, in order of precedence: water NDWI > 0.05; vegetation NDVI > 0.30; bare soil NDBI > 0.12 and NDVI > 0.15; built-up = remaining pixels with NDVI < 0.25. NDBI > 0 on its own under-detects dense Indian rooftops.
6. Per-ward area statistics, with cloud gaps extrapolated. Colourised NDVI and new-built-up PNG overlays for Leaflet.

City built-up area is ≈200 km² of 474 km² and is essentially stable between 2019 and 2026 (−2.7 %). Mumbai is largely built out. The strongest signals are peripheral expansion (T, R/C) and canopy greening in older wards.

## Growth classes (`backend/app/analytics/growth.py`)

| Class | Rule |
|---|---|
| RAPID_EXPANSION | built-up ≥ +8 %, or ≥ +5 % with vegetation ≤ −5 % |
| DENSIFYING | built-up share ≥ 55 % and (built-up > 0 % or complaint growth ≥ 15 %) |
| GREENING | vegetation ≥ +10 % and built-up ≤ 0 % |
| STABLE | otherwise |

## Infrastructure gaps (`backend/app/gis/infrastructure_gap.py`, norms in `analytics/norms.py`)

| Sector | Required | Existing | Confidence |
|---|---|---|---|
| Water | population × 135 lpcd | ward supply records (synthetic) | DEMO |
| Waste | population × 0.45 kg/day | processing records (synthetic) | DEMO |
| Drainage | rational method Q = C·i·A at 50 mm/h | same at legacy 25 mm/h. Severity comes from DEM low-lying share and flood complaints. | MEDIUM |
| Healthcare | 1 facility / 15,000 | OSM hospitals + clinics | LOW |
| Education | 1 school / 5,000 | OSM schools | LOW |
| Transit | 4 stops / km² built-up | OSM bus stops + 3 × stations | LOW |
| Open space | 10 m² / capita | OSM green land-use area | MEDIUM |

Severity bands on deficit %: ≥ 40 CRITICAL, ≥ 20 HIGH, ≥ 5 MODERATE.

## Hotspots

DBSCAN with the haversine metric on geolocated complaints (API default 600 m, min 8 points, last 12 months), run per category in the seed to assign `cluster_id`.
