# Data sources

| Dataset | Provider / licence | Fetcher | Output (committed) |
|---|---|---|---|
| BMC ward boundaries (24, admin_level 10) | OpenStreetMap, ODbL | `scripts/ingest/osm_boundaries.py` | `mumbai_wards.geojson` |
| Census 2011 PCA by census ward, mapped to BMC wards | ORGI via data.opencity.in, public domain | `scripts/ingest/census.py` | `census2011_mumbai_wards.csv` |
| Amenities, transit stops, utilities (~5,200) | OSM | `osm_features.build_assets` | `osm_assets.json` |
| Place-name gazetteer (~3,900 in-city names) | OSM | `osm_features.build_gazetteer` | `osm_gazetteer.json` |
| Road km by class, building counts per ward | OSM (Overpass `make stat`) | `osm_features.build_ward_stats` | `osm_ward_stats.json` |
| Land-use shares per ward | OSM landuse / leisure / natural polygons | `osm_features.build_landuse` | `osm_landuse.json` |
| Sentinel-2 L2A composites 2019 / 2022 / 2026 | Copernicus via Microsoft Planetary Computer | `scripts/ingest/sentinel.py` | `sentinel/sentinel_indices.json`, `overlay_*.png` |
| Elevation | Copernicus DEM GLO-30 | `scripts/ingest/dem.py` | `dem_ward_stats.json` |

Run everything with `python -m scripts.ingest.fetch_all [--refresh]`. Raw API responses are cached under `external/osm`, `external/census` and `external/sentinel/cache`; these are git-ignored.

## Synthetic (demonstration) data

No open, geolocated, ward-level Mumbai datasets exist for the following, so `scripts/synthetic.py` generates them with a fixed seed:

- **Citizen complaints.** Phrase inventory separate from the classifier corpus. Locations are real OSM places inside each ward. Category rates are driven by real attributes: DEM low-lying share for flooding and drainage, Census literacy for water supply, density for waste, OSM facility gaps for health and transit.
- **Monthly water / waste / ridership.** Census population × CPHEEO / MoHUA norms × Mumbai CMP trip rates, with seasonality.
- **Ward water-supply and waste-processing levels.** Equity-weighted by literacy (a proxy for informal settlements).
- **Monthly rainfall / PM2.5.** IMD Santacruz normals and typical SAFAR / CPCB seasonality.

Replace them with real feeds through `POST /api/v1/data-sources/import` (CSV / GeoJSON), then use the recompute and retrain endpoints.

## Known limitations

- OSM facility coverage (schools, bus stops) is incomplete. These gaps are flagged `data_confidence: LOW`.
- Ward-level 2001 Census data is not open, so population is projected with the city-wide 2001–11 CAGR (≈0.38 %/yr).
- The DEM is a surface model (it includes buildings). Low-lying shares are indicative.
