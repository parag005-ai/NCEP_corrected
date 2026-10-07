"""Password hashing (stdlib pbkdf2) + JWT helpers — no native crypto deps."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy import Select

from app.config import settings
from app.database import get_db
from app.models import Doctor, Patient, PatientOrganisationLink, User

_PBKDF2_ROUNDS = 200_000

SESSION_COOKIE = "ncep_session"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # The browser client authenticates via the httpOnly session cookie set on
    # login; a Bearer header (scripts, tests, API tooling) is also accepted.
    token = credentials.credentials if credentials else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise creds_exc
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise creds_exc
    if not user_id:
        raise creds_exc
    user = db.get(User, user_id)
    if user is None:
        raise creds_exc
    return user


def require_roles(*roles: str):
    """Dependency factory: 403s unless the caller's role is one of `roles`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dependency


def scoped_organisation_id(user: User) -> str | None:
    """Organisation filter to enforce for this caller, or None for superadmin (no filter)."""
    return None if user.role == "superadmin" else user.organisation_id


def resolve_patient_id(user: User, db: Session) -> str | None:
    """The Patient row this user IS, if role=patient (mirrors auth.py:build_session)."""
    patient = db.scalar(select(Patient).where(Patient.email == user.email))
    return patient.id if patient else None


def resolve_doctor_id(user: User, db: Session) -> str | None:
    """The Doctor row this user IS, if role=doctor (mirrors auth.py:build_session)."""
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    return doctor.id if doctor else None


def patient_shared_organisation_ids(db: Session, patient_id: str) -> set[str]:
    """Organisations a PatientOrganisationLink has explicitly granted shared access to
    this patient, beyond whichever organisation is otherwise treated as their home.
    Never looks at the Patient row itself, so it stays correct (empty) even in the
    edge case of a dangling patient_id with no Patient row."""
    return set(
        db.scalars(
            select(PatientOrganisationLink.organisation_id).where(
                PatientOrganisationLink.patient_id == patient_id
            )
        ).all()
    )


def user_can_access_patient_data(
    user: User, patient_id: str, db: Session, *, home_organisation_id: str | None = None
) -> bool:
    """Whether `user`'s organisation may read data (ECG record / report / patient) tied
    to this patient -- their home organisation, or one explicitly granted shared access
    via PatientOrganisationLink. Superadmin is unscoped, as everywhere else.

    Pass `home_organisation_id` as the *resource's own* denormalized organisation_id
    (e.g. ECGRecord.organisation_id) when the caller already has it -- this keeps the
    common same-organisation check exactly as fast and side-effect-free as it was
    before sharing existed, and independent of whether the Patient row backing
    `patient_id` still exists or has since moved (callers upstream, e.g. the Generation
    Context Loader, rely on that distinction to raise their own, more specific error).
    """
    if user.role == "superadmin":
        return True
    home = home_organisation_id
    if home is None:
        patient = db.get(Patient, patient_id)
        home = patient.organisation_id if patient else None
    if home is not None and home == user.organisation_id:
        return True
    return user.organisation_id in patient_shared_organisation_ids(db, patient_id)


def patients_visible_to_organisation(organisation_id: str) -> Select:
    """Select of Patient.id whose home organisation is `organisation_id`, or which have
    been shared with it -- use as `Model.patient_id.in_(patients_visible_to_organisation(...))`."""
    home = select(Patient.id).where(Patient.organisation_id == organisation_id)
    shared = select(PatientOrganisationLink.patient_id).where(
        PatientOrganisationLink.organisation_id == organisation_id
    )
    return home.union(shared)
