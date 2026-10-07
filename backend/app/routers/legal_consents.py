import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LegalConsent, User
from app.schemas import LegalConsentAccept, LegalConsentStatus
from app.security import get_current_user

router = APIRouter(prefix="/api/legal-consents", tags=["legal-consents"])

CURRENT_TERMS_VERSION = "1"


@router.get("/current", response_model=LegalConsentStatus)
def get_current_consent(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    consent = db.scalar(
        select(LegalConsent)
        .where(LegalConsent.user_id == user.id, LegalConsent.version == CURRENT_TERMS_VERSION)
        .order_by(LegalConsent.accepted_at.desc())
    )
    if consent is None:
        return LegalConsentStatus(accepted=False, version=CURRENT_TERMS_VERSION)
    return LegalConsentStatus(accepted=True, version=consent.version, accepted_at=consent.accepted_at)


@router.post("/current", response_model=LegalConsentStatus)
def accept_current_consent(
    payload: LegalConsentAccept | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = payload.version if payload else CURRENT_TERMS_VERSION
    now = datetime.now(timezone.utc)
    consent = LegalConsent(id=f"consent-{uuid.uuid4().hex[:8]}", user_id=user.id, version=version, accepted_at=now)
    db.add(consent)
    db.commit()
    return LegalConsentStatus(accepted=True, version=version, accepted_at=now)
