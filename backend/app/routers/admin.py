from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditLog,
    ClinicalReport,
    Doctor,
    ECGRecord,
    LegalConsent,
    Organisation,
    Patient,
    UsageRecord,
    User,
)
from app.schemas import ApplicationDataResetResponse
from app.security import require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/application-data", response_model=ApplicationDataResetResponse)
def reset_application_data(db: Session = Depends(get_db), _=Depends(require_roles("superadmin"))):
    """Factory-resets the platform: wipes every row, then reseeds the same fixed
    demo dataset app.seed ships with. Superadmin-only. Deletion order respects
    the RESTRICT foreign keys between users/doctors/patients/reports/ecg
    records and organisations (children before parents)."""
    from app.seed import seed_db  # deferred: avoids a import-time cycle with app.database

    for model in (UsageRecord, LegalConsent, AuditLog, ClinicalReport, ECGRecord, Patient, Doctor, User, Organisation):
        db.query(model).delete()
    db.commit()

    # force=True: the table is empty from the delete loop above, but reuses
    # the same request-scoped session rather than seed()'s own SessionLocal,
    # which would be a different database under a get_db override (tests) and
    # is otherwise just a redundant second connection.
    seed_db(db, force=True)

    return ApplicationDataResetResponse(ok=True, reset_at=datetime.now(timezone.utc))
