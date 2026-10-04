"""Spectral index computation and land-cover classification for multispectral imagery (Sentinel-2 / Landsat).

Scene download and compositing lives in scripts/ingest/sentinel.py; this module only holds the maths so
it has no heavy dependencies (rasterio is imported lazily for optional GeoTIFF export).
"""
from typing import Dict, Optional

import numpy as np

# Thresholds commonly used for Sentinel-2 surface reflectance (see docs/gis.md)
NDVI_VEGETATION = 0.30
NDWI_WATER = 0.05
NDBI_BUILT = 0.0
NDVI_BUILT_MAX = 0.20


def _nd(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a.astype("float64")
    b = b.astype("float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    out[~np.isfinite(out)] = np.nan
    return np.clip(out, -1.0, 1.0)


def calculate_spectral_indices(
    nir_band: np.ndarray,
    red_band: np.ndarray,
    swir_band: np.ndarray,
    green_band: np.ndarray,
) -> Dict[str, np.ndarray]:
    """
    NDVI = (NIR − RED) / (NIR + RED)      vegetation
    NDBI = (SWIR − NIR) / (SWIR + NIR)    built-up
    NDWI = (GREEN − NIR) / (GREEN + NIR)  open water (McFeeters 1996)
    Pixels with zero denominator are NaN.
    """
    return {
        "ndvi": _nd(nir_band, red_band),
        "ndbi": _nd(swir_band, nir_band),
        "ndwi": _nd(green_band, nir_band),
    }


def classify_land_cover(ndvi: np.ndarray, ndbi: np.ndarray, ndwi: np.ndarray) -> Dict[str, np.ndarray]:
    """Rule-based land-cover masks. Water takes precedence, then vegetation; built-up (impervious) is the
    remaining low-NDVI surface. NDBI > 0 alone under-detects dense Indian rooftops (tin / tarpaulin / concrete
    mixtures), so NDBI only separates bare soil (high NDBI, NDVI in the sparse range) from impervious cover."""
    finite = np.isfinite(ndvi) & np.isfinite(ndbi) & np.isfinite(ndwi)
    water = finite & (ndwi > NDWI_WATER)
    vegetation = finite & ~water & (ndvi > NDVI_VEGETATION)
    sparse = finite & ~water & ~vegetation
    bare_soil = sparse & (ndbi > 0.12) & (ndvi > 0.15)
    built_up = sparse & ~bare_soil & (ndvi < NDVI_BUILT_MAX + 0.05)
    return {"water": water, "vegetation": vegetation, "built_up": built_up, "bare_soil": bare_soil}


def write_index_geotiff(path: str, indices: Dict[str, np.ndarray], transform, crs: str = "EPSG:4326") -> Optional[str]:
    """Optional export of index rasters as a 3-band GeoTIFF (requires rasterio)."""
    import rasterio

    ndvi = indices["ndvi"]
    with rasterio.open(path, "w", driver="GTiff", height=ndvi.shape[0], width=ndvi.shape[1], count=3,
                       dtype="float32", crs=crs, transform=transform, nodata=np.nan) as dst:
        for i, key in enumerate(("ndvi", "ndbi", "ndwi"), start=1):
            dst.write(indices[key].astype("float32"), i)
            dst.set_band_description(i, key.upper())
    return path
