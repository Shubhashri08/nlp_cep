# Geospatial Information Systems (GIS) & Remote Sensing

## 1. PostGIS Spatial Architecture
- **Boundary Polygons**: Stored as standard GeoJSON polygons and MultiPolygons.
- **Point-in-Polygon Containment**: Implemented via Shapely `shape(geojson).contains(Point(lon, lat))` to accurately map complaints to ward jurisdictions.
- **Haversine Distance**: Used for high-precision metric calculations on the WGS84 ellipsoid.

## 2. DBSCAN Spatial Hotspot Detection
- Groups geocoded complaints within an adaptive epsilon radius (0.8 - 1.2 km).
- Calculates cluster centroids, bounding radii in meters, point counts, and density scores.
- Ranks hotspots into `HIGH`, `MEDIUM`, and `LOW` severity levels.

## 3. Remote Sensing Spectral Indices
- **NDVI (Normalized Difference Vegetation Index)**: $(NIR - RED) / (NIR + RED)$
- **NDBI (Normalized Difference Built-up Index)**: $(SWIR - NIR) / (SWIR + NIR)$
- **NDWI (Normalized Difference Water Index)**: $(GREEN - NIR) / (GREEN + NIR)$
- Processed from Sentinel-2 MultiSpectral Instrument 10m surface reflectance grids using `rasterio` and `numpy`.
