# Real Data Sources and Provenance

## 1. Authoritative Datasets Used

| Dataset Name | Source Provider | Format | License | Geographic Scope |
|---|---|---|---|---|
| Municipal Ward Administrative Boundaries | MCGM / Survey of India | GeoJSON Polygons | GODL-India | Metropolitan Mumbai (Wards A to T) |
| Citizen Grievance Redressal Records | MCGM 24x7 Portal / data.gov.in | CSV / REST API | GODL-India | Citywide Citizen Feedback |
| Sentinel-2 MultiSpectral Optical Bands | ESA Copernicus / ISRO Bhuvan | GeoTIFF 10m | Open Access Copernicus | 100 km² Metropolitan Coastal Corridor |
| Census Demographics & Household Stats | Census Commissioner of India | Tabular / CSV | GODL-India | Ward Demographics (2021/2026 Projections) |
| Air Quality Monitoring Network | CPCB / MPCB Stations | Real-time Sensors | Open Government Data | PM2.5, PM10, AQI Index |
| OpenStreetMap Road Networks & Transit | OpenStreetMap Contributors | Vector PBF / Overpass | ODbL | Road density & transit stops |

## 2. Ingestion & Quality Validation Pipeline
Every uploaded or ingested dataset undergoes:
1. Schema & Data Type Enforcement
2. Coordinate System Validation (WGS84 EPSG:4326)
3. Duplicate Detection & De-duplication
4. Missing-Value Imputation / Rejection
5. Outlier Detection
6. Data Quality Score calculation across Completeness, Consistency, Freshness, and Geographic Validity.
