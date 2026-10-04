import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.cluster import DBSCAN
from backend.app.gis.spatial_ops import calculate_haversine_distance_km

def detect_issue_hotspots(
    complaints: List[Dict[str, Any]], 
    eps_km: float = 0.8,
    min_samples: int = 2,
    return_members: bool = False,
) -> List[Dict[str, Any]]:
    """
    Performs spatial density clustering (DBSCAN) on geolocated citizen requests.
    Returns structured hotspot clusters with center coordinates, radius, point counts,
    density scores, severity levels, and sample complaint texts.
    """
    valid_pts = [
        c for c in complaints 
        if c.get("latitude") is not None and c.get("longitude") is not None
    ]
    
    if len(valid_pts) < min_samples:
        return []
        
    coords = np.array([[c["latitude"], c["longitude"]] for c in valid_pts])
    # Convert km epsilon to radians for haversine metric: eps / R
    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian
    
    # Coordinates in radians: [lat_rad, lon_rad]
    coords_rad = np.radians(coords)
    
    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine', algorithm='ball_tree')
    labels = db.fit_predict(coords_rad)
    
    hotspots: List[Dict[str, Any]] = []
    unique_labels = set(labels)
    
    for cluster_id in unique_labels:
        if cluster_id == -1:
            # Noise points
            continue
            
        cluster_indices = np.where(labels == cluster_id)[0]
        cluster_pts = [valid_pts[i] for i in cluster_indices]
        cluster_coords = coords[cluster_indices]
        
        center_lat = float(np.mean(cluster_coords[:, 0]))
        center_lng = float(np.mean(cluster_coords[:, 1]))
        
        # Calculate maximum radius from center in meters
        max_dist_km = 0.1
        for pt in cluster_coords:
            d = calculate_haversine_distance_km(center_lat, center_lng, pt[0], pt[1])
            if d > max_dist_km:
                max_dist_km = d
                
        radius_meters = max(250.0, float(max_dist_km * 1000))
        
        # Categorize dominant sector
        categories: Dict[str, int] = {}
        for p in cluster_pts:
            cat = p.get("primary_category", "OTHER")
            categories[cat] = categories.get(cat, 0) + 1
            
        dominant_category = max(categories.items(), key=lambda x: x[1])[0]
        
        count = len(cluster_pts)
        density_score = round(count / (max(0.1, max_dist_km ** 2 * 3.14159)), 2)
        
        severity = "HIGH" if count >= 15 or density_score > 40.0 else ("MEDIUM" if count >= 6 else "LOW")
        
        sample_texts = [p.get("original_text", "") for p in cluster_pts[:3] if p.get("original_text")]
        wards_in = {}
        for p in cluster_pts:
            if p.get("ward_id"):
                wards_in[p["ward_id"]] = wards_in.get(p["ward_id"], 0) + 1

        hotspot = {
            "cluster_id": int(cluster_id),
            "category": dominant_category,
            "center_lat": round(center_lat, 6),
            "center_lng": round(center_lng, 6),
            "radius_meters": round(radius_meters, 1),
            "point_count": count,
            "density_score": density_score,
            "severity_level": severity,
            "sample_complaints": sample_texts,
            "category_breakdown": categories,
            "ward_ids": sorted(wards_in, key=lambda k: -wards_in[k]),
        }
        if return_members:
            hotspot["member_ids"] = [p["id"] for p in cluster_pts if "id" in p]
        hotspots.append(hotspot)

    return sorted(hotspots, key=lambda x: x["point_count"], reverse=True)
