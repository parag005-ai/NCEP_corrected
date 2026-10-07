import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import get_current_user, hash_password, require_roles, scoped_organisation_id

router = APIRouter(prefix="/api/users", tags=["users"])

_SELF_UPDATABLE_FIELDS = {"avatar_url"}


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
    organisation_id: str | None = Query(None, alias="organisationId"),
    role: str | None = Query(None),
    email: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(User)
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        stmt = stmt.where(User.organisation_id == scoped_org)
    elif organisation_id:
        stmt = stmt.where(User.organisation_id == organisation_id)
    if role:
        stmt = stmt.where(User.role == role)
    if email:
        stmt = stmt.where(User.email == email.lower())
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(User, user_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    is_self = obj.id == user.id
    is_admin_in_scope = user.role in ("admin", "superadmin") and (
        user.role == "superadmin" or obj.organisation_id == user.organisation_id
    )
    if not (is_self or is_admin_in_scope):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return obj


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    data = payload.model_dump()
    password = data.pop("password")
    if not password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A password is required to create a user.")
    if db.scalar(select(User).where(User.email == data["email"])):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    scoped_org = scoped_organisation_id(user)
    if scoped_org:
        data["organisation_id"] = scoped_org
    obj = User(
        id=data.pop("id", None) or f"user-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc),
        last_active=None,
        password_hash=hash_password(password),
        **data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = db.get(User, user_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    is_self = obj.id == user.id
    is_admin_in_scope = user.role in ("admin", "superadmin") and (
        user.role == "superadmin" or obj.organisation_id == user.organisation_id
    )
    if not (is_self or is_admin_in_scope):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    updates = payload.model_dump(exclude_unset=True)
    if is_self and not is_admin_in_scope:
        updates = {k: v for k, v in updates.items() if k in _SELF_UPDATABLE_FIELDS}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def upsert_user(
    user_id: str,
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    """Idempotent create-or-replace, keyed on the path id (see organisations.py
    for why: client-generated ids need a single-request upsert).

    Doctors may only use this to create a brand-new patient login (e.g. when
    registering a new patient) -- never to edit an existing account or to
    create/edit any other role. Everything else stays admin/superadmin-only.
    """
    data = payload.model_dump()
    data.pop("id", None)
    password = data.pop("password")
    scoped_org = scoped_organisation_id(user)
    obj = db.get(User, user_id)
    if user.role == "doctor":
        if obj is not None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctors cannot edit existing user accounts.")
        data["role"] = "patient"
    if obj is None:
        if not password:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A password is required to create a user.")
        if data.get("email") and db.scalar(select(User).where(User.email == data["email"])):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        if scoped_org:
            data["organisation_id"] = scoped_org
        obj = User(
            id=user_id,
            created_at=datetime.now(timezone.utc),
            last_active=None,
            password_hash=hash_password(password),
            **data,
        )
        db.add(obj)
    else:
        if scoped_org and obj.organisation_id != scoped_org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if password:
            obj.password_hash = hash_password(password)
        for k, v in data.items():
            if scoped_org and k == "organisation_id":
                continue
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(User, user_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db.delete(obj)
    db.commit()
