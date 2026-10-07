"""Persistence for Report Generation Jobs (Sprint 2.18 / 10.8).

Database operations only. This repository never decides *whether* a state
transition is legal, whether a stage may be retried, or what the next stage
is -- those decisions belong exclusively to the Workflow Orchestrator
(Sprint 3.12). It only records what the orchestrator has decided.

Transaction policy: every method flushes so that database constraints fail
fast, and never commits. The caller (orchestrator or API layer) owns the
transaction boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.reporting.constants import JobStatus, PipelineStage, REPORT_PIPELINE_VERSION
from app.config import get_settings
from app.reporting.exceptions import ReportJobNotFoundError
from app.reporting.models.execution import JobFailure, StageExecution
from app.reporting.models.generation_job import ReportGenerationJob


class ReportGenerationJobRepository:
    """Creates, reads and updates ``ReportGenerationJob`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        ecg_record_id: str,
        patient_id: str,
        organisation_id: str,
        requested_by_user_id: str,
        requested_by_doctor_id: str | None = None,
        status: JobStatus = JobStatus.REQUESTED,
        pipeline_version: str = REPORT_PIPELINE_VERSION,
    ) -> ReportGenerationJob:
        """Persists a new report generation job.

        Lineage identifiers are supplied by the caller, which has already
        resolved and authorized them against the upstream modules; the
        foreign keys on the row are the final integrity guarantee.
        """
        now = datetime.now(timezone.utc)
        job = ReportGenerationJob(
            ecg_record_id=ecg_record_id,
            patient_id=patient_id,
            organisation_id=organisation_id,
            requested_by_user_id=requested_by_user_id,
            requested_by_doctor_id=requested_by_doctor_id,
            status=status.value,
            progress_percent=0,
            attempt_count=0,
            stage_history=[],
            pipeline_version=pipeline_version,
            created_at=now,
            updated_at=now,
        )
        self._session.add(job)
        self._session.flush()
        return job

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, job_id: str) -> ReportGenerationJob | None:
        """Returns the job, or None when it does not exist."""
        return self._session.get(ReportGenerationJob, job_id)

    def require(self, job_id: str) -> ReportGenerationJob:
        """Returns the job, raising ``ReportJobNotFoundError`` when absent."""
        job = self.get(job_id)
        if job is None:
            raise ReportJobNotFoundError(f"Report generation job {job_id!r} does not exist")
        return job

    def list_for_ecg_record(
        self, ecg_record_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[ReportGenerationJob]:
        """Job history for one recording, most recently created first."""
        stmt = (
            select(ReportGenerationJob)
            .where(ReportGenerationJob.ecg_record_id == ecg_record_id)
            .order_by(ReportGenerationJob.created_at.desc(), ReportGenerationJob.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(stmt))

    # ------------------------------------------------------------------
    # Execution state
    # ------------------------------------------------------------------

    def update_execution_state(
        self,
        job: ReportGenerationJob,
        *,
        status: JobStatus | None = None,
        current_stage: PipelineStage | None = None,
        progress_percent: int | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        failure: JobFailure | None = None,
    ) -> ReportGenerationJob:
        """Applies the execution state the orchestrator has decided.

        Only the arguments that are supplied are written; every other field
        keeps its current value. ``updated_at`` is always refreshed.
        """
        if status is not None:
            job.status = status.value
        if current_stage is not None:
            job.current_stage = current_stage.value
        if progress_percent is not None:
            job.progress_percent = progress_percent
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at
        if failure is not None:
            job.failed_stage = failure.stage.value if failure.stage else None
            job.error_code = failure.code
            job.error_message = failure.message
        job.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return job

    def append_stage_execution(
        self, job: ReportGenerationJob, execution: StageExecution
    ) -> ReportGenerationJob:
        """Appends one stage execution record to the job's history (Sprint 3.11).

        The history list is replaced rather than mutated in place so that the
        change is detected on a JSON column, and so that already-recorded
        executions are never modified.
        """
        job.stage_history = [*job.stage_history, execution.to_dict()]
        job.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return job

    def claim(
        self, job: ReportGenerationJob, *, expected: JobStatus, target: JobStatus
    ) -> bool:
        """Moves a job to ``target`` only if it is still in ``expected``.

        A single conditional UPDATE, so two workers racing to execute the same
        job cannot both win: the loser's statement matches no row. Returns
        whether this caller claimed the job.
        """
        claimed = self._session.execute(
            update(ReportGenerationJob)
            .where(
                ReportGenerationJob.id == job.id,
                ReportGenerationJob.status == expected.value,
            )
            .values(status=target.value, updated_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session="fetch")
        ).rowcount
        self._session.flush()
        return claimed == 1

    def increment_attempt(self, job: ReportGenerationJob) -> ReportGenerationJob:
        """Records that the orchestrator has started another execution attempt."""
        job.attempt_count += 1
        job.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return job

    def fail_if_stale(self, job: ReportGenerationJob) -> bool:
        """Marks an abandoned RUNNING job terminal when its heartbeat is stale."""
        if job.status != JobStatus.RUNNING.value:
            return False
        updated_at = job.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()
        if age_seconds <= get_settings().report_stale_after_seconds:
            return False
        stage = None
        if job.current_stage:
            try:
                stage = PipelineStage(job.current_stage)
            except ValueError:
                stage = None
        self.update_execution_state(
            job,
            status=JobStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
            failure=JobFailure(
                code="REPORT_JOB_STALE",
                message=f"Report job stopped updating for more than {get_settings().report_stale_after_seconds} seconds",
                stage=stage,
            ),
        )
        self._session.commit()
        return True
