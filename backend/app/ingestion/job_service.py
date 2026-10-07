"""Persistent asynchronous lifecycle for canonical ECG ingestion."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.ingestion.exceptions import IngestionError
from app.ingestion.record_creator import create_ecg_record
from app.ingestion.storage.artifacts import to_jsonable
from app.ingestion.storage.orchestrator import StorageOrchestrator
from app.ingestion.upload_orchestrator import UploadOrchestrator, UploadSession
from app.models import ECGIngestJob, ECGRecord, Patient
from app.preprocessing.pipeline import (
    PreprocessingOrchestrator,
    generate_preprocessed_artifact,
    generate_preprocessing_report,
)
from app.storage.file.filesystem import FilesystemArtifactStore

logger = logging.getLogger(__name__)

# A canonical ECG is not successful unless every item below plus every raw
# uploaded companion file is durable and checksum-verified.
CANONICAL_MANDATORY_ARTIFACTS: tuple[str, ...] = (
    "waveform/waveform.npz",
    "waveform/waveform.csv",
    "waveform/waveform_meta.json",
    "metadata/patient_metadata.json",
    "metadata/ecg_metadata.json",
    "metadata/clinical_metadata.json",
    "metadata/device_metadata.json",
    "metadata/quality_metadata.json",
    "metadata/annotations.json",
    "metadata/source_information.json",
    "manifest/manifest.json",
    "preprocessing/preprocessed.npz",
    "preprocessing/preprocessing_report.json",
)


def create_or_get_ingest_job(
    db: Session,
    *,
    session: UploadSession,
    fingerprint: str,
    idempotency_key: str,
    patient: Patient,
    doctor_id: str,
    requested_by_user_id: str,
    uploaded_by: str,
    request_metadata: dict,
) -> tuple[ECGIngestJob, bool]:
    existing = db.scalar(select(ECGIngestJob).where(ECGIngestJob.idempotency_key == idempotency_key))
    if existing is not None:
        return existing, False

    now = datetime.now(timezone.utc)
    job = ECGIngestJob(
        id=f"igj-{uuid.uuid4().hex[:12]}",
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        patient_id=patient.id,
        doctor_id=doctor_id or patient.assigned_doctor_id or "",
        organisation_id=patient.organisation_id,
        requested_by_user_id=requested_by_user_id,
        uploaded_by=uploaded_by,
        upload_id=session.upload_id,
        file_names=[path.name for path in session.files],
        request_metadata=request_metadata,
        status="QUEUED",
        attempt_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ECGIngestJob).where(ECGIngestJob.idempotency_key == idempotency_key))
        if existing is None:
            raise
        return existing, False
    db.refresh(job)
    return job, True


def _update_job(db: Session, job: ECGIngestJob, **fields) -> None:
    for name, value in fields.items():
        setattr(job, name, value)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def _build_ecg_row(
    *, record, manifest, preprocessing, storage_result, store: FilesystemArtifactStore,
    patient: Patient, file_names: list[str], doctor_id: str, request_metadata: dict,
    uploaded_by: str, artifact_manifest: dict,
) -> ECGRecord:
    from datetime import date

    recording_date = request_metadata.get("recordingDate") or ""
    return ECGRecord(
        id=f"ecg-{uuid.uuid4().hex[:8]}",
        patient_id=patient.id,
        patient_name=patient.name,
        doctor_id=doctor_id or patient.assigned_doctor_id or "",
        organisation_id=patient.organisation_id,
        file_name=", ".join(file_names),
        file_type=record.ecg_metadata.source_format.value,
        recording_date=date.fromisoformat(recording_date) if recording_date else date.today(),
        device_source=request_metadata.get("deviceSource") or (record.device_metadata.model or ""),
        notes=request_metadata.get("notes") or "",
        status="Uploaded",
        uploaded_at=datetime.now(timezone.utc),
        uploaded_by=uploaded_by,
        storage_path=str(store.record_dir(record.record_id) / "waveform" / "waveform.csv"),
        source_format=record.ecg_metadata.source_format.value,
        sampling_rate_hz=record.ecg_metadata.sampling_rate_hz,
        lead_count=record.ecg_metadata.lead_count,
        available_leads=[lead.value for lead in record.ecg_metadata.available_leads],
        xyz_available=record.ecg_metadata.xyz_available,
        duration_seconds=record.ecg_metadata.recording_duration_seconds,
        sample_count=record.ecg_metadata.sample_count,
        units=record.ecg_metadata.units,
        record_id=record.record_id,
        record_dir=str(storage_result.record_dir),
        validation_status=manifest.validation_status.value if manifest else None,
        validation_issues=[to_jsonable(dataclasses.asdict(issue)) for issue in manifest.validation_issues] if manifest else None,
        quality_score=preprocessing.quality_score,
        quality_flags=list(preprocessing.quality_flags),
        beat_count=preprocessing.beat_count,
        artifact_manifest=artifact_manifest,
    )


def run_ingest_job(job_id: str) -> None:
    """Runs after the 202 response and persists a terminal job state."""
    with SessionLocal() as db:
        job = db.get(ECGIngestJob, job_id)
        if job is None or job.status != "QUEUED":
            return
        _update_job(
            db,
            job,
            status="RUNNING",
            current_stage="LOAD_STAGED_UPLOAD",
            attempt_count=job.attempt_count + 1,
            started_at=job.started_at or datetime.now(timezone.utc),
            error_code=None,
            error_message=None,
        )

        upload_orchestrator = UploadOrchestrator()
        store = FilesystemArtifactStore()
        upload_session: UploadSession | None = None
        canonical_record_id: str | None = None
        try:
            upload_session = upload_orchestrator.get_session(job.upload_id)
            patient = db.get(Patient, job.patient_id)
            if patient is None or patient.organisation_id != job.organisation_id:
                raise RuntimeError("The ingest job's patient is no longer available in its organisation")

            _update_job(db, job, current_stage="INGEST_CANONICAL_RECORD")
            result = create_ecg_record(
                upload_session.upload_id,
                list(upload_session.files),
                storage=StorageOrchestrator(store=store),
            )
            canonical_record_id = result.record.record_id

            _update_job(db, job, current_stage="PREPROCESS")
            preprocessing = PreprocessingOrchestrator.run(result.record.waveform)
            store.write_bytes(
                canonical_record_id,
                "preprocessing/preprocessed.npz",
                generate_preprocessed_artifact(preprocessing),
            )
            store.write_json(
                canonical_record_id,
                "preprocessing/preprocessing_report.json",
                generate_preprocessing_report(preprocessing),
            )

            _update_job(db, job, current_stage="VERIFY_DURABLE_ARTIFACTS")
            required_paths = [
                *CANONICAL_MANDATORY_ARTIFACTS,
                *(f"raw/{path.name}" for path in upload_session.files),
            ]
            artifact_manifest = store.finalize_artifact_manifest(canonical_record_id, required_paths)

            _update_job(db, job, current_stage="COMMIT_RECORD")
            obj = _build_ecg_row(
                record=result.record,
                manifest=result.storage.manifest,
                preprocessing=preprocessing,
                storage_result=result.storage,
                store=store,
                patient=patient,
                file_names=job.file_names,
                doctor_id=job.doctor_id,
                request_metadata=job.request_metadata,
                uploaded_by=job.uploaded_by,
                artifact_manifest=artifact_manifest,
            )
            db.add(obj)
            db.flush()
            job.ecg_record_id = obj.id
            job.status = "SUCCEEDED"
            job.current_stage = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            job.updated_at = job.completed_at
            db.commit()
        except Exception as exc:  # noqa: BLE001 -- every failure must become terminal
            db.rollback()
            if canonical_record_id:
                store.remove_record(canonical_record_id)
            job = db.get(ECGIngestJob, job_id)
            if job is not None:
                job.status = "FAILED"
                job.error_code = type(exc).__name__
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = job.completed_at
                db.commit()
            if isinstance(exc, IngestionError):
                logger.info("ECG ingest job %s failed at %s: %s", job_id, exc.stage, exc)
            else:
                logger.exception("ECG ingest job %s failed", job_id)
        finally:
            if upload_session is not None:
                upload_orchestrator.cleanup_session(upload_session)
