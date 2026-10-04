"""Infrastructure gap analysis: compares norm-based requirements against observed supply for each ward.

Inputs come from the database (population: Census; facilities: OSM; land cover: Sentinel-2 / OSM;
water & waste service records: synthetic where no open ward-level data exists). Every gap row carries the
norm reference and the provenance of its inputs.
"""
from typing import Any, Dict, List, Optional

from backend.app.analytics.norms import NORMS, norm, severity_for


def _gap(ward_id, sector, required, existing, unit, norm_key, complaints, area, evidence, invert=False):
    required = float(required)
    existing = float(existing)
    deficit = max(0.0, required - existing)
    pct = round(100.0 * deficit / required, 1) if required > 0 else 0.0
    return {
        "ward_id": ward_id,
        "sector": sector,
        "required_capacity": round(required, 2),
        "existing_capacity": round(existing, 2),
        "deficit_amount": round(deficit, 2),
        "deficit_percentage": pct,
        "unit": unit,
        "severity": severity_for(pct),
        "complaint_density": round(complaints / max(0.1, area), 3),
        "norm_reference": NORMS[norm_key]["ref"],
        "evidence": evidence,
    }


def compute_ward_infrastructure_gaps(
    ward_id: int,
    population: int,
    area_sq_km: float,
    asset_counts: Dict[str, int],
    complaints_by_category: Dict[str, int],
    built_up_sq_km: Optional[float] = None,
    green_share_pct: Optional[float] = None,
    water_supplied_mld: Optional[float] = None,
    waste_processed_tpd: Optional[float] = None,
    land_cover_source: str = "SENTINEL",
    low_lying_share: Optional[float] = None,
) -> List[Dict[str, Any]]:
    c = complaints_by_category
    gaps: List[Dict[str, Any]] = []

    # Healthcare – primary care facilities (hospitals + clinics / dispensaries mapped in OSM)
    req = population / norm("primary_health_per_pop")
    have = asset_counts.get("HEALTHCARE", 0)
    gaps.append(_gap(ward_id, "Healthcare Capacity", req, have, "primary health facilities", "primary_health_per_pop",
                     c.get("HEALTHCARE", 0), area_sq_km,
                     {"population": population, "facilities_osm": have, "provenance": ["CENSUS", "OSM"], "data_confidence": "LOW",
                      "caveat": "Counts only facilities mapped in OSM (includes private clinics); verify against the BMC health-post register"}))

    # Education
    req = population / norm("school_per_pop")
    have = asset_counts.get("EDUCATION_SCHOOL", asset_counts.get("EDUCATION", 0))
    gaps.append(_gap(ward_id, "Education", req, have, "schools", "school_per_pop", c.get("EDUCATION", 0), area_sq_km,
                     {"population": population, "schools_osm": have, "provenance": ["CENSUS", "OSM"], "data_confidence": "LOW",
                      "caveat": "OSM maps only a fraction of Mumbai's schools; verify against the UDISE+ school register before acting"}))

    # Public transit access – bus stops relative to built-up area
    built = built_up_sq_km if built_up_sq_km is not None else area_sq_km * 0.6
    req = built * norm("bus_stops_per_sqkm_built")
    have = asset_counts.get("BUS_STOP", 0) + 3 * (asset_counts.get("RAIL_STATION", 0) + asset_counts.get("METRO_STATION", 0))
    gaps.append(_gap(ward_id, "Public Transit Access", req, have, "stop-equivalents (rail/metro station = 3)",
                     "bus_stops_per_sqkm_built", c.get("PUBLIC_TRANSPORT", 0) + c.get("TRAFFIC", 0), area_sq_km,
                     {"built_up_sq_km": round(built, 2), "bus_stops_osm": asset_counts.get("BUS_STOP", 0),
                      "rail_stations": asset_counts.get("RAIL_STATION", 0), "metro_stations": asset_counts.get("METRO_STATION", 0),
                      "provenance": [land_cover_source, "OSM"], "data_confidence": "LOW",
                      "caveat": "OSM bus-stop coverage is incomplete; verify against the BEST stop inventory"}))

    # Open space per capita
    if green_share_pct is not None:
        green_sqm = area_sq_km * 1e6 * green_share_pct / 100.0
        req = population * norm("open_space_sqm_per_capita") / 1e4  # hectares
        gaps.append(_gap(ward_id, "Open Space", req, green_sqm / 1e4, "hectares", "open_space_sqm_per_capita",
                         c.get("PARKS", 0), area_sq_km,
                         {"green_share_pct": round(green_share_pct, 2),
                          "open_space_sqm_per_capita": round(green_sqm / max(1, population), 2),
                          "provenance": ["OSM", "CENSUS"], "data_confidence": "MEDIUM"}))

    # Storm-water drainage – rational method Q = C·i·A, legacy (25 mm/h) vs BRIMSTOWAD (50 mm/h) design
    green = (green_share_pct or 0.0) / 100.0 * area_sq_km
    built_c = min(area_sq_km, built)
    other = max(0.0, area_sq_km - built_c - green)
    c_eff = (norm("runoff_coeff_built") * built_c + norm("runoff_coeff_green") * green + norm("runoff_coeff_other") * other) / max(0.01, area_sq_km)
    area_m2 = area_sq_km * 1e6
    q_req = c_eff * (norm("design_rainfall_mm_hr") / 1000 / 3600) * area_m2
    q_have = c_eff * (norm("legacy_rainfall_mm_hr") / 1000 / 3600) * area_m2
    gaps.append(_gap(ward_id, "Drainage & Storm Water", q_req, q_have, "m³/s peak runoff capacity", "design_rainfall_mm_hr",
                     c.get("FLOODING", 0) + c.get("DRAINAGE", 0), area_sq_km,
                     {"runoff_coefficient": round(c_eff, 3), "built_up_sq_km": round(built_c, 2),
                      "provenance": [land_cover_source, "DERIVED"], "data_confidence": "MEDIUM",
                      "low_lying_share_below_5m": low_lying_share,
                      "caveat": "Assumes legacy 25 mm/h network; replace with ward drain inventory when available"}))
    # The capacity ratio is uniform by construction, so severity reflects exposure: low-lying land (DEM) and
    # flood complaint density decide how urgent the upgrade is.
    drain = gaps[-1]
    flood_density = drain["complaint_density"]
    if low_lying_share is not None:
        if low_lying_share >= 0.22 or flood_density >= 2.0:
            drain["severity"] = "CRITICAL"
        elif low_lying_share >= 0.12 or flood_density >= 1.0:
            drain["severity"] = "HIGH"
        else:
            drain["severity"] = "MODERATE"

    # Water supply (service records)
    if water_supplied_mld is not None:
        req = population * norm("water_lpcd") / 1e6
        gaps.append(_gap(ward_id, "Water Supply", req, water_supplied_mld, "MLD", "water_lpcd",
                         c.get("WATER_SUPPLY", 0), area_sq_km,
                         {"population": population, "supplied_mld": round(water_supplied_mld, 2),
                          "provenance": ["CENSUS", "SYNTHETIC"], "data_confidence": "DEMO"}))

    # Solid waste processing (service records)
    if waste_processed_tpd is not None:
        req = population * norm("waste_kg_per_capita") / 1000
        gaps.append(_gap(ward_id, "Waste Management", req, waste_processed_tpd, "TPD", "waste_kg_per_capita",
                         c.get("WASTE_MANAGEMENT", 0), area_sq_km,
                         {"population": population, "processed_tpd": round(waste_processed_tpd, 2),
                          "provenance": ["CENSUS", "SYNTHETIC"], "data_confidence": "DEMO"}))
    return gaps
