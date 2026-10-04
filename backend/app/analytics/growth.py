"""Urban growth pattern detection per ward.

Signals:
  * built-up area change and vegetation change between satellite epochs (Sentinel-2 NDBI/NDVI classification)
  * built-up share (density of development) and building footprint density (OSM)
  * complaint volume growth (last 12 vs previous 12 months) as a proxy for service-demand pressure
Classes (thresholds documented in docs/gis.md):
  RAPID_EXPANSION – built-up grew ≥ 8 % over the period, or ≥ 5 % with vegetation loss ≥ 5 %
  DENSIFYING      – already ≥ 55 % built-up and still growing (> 0 %) or complaint pressure rising ≥ 15 %
  GREENING        – vegetation grew ≥ 10 % and built-up did not grow
  STABLE          – everything else
"""
from typing import Any, Dict, List, Optional


def pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    return round(100.0 * (new - old) / old, 2)


def classify_growth(built_change_pct: Optional[float], veg_change_pct: Optional[float],
                    built_share_pct: Optional[float], complaint_growth_pct: Optional[float]) -> str:
    b = built_change_pct or 0.0
    v = veg_change_pct or 0.0
    share = built_share_pct or 0.0
    cg = complaint_growth_pct or 0.0
    if b >= 8.0 or (b >= 5.0 and v <= -5.0):
        return "RAPID_EXPANSION"
    if share >= 55.0 and (b > 0.0 or cg >= 15.0):
        return "DENSIFYING"
    if v >= 10.0 and b <= 0.0:
        return "GREENING"
    return "STABLE"


def ward_growth_profile(ward_area: float, epochs: Dict[str, Dict[str, Any]], complaint_growth_pct: Optional[float],
                        population_cagr_pct: float) -> Dict[str, Any]:
    """epochs: {year: {built_up_sq_km, vegetation_sq_km, water_sq_km, mean_ndvi, mean_ndbi}} for one ward."""
    years = sorted(epochs)
    first, last = epochs[years[0]], epochs[years[-1]]
    built_change = pct_change(last["built_up_sq_km"], first["built_up_sq_km"])
    veg_change = pct_change(last["vegetation_sq_km"], first["vegetation_sq_km"])
    built_share = 100.0 * last["built_up_sq_km"] / ward_area if ward_area else None
    span = int(years[-1]) - int(years[0]) if len(years) > 1 else 1
    annual_built = ((last["built_up_sq_km"] / first["built_up_sq_km"]) ** (1 / span) - 1) * 100 if first["built_up_sq_km"] and span else 0.0
    return {
        "period": f"{years[0]}–{years[-1]}",
        "start_year": int(years[0]),
        "end_year": int(years[-1]),
        "built_up_start_sq_km": first["built_up_sq_km"],
        "built_up_end_sq_km": last["built_up_sq_km"],
        "built_up_change_sq_km": round(last["built_up_sq_km"] - first["built_up_sq_km"], 3),
        "built_up_change_pct": built_change,
        "built_up_share_pct": round(built_share, 1) if built_share is not None else None,
        "vegetation_change_sq_km": round(last["vegetation_sq_km"] - first["vegetation_sq_km"], 3),
        "vegetation_change_pct": veg_change,
        "water_change_sq_km": round(last["water_sq_km"] - first["water_sq_km"], 3),
        "ndvi_change": round((last.get("mean_ndvi") or 0) - (first.get("mean_ndvi") or 0), 4),
        "ndbi_change": round((last.get("mean_ndbi") or 0) - (first.get("mean_ndbi") or 0), 4),
        "annual_built_up_growth_pct": round(annual_built, 2),
        "population_cagr_pct": round(population_cagr_pct, 3),
        "complaint_growth_pct": complaint_growth_pct,
        "growth_class": classify_growth(built_change, veg_change, built_share, complaint_growth_pct),
    }


def summarize_city(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not profiles:
        return {}
    start = sum(p["built_up_start_sq_km"] for p in profiles)
    end = sum(p["built_up_end_sq_km"] for p in profiles)
    veg = sum(p["vegetation_change_sq_km"] for p in profiles)
    counts: Dict[str, int] = {}
    for p in profiles:
        counts[p["growth_class"]] = counts.get(p["growth_class"], 0) + 1
    fastest = sorted(profiles, key=lambda p: -(p["built_up_change_pct"] or -999))[:3]
    return {
        "period": profiles[0]["period"],
        "built_up_start_sq_km": round(start, 2),
        "built_up_end_sq_km": round(end, 2),
        "built_up_expansion_pct": pct_change(end, start),
        "vegetation_change_sq_km": round(veg, 2),
        "class_counts": counts,
        "fastest_growing_wards": [{"ward_code": p.get("ward_code"), "built_up_change_pct": p["built_up_change_pct"]} for p in fastest],
    }
