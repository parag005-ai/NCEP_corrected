import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organisation, Patient, User
from app.schemas import OrganisationCreate, OrganisationOut, OrganisationUpdate
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/api/organisations", tags=["organisations"])


def _with_live_counts(obj: Organisation, db: Session) -> Organisation:
    """Stored total_users/total_patients drift from reality (never incremented on
    create/delete elsewhere) -- overwrite with a live count before returning."""
    obj.total_users = db.scalar(select(func.count()).select_from(User).where(User.organisation_id == obj.id)) or 0
    obj.total_patients = (
        db.scalar(select(func.count()).select_from(Patient).where(Patient.organisation_id == obj.id)) or 0
    )
    return obj


@router.get("", response_model=list[OrganisationOut])
def list_organisations(
    db: Session = Depends(get_db),
    _=Depends(require_roles("superadmin")),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    orgs = db.scalars(select(Organisation).limit(limit).offset(offset)).all()
    return [_with_live_counts(o, db) for o in orgs]


@router.get("/{org_id}", response_model=OrganisationOut)
def get_organisation(org_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Organisation, org_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
    if user.role != "superadmin" and obj.id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
    return _with_live_counts(obj, db)


@router.post("", response_model=OrganisationOut, status_code=status.HTTP_201_CREATED)
def create_organisation(
    payload: OrganisationCreate, db: Session = Depends(get_db), _=Depends(require_roles("superadmin"))
):
    data = payload.model_dump()
    obj = Organisation(
        id=data.pop("id", None) or f"org-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc),
        **data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _with_live_counts(obj, db)


@router.patch("/{org_id}", response_model=OrganisationOut)
def update_organisation(
    org_id: str,
    payload: OrganisationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(Organisation, org_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
    if user.role != "superadmin" and obj.id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _with_live_counts(obj, db)


@router.put("/{org_id}", response_model=OrganisationOut)
def upsert_organisation(
    org_id: str,
    payload: OrganisationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("superadmin")),
):
    """Idempotent create-or-replace, keyed on the path id -- lets callers that
    generate their own client-side ids (see build spec's §PUT semantics) mint
    a new organisation or overwrite one they already know the id of, in one
    request rather than a GET-then-POST-or-PATCH round trip."""
    data = payload.model_dump()
    data.pop("id", None)
    obj = db.get(Organisation, org_id)
    if obj is None:
        obj = Organisation(id=org_id, created_at=datetime.now(timezone.utc), **data)
        db.add(obj)
    else:
        for k, v in data.items():
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _with_live_counts(obj, db)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organisation(
    org_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_roles("superadmin")),
):
    obj = db.get(Organisation, org_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
    # Users/doctors/patients FK to organisations with ondelete=RESTRICT -- check
    # up front so a non-empty org 409s cleanly instead of raising a raw
    # IntegrityError from the commit below.
    user_count = db.scalar(select(func.count()).select_from(User).where(User.organisation_id == org_id)) or 0
    patient_count = db.scalar(select(func.count()).select_from(Patient).where(Patient.organisation_id == org_id)) or 0
    if user_count or patient_count:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Organisation still has users or patients assigned; reassign or remove them first.",
        )
    db.delete(obj)
    db.commit()
