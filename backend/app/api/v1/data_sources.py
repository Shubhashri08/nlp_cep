import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.gis.spatial_ops import find_ward_for_point
from backend.app.models.entities import (
    CitizenRequest, DataQualityReport, DataSource, InfrastructureAsset, Provenance, RequestEmbedding, RequestStatus,
    User, UserRole, Ward,
)
from backend.app.nlp.embeddings import get_embedding_engine
from backend.app.nlp.geocoder import in_study_area
from backend.app.nlp.pipeline import process_text

router = APIRouter(dependencies=[Depends(get_current_user)])

IMPORT_SCHEMAS = {
    "complaints": {"required": ["text"], "optional": ["latitude", "longitude", "ward_code", "created_at", "status", "source"]},
    "assets": {"required": ["name", "asset_type", "latitude", "longitude"], "optional": ["subtype", "capacity", "capacity_unit"]},
}


@router.get("")
def get_data_sources(db: Session = Depends(get_db)):
    reports = {r.data_source_id: r for r in db.query(DataQualityReport).order_by(DataQualityReport.assessed_at).all()}
    out = []
    for s in db.query(DataSource).order_by(DataSource.id).all():
        r = reports.get(s.id)
        out.append({
            "id": s.id, "source_name": s.source_name, "provider": s.provider, "dataset_type": s.dataset_type,
            "provenance": s.provenance, "source_url": s.source_url, "license": s.license,
            "date_collected": s.date_collected.strftime("%Y-%m-%d"), "geographic_scope": s.geographic_scope,
            "update_frequency": s.update_frequency, "schema_info": s.schema_info, "notes": s.notes, "quality_score": s.quality_score,
            "quality_report": {k: getattr(r, k) for k in ("total_records", "completeness_score", "duplicate_rate", "missing_values_count",
                                                          "geographic_validity_rate", "freshness_days", "consistency_score",
                                                          "overall_quality_score")} if r else None,
        })
    return out


@router.get("/import/schemas")
def import_schemas():
    return IMPORT_SCHEMAS


def _rows(filename: str, data: bytes):
    text = data.decode("utf-8-sig")
    if filename.lower().endswith((".geojson", ".json")):
        fc = json.loads(text)
        for f in fc.get("features", []):
            props = dict(f.get("properties") or {})
            geom = f.get("geometry") or {}
            if geom.get("type") == "Point":
                props["longitude"], props["latitude"] = geom["coordinates"][:2]
            yield props
    else:
        yield from csv.DictReader(io.StringIO(text))


@router.post("/import")
async def import_dataset(request: Request, dataset: str = Form(...), source_name: str = Form(...), file: UploadFile = File(...),
                         db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.ANALYST))):
    """Import complaints or assets from CSV / GeoJSON. Records are validated, located to wards and quality-scored."""
    if dataset not in IMPORT_SCHEMAS:
        raise HTTPException(status_code=422, detail=f"dataset must be one of {list(IMPORT_SCHEMAS)}")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (20 MB max)")
    try:
        rows = list(_rows(file.filename or "", data))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")
    if not rows:
        raise HTTPException(status_code=422, detail="No records found")
    missing_cols = [c for c in IMPORT_SCHEMAS[dataset]["required"] if c not in rows[0]]
    if missing_cols:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {missing_cols}")

    wards = db.query(Ward).all()
    by_code = {w.ward_code: w for w in wards}
    seen, ok, missing, invalid_geo, dups = set(), 0, 0, 0, 0
    emb = get_embedding_engine() if dataset == "complaints" else None
    for i, row in enumerate(rows):
        if any(not str(row.get(c) or "").strip() for c in IMPORT_SCHEMAS[dataset]["required"]):
            missing += 1
            continue
        key = json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        try:
            lat = float(row["latitude"]) if row.get("latitude") not in (None, "") else None
            lng = float(row["longitude"]) if row.get("longitude") not in (None, "") else None
        except ValueError:
            lat = lng = None
        if lat is not None and not in_study_area(lat, lng):
            invalid_geo += 1
            lat = lng = None
        if dataset == "assets":
            if lat is None:
                continue
            ward = find_ward_for_point(lat, lng, wards)
            if not ward:
                invalid_geo += 1
                continue
            cap = float(row["capacity"]) if row.get("capacity") not in (None, "") else None
            db.add(InfrastructureAsset(asset_uid=f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}", name=str(row["name"])[:200],
                                       asset_type=str(row["asset_type"]).upper(), subtype=row.get("subtype"), capacity=cap,
                                       capacity_unit=row.get("capacity_unit"), capacity_estimated=cap is None, ward_id=ward.id,
                                       latitude=lat, longitude=lng, provenance=Provenance.IMPORTED.value))
            ok += 1
        else:
            res = process_text(str(row["text"]), fallback_lat=lat, fallback_lng=lng, db=db, allow_network_geocoding=False)
            ward = find_ward_for_point(res["latitude"], res["longitude"], wards) if res["latitude"] is not None else None
            ward = ward or by_code.get(str(row.get("ward_code") or "").upper())
            try:
                created = datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc).replace(tzinfo=None)
            except ValueError:
                created = datetime.now(timezone.utc).replace(tzinfo=None)
            try:
                status = RequestStatus(str(row.get("status") or "OPEN").upper())
            except ValueError:
                status = RequestStatus.OPEN
            r = CitizenRequest(original_text=str(row["text"]), cleaned_text=res["cleaned_text"], language=res["language"],
                               language_confidence=res["language_confidence"], primary_category=res["primary_category"],
                               categories=res["categories"], confidence=res["confidence"], model_version=res["model_version"],
                               entities=res["entities"], summary=res["summary"], raw_location_text=res["raw_location_text"],
                               latitude=res["latitude"], longitude=res["longitude"], geocoding_confidence=res["geocoding_confidence"],
                               geocoding_method=res["geocoding_method"], is_location_resolved=res["is_location_resolved"],
                               address=res["address"], ward_id=ward.id if ward else None, source=row.get("source") or source_name,
                               provenance=Provenance.IMPORTED.value, status=status, created_at=created)
            db.add(r)
            db.flush()
            r.request_uid = f"CR-{created.year}-{r.id:06d}"
            db.add(RequestEmbedding(request_id=r.id, embedding_vector=res["embedding_vector"], embedding_model=emb.model_name))
            ok += 1

    total = len(rows)
    completeness = 1 - missing / total
    geo_valid = 1 - invalid_geo / total
    dup_rate = dups / total
    overall = round(0.4 * completeness + 0.3 * geo_valid + 0.3 * (1 - dup_rate), 3)
    src = DataSource(source_name=source_name, provider=user.full_name, dataset_type=f"Imported {dataset} ({file.filename})",
                     provenance=Provenance.IMPORTED.value, license="As provided by uploader", date_collected=datetime.now(timezone.utc),
                     geographic_scope="Greater Mumbai", update_frequency="Ad hoc", schema_info={"columns": list(rows[0].keys())},
                     notes=f"{ok} of {total} records imported", quality_score=overall)
    db.add(src)
    db.flush()
    db.add(DataQualityReport(data_source_id=src.id, total_records=total, completeness_score=round(completeness, 3),
                             duplicate_rate=round(dup_rate, 4), missing_values_count=missing, geographic_validity_rate=round(geo_valid, 3),
                             freshness_days=0, consistency_score=1.0, overall_quality_score=overall))
    audit(db, user, "DATA_IMPORTED", "DATA_SOURCE", src.id, {"dataset": dataset, "imported": ok, "total": total}, request)
    db.commit()
    return {"data_source_id": src.id, "total_records": total, "imported": ok, "missing_required": missing,
            "invalid_locations": invalid_geo, "duplicates": dups, "quality_score": overall,
            "note": "Run 'Recompute gaps' / 'Retrain forecaster' to reflect new data in analytics."}
