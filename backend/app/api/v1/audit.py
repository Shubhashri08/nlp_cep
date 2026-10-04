from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import require_role
from backend.app.database.session import get_db
from backend.app.models.entities import AuditLog, User

router = APIRouter()


@router.get("")
def get_audit_logs(limit: int = Query(100, ge=1, le=1000), action: Optional[str] = None, db: Session = Depends(get_db),
                   _: User = Depends(require_role())):  # ADMIN only
    users = {u.id: u.email for u in db.query(User).all()}
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    return [{"id": l.id, "user_id": l.user_id, "user_email": users.get(l.user_id), "action": l.action,
             "resource_type": l.resource_type, "resource_id": l.resource_id, "details": l.details, "ip_address": l.ip_address,
             "timestamp": l.timestamp.isoformat()} for l in q.order_by(AuditLog.timestamp.desc()).limit(limit).all()]
