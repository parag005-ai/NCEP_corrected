import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor, Patient, User
from app.schemas import DoctorCreate, DoctorOut, DoctorUpdate
from app.security import get_current_user, require_roles, resolve_patient_id, scoped_organisation_id

router = APIRouter(prefix="/api/doctors", tags=["doctors"])

_SELF_UPDATABLE_FIELDS = {"name", "email", "phone", "speciality"}


@router.get("", response_model=list[DoctorOut])
def list_doctors(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
    organisation_id: str | None = Query(None, alias="organisationId"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Doctor)
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        stmt = stmt.where(Doctor.organisation_id == scoped_org)
    elif organisation_id:
        stmt = stmt.where(Doctor.organisation_id == organisation_id)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Doctor, doctor_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    if user.role == "patient":
        patient_id = resolve_patient_id(user, db)
        patient = db.get(Patient, patient_id) if patient_id else None
        if patient is None or patient.assigned_doctor_id != doctor_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    elif user.role in ("admin", "doctor", "superadmin"):
        if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return obj


@router.post("", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def create_doctor(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    data = payload.model_dump()
    data["user_id"] = data.get("user_id") or None  # "" isn't a valid FK value
    if data.get("email") and db.scalar(select(Doctor).where(Doctor.email == data["email"])):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        data["organisation_id"] = scoped_org
    obj = Doctor(
        id=data.pop("id", None) or f"doc-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc),
        **data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{doctor_id}", response_model=DoctorOut)
def update_doctor(
    doctor_id: str,
    payload: DoctorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = db.get(Doctor, doctor_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    is_self = user.role == "doctor" and obj.user_id == user.id
    is_staff_in_scope = user.role in ("admin", "superadmin") and (
        user.role == "superadmin" or obj.organisation_id == user.organisation_id
    )
    if not (is_self or is_staff_in_scope):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    updates = payload.model_dump(exclude_unset=True)
    if is_self and not is_staff_in_scope:
        # Doctors may update their own contact/speciality details, but not
        # status, organisation, or assigned-patient bookkeeping.
        updates = {k: v for k, v in updates.items() if k in _SELF_UPDATABLE_FIELDS}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{doctor_id}", response_model=DoctorOut)
def upsert_doctor(
    doctor_id: str,
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    data = payload.model_dump()
    data.pop("id", None)
    data["user_id"] = data.get("user_id") or None
    scoped_org = scoped_organisation_id(user)
    obj = db.get(Doctor, doctor_id)
    if obj is None:
        if data.get("email") and db.scalar(select(Doctor).where(Doctor.email == data["email"])):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        if scoped_org:
            data["organisation_id"] = scoped_org
        obj = Doctor(
            id=doctor_id,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
            **data,
        )
        db.add(obj)
    else:
        if scoped_org and obj.organisation_id != scoped_org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
        for k, v in data.items():
            if scoped_org and k == "organisation_id":
                continue
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(Doctor, doctor_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    db.delete(obj)
    db.commit()
