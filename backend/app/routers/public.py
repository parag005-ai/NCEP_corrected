from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ECGRecord, Organisation
from app.rate_limit import limiter
from app.reporting.models.generated_report import GeneratedReport
from app.schemas import CamelModel

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicStats(CamelModel):
    """Real, aggregate, non-identifying platform counts for public marketing
    pages. Deliberately excludes anything patient-, doctor- or org-specific --
    a public page must never reveal which real organisations use the
    platform or how much of anything a specific tenant has."""

    organisations_count: int
    ecg_recordings_processed: int
    reports_generated: int


@router.get("/stats", response_model=PublicStats)
@limiter.limit("30/minute")
def get_public_stats(request: Request, db: Session = Depends(get_db)):
    return PublicStats(
        organisations_count=db.scalar(select(func.count()).select_from(Organisation)) or 0,
        ecg_recordings_processed=db.scalar(select(func.count()).select_from(ECGRecord)) or 0,
        reports_generated=db.scalar(select(func.count()).select_from(GeneratedReport)) or 0,
    )
