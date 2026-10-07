import os
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.job_service import (
    create_or_get_ingest_job,
    run_ingest_job,
)
from app.ingestion.idempotency import effective_idempotency_key, request_fingerprint
from app.ingestion.upload_orchestrator import UploadOrchestrator
from app.models import ECGIngestJob, ECGRecord, Patient, User
from app.schemas import ECGIngestJobOut, ECGRecordCreate, ECGRecordOut, ECGRecordUpdate, WaveformResponse
from app.security import (
    get_current_user,
    patients_visible_to_organisation,
    require_roles,
    resolve_patient_id,
    scoped_organisation_id,
    user_can_access_patient_data,
)
from app.storage.file.filesystem import FilesystemArtifactStore
from app.config import get_settings
from app.waveform import build_meta, parse_ecg_metadata, read_waveform

router = APIRouter(prefix="/api/ecg-records", tags=["ecg"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_accessible_ecg(ecg_id: str, db: Session, user: User) -> ECGRecord:
    """Fetch an ECG record, enforcing the same read-access rule everywhere it's needed
    (get/waveform/download): patient sees only their own record, staff see only their
    own organisation's (superadmin sees all)."""
    obj = db.get(ECGRecord, ecg_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    if user.role == "patient":
        if resolve_patient_id(user, db) != obj.patient_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    elif user.role in ("admin", "doctor", "superadmin"):
        if not user_can_access_patient_data(user, obj.patient_id, db, home_organisation_id=obj.organisation_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return obj


def _check_patient_in_scope(patient: Patient, user: User) -> None:
    """Uploading/ingesting for a patient outside the caller's own organisation is refused."""
    if user.role != "superadmin" and patient.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")


@router.get("", response_model=list[ECGRecordOut])
def list_ecg(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "patient", "superadmin")),
    patient_id: str | None = Query(None, alias="patientId"),
    doctor_id: str | None = Query(None, alias="doctorId"),
    organisation_id: str | None = Query(None, alias="organisationId"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(ECGRecord)
    if user.role == "patient":
        stmt = stmt.where(ECGRecord.patient_id == resolve_patient_id(user, db))
    else:
        scoped_org = scoped_organisation_id(user)
        if scoped_org:
            stmt = stmt.where(ECGRecord.patient_id.in_(patients_visible_to_organisation(scoped_org)))
        elif organisation_id:
            stmt = stmt.where(ECGRecord.patient_id.in_(patients_visible_to_organisation(organisation_id)))
        if patient_id:
            stmt = stmt.where(ECGRecord.patient_id == patient_id)
        if doctor_id:
            stmt = stmt.where(ECGRecord.doctor_id == doctor_id)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.post("", response_model=ECGRecordOut, status_code=status.HTTP_201_CREATED)
def create_ecg(
    payload: ECGRecordCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "doctor", "superadmin")),
):
    """JSON-based creation (metadata only, no binary file)."""
    obj = ECGRecord(
        id=f"ecg-{uuid.uuid4().hex[:8]}",
        uploaded_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/upload", response_model=ECGRecordOut, status_code=status.HTTP_201_CREATED)
async def upload_ecg(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
    file: UploadFile = File(..., description="Waveform CSV (or other ECG file)"),
    ecg_metadata: UploadFile | None = File(None, alias="ecgMetadata"),
    patient_metadata: UploadFile | None = File(None, alias="patientMetadata"),
    patient_id: str = Form(..., alias="patientId"),
    doctor_id: str = Form("", alias="doctorId"),
    device_source: str = Form("", alias="deviceSource"),
    recording_date: str = Form("", alias="recordingDate"),
    notes: str = Form(""),
):
    """Multipart upload for the demo SAECG bundle.

    Accepts the waveform CSV plus optional ecg_metadata.json / patient_metadata.json
    sidecars, stores the raw file, and parses signal metadata into the record.
    """
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    _check_patient_in_scope(patient, user)

    ecg_id = f"ecg-{uuid.uuid4().hex[:8]}"
    ext = os.path.splitext(file.filename or "")[1] or ".csv"
    storage_path = os.path.join(UPLOAD_DIR, f"{ecg_id}{ext}")
    with open(storage_path, "wb") as f:
        f.write(await file.read())

    ecg_meta = parse_ecg_metadata(await ecg_metadata.read()) if ecg_metadata else {}

    meta = None
    if ext.lower() == ".csv":
        try:
            meta = build_meta(storage_path, ecg_meta)
        except Exception:  # noqa: BLE001 — parsing must never break the upload
            meta = None

    file_type = (ext.lstrip(".") or "BIN").upper()
    obj = ECGRecord(
        id=ecg_id,
        patient_id=patient_id,
        patient_name=patient.name,
        doctor_id=doctor_id or patient.assigned_doctor_id,
        organisation_id=patient.organisation_id,
        file_name=file.filename or f"{ecg_id}{ext}",
        file_type=file_type,
        recording_date=date.fromisoformat(recording_date) if recording_date else date.today(),
        device_source=device_source or (ecg_meta.get("device_model") or ""),
        notes=notes,
        status="Uploaded",
        uploaded_at=datetime.now(timezone.utc),
        uploaded_by=user.name,
        storage_path=storage_path,
    )
    if meta is not None:
        obj.source_format = meta.source_format or file_type
        obj.sampling_rate_hz = meta.sampling_rate_hz
        obj.lead_count = meta.lead_count
        obj.available_leads = meta.available_leads
        obj.xyz_available = meta.xyz_available
        obj.duration_seconds = meta.duration_seconds
        obj.sample_count = meta.sample_count
        obj.units = meta.units
        obj.record_id = meta.record_id

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _ingest_job_out(job: ECGIngestJob) -> ECGIngestJobOut:
    safe_error = None
    if job.error_code in {
        "FormatDetectionError",
        "UnsupportedFormatError",
        "MissingRequiredFileError",
        "MalformedFileError",
        "ValidationFailedError",
        "UploadTooLargeError",
        "DuplicateFilenameError",
    }:
        safe_error = job.error_message
    elif job.error_code in {"FileStorageError", "StorageError", "RuntimeError"}:
        safe_error = "Durable ECG artifact storage or processing failed. Retry after checking storage availability."
    elif job.error_code == "INGEST_JOB_STALE":
        safe_error = "ECG processing stopped before reaching a terminal state. Please retry."
    elif job.error_code:
        safe_error = "ECG processing failed. Please retry or contact support with the ingest job ID."
    return ECGIngestJobOut(
        id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        attempt_count=job.attempt_count,
        ecg_record_id=job.ecg_record_id,
        error_code=job.error_code,
        error_message=safe_error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        status_url=f"/api/ecg-records/ingest-jobs/{job.id}",
    )


@router.post("/ingest", response_model=ECGIngestJobOut, status_code=status.HTTP_202_ACCEPTED)
async def ingest_ecg(
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
    files: list[UploadFile] = File(..., description="One or more ECG source files (e.g. WFDB .hea+.dat pair)"),
    patient_id: str = Form(..., alias="patientId"),
    doctor_id: str = Form("", alias="doctorId"),
    device_source: str = Form("", alias="deviceSource"),
    recording_date: str = Form("", alias="recordingDate"),
    notes: str = Form(""),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Stages one upload and returns a persistent ingest operation immediately."""
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    _check_patient_in_scope(patient, user)

    upload_files = [(f.filename or "upload", await f.read()) for f in files]
    fingerprint = request_fingerprint(patient.id, upload_files)
    effective_key = effective_idempotency_key(
        organisation_id=patient.organisation_id,
        requested_by_user_id=user.id,
        fingerprint=fingerprint,
        supplied_key=idempotency_key,
    )
    upload_orchestrator = UploadOrchestrator()
    existing = db.scalar(select(ECGIngestJob).where(ECGIngestJob.idempotency_key == effective_key))
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Idempotency-Key was already used for a different ECG upload",
            )
        if existing.status != "FAILED" or existing.ecg_record_id:
            return _ingest_job_out(existing)
        # A retry reuses the same operation identity and can never create a
        # second canonical record for the same successful operation.
        retry_session = UploadOrchestrator().create_session(upload_files)
        existing.upload_id = retry_session.upload_id
        existing.file_names = [path.name for path in retry_session.files]
        existing.status = "QUEUED"
        existing.current_stage = None
        existing.error_code = None
        existing.error_message = None
        existing.started_at = None
        existing.completed_at = None
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        background.add_task(run_ingest_job, existing.id)
        return _ingest_job_out(existing)

    session = upload_orchestrator.create_session(upload_files)
    job, created = create_or_get_ingest_job(
        db,
        session=session,
        fingerprint=fingerprint,
        idempotency_key=effective_key,
        patient=patient,
        doctor_id=doctor_id,
        requested_by_user_id=user.id,
        uploaded_by=user.name,
        request_metadata={"deviceSource": device_source, "recordingDate": recording_date, "notes": notes},
    )
    if not created:
        upload_orchestrator.cleanup_session(session)
    else:
        background.add_task(run_ingest_job, job.id)
    return _ingest_job_out(job)


@router.get("/ingest-jobs/{job_id}", response_model=ECGIngestJobOut)
def get_ingest_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    job = db.get(ECGIngestJob, job_id)
    if job is None or (user.role != "superadmin" and job.organisation_id != user.organisation_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG ingest job not found")
    if job.status in {"QUEUED", "RUNNING"}:
        updated_at = job.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - updated_at).total_seconds() > get_settings().report_stale_after_seconds:
            job.status = "FAILED"
            job.error_code = "INGEST_JOB_STALE"
            job.error_message = "ECG processing stopped before reaching a terminal state"
            job.completed_at = datetime.now(timezone.utc)
            job.updated_at = job.completed_at
            db.commit()
    return _ingest_job_out(job)


@router.get("/{ecg_id}", response_model=ECGRecordOut)
def get_ecg(ecg_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_accessible_ecg(ecg_id, db, user)


@router.get("/{ecg_id}/waveform", response_model=WaveformResponse)
def get_waveform(
    ecg_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    leads: str | None = Query(None, description="Comma-separated lead names, e.g. I,II,V1"),
    max_points: int = Query(2000, ge=100, le=20000, alias="maxPoints"),
):
    """Return downsampled waveform samples for the ECG viewer."""
    obj = _get_accessible_ecg(ecg_id, db, user)
    if not obj.record_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This legacy record has no canonical waveform artifacts")
    try:
        from app.reporting.repositories.ecg_artifact_repository import ECGArtifactRepository

        bundle = ECGArtifactRepository().load_bundle(obj)
        if bundle.waveform_csv is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Canonical waveform CSV is unavailable")
        waveform_path = bundle.waveform_csv.absolute_path
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Canonical waveform artifact is unavailable or failed integrity verification",
        ) from exc

    requested = [l.strip() for l in leads.split(",")] if leads else None
    sel_leads, time_s, signals, factor = read_waveform(waveform_path, requested, max_points, obj.sample_count)
    return WaveformResponse(
        ecg_record_id=obj.id,
        sampling_rate_hz=obj.sampling_rate_hz,
        leads=sel_leads,
        point_count=len(time_s),
        downsample_factor=factor,
        time_s=time_s,
        signals=signals,
    )


@router.get("/{ecg_id}/artifact-manifest")
def get_artifact_manifest(
    ecg_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns integrity metadata without exposing private storage locations."""
    obj = _get_accessible_ecg(ecg_id, db, user)
    manifest = obj.artifact_manifest
    if not manifest and obj.record_id:
        try:
            manifest = FilesystemArtifactStore().read_json(obj.record_id, "manifest/artifact_manifest.json")
        except Exception as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, "Artifact manifest is unavailable") from exc
    if not manifest:
        raise HTTPException(status.HTTP_409_CONFLICT, "This record has no canonical artifact manifest")
    return {
        "schemaVersion": manifest.get("schemaVersion"),
        "recordId": manifest.get("recordId"),
        "durableStorageMode": manifest.get("durableStorageMode"),
        "verifiedAt": manifest.get("verifiedAt"),
        "artifacts": [
            {
                "relativePath": item.get("relativePath"),
                "sizeBytes": item.get("sizeBytes"),
                "checksumSha256": item.get("checksumSha256"),
                "mandatory": item.get("mandatory", False),
            }
            for item in manifest.get("artifacts", [])
        ],
    }


@router.get("/{ecg_id}/download")
def download_ecg(ecg_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Download the originally stored ECG file for this record."""
    obj = _get_accessible_ecg(ecg_id, db, user)
    download_path = obj.storage_path
    if obj.record_id:
        try:
            from app.reporting.repositories.ecg_artifact_repository import ECGArtifactRepository

            bundle = ECGArtifactRepository().load_bundle(obj)
            download_path = bundle.waveform_csv.absolute_path if bundle.waveform_csv else bundle.waveform.absolute_path
        except Exception as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, "Canonical ECG artifact is unavailable") from exc
    if not download_path or not os.path.exists(download_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No stored file for this record")
    return FileResponse(
        download_path,
        filename=obj.file_name or os.path.basename(download_path),
        media_type="application/octet-stream",
    )


@router.patch("/{ecg_id}", response_model=ECGRecordOut)
def update_ecg(
    ecg_id: str,
    payload: ECGRecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "doctor", "superadmin")),
):
    obj = db.get(ECGRecord, ecg_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{ecg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ecg(
    ecg_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "superadmin")),
):
    obj = db.get(ECGRecord, ecg_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    if user.role != "superadmin" and obj.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")

    storage_path = obj.storage_path
    canonical_record_id = obj.record_id

    # The row goes first: a recording still referenced by a generated report
    # must keep its artifacts, and removing files before the delete is known to
    # have succeeded would strand a row pointing at nothing.
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ECG record cannot be deleted while generated reports reference it",
        ) from exc

    if storage_path and os.path.exists(storage_path):
        os.remove(storage_path)
    if canonical_record_id:
        # Removes the whole record-scoped artifact tree (raw, waveform,
        # metadata, manifest, preprocessing), not just the waveform file.
        FilesystemArtifactStore().remove_record(canonical_record_id)
