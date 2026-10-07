import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClinicalReport, ECGRecord, Patient, User
from app.schemas import ClinicalFlag, PipelineReportData, ReportCreate, ReportOut, ReportUpdate
from app.security import (
    get_current_user,
    patients_visible_to_organisation,
    require_roles,
    resolve_patient_id,
    scoped_organisation_id,
    user_can_access_patient_data,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _check_report_access(obj: ClinicalReport, user: User, db: Session) -> None:
    if user.role == "patient":
        if not obj.shared_with_patient or obj.patient_id != resolve_patient_id(user, db):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    elif user.role in ("admin", "doctor", "superadmin"):
        if not user_can_access_patient_data(user, obj.patient_id, db, home_organisation_id=obj.organisation_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "patient", "superadmin")),
    patient_id: str | None = Query(None, alias="patientId"),
    doctor_id: str | None = Query(None, alias="doctorId"),
    organisation_id: str | None = Query(None, alias="organisationId"),
    shared_with_patient: bool | None = Query(None, alias="sharedWithPatient"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(ClinicalReport)
    if user.role == "patient":
        stmt = stmt.where(
            ClinicalReport.patient_id == resolve_patient_id(user, db),
            ClinicalReport.shared_with_patient.is_(True),
        )
    else:
        scoped_org = scoped_organisation_id(user)
        if scoped_org:
            stmt = stmt.where(ClinicalReport.patient_id.in_(patients_visible_to_organisation(scoped_org)))
        elif organisation_id:
            stmt = stmt.where(ClinicalReport.patient_id.in_(patients_visible_to_organisation(organisation_id)))
        if patient_id:
            stmt = stmt.where(ClinicalReport.patient_id == patient_id)
        if doctor_id:
            stmt = stmt.where(ClinicalReport.doctor_id == doctor_id)
        if shared_with_patient is not None:
            stmt = stmt.where(ClinicalReport.shared_with_patient == shared_with_patient)
    if status_filter:
        stmt = stmt.where(ClinicalReport.status == status_filter)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role == "patient":
        if not obj.shared_with_patient or obj.patient_id != resolve_patient_id(user, db):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    elif user.role in ("admin", "doctor", "superadmin"):
        if not user_can_access_patient_data(user, obj.patient_id, db, home_organisation_id=obj.organisation_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return obj


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "doctor", "superadmin")),
):
    now = datetime.now(timezone.utc)
    data = payload.model_dump()
    obj = ClinicalReport(
        id=data.pop("id", None) or f"rpt-{uuid.uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
        **data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: str,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{report_id}/approve", response_model=ReportOut)
def approve_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    obj.status = "Approved"
    obj.reviewed_by = user.name
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{report_id}/share", response_model=ReportOut)
def share_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    obj.status = "Shared"
    obj.shared_with_patient = True
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{report_id}", response_model=ReportOut)
def upsert_report(
    report_id: str,
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    data = payload.model_dump()
    data.pop("id", None)
    now = datetime.now(timezone.utc)
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        if user.role != "superadmin":
            data["organisation_id"] = user.organisation_id
        obj = ClinicalReport(id=report_id, created_at=now, updated_at=now, **data)
        db.add(obj)
    else:
        if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
        for k, v in data.items():
            if user.role != "superadmin" and k == "organisation_id":
                continue
            setattr(obj, k, v)
        obj.updated_at = now
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(ClinicalReport, report_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    db.delete(obj)
    db.commit()


_PREPROCESSING_STATUS_BY_VALIDATION = {
    "valid": "Completed",
    "warning": "Completed",
    "invalid": "Failed",
}


@router.get("/{report_id}/pipeline", response_model=PipelineReportData)
def get_pipeline_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Signal-processing view of a report's underlying ECG record.

    Populated from what `app.preprocessing` actually computes and persists on
    ECGRecord (beat count, quality score/flags). This pipeline does not run
    SAECG late-potential or QT/repolarization analysis yet, so those fields
    come back empty/null rather than invented -- a real "not yet available"
    beats a fabricated clinical number.
    """
    report = db.get(ClinicalReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    _check_report_access(report, user, db)

    ecg = db.get(ECGRecord, report.ecg_record_id) if report.ecg_record_id else None
    patient = db.get(Patient, report.patient_id) if report.patient_id else None

    age_sex = ""
    if patient and (patient.age or patient.gender):
        age_sex = f"{patient.age}{patient.gender[:1].upper()}" if patient.gender else str(patient.age)

    quality_score = ecg.quality_score if ecg and ecg.quality_score is not None else 0.0
    beat_count = ecg.beat_count if ecg and ecg.beat_count is not None else 0
    validation_status = ecg.validation_status if ecg else None
    # No ecg / no validation_status means "never run through the ingestion+
    # preprocessing pipeline" (e.g. legacy seed data) -- that's pending work,
    # not a failure, so only an explicit "invalid" maps to Failed.
    preprocessing_status = _PREPROCESSING_STATUS_BY_VALIDATION.get(validation_status or "", "In Progress")
    analysis_status = {"Approved": "Validated", "Shared": "Validated", "Draft": "Pending", "In Review": "Pending"}.get(
        report.status, "Pending"
    )
    confidence_score = "High" if quality_score >= 80 else "Medium" if quality_score >= 50 else "Low"

    clinical_flags = [
        ClinicalFlag(name=flag, result="POSITIVE", description="Raised by the preprocessing quality assessor.")
        for flag in (ecg.quality_flags or [])
    ] if ecg else []

    recording_duration = f"{ecg.duration_seconds:.1f} s" if ecg and ecg.duration_seconds else ""
    lead_name = ", ".join(ecg.available_leads) if ecg and ecg.available_leads else ""

    return PipelineReportData(
        processing_id=report.ecg_record_id or report.id,
        clinical_unit=report.organisation_id,
        patient_name=report.patient_name,
        age_sex=age_sex,
        patient_id=report.patient_id,
        lead_name=lead_name,
        recording_duration=recording_duration,
        report_date=report.created_at.date().isoformat() if report.created_at else "",
        physician=report.doctor_name,
        preprocessing_status=preprocessing_status,
        analysis_status=analysis_status,
        signal_quality_score=quality_score,
        r_peak_count=beat_count,
        qrs_complexes=beat_count,
        qrs_note="R-peak and QRS complex counts share the same beat-detection pass.",
        mean_heart_rate=0,
        clinical_flags=clinical_flags,
        saecg_parameters=[],
        qt_interval=None,
        qtc_bazett=None,
        qt_dispersion=None,
        tpeak_tend=None,
        tpe_qt_ratio=None,
        t_wave_dispersion=None,
        qtc_highlighted=False,
        clinical_insight=(
            "SAECG late-potential and QT/repolarization analysis are not yet implemented in this pipeline; "
            "the figures above reflect signal-quality and beat-detection output only."
        ),
        confidence_score=confidence_score,
        automated_analysis=f"Beat detection found {beat_count} beats at a mean signal quality of {quality_score:.0f}/100."
        if ecg
        else "No linked ECG record to analyze.",
        physician_name=report.doctor_name,
        physician_title="Attending Physician",
    )
