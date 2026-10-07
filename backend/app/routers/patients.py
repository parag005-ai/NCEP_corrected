import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor, Patient, PatientOrganisationLink, User
from app.schemas import PatientCreate, PatientLinkRequest, PatientOut, PatientUpdate
from app.security import (
    get_current_user,
    patients_visible_to_organisation,
    require_roles,
    resolve_doctor_id,
    resolve_patient_id,
    scoped_organisation_id,
    user_can_access_patient_data,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])

_SELF_UPDATABLE_FIELDS = {"name", "email", "phone"}


def _sync_assigned_doctor_name(data: dict, db: Session) -> None:
    """The doctor's display name is denormalized onto Patient -- always derive it
    server-side from assigned_doctor_id so it can't drift from the real Doctor row."""
    if "assigned_doctor_id" not in data:
        return
    data["assigned_doctor_id"] = data["assigned_doctor_id"] or None  # "" isn't a valid FK value
    doctor = db.get(Doctor, data["assigned_doctor_id"]) if data["assigned_doctor_id"] else None
    data["assigned_doctor"] = doctor.name if doctor else ""


@router.get("", response_model=list[PatientOut])
def list_patients(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
    organisation_id: str | None = Query(None, alias="organisationId"),
    assigned_doctor_id: str | None = Query(None, alias="assignedDoctorId"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Patient)
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        stmt = stmt.where(Patient.id.in_(patients_visible_to_organisation(scoped_org)))
    elif organisation_id:
        stmt = stmt.where(Patient.id.in_(patients_visible_to_organisation(organisation_id)))
    if user.role == "doctor":
        stmt = stmt.where(Patient.assigned_doctor_id == resolve_doctor_id(user, db))
    elif assigned_doctor_id:
        stmt = stmt.where(Patient.assigned_doctor_id == assigned_doctor_id)
    if status_filter:
        stmt = stmt.where(Patient.status == status_filter)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Patient, patient_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    if user.role == "patient":
        if resolve_patient_id(user, db) != patient_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    elif user.role in ("admin", "doctor", "superadmin"):
        if not user_can_access_patient_data(user, patient_id, db, home_organisation_id=obj.organisation_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return obj


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    data = payload.model_dump()
    if data.get("email") and db.scalar(select(Patient).where(Patient.email == data["email"])):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        data["organisation_id"] = scoped_org
    _sync_assigned_doctor_name(data, db)
    obj = Patient(
        id=data.pop("id", None) or f"pat-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc),
        **data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = db.get(Patient, patient_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    is_self = user.role == "patient" and resolve_patient_id(user, db) == patient_id
    is_staff_in_scope = user.role in ("admin", "doctor", "superadmin") and (
        user.role == "superadmin" or obj.organisation_id == user.organisation_id
    )
    if not (is_self or is_staff_in_scope):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    updates = payload.model_dump(exclude_unset=True)
    if is_self and not is_staff_in_scope:
        # Patients may update their own demographic contact details, but not
        # clinical fields (medical_notes, status) or their care assignment.
        updates = {k: v for k, v in updates.items() if k in _SELF_UPDATABLE_FIELDS}
    _sync_assigned_doctor_name(updates, db)
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{patient_id}", response_model=PatientOut)
def upsert_patient(
    patient_id: str,
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    data = payload.model_dump()
    data.pop("id", None)
    scoped_org = scoped_organisation_id(user)
    obj = db.get(Patient, patient_id)
    if obj is None:
        if data.get("email") and db.scalar(select(Patient).where(Patient.email == data["email"])):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        if scoped_org:
            data["organisation_id"] = scoped_org
        _sync_assigned_doctor_name(data, db)
        obj = Patient(id=patient_id, created_at=datetime.now(timezone.utc), **data)
        db.add(obj)
    else:
        if scoped_org and obj.organisation_id != scoped_org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
        _sync_assigned_doctor_name(data, db)
        for k, v in data.items():
            if scoped_org and k == "organisation_id":
                continue
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{patient_id}/link", response_model=PatientOut)
def link_existing_patient(
    patient_id: str,
    payload: PatientLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    """Grants the caller's organisation (or, for superadmin, an explicitly named one)
    access to a patient who is already registered -- possibly at another organisation
    entirely. Does not move or copy the patient: their existing ECG records and reports
    become visible to the newly-linked organisation as-is (see security.py's
    user_can_access_patient_data / patients_visible_to_organisation), and continue to
    show under whichever organisation originally created them."""
    obj = db.get(Patient, patient_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    target_org = scoped_organisation_id(user) or payload.organisation_id
    if not target_org:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "organisationId is required for superadmin"
        )
    if obj.organisation_id == target_org:
        return obj

    existing = db.scalar(
        select(PatientOrganisationLink).where(
            PatientOrganisationLink.patient_id == patient_id,
            PatientOrganisationLink.organisation_id == target_org,
        )
    )
    if existing is None:
        db.add(
            PatientOrganisationLink(
                id=f"pol-{uuid.uuid4().hex[:8]}",
                patient_id=patient_id,
                organisation_id=target_org,
                linked_by_user_id=user.id,
                linked_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    return obj


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(Patient, patient_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    db.delete(obj)
    db.commit()
