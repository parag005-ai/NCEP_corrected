"""Report Generation API (Sprint 10.15).

    POST   /api/report-generation/jobs                      request a report
    GET    /api/report-generation/jobs                      job history for a recording
    GET    /api/report-generation/jobs/{job_id}             poll status and progress
    POST   /api/report-generation/jobs/{job_id}/cancel      cancel an unfinished job
    GET    /api/report-generation/reports                   report versions for a recording
    GET    /api/report-generation/reports/{report_id}       report metadata and artifacts
    GET    /api/report-generation/reports/{report_id}/html  the Detailed report document
    GET    /api/report-generation/reports/{report_id}/summary  the Summary, as data
    GET    /api/report-generation/reports/{report_id}/pdf   the Detailed report PDF
    GET    /api/report-generation/reports/{report_id}/artifacts/{artifact_id}

The API layer contains no business logic (Sprint 10.4): it authorizes, calls
the service or a repository, and shapes the response. Generation itself always
goes through the Workflow Orchestrator.

Access is resolved from the authenticated session. A client never supplies an
organisation, patient or doctor identifier, and never receives a filesystem
location -- documents are fetched by artifact identifier and streamed from a
path resolved on the server.
"""

from __future__ import annotations

from pathlib import Path

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.reporting.access import authorize_report_access, resolve_accessible_ecg
from app.reporting.api.schemas import (
    API_PREFIX,
    GeneratedReportOut,
    ReportArtifactOut,
    ReportGenerationJobOut,
    ReportGenerationRequest,
)
from app.reporting.api.service import create_generation_job, run_generation_job
from app.reporting.constants import ArtifactStatus, ArtifactType
from app.reporting.exceptions import (
    ConcurrentJobExecutionError,
    ECGRecordNotFoundError,
    InvalidJobTransitionError,
    ReportAccessDeniedError,
    ReportArtifactStorageError,
    ReportingError,
)
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.models.report_artifact import ReportArtifact
from app.reporting.orchestrator import build_orchestrator
from app.reporting.repositories.artifact_repository import ReportArtifactRepository
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository
from app.reporting.storage.artifact_store import ReportArtifactStore
from app.security import require_roles

router = APIRouter(prefix=API_PREFIX, tags=["report-generation"])

#: Only clinical staff request and cancel report generation. Patient access to
#: generated reports is a distribution feature the Sprint defers (10.26).
GENERATION_ROLES = ("admin", "doctor", "superadmin")
READ_ROLES = ("admin", "doctor", "superadmin")

#: Safe, human summaries for the failure categories a client may see. The
#: diagnostic text stored on the job can name internal paths, so it is never
#: returned (Sprint 10.24).
_SAFE_ERROR_MESSAGES = {
    "ECGArtifactUnavailableError": "The ECG recording has no report-ready artifacts.",
    "ECGRecordNotFoundError": "The ECG recording no longer exists.",
    "ReportAccessDeniedError": "The requester may not access this ECG recording.",
    "InconsistentContextError": "The recording's patient or organisation data is inconsistent.",
    "UpstreamRecordMissingError": "A record this report depends on no longer exists.",
    "WaveformReadError": "The recording's waveform could not be read.",
    "TemplateNotFoundError": "The report template is unavailable.",
    "TemplateRenderingError": "The report could not be composed into its template.",
    "PDFRenderingError": "The report PDF could not be produced.",
    "ArtifactIntegrityError": "A generated document failed its integrity check.",
    "REPORT_JOB_STALE": "Report generation stopped before reaching a terminal stage.",
    "REPORT_WORKER_EXCEPTION": "The report worker stopped unexpectedly.",
}
_GENERIC_ERROR_MESSAGE = "Report generation failed. The generation record has the details."


# ---------------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------------


def _http_error(exc: ReportingError) -> HTTPException:
    """Maps an internal failure onto a response that leaks nothing."""
    if isinstance(exc, ECGRecordNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "ECG record not found")
    if isinstance(exc, ReportAccessDeniedError):
        return HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    if isinstance(exc, (InvalidJobTransitionError, ConcurrentJobExecutionError)):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Report generation error")


# ---------------------------------------------------------------------------
# Response building
# ---------------------------------------------------------------------------


def _safe_error_message(job: ReportGenerationJob) -> str | None:
    if not job.error_code:
        return None
    return _SAFE_ERROR_MESSAGES.get(job.error_code, _GENERIC_ERROR_MESSAGE)


def _job_out(job: ReportGenerationJob, report: GeneratedReport | None) -> ReportGenerationJobOut:
    return ReportGenerationJobOut(
        id=job.id,
        ecg_record_id=job.ecg_record_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_stage=job.current_stage,
        failed_stage=job.failed_stage,
        attempt_count=job.attempt_count,
        error_code=job.error_code,
        error_message=_safe_error_message(job),
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        report_id=report.id if report else None,
        status_url=f"{API_PREFIX}/jobs/{job.id}",
        report_url=f"{API_PREFIX}/reports/{report.id}" if report else None,
    )


def _artifact_out(report: GeneratedReport, artifact: ReportArtifact) -> ReportArtifactOut:
    return ReportArtifactOut(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        content_type=artifact.content_type,
        file_size_bytes=artifact.file_size_bytes,
        checksum_sha256=artifact.checksum_sha256,
        status=artifact.status,
        generated_at=artifact.generated_at,
        artifact_metadata=artifact.artifact_metadata,
        download_url=f"{API_PREFIX}/reports/{report.id}/artifacts/{artifact.id}",
    )


def _report_out(report: GeneratedReport, artifacts: list[ReportArtifact]) -> GeneratedReportOut:
    available = {a.artifact_type for a in artifacts}
    return GeneratedReportOut(
        id=report.id,
        job_id=report.job_id,
        ecg_record_id=report.ecg_record_id,
        patient_id=report.patient_id,
        doctor_id=report.doctor_id,
        version=report.version,
        status=report.status,
        generated_at=report.generated_at,
        summary_template_id=report.summary_template_id,
        summary_template_version=report.summary_template_version,
        detailed_template_id=report.detailed_template_id,
        detailed_template_version=report.detailed_template_version,
        pipeline_version=report.pipeline_version,
        schema_version=report.schema_version,
        software_version=report.software_version,
        artifacts=[_artifact_out(report, a) for a in artifacts],
        html_url=(
            f"{API_PREFIX}/reports/{report.id}/html"
            if ArtifactType.DETAILED_HTML.value in available
            else None
        ),
        pdf_url=(
            f"{API_PREFIX}/reports/{report.id}/pdf"
            if ArtifactType.DETAILED_PDF.value in available
            else None
        ),
        summary_url=(
            f"{API_PREFIX}/reports/{report.id}/summary"
            if ArtifactType.SUMMARY_JSON.value in available
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def _accessible_report(report_id: str, db: Session, user: User) -> GeneratedReport:
    report = GeneratedReportRepository(db).get(report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    try:
        authorize_report_access(user, report, db)
    except ReportAccessDeniedError:
        # Indistinguishable from "does not exist", so a caller cannot probe
        # for reports belonging to another tenant.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found") from None
    return report


def _accessible_job(job_id: str, db: Session, user: User) -> ReportGenerationJob:
    repository = ReportGenerationJobRepository(db)
    job = repository.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report generation job not found")
    if user.role != "superadmin" and job.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report generation job not found")
    repository.fail_if_stale(job)
    return job


def _artifact_bytes(report: GeneratedReport, artifact: ReportArtifact) -> bytes:
    """The stored document's bytes, once it is verified and released for download.

    Reads through ``ReportArtifactStore`` (not a raw path check) so a document
    whose local copy was lost -- a host with no persistent disk recycling the
    instance that generated it -- is still served from its Cloudinary backup.
    """
    if artifact.status not in (ArtifactStatus.AVAILABLE.value, ArtifactStatus.ARCHIVED.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Report document is not yet available for download"
        )
    path = Path(report.storage_dir) / artifact.storage_location
    try:
        return ReportArtifactStore().read(path)
    except ReportArtifactStorageError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report document not found") from None


def _download(report: GeneratedReport, artifact: ReportArtifact, filename: str) -> Response:
    return Response(
        content=_artifact_bytes(report, artifact),
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _single_artifact(
    report: GeneratedReport, db: Session, artifact_type: ArtifactType
) -> ReportArtifact:
    artifacts = ReportArtifactRepository(db).list_for_report(report.id, artifact_type=artifact_type)
    if not artifacts:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report document not found")
    return artifacts[-1]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=ReportGenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
def request_report_generation(
    payload: ReportGenerationRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*GENERATION_ROLES)),
):
    """Queues a report generation and returns immediately (Sprint 3.2).

    The response carries the identifiers and the status URL a client needs to
    poll; generation continues in the background.
    """
    try:
        job = create_generation_job(db, user, payload.ecg_record_id)
    except ReportingError as exc:
        raise _http_error(exc) from exc

    background.add_task(run_generation_job, job.id)
    return _job_out(job, None)


@router.get("/jobs", response_model=list[ReportGenerationJobOut])
def list_generation_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
    ecg_record_id: str = Query(..., alias="ecgRecordId"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Generation history for one recording, most recent first."""
    try:
        record = resolve_accessible_ecg(db, user, ecg_record_id)
    except ReportingError as exc:
        raise _http_error(exc) from exc

    reports = GeneratedReportRepository(db)
    job_repository = ReportGenerationJobRepository(db)
    jobs = job_repository.list_for_ecg_record(
        record.id, limit=limit, offset=offset
    )
    for job in jobs:
        job_repository.fail_if_stale(job)
    return [_job_out(job, reports.get_by_job(job.id)) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ReportGenerationJobOut)
def get_generation_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    """Current status, stage and progress of one generation (Sprint 3.13)."""
    job = _accessible_job(job_id, db, user)
    return _job_out(job, GeneratedReportRepository(db).get_by_job(job.id))


@router.post("/jobs/{job_id}/cancel", response_model=ReportGenerationJobOut)
def cancel_generation_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*GENERATION_ROLES)),
):
    """Cancels a job that has not finished.

    A finished job cannot be cancelled; the job state machine decides, and a
    refusal is a conflict rather than an error.
    """
    job = _accessible_job(job_id, db, user)
    try:
        build_orchestrator(db).cancel(job)
    except ReportingError as exc:
        raise _http_error(exc) from exc
    return _job_out(job, GeneratedReportRepository(db).get_by_job(job.id))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.get("/reports", response_model=list[GeneratedReportOut])
def list_generated_reports(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
    ecg_record_id: str = Query(..., alias="ecgRecordId"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Every report version generated for one recording, newest first."""
    try:
        record = resolve_accessible_ecg(db, user, ecg_record_id)
    except ReportingError as exc:
        raise _http_error(exc) from exc

    artifacts = ReportArtifactRepository(db)
    reports = GeneratedReportRepository(db).list_for_ecg_record(
        record.id, limit=limit, offset=offset
    )
    return [_report_out(r, artifacts.list_for_report(r.id)) for r in reports]


@router.get("/reports/{report_id}", response_model=GeneratedReportOut)
def get_generated_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    """Report metadata, provenance and the documents it produced."""
    report = _accessible_report(report_id, db, user)
    return _report_out(report, ReportArtifactRepository(db).list_for_report(report.id))


@router.get("/reports/{report_id}/summary")
def get_report_summary(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
) -> dict:
    """The Summary Report of this version, as structured data.

    The Summary's presentation belongs to the frontend, so the backend serves
    the document the Summary builder composed during this generation. It is
    returned exactly as it was persisted -- never recomposed on read -- so a
    historical report always reports what it reported when it was generated.

    The payload carries the report identity and version, the generation
    provenance, and every section in order with its values, availability
    states, placeholders, notes and figure references.
    """
    report = _accessible_report(report_id, db, user)
    artifact = _single_artifact(report, db, ArtifactType.SUMMARY_JSON)
    data = _artifact_bytes(report, artifact)
    try:
        return json.loads(data.decode("utf-8"))
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Summary report data not found"
        ) from exc


@router.get("/reports/{report_id}/html", response_class=Response)
def download_report_html(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    """The canonical Detailed report document."""
    report = _accessible_report(report_id, db, user)
    artifact = _single_artifact(report, db, ArtifactType.DETAILED_HTML)
    return _download(report, artifact, f"ncep-report-{report.id}-v{report.version}.html")


@router.get("/reports/{report_id}/pdf", response_class=Response)
def download_report_pdf(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    """The Detailed report as a downloadable PDF."""
    report = _accessible_report(report_id, db, user)
    artifact = _single_artifact(report, db, ArtifactType.DETAILED_PDF)
    return _download(report, artifact, f"ncep-report-{report.id}-v{report.version}.pdf")


@router.get("/reports/{report_id}/artifacts/{artifact_id}", response_class=Response)
def download_report_artifact(
    report_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    """Any registered document of a report, by identifier."""
    report = _accessible_report(report_id, db, user)
    artifact = ReportArtifactRepository(db).get(artifact_id)
    if artifact is None or artifact.report_id != report.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report document not found")

    suffix = Path(artifact.storage_location).suffix
    return _download(report, artifact, f"ncep-report-{report.id}-{artifact.artifact_type.lower()}{suffix}")

