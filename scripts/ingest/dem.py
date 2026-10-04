"""Copernicus DEM GLO-30 elevation statistics per BMC ward (via Microsoft Planetary Computer).

Output: backend/data/external/dem_ward_stats.json
  mean / median / p10 elevation (m) and share of ward area below 5 m and 10 m – key flood-exposure inputs
  for a coastal city where much of the island city is reclaimed land near sea level.
"""
import os
import sys

import numpy as np
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from scripts.ingest.common import external_path, load_json, save_json

RES_DEG = 0.0003


def run(refresh: bool = False):
    out = external_path("dem_ward_stats.json")
    if os.path.exists(out) and not refresh:
        print("  [dem] cached")
        return load_json(out)
    try:
        import planetary_computer
        import pystac_client
        import rasterio
        import rasterio.transform
        from rasterio.enums import Resampling
        from rasterio.features import geometry_mask
        from rasterio.merge import merge
        from rasterio.vrt import WarpedVRT
    except ImportError:
        print("  [dem] optional dependencies missing: pip install -r requirements-rs.txt")
        return None

    wards_fc = load_json(external_path("mumbai_wards.geojson"))
    geoms = {f["properties"]["ward_code"]: shape(f["geometry"]) for f in wards_fc["features"]}
    city = unary_union(list(geoms.values()))
    west, south, east, north = city.bounds
    width, height = int(np.ceil((east - west) / RES_DEG)), int(np.ceil((north - south) / RES_DEG))
    transform = rasterio.transform.from_origin(west, north, RES_DEG, RES_DEG)

    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                        modifier=planetary_computer.sign_inplace)
    items = list(catalog.search(collections=["cop-dem-glo-30"], bbox=[west, south, east, north]).items())
    print(f"  [dem] {len(items)} DEM tiles")
    dem = np.full((height, width), np.nan, dtype="float32")
    for it in items:
        with rasterio.open(it.assets["data"].href) as src:
            with WarpedVRT(src, crs="EPSG:4326", transform=transform, width=width, height=height,
                           resampling=Resampling.bilinear, nodata=-32767) as vrt:
                arr = vrt.read(1).astype("float32")
                arr[arr <= -1000] = np.nan
                dem = np.where(np.isnan(dem), arr, dem)

    stats = {}
    for code, g in geoms.items():
        m = ~geometry_mask([mapping(g)], out_shape=(height, width), transform=transform)
        vals = dem[m]
        vals = vals[np.isfinite(vals)]
        if not len(vals):
            continue
        stats[code] = {
            "mean_elevation_m": round(float(vals.mean()), 2),
            "median_elevation_m": round(float(np.median(vals)), 2),
            "p10_elevation_m": round(float(np.percentile(vals, 10)), 2),
            "share_below_5m": round(float((vals < 5).mean()), 4),
            "share_below_10m": round(float((vals < 10).mean()), 4),
        }
    save_json(out, {"source": "Copernicus DEM GLO-30 (ESA), via Microsoft Planetary Computer", "wards": stats})
    print(f"  [dem] stats for {len(stats)} wards")
    return stats


if __name__ == "__main__":
    run(refresh="--refresh" in sys.argv)
