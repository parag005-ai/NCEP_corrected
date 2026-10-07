"""Generation Context Loader (Sprint 3.6).

Collects every piece of information a report generation needs -- organisation,
patient, doctor, ECG record, ECG artifacts and (from Phase 2) Signal
Processing outputs -- into one immutable Generation Context, before any
pipeline stage runs. No downstream stage communicates with an upstream module
again (Sprint 3.6 / 6.5).

Tenant safety is enforced here rather than assumed. The loader trusts nothing
that was written onto the job row: it re-resolves every upstream record from
the ECG recording itself, re-checks that the job's requester may still access
that recording under the platform's own ownership rules, and refuses to build
a context whose records disagree with each other (Sprint 5.12 consistency
validation, 10.10 authorization, 10.24 organisation isolation).

Every failure raised here is a critical failure (Sprint 2.12 / 3.14): the
orchestrator terminates the job and no partial report is exposed. The single
recoverable case is an unresolvable doctor, which yields a context with no
doctor rather than an error.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Doctor, ECGRecord, Organisation, Patient, User
from app.reporting.access import authorize_ecg_access
from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    REPORT_SCHEMA_VERSION,
    REPORTING_SOFTWARE_VERSION,
)
from app.reporting.context.generation_context import (
    DoctorContext,
    ECGRecordContext,
    GenerationContext,
    GenerationMetadata,
    OrganisationContext,
    PatientContext,
    RecordingQualitySummary,
)
from app.reporting.context.signal_processing_builder import build_signal_processing_outputs
from app.reporting.exceptions import (
    ECGArtifactUnavailableError,
    ECGRecordNotFoundError,
    InconsistentContextError,
    UpstreamRecordMissingError,
)
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.repositories.ecg_artifact_repository import ECGArtifactRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository


class GenerationContextLoader:
    """Builds the immutable Generation Context for one report generation job."""

    def __init__(
        self,
        session: Session,
        *,
        artifacts: ECGArtifactRepository | None = None,
        reports: GeneratedReportRepository | None = None,
    ) -> None:
        self._session = session
        self._artifacts = artifacts or ECGArtifactRepository()
        self._reports = reports or GeneratedReportRepository(session)

    def load(self, job: ReportGenerationJob) -> GenerationContext:
        """Collects and validates everything required to generate both report variants.

        Raises:
            ECGRecordNotFoundError: the recording no longer exists.
            UpstreamRecordMissingError: a mandatory upstream record is absent.
            ReportAccessDeniedError: the requester may not access the recording.
            InconsistentContextError: the upstream records disagree.
            ECGArtifactUnavailableError: the canonical ECG artifacts are unreadable.
        """
        record = self._session.get(ECGRecord, job.ecg_record_id)
        if record is None:
            raise ECGRecordNotFoundError(f"ECG record {job.ecg_record_id!r} does not exist")

        requester = self._require_user(job.requested_by_user_id)
        self._authorize(requester, record)
        self._verify_job_matches_record(job, record)

        organisation = self._require_organisation(record)
        patient = self._require_patient(record)
        doctor = self._resolve_doctor(record, patient)

        ecg_context = self._build_ecg_context(record)
        artifacts = self._load_artifacts_with_timeout(record)

        return GenerationContext(
            generation=GenerationMetadata(
                job_id=job.id,
                ecg_record_id=record.id,
                requested_by_user_id=requester.id,
                report_version=self._reports.next_version(record.id),
                generated_at=datetime.now(timezone.utc),
                pipeline_version=job.pipeline_version or REPORT_PIPELINE_VERSION,
                schema_version=REPORT_SCHEMA_VERSION,
                software_version=REPORTING_SOFTWARE_VERSION,
            ),
            organisation=self._build_organisation_context(organisation),
            patient=self._build_patient_context(patient),
            doctor=self._build_doctor_context(doctor) if doctor is not None else None,
            ecg=ecg_context,
            artifacts=artifacts,
            # Real, computed sections (raw measurements only -- see
            # app/signal_processing/README.md for what is deliberately not
            # included pending the medical team's confirmation), degrading
            # to the Phase 1 all-awaiting placeholder if the waveform can't
            # be read or analysis fails unexpectedly (Sprint 3.15 No
            # Fabrication Policy: absent data says so, it is never invented).
            signal_processing=self._build_signal_processing_with_timeout(
                artifacts,
                ecg_record_id=record.id,
                fallback_sampling_rate_hz=ecg_context.sampling_rate_hz,
                fallback_units=ecg_context.units,
            ),
        )

    def _load_artifacts_with_timeout(self, record: ECGRecord):
        """Bounds durable-store access so the job can always reach FAILED."""
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ecg-artifact-load")
        future = executor.submit(self._artifacts.load_bundle, record)
        try:
            return future.result(timeout=get_settings().report_context_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ECGArtifactUnavailableError(
                f"Timed out loading canonical artifacts for ECG record {record.id!r}"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _build_signal_processing_with_timeout(
        self, artifacts, *, ecg_record_id: str, fallback_sampling_rate_hz, fallback_units
    ):
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="report-signal-processing")
        future = executor.submit(
            build_signal_processing_outputs,
            artifacts,
            ecg_record_id=ecg_record_id,
            fallback_sampling_rate_hz=fallback_sampling_rate_hz,
            fallback_units=fallback_units,
        )
        try:
            return future.result(timeout=get_settings().report_context_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ECGArtifactUnavailableError(
                f"Timed out preparing signal-processing context for ECG record {ecg_record_id!r}"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------------
    # Authorization and consistency
    # ------------------------------------------------------------------

    def _require_user(self, user_id: str) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise UpstreamRecordMissingError(
                f"Requesting user {user_id!r} no longer exists; report generation cannot be attributed"
            )
        return user

    def _authorize(self, requester: User, record: ECGRecord) -> None:
        """Re-applies the platform's ECG ownership rules to the persisted job.

        The same rule the API applied when it accepted the request, checked
        again here so a job can never be executed for a recording its
        requester may not reach (see ``app.reporting.access``).
        """
        authorize_ecg_access(requester, record, self._session)

    def _verify_job_matches_record(self, job: ReportGenerationJob, record: ECGRecord) -> None:
        """Refuses a job whose stored lineage disagrees with the recording.

        The job row is written before the pipeline runs; if the recording has
        since been re-assigned, or the job was created with mismatched
        identifiers, the report would present one patient's or tenant's data
        under another's identity.
        """
        if job.patient_id != record.patient_id:
            raise InconsistentContextError(
                f"Job {job.id!r} references patient {job.patient_id!r} but ECG record {record.id!r} "
                f"belongs to patient {record.patient_id!r}"
            )
        if job.organisation_id != record.organisation_id:
            raise InconsistentContextError(
                f"Job {job.id!r} references organisation {job.organisation_id!r} but ECG record "
                f"{record.id!r} belongs to organisation {record.organisation_id!r}"
            )

    def _require_organisation(self, record: ECGRecord) -> Organisation:
        organisation = self._session.get(Organisation, record.organisation_id)
        if organisation is None:
            raise UpstreamRecordMissingError(
                f"Organisation {record.organisation_id!r} of ECG record {record.id!r} does not exist"
            )
        return organisation

    def _require_patient(self, record: ECGRecord) -> Patient:
        patient = self._session.get(Patient, record.patient_id)
        if patient is None:
            raise UpstreamRecordMissingError(
                f"Patient {record.patient_id!r} of ECG record {record.id!r} does not exist"
            )
        if patient.organisation_id != record.organisation_id:
            raise InconsistentContextError(
                f"Patient {patient.id!r} belongs to organisation {patient.organisation_id!r} but ECG "
                f"record {record.id!r} belongs to organisation {record.organisation_id!r}"
            )
        return patient

    def _resolve_doctor(self, record: ECGRecord, patient: Patient) -> Doctor | None:
        """The clinician the recording is attributed to, if one can be resolved.

        The recording's own ``doctor_id`` wins; the patient's assigned doctor
        is the fallback. An unresolvable doctor is a recoverable condition
        (Sprint 3.14) and produces a context without doctor information rather
        than a failure. A doctor from another organisation is not recoverable.
        """
        for doctor_id in (record.doctor_id, patient.assigned_doctor_id):
            if not doctor_id:
                continue
            doctor = self._session.get(Doctor, doctor_id)
            if doctor is None:
                continue
            if doctor.organisation_id != record.organisation_id:
                raise InconsistentContextError(
                    f"Doctor {doctor.id!r} belongs to organisation {doctor.organisation_id!r} but ECG "
                    f"record {record.id!r} belongs to organisation {record.organisation_id!r}"
                )
            return doctor
        return None

    # ------------------------------------------------------------------
    # Context construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_organisation_context(organisation: Organisation) -> OrganisationContext:
        return OrganisationContext(
            organisation_id=organisation.id,
            name=organisation.name,
            address=organisation.address,
            contact=organisation.contact,
        )

    @staticmethod
    def _build_patient_context(patient: Patient) -> PatientContext:
        return PatientContext(
            patient_id=patient.id,
            name=patient.name,
            age=patient.age,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            status=patient.status,
            medical_notes=patient.medical_notes,
        )

    @staticmethod
    def _build_doctor_context(doctor: Doctor) -> DoctorContext:
        return DoctorContext(
            doctor_id=doctor.id,
            name=doctor.name,
            speciality=doctor.speciality,
            staff_id=doctor.staff_id,
            role=doctor.role,
        )

    @staticmethod
    def _build_ecg_context(record: ECGRecord) -> ECGRecordContext:
        return ECGRecordContext(
            ecg_record_id=record.id,
            canonical_record_id=record.record_id or "",
            file_name=record.file_name,
            file_type=record.file_type,
            source_format=record.source_format,
            device_source=record.device_source,
            recording_date=record.recording_date,
            uploaded_at=record.uploaded_at,
            uploaded_by=record.uploaded_by,
            sampling_rate_hz=record.sampling_rate_hz,
            lead_count=record.lead_count,
            available_leads=tuple(record.available_leads or ()),
            xyz_available=record.xyz_available,
            duration_seconds=record.duration_seconds,
            sample_count=record.sample_count,
            units=record.units,
            notes=record.notes,
            quality=RecordingQualitySummary(
                quality_score=record.quality_score,
                quality_flags=tuple(record.quality_flags or ()),
                beat_count=record.beat_count,
                validation_status=record.validation_status,
                validation_issues=tuple(record.validation_issues or ()),
            ),
        )
