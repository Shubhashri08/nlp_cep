from typing import List, Dict, Any

# Urban Planning Benchmark Norms (URDPFI Guidelines - Govt of India)
# - Water: 135-150 Liters Per Capita per Day (LPCD) -> MLD = (Pop * 135) / 1,000,000
# - Solid Waste: 0.45 kg per capita per day -> Metric Tons / Day = (Pop * 0.45) / 1,000
# - Healthcare: 1 Primary Health Center / 50,000 pop, 1 Hospital bed / 250 pop
# - Education: 1 Primary School / 4,000 pop
# - Drainage: Storm drain discharge capacity vs peak rainfall runoff coefficient

def compute_ward_infrastructure_gaps(
    ward_id: int,
    ward_name: str,
    population: int,
    area_sq_km: float,
    assets: List[Dict[str, Any]],
    complaints_count_by_cat: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Computes rigorous, traceable infrastructure gaps comparing real demand vs existing capacity.
    """
    gaps: List[Dict[str, Any]] = []
    
    # 1. WATER SUPPLY GAP
    required_water_mld = round((population * 135) / 1_000_000, 2)
    existing_water_mld = sum(
        a["capacity"] for a in assets 
        if a.get("asset_type") == "WATER_SUPPLY" and a.get("capacity_unit") == "MLD"
    )
    water_deficit = round(max(0.0, required_water_mld - existing_water_mld), 2)
    water_deficit_pct = round((water_deficit / max(1.0, required_water_mld)) * 100, 1)
    water_complaints = complaints_count_by_cat.get("WATER_SUPPLY", 0)
    
    if water_deficit > 0 or water_complaints > 5:
        severity = "CRITICAL" if water_deficit_pct > 30 else ("HIGH" if water_deficit_pct > 15 else "MODERATE")
        gaps.append({
            "ward_id": ward_id,
            "ward_name": ward_name,
            "sector": "Water Supply",
            "required_capacity": required_water_mld,
            "existing_capacity": round(existing_water_mld, 2),
            "deficit_amount": water_deficit,
            "deficit_percentage": water_deficit_pct,
            "unit": "MLD (Million Liters/Day)",
            "severity": severity,
            "complaint_density": round(water_complaints / max(0.1, area_sq_km), 2),
            "norm_reference": "URDPFI standard: 135 LPCD potable water benchmark"
        })

    # 2. SOLID WASTE MANAGEMENT GAP
    required_waste_tpd = round((population * 0.45) / 1_000, 2)  # Metric tons per day
    existing_waste_tpd = sum(
        a["capacity"] for a in assets 
        if a.get("asset_type") == "WASTE_MANAGEMENT" and a.get("capacity_unit") in ("tons/day", "TPD")
    )
    waste_deficit = round(max(0.0, required_waste_tpd - existing_waste_tpd), 2)
    waste_deficit_pct = round((waste_deficit / max(1.0, required_waste_tpd)) * 100, 1)
    waste_complaints = complaints_count_by_cat.get("WASTE_MANAGEMENT", 0)
    
    if waste_deficit > 0 or waste_complaints > 5:
        severity = "CRITICAL" if waste_deficit_pct > 25 else ("HIGH" if waste_deficit_pct > 10 else "MODERATE")
        gaps.append({
            "ward_id": ward_id,
            "ward_name": ward_name,
            "sector": "Waste Management",
            "required_capacity": required_waste_tpd,
            "existing_capacity": round(existing_waste_tpd, 2),
            "deficit_amount": waste_deficit,
            "deficit_percentage": waste_deficit_pct,
            "unit": "TPD (Tons Per Day)",
            "severity": severity,
            "complaint_density": round(waste_complaints / max(0.1, area_sq_km), 2),
            "norm_reference": "MoHUA / SWM Rules: 0.45 kg/capita/day municipal solid waste"
        })

    # 3. DRAINAGE & FLOOD RESILIENCE GAP
    flood_complaints = complaints_count_by_cat.get("FLOODING", 0) + complaints_count_by_cat.get("DRAINAGE", 0)
    existing_drain_km = sum(
        a["capacity"] for a in assets 
        if a.get("asset_type") == "DRAINAGE" and a.get("capacity_unit") == "km"
    )
    recommended_drain_km = round(area_sq_km * 4.5, 2)  # Benchmark: 4.5 km storm network per sq km
    drain_deficit = round(max(0.0, recommended_drain_km - existing_drain_km), 2)
    drain_deficit_pct = round((drain_deficit / max(1.0, recommended_drain_km)) * 100, 1)
    
    if drain_deficit > 0 or flood_complaints > 3:
        severity = "CRITICAL" if flood_complaints >= 8 or drain_deficit_pct > 40 else ("HIGH" if drain_deficit_pct > 20 else "MODERATE")
        gaps.append({
            "ward_id": ward_id,
            "ward_name": ward_name,
            "sector": "Drainage & Storm Water",
            "required_capacity": recommended_drain_km,
            "existing_capacity": round(existing_drain_km, 2),
            "deficit_amount": drain_deficit,
            "deficit_percentage": drain_deficit_pct,
            "unit": "km of covered network",
            "severity": severity,
            "complaint_density": round(flood_complaints / max(0.1, area_sq_km), 2),
            "norm_reference": "CPHEEO Storm Drainage Manual: minimum 4.5 km primary/secondary drains per km²"
        })

    # 4. HEALTHCARE INFRASTRUCTURE GAP
    required_beds = int(population / 250)
    existing_beds = int(sum(
        a["capacity"] for a in assets 
        if a.get("asset_type") == "HEALTHCARE" and a.get("capacity_unit") == "beds"
    ))
    bed_deficit = max(0, required_beds - existing_beds)
    bed_deficit_pct = round((bed_deficit / max(1, required_beds)) * 100, 1)
    health_complaints = complaints_count_by_cat.get("HEALTHCARE", 0)
    
    if bed_deficit > 0:
        severity = "CRITICAL" if bed_deficit_pct > 40 else ("HIGH" if bed_deficit_pct > 20 else "MODERATE")
        gaps.append({
            "ward_id": ward_id,
            "ward_name": ward_name,
            "sector": "Healthcare Capacity",
            "required_capacity": float(required_beds),
            "existing_capacity": float(existing_beds),
            "deficit_amount": float(bed_deficit),
            "deficit_percentage": bed_deficit_pct,
            "unit": "Hospital beds",
            "severity": severity,
            "complaint_density": round(health_complaints / max(0.1, area_sq_km), 2),
            "norm_reference": "WHO / IPHS Benchmark: 4 beds per 1,000 population (1:250)"
        })

    return gaps
