"""Real Sentinel-2 L2A remote sensing for Greater Mumbai via Microsoft Planetary Computer (anonymous STAC).

For each epoch (dry-season window, low cloud cover) we:
  1. search sentinel-2-l2a scenes intersecting the city,
  2. read B03 (green), B04 (red), B08 (NIR), B11 (SWIR-1) and SCL resampled onto a common EPSG:4326 grid,
  3. mask clouds / shadows with the Scene Classification Layer, build a per-pixel median composite,
  4. compute NDVI, NDBI, NDWI (backend/app/gis/remote_sensing.calculate_spectral_indices),
  5. aggregate mean indices and built-up / vegetation / water areas per BMC ward.

Outputs (backend/data/external/sentinel/):
  sentinel_indices.json          – per-epoch city + per-ward statistics (committed)
  overlay_<epoch>_ndvi.png       – colourised NDVI overlays for the web map
  overlay_builtup_change.png     – pixels that became built-up between the first and last epoch
Requires: pip install -r requirements-rs.txt
"""
import json
import os
import sys
from typing import Dict, List

import numpy as np
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from backend.app.gis.remote_sensing import calculate_spectral_indices, classify_land_cover
from scripts.ingest.common import external_path, load_json, save_json

# Same dry-season window each year so phenology and haze are comparable
EPOCHS = {
    "2019": "2019-01-01/2019-02-28",
    "2022": "2022-01-01/2022-02-28",
    "2026": "2026-01-01/2026-02-28",
}
SCENES_PER_TILE = 3
RES_DEG = 0.0003  # ~33 m grid; enough for ward-level statistics and fast to download
SCL_INVALID = {0, 1, 3, 8, 9, 10, 11}  # no data, saturated, cloud shadow, cloud med/high, cirrus, snow


def _grid(bounds):
    import rasterio.transform
    west, south, east, north = bounds
    width = int(np.ceil((east - west) / RES_DEG))
    height = int(np.ceil((north - south) / RES_DEG))
    transform = rasterio.transform.from_origin(west, north, RES_DEG, RES_DEG)
    return transform, width, height


def _read_band(href: str, transform, width, height, resampling):
    import rasterio
    from rasterio.vrt import WarpedVRT
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs="EPSG:4326", transform=transform, width=width, height=height,
                       resampling=resampling, nodata=0) as vrt:
            return vrt.read(1).astype("float32")


def _composite(items, transform, width, height) -> Dict[str, np.ndarray]:
    import planetary_computer
    from rasterio.enums import Resampling

    stacks = {b: [] for b in ("green", "red", "nir", "swir")}
    for item in items:
        item = planetary_computer.sign(item)
        baseline = float(item.properties.get("s2:processing_baseline", "0") or 0)
        offset = 1000.0 if baseline >= 4.0 else 0.0
        print(f"    reading {item.id} (cloud {item.properties.get('eo:cloud_cover'):.1f}%, baseline {baseline})")
        scl = _read_band(item.assets["SCL"].href, transform, width, height, Resampling.nearest)
        valid = ~np.isin(scl.astype(int), list(SCL_INVALID))
        for band, key in (("green", "B03"), ("red", "B04"), ("nir", "B08"), ("swir", "B11")):
            arr = _read_band(item.assets[key].href, transform, width, height, Resampling.bilinear)
            refl = (arr - offset) / 10000.0
            refl[(~valid) | (arr == 0)] = np.nan
            stacks[band].append(refl)
    with np.errstate(all="ignore"):
        return {b: np.nanmedian(np.stack(v), axis=0) for b, v in stacks.items()}


def _normalize_to_reference(comp, ref, city_mask, max_samples: int = 200_000):
    """Relative radiometric normalisation (Schott et al. 1988): per-band linear regression onto the reference
    epoch fitted on pseudo-invariant features – pixels whose NDVI percentile rank is (nearly) unchanged.
    Removes epoch-wide shifts (haze, processing baseline, sun angle) while preserving local change."""
    with np.errstate(all="ignore"):
        ndvi_c = (comp["nir"] - comp["red"]) / (comp["nir"] + comp["red"])
        ndvi_r = (ref["nir"] - ref["red"]) / (ref["nir"] + ref["red"])
    valid = city_mask & np.isfinite(ndvi_c) & np.isfinite(ndvi_r)
    for b in comp:
        valid &= np.isfinite(comp[b]) & np.isfinite(ref[b])
    vc, vr = ndvi_c[valid], ndvi_r[valid]
    rank_c = np.argsort(np.argsort(vc)) / max(1, len(vc) - 1)
    rank_r = np.argsort(np.argsort(vr)) / max(1, len(vr) - 1)
    pif = np.abs(rank_c - rank_r) < 0.01
    rng = np.random.default_rng(0)
    pif_idx = np.flatnonzero(pif)
    if len(pif_idx) > max_samples:
        pif_idx = rng.choice(pif_idx, max_samples, replace=False)
    fit = {"pif_pixels": int(pif.sum())}
    out = {}
    for b in comp:
        x = comp[b][valid][pif_idx]
        y = ref[b][valid][pif_idx]
        gain, offset = np.polyfit(x, y, 1)
        out[b] = comp[b] * gain + offset
        fit[b] = {"gain": round(float(gain), 4), "offset": round(float(offset), 4)}
    return out, fit


def _colourise_ndvi(ndvi: np.ndarray, city_mask: np.ndarray) -> np.ndarray:
    # Pearl -> Buff -> green ramp for vegetation, transparent outside the city / no data
    rgba = np.zeros(ndvi.shape + (4,), dtype=np.uint8)
    v = np.clip((ndvi + 0.1) / 0.8, 0, 1)
    low = np.array([138, 59, 8])      # citrine brown (bare / built)
    mid = np.array([243, 213, 141])   # buff
    high = np.array([46, 125, 50])    # vegetation green
    t = v[..., None]
    col = np.where(t < 0.5, low + (mid - low) * (t / 0.5), mid + (high - mid) * ((t - 0.5) / 0.5))
    rgba[..., :3] = np.nan_to_num(col).astype(np.uint8)
    rgba[..., 3] = np.where(city_mask & ~np.isnan(ndvi), 170, 0)
    return rgba


def _write_png(path: str, rgba: np.ndarray):
    import rasterio
    h, w, _ = rgba.shape
    with rasterio.open(path, "w", driver="PNG", width=w, height=h, count=4, dtype="uint8") as dst:
        for i in range(4):
            dst.write(rgba[..., i], i + 1)


def run(refresh: bool = False, refresh_download: bool = False):
    try:
        import pystac_client
        import planetary_computer  # noqa: F401
        from rasterio.features import geometry_mask
    except ImportError:
        print("  [sentinel] optional dependencies missing: pip install -r requirements-rs.txt")
        return None

    out_path = external_path("sentinel", "sentinel_indices.json")
    if os.path.exists(out_path) and not refresh:
        print("  [sentinel] cached results found; use --refresh to recompute")
        return load_json(out_path)

    wards_fc = load_json(external_path("mumbai_wards.geojson"))
    ward_geoms = {f["properties"]["ward_code"]: shape(f["geometry"]) for f in wards_fc["features"]}
    city = unary_union(list(ward_geoms.values()))
    bounds = city.bounds  # (minx, miny, maxx, maxy)
    transform, width, height = _grid(bounds)
    lat_rows = bounds[3] - (np.arange(height) + 0.5) * RES_DEG
    pixel_km2 = (RES_DEG * 111.320 * np.cos(np.radians(lat_rows)))[:, None] * (RES_DEG * 110.574)
    pixel_km2 = np.broadcast_to(pixel_km2, (height, width))

    city_mask = ~geometry_mask([mapping(city)], out_shape=(height, width), transform=transform)
    ward_masks = {c: ~geometry_mask([mapping(g)], out_shape=(height, width), transform=transform)
                  for c, g in ward_geoms.items()}

    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    results = {"grid_resolution_deg": RES_DEG, "epochs": {}}
    classes_by_epoch = {}
    reference = None
    for epoch, dt in EPOCHS.items():
        search = catalog.search(collections=["sentinel-2-l2a"], bbox=list(bounds), datetime=dt,
                                query={"eo:cloud_cover": {"lt": 10}}, sortby=[{"field": "eo:cloud_cover", "direction": "asc"}],
                                max_items=40)
        items = list(search.items())
        # Keep the clearest scenes, but make sure every MGRS tile covering the city is represented
        by_tile: Dict[str, List] = {}
        for it in items:
            by_tile.setdefault(it.properties.get("s2:mgrs_tile", "?"), []).append(it)
        chosen = []
        for tile_items in by_tile.values():
            dates = set()
            for it in tile_items:  # already sorted by cloud cover
                d = it.properties["datetime"][:10]
                if d not in dates:
                    dates.add(d)
                    chosen.append(it)
                if len(dates) >= SCENES_PER_TILE:
                    break
        if not chosen:
            print(f"  [sentinel] no scenes for {epoch}")
            continue
        print(f"  [sentinel] epoch {epoch}: {len(chosen)} scenes across tiles {sorted(by_tile)}")
        cache = external_path("sentinel", "cache", f"composite_{epoch}.npz")
        if os.path.exists(cache) and not refresh_download:
            comp = dict(np.load(cache))
            print(f"    using cached composite {cache}")
        else:
            comp = _composite(chosen, transform, width, height)
            np.savez_compressed(cache, **comp)
        if reference is None:
            reference = comp
        else:
            comp, fit = _normalize_to_reference(comp, reference, city_mask)
            print(f"    PIF radiometric normalisation: {fit}")
        idx = calculate_spectral_indices(comp["nir"], comp["red"], comp["swir"], comp["green"])
        classes = classify_land_cover(idx["ndvi"], idx["ndbi"], idx["ndwi"])
        classes_by_epoch[epoch] = classes

        def _stats(mask):
            valid = mask & ~np.isnan(idx["ndvi"])
            area = float(pixel_km2[mask].sum())
            observed = float(pixel_km2[valid].sum())
            scale = area / observed if observed else 0.0  # extrapolate class areas to cloud-masked gaps
            return {
                "area_sq_km": round(area, 3),
                "valid_fraction": round(observed / area, 3) if area else 0.0,
                "mean_ndvi": round(float(np.nanmean(idx["ndvi"][valid])), 4) if valid.any() else None,
                "mean_ndbi": round(float(np.nanmean(idx["ndbi"][valid])), 4) if valid.any() else None,
                "mean_ndwi": round(float(np.nanmean(idx["ndwi"][valid])), 4) if valid.any() else None,
                "built_up_sq_km": round(float(pixel_km2[valid & classes["built_up"]].sum()) * scale, 3),
                "vegetation_sq_km": round(float(pixel_km2[valid & classes["vegetation"]].sum()) * scale, 3),
                "water_sq_km": round(float(pixel_km2[valid & classes["water"]].sum()) * scale, 3),
            }

        results["epochs"][epoch] = {
            "date_range": dt,
            "scenes": [{"id": it.id, "date": it.properties["datetime"][:10],
                        "cloud_cover": it.properties.get("eo:cloud_cover")} for it in chosen],
            "city": _stats(city_mask),
            "wards": {c: _stats(m) for c, m in ward_masks.items()},
        }
        _write_png(external_path("sentinel", f"overlay_{epoch}_ndvi.png"), _colourise_ndvi(idx["ndvi"], city_mask))

    epochs = sorted(classes_by_epoch)
    if len(epochs) >= 2:
        first, last = classes_by_epoch[epochs[0]]["built_up"], classes_by_epoch[epochs[-1]]["built_up"]
        new_built = (~first) & last & city_mask
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[new_built] = [229, 157, 44, 220]  # marigold = newly built-up
        _write_png(external_path("sentinel", "overlay_builtup_change.png"), rgba)
    # Leaflet expects [[south, west], [north, east]]
    results["overlay_bounds"] = [[bounds[3] - height * RES_DEG, bounds[0]], [bounds[3], bounds[0] + width * RES_DEG]]
    save_json(out_path, results)
    print(f"  [sentinel] wrote {out_path}")
    return results


if __name__ == "__main__":
    # --refresh recomputes statistics (re-using cached composites); --redownload fetches scenes again
    run(refresh="--refresh" in sys.argv or "--redownload" in sys.argv, refresh_download="--redownload" in sys.argv)
