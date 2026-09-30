from typing import Optional

from backend.app.models.entities import CitizenRequest
from backend.app.schemas.dss_schemas import CitizenRequestResponse


def citizen_request_out(r: CitizenRequest, ward_name: Optional[str] = None) -> CitizenRequestResponse:
    return CitizenRequestResponse(
        id=r.id, request_uid=r.request_uid, original_text=r.original_text, cleaned_text=r.cleaned_text,
        language=r.language, language_confidence=r.language_confidence, primary_category=r.primary_category,
        categories=r.categories or [], confidence=r.confidence, model_version=r.model_version or "",
        entities=r.entities or [], summary=r.summary, raw_location_text=r.raw_location_text,
        latitude=r.latitude, longitude=r.longitude, geocoding_confidence=r.geocoding_confidence or 0.0,
        geocoding_method=r.geocoding_method, is_location_resolved=bool(r.is_location_resolved), address=r.address,
        ward_id=r.ward_id, ward_name=ward_name if ward_name is not None else (r.ward.name if r.ward else None),
        source=r.source or "", provenance=r.provenance, status=r.status, cluster_id=r.cluster_id,
        created_at=r.created_at, resolved_at=r.resolved_at,
    )
