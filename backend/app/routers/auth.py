import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AuditLog, Doctor, Organisation, Patient, User
from app.rate_limit import limiter
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    Session as SessionSchema,
)
from app.security import SESSION_COOKIE, create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Session fields a user may edit about themselves via PATCH /auth/session --
# role, organisationId and the patient/doctor linkage are derived server-side
# (see build_session) and never client-writable.
_SELF_UPDATABLE_SESSION_FIELDS = {"name", "avatar_url"}


def _set_session_cookie(response: Response, token: str) -> None:
    # SameSite is evaluated per registrable domain, not per origin -- it
    # ignores port, so a "localhost:3000" frontend and "localhost:8000"
    # backend are same-site and samesite="lax" is sent on fetch() between
    # them. In production the frontend/backend are assumed to share a
    # registrable domain too (see CORS_ORIGINS); samesite="none" is only
    # needed for a genuinely cross-site deployment, and that requires
    # secure=True, which in turn requires HTTPS -- so both are gated on
    # app_env=production rather than hardcoded, or the cookie would never be
    # sent back at all over a plain http://localhost dev/test connection.
    is_production = settings.app_env == "production"
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        path="/",
        max_age=settings.jwt_expire_minutes * 60,
    )


def build_session(user: User, db: Session) -> SessionSchema:
    patient_id = None
    doctor_id = None
    if user.role == "patient":
        patient = db.scalar(select(Patient).where(Patient.email == user.email))
        patient_id = patient.id if patient else None
    if user.role == "doctor":
        doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
        doctor_id = doctor.id if doctor else None
    return SessionSchema(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        organisation_id=user.organisation_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        avatar_url=user.avatar_url,
    )


def _resolve_login_user(identifier: str, db: Session) -> User | None:
    """Resolves the login identifier field to a User account.

    Accepts a work email (the historical/primary path), or an ID the account
    holder was actually handed: a patient's Patient ID (what staff hand out
    alongside the pat-XXX_name temp password), a doctor's Doctor ID or staff
    ID, or -- as a catch-all covering admin/superadmin, who have no separate
    profile table -- the raw User ID.
    """
    identifier = identifier.strip()
    if not identifier:
        return None
    user = db.scalar(select(User).where(User.email == identifier.lower()))
    if user:
        return user
    user = db.scalar(select(User).where(User.email.ilike(identifier)))
    if user:
        return user
    patient = db.scalar(select(Patient).where(Patient.id == identifier))
    if patient and patient.email:
        user = db.scalar(select(User).where(User.email == patient.email))
        if user:
            return user
    doctor = db.scalar(
        select(Doctor).where((Doctor.id == identifier) | (Doctor.staff_id == identifier))
    )
    if doctor and doctor.email:
        user = db.scalar(select(User).where(User.email == doctor.email))
        if user:
            return user
    return db.scalar(select(User).where(User.id == identifier))


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    user = _resolve_login_user(payload.email, db)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ID/email or password.")
    if user.status != "Active":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This account is not active. Contact your administrator.",
        )
    token = create_access_token(user.id)
    _set_session_cookie(response, token)
    return LoginResponse(session=build_session(user, db))


@router.post("/password-reset-request", response_model=PasswordResetRequestResponse)
@limiter.limit("5/minute")
def request_password_reset(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Logs a real, admin-visible password reset request.

    There is no outbound email service configured for this platform, so this
    cannot silently claim to have "sent an email" -- that would be exactly
    the kind of fabricated confirmation this codebase avoids elsewhere. What
    it does instead is real: it writes an audit log entry the requester's own
    organisation admin (or superadmin, if the email doesn't match anyone)
    already has a real, working view onto, so a human can verify identity and
    reset the account.

    The response is identical whether or not the email matches an account,
    so this endpoint cannot be used to enumerate registered users.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        user = db.scalar(select(User).where(User.email.ilike(payload.email)))

    organisation_id = user.organisation_id if user else ""
    organisation = db.get(Organisation, organisation_id) if organisation_id else None
    db.add(
        AuditLog(
            id=f"log-{uuid.uuid4().hex[:8]}",
            event="Password reset requested",
            event_type="password_reset_requested",
            resource=f"User {user.id}" if user else "",
            result="Success",
            details=(
                f"Password reset requested for {payload.email}. An administrator should verify the "
                "requester's identity before resetting the account password."
            ),
            actor_id="",
            actor_name=payload.email,
            actor_role="",
            organisation_id=organisation_id,
            organisation_name=organisation.name if organisation else "",
            ip_address=request.client.host if request.client else "",
            timestamp=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return PasswordResetRequestResponse(
        message="If an account exists for this email, a request has been logged and an administrator will be in touch."
    )


@router.get("/me", response_model=SessionSchema)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_session(user, db)


@router.get("/session", response_model=SessionSchema)
def get_session(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Alias for /me. Some frontend service layers address the caller's
    identity as a REST-ish "session" resource rather than "/me"."""
    return build_session(user, db)


@router.patch("/session", response_model=SessionSchema)
def update_session(
    payload: SessionSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates the caller's own display name/avatar. Role, organisation and
    identity fields in the payload are accepted (the frontend's Session type
    round-trips the whole object) but ignored -- only the fields in
    _SELF_UPDATABLE_SESSION_FIELDS are ever written."""
    updates = payload.model_dump(exclude_unset=True, by_alias=False)
    for field in _SELF_UPDATABLE_SESSION_FIELDS:
        if field in updates and updates[field] is not None:
            setattr(user, field, updates[field])
    db.commit()
    db.refresh(user)
    return build_session(user, db)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user)):
    is_production = settings.app_env == "production"
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=is_production,
        samesite="none" if is_production else "lax",
    )
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}
