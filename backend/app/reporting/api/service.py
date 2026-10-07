"""Application service behind the Report Generation API (Sprint 10.4 / 10.7).

Sits between the HTTP layer and the Workflow Orchestrator: it authorizes the
request, creates the job, and hands execution to a background runner so the
request returns immediately (Sprint 3.2 asynchronous generation).

It adds no report-generation logic of its own -- every stage of the pipeline
is the orchestrator's, and every persisted decision is the repositories'.

Background execution uses the ASGI server's own background-task mechanism: no
queue, broker or scheduler is introduced, because the orchestrator is a plain
synchronous callable and the repository has no such infrastructure. The runner
opens its own database session, since the request's session is closed as soon
as the response is sent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.reporting.access import resolve_accessible_ecg
from app.reporting.constants import JobStatus, PipelineStage
from app.reporting.models.execution import JobFailure
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.orchestrator import build_orchestrator
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.security import resolve_doctor_id

logger = logging.getLogger(__name__)


def create_generation_job(
    session: Session, requester: User, ecg_record_id: str
) -> ReportGenerationJob:
    """Authorizes the request and queues a report generation.

    Tenant and lineage come from the recording, never from the caller: the
    request carries only which recording to report on.

    Raises:
        ECGRecordNotFoundError: no such recording.
        ReportAccessDeniedError: the recording is outside the caller's reach.
    """
    record = resolve_accessible_ecg(session, requester, ecg_record_id)
    orchestrator = build_orchestrator(session)
    job = orchestrator.create_job(
        ecg_record_id=record.id,
        patient_id=record.patient_id,
        organisation_id=record.organisation_id,
        requested_by_user_id=requester.id,
        requested_by_doctor_id=resolve_doctor_id(requester, session),
    )
    logger.info(
        "report generation requested job_id=%s ecg_record_id=%s by=%s",
        job.id,
        record.id,
        requester.id,
    )
    return job


def run_generation_job(job_id: str) -> None:
    """Executes a queued job on its own session, outside the request cycle.

    Never raises: a background task that propagated would be logged by the
    server and lost. Pipeline failures are already recorded on the job by the
    orchestrator, which also rolls back partial output.
    """
    session = SessionLocal()
    try:
        job = ReportGenerationJobRepository(session).get(job_id)
        if job is None:
            logger.warning("report generation job %s vanished before execution", job_id)
            return
        build_orchestrator(session).run(job)
    except Exception:  # noqa: BLE001 -- a background failure must not escape
        logger.exception("report generation job %s could not be executed", job_id)
        session.rollback()
        job = ReportGenerationJobRepository(session).get(job_id)
        if job is not None and job.status not in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        }:
            stage = None
            if job.current_stage:
                try:
                    stage = PipelineStage(job.current_stage)
                except ValueError:
                    stage = None
            ReportGenerationJobRepository(session).update_execution_state(
                job,
                status=JobStatus.FAILED,
                completed_at=datetime.now(timezone.utc),
                failure=JobFailure(
                    code="REPORT_WORKER_EXCEPTION",
                    message="The report worker terminated unexpectedly",
                    stage=stage,
                ),
            )
            session.commit()
    finally:
        session.close()
