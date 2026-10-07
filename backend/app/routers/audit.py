import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Organisation, User
from app.schemas import AuditLogCreate, AuditLogOut
from app.security import get_current_user, require_roles, scoped_organisation_id

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
    organisation_id: str | None = Query(None, alias="organisationId"),
    event_type: str | None = Query(None, alias="eventType"),
    actor_id: str | None = Query(None, alias="actorId"),
    actor_role: str | None = Query(None, alias="actorRole"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        stmt = stmt.where(AuditLog.organisation_id == scoped_org)
    elif organisation_id:
        stmt = stmt.where(AuditLog.organisation_id == organisation_id)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.post("", response_model=AuditLogOut, status_code=status.HTTP_201_CREATED)
def create_audit_log(
    payload: AuditLogCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Persists one audit event for the CALLING user's own action.

    Identity/origin fields are never taken from the client -- a caller could
    otherwise forge audit entries attributed to someone else. Only the
    free-text description of what happened (event, eventType, resource,
    result, details) comes from the request body.
    """
    data = payload.model_dump()
    organisation = db.get(Organisation, user.organisation_id)
    obj = AuditLog(
        id=data.pop("id", None) or f"log-{uuid.uuid4().hex[:8]}",
        event=data.get("event", ""),
        event_type=data.get("event_type", ""),
        resource=data.get("resource", ""),
        result=data.get("result", "Success"),
        details=data.get("details", ""),
        actor_id=user.id,
        actor_name=user.name,
        actor_role=user.role,
        organisation_id=user.organisation_id,
        organisation_name=organisation.name if organisation else "",
        ip_address=request.client.host if request.client else "",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
