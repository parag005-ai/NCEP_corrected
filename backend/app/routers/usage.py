import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organisation, UsageRecord, User
from app.schemas import UsageRecordCreate, UsageRecordOut
from app.security import require_roles, scoped_organisation_id

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=list[UsageRecordOut])
def list_usage_records(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
    organisation_id: str | None = Query(None, alias="organisationId"),
    doctor_id: str | None = Query(None, alias="doctorId"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(UsageRecord).order_by(UsageRecord.timestamp.desc())
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        stmt = stmt.where(UsageRecord.organisation_id == scoped_org)
    elif organisation_id:
        stmt = stmt.where(UsageRecord.organisation_id == organisation_id)
    if doctor_id:
        stmt = stmt.where(UsageRecord.doctor_id == doctor_id)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.post("", response_model=UsageRecordOut, status_code=201)
def create_usage_record(
    payload: UsageRecordCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    """Records one billable action for the caller's own organisation.

    organisationId/organisationName are always derived from the caller's
    session, never trusted from the request body -- otherwise any caller
    could bill usage against an organisation they don't belong to.
    """
    data = payload.model_dump()
    data.pop("id", None)
    scoped_org = scoped_organisation_id(user)
    organisation_id = scoped_org or data.get("organisation_id") or user.organisation_id
    organisation = db.get(Organisation, organisation_id)
    obj = UsageRecord(
        id=f"usage-{uuid.uuid4().hex[:8]}",
        action=data.get("action", ""),
        credits_used=data.get("credits_used", 0),
        organisation_id=organisation_id,
        organisation_name=organisation.name if organisation else "",
        doctor_id=data.get("doctor_id"),
        doctor_name=data.get("doctor_name"),
        status=data.get("status", "Success"),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
