from typing import List, Dict, Any

def summarize_single_complaint(text: str, category: str, entities: List[Dict[str, Any]]) -> str:
    """Generates a concise, structured 1-sentence summary of an individual complaint."""
    locs = [e["text"] for e in entities if e.get("label") in ("LOCATION_LANDMARK", "ROAD", "WARD")]
    infra = [e["text"] for e in entities if "INFRA" in e.get("label", "")]
    
    loc_str = f" at {locs[0]}" if locs else ""
    infra_str = f" concerning {infra[0]}" if infra else ""
    
    cat_friendly = category.replace("_", " ").title()
    return f"{cat_friendly} issue reported{loc_str}{infra_str}: {text[:140]}..." if len(text) > 140 else f"{cat_friendly} issue reported{loc_str}{infra_str}: {text}"

def summarize_complaint_cluster(
    records: List[Dict[str, Any]], 
    ward_name: str, 
    category: str
) -> Dict[str, Any]:
    """
    Synthesizes a traceable cluster summary from multiple actual complaints in a ward/zone.
    Maintains full traceability back to source IDs.
    """
    total = len(records)
    if total == 0:
        return {
            "summary": f"No complaints recorded for {category} in {ward_name}.",
            "source_record_ids": [],
            "key_locations": [],
            "cluster_count": 0
        }
        
    locations_count: Dict[str, int] = {}
    record_ids = []
    
    for r in records:
        record_ids.append(r.get("id"))
        if r.get("address"):
            addr = r["address"]
            locations_count[addr] = locations_count.get(addr, 0) + 1
        elif r.get("raw_location_text"):
            loc = r["raw_location_text"]
            locations_count[loc] = locations_count.get(loc, 0) + 1
            
    top_locs = sorted(locations_count.items(), key=lambda x: x[1], reverse=True)[:3]
    loc_summary = ", ".join([f"{l[0]} ({l[1]} reports)" for l in top_locs]) if top_locs else f"{ward_name} jurisdiction"
    
    cat_name = category.replace("_", " ").title()
    summary_text = (
        f"A total of {total} {cat_name} grievances were identified in {ward_name}. "
        f"Reports are heavily concentrated around {loc_summary}. "
        f"Citizens predominantly highlight recurring service disruptions and infrastructure degradation."
    )
    
    return {
        "summary": summary_text,
        "source_record_ids": record_ids,
        "key_locations": [l[0] for l in top_locs],
        "cluster_count": total
    }
