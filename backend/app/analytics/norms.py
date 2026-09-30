"""Planning norms and unit costs used across gap analysis, scenarios and recommendations.

Each constant carries its reference so every derived number is traceable.
"""

NORMS = {
    "water_lpcd": {"value": 135, "unit": "litres/capita/day",
                   "ref": "CPHEEO Manual on Water Supply (1999): 135 lpcd for cities with sewerage"},
    "waste_kg_per_capita": {"value": 0.45, "unit": "kg/capita/day",
                            "ref": "MoHUA SWM Manual (2016): 0.45–0.6 kg/capita/day for metro cities (lower bound)"},
    "primary_health_per_pop": {"value": 15_000, "unit": "persons per primary health facility",
                               "ref": "URDPFI Guidelines (2015), Vol I Table 11.3: dispensary per 15,000 population"},
    "hospital_per_pop": {"value": 100_000, "unit": "persons per hospital",
                         "ref": "URDPFI Guidelines (2015): intermediate hospital (Cat. B) per 1,00,000 population"},
    "school_per_pop": {"value": 5_000, "unit": "persons per school",
                       "ref": "URDPFI Guidelines (2015), Table 11.1: primary school per 5,000 population"},
    "open_space_sqm_per_capita": {"value": 10.0, "unit": "m² per capita",
                                  "ref": "URDPFI Guidelines (2015): 10–12 m² organised open space per capita"},
    "bus_stops_per_sqkm_built": {"value": 4.0, "unit": "stops per km² built-up area",
                                 "ref": "MoHUA bus stop spacing guidance (~500 m): ≈4 stops per km² of urbanised area"},
    "design_rainfall_mm_hr": {"value": 50.0, "unit": "mm/hour",
                              "ref": "BRIMSTOWAD (MCGM, 2006) revised storm-water design intensity for Mumbai"},
    "legacy_rainfall_mm_hr": {"value": 25.0, "unit": "mm/hour",
                              "ref": "Pre-BRIMSTOWAD British-era design intensity of Mumbai's storm-water drains"},
    "runoff_coeff_built": {"value": 0.90, "unit": "", "ref": "Rational method runoff coefficient, dense impervious"},
    "runoff_coeff_green": {"value": 0.25, "unit": "", "ref": "Rational method runoff coefficient, vegetated surfaces"},
    "runoff_coeff_other": {"value": 0.60, "unit": "", "ref": "Rational method runoff coefficient, mixed urban"},
}

# Indicative unit costs (₹ crore) used only to rank options; replace with the municipal schedule of rates.
UNIT_COSTS_CR = {
    "storm_drain_upgrade_per_m3s": {"value": 6.0, "ref": "Indicative; BRIMSTOWAD phase costs ≈ ₹1,200 Cr for ~200 m³/s capacity addition"},
    "water_augmentation_per_mld": {"value": 1.2, "ref": "Indicative bulk treatment + transmission cost per MLD"},
    "waste_processing_per_tpd": {"value": 0.25, "ref": "Indicative integrated processing facility cost per TPD"},
    "primary_health_centre": {"value": 4.0, "ref": "Indicative urban PHC / dispensary construction + equipment"},
    "school": {"value": 6.0, "ref": "Indicative municipal school building"},
    "bus_stop": {"value": 0.08, "ref": "Indicative bus shelter with signage"},
    "open_space_per_ha": {"value": 3.0, "ref": "Indicative park development per hectare (excl. land)"},
    "transit_capacity_pct": {"value": 45.0, "ref": "Indicative cost per 1% city-wide bus fleet capacity increase"},
}

SEVERITY_BANDS = [(40.0, "CRITICAL"), (20.0, "HIGH"), (5.0, "MODERATE")]


def severity_for(deficit_pct: float) -> str:
    for threshold, label in SEVERITY_BANDS:
        if deficit_pct >= threshold:
            return label
    return "LOW"


def norm(key: str) -> float:
    return NORMS[key]["value"]
