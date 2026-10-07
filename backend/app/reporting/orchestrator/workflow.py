"""Workflow Orchestrator -- the central controller of report generation.

Sprint 3.5 / 10.7 responsibilities: start report generation, coordinate stage
execution, maintain execution order, update job progress, handle retries,
record stage history, manage failures, and finalize the job.

It contains no clinical logic, performs no rendering, no visualization and no
composition: it decides *what runs next and what the job's state becomes*,
and delegates all work to the stages it was given. Stages are injected, so the
orchestrator never imports a domain package and later increments extend the
pipeline without touching this module.

Execution is synchronous here on purpose. Scheduling -- running a job on a
background worker so the API can return immediately (Sprint 3.2) -- is the
responsibility of the API layer that will call ``run()``; keeping the two
separate lets the same orchestration logic run inline in tests and in the
background in production.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    JobStatus,
    PipelineStage,
    StageStatus,
)
from app.reporting.context.generation_context import GenerationContext
from app.reporting.exceptions import (
    ConcurrentJobExecutionError,
    PipelineDefinitionError,
    ReportingError,
)
from app.reporting.models.execution import JobFailure, StageExecution
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.orchestrator.cleanup import JobFailureCleanup
from app.reporting.orchestrator.stage import ReportPipelineStage, StageInput, StageResult
from app.reporting.orchestrator.state_machine import JobStateMachine
from app.reporting.repositories.job_repository import ReportGenerationJobRepository

logger = logging.getLogger(__name__)

#: Maximum attempts per stage, including the first. Retries apply only to
#: failures that declare themselves transient (Sprint 3.16).
DEFAULT_MAX_STAGE_ATTEMPTS = 3


class WorkflowOrchestrator:
    """Creates report generation jobs and drives them through the pipeline."""

    def __init__(
        self,
        session: Session,
        stages: Iterable[ReportPipelineStage],
        *,
        jobs: ReportGenerationJobRepository | None = None,
        cleanup: JobFailureCleanup | None = None,
        max_stage_attempts: int = DEFAULT_MAX_STAGE_ATTEMPTS,
    ) -> None:
        self._session = session
        self._jobs = jobs or ReportGenerationJobRepository(session)
        self._stages = tuple(stages)
        self._cleanup = cleanup
        self._max_stage_attempts = max(1, max_stage_attempts)
        self._validate_stage_order()

    # ------------------------------------------------------------------
    # Job creation
    # ------------------------------------------------------------------

    def create_job(
        self,
        *,
        ecg_record_id: str,
        patient_id: str,
        organisation_id: str,
        requested_by_user_id: str,
        requested_by_doctor_id: str | None = None,
    ) -> ReportGenerationJob:
        """Records a report generation request and queues it for execution.

        The job is persisted as ``REQUESTED`` and immediately moved to
        ``QUEUED``: it is accepted and waiting for a runner to pick it up
        (Sprint 10.6). Execution begins when ``run`` is called.
        """
        job = self._jobs.create(
            ecg_record_id=ecg_record_id,
            patient_id=patient_id,
            organisation_id=organisation_id,
            requested_by_user_id=requested_by_user_id,
            requested_by_doctor_id=requested_by_doctor_id,
            pipeline_version=REPORT_PIPELINE_VERSION,
        )
        self._transition(job, JobStatus.QUEUED)
        self._session.commit()
        logger.info(
            "report generation job queued job_id=%s ecg_record_id=%s requested_by=%s",
            job.id,
            job.ecg_record_id,
            job.requested_by_user_id,
        )
        return job

    def cancel(self, job: ReportGenerationJob) -> ReportGenerationJob:
        """Cancels a job that has not finished (Sprint 3.12).

        A job cancelled while running stops at the next stage boundary; a
        stage already in flight is allowed to finish rather than being torn
        down mid-write.
        """
        self._transition(job, JobStatus.CANCELLED, completed_at=datetime.now(timezone.utc))
        self._session.commit()
        logger.info("report generation job cancelled job_id=%s", job.id)
        self._roll_back_partial_output(job)
        return job

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, job: ReportGenerationJob) -> ReportGenerationJob:
        """Executes the pipeline for one job and finalizes its state.

        A job parked in ``WAITING_FOR_SIGNAL_PROCESSING`` resumes at the stage
        that parked it rather than replaying the stages that already
        succeeded.

        Progress and stage history are committed after every stage so a
        polling client observes execution as it happens (Sprint 3.13).
        Returns the job in its final state; pipeline failures are recorded on
        the job rather than raised.
        """
        start_index = self._resume_index(job)
        self._claim(job)
        self._jobs.update_execution_state(
            job, started_at=None if job.started_at else datetime.now(timezone.utc)
        )
        self._jobs.increment_attempt(job)
        self._session.commit()

        context: GenerationContext | None = None
        outputs: dict[PipelineStage, Mapping[str, Any]] = {}

        for index in range(start_index, len(self._stages)):
            stage = self._stages[index]
            if self._is_cancelled(job):
                logger.info("report generation job stopped after cancellation job_id=%s", job.id)
                return job

            self._jobs.update_execution_state(job, current_stage=stage.stage)
            self._session.commit()

            result = self._execute_stage(stage, job, context, outputs)

            if result.context is not None:
                context = result.context
            if result.outputs:
                outputs[stage.stage] = result.outputs

            if result.status is StageStatus.WAITING:
                self._suspend(job, stage.stage, result)
                return job
            if not result.should_continue:
                self._fail(job, stage.stage, result)
                return job

            self._jobs.update_execution_state(job, progress_percent=self._progress_after(index))
            self._session.commit()

        return self._complete(job)

    # ------------------------------------------------------------------
    # Stage execution and retries
    # ------------------------------------------------------------------

    def _execute_stage(
        self,
        stage: ReportPipelineStage,
        job: ReportGenerationJob,
        context: GenerationContext | None,
        outputs: Mapping[PipelineStage, Mapping[str, Any]],
    ) -> StageResult:
        """Runs one stage, retrying only transient failures (Sprint 3.16).

        Every attempt -- successful or not -- is appended to the job's stage
        history, so a retried stage leaves a complete audit trail rather than
        only its final outcome (Sprint 3.11 / 10.13).
        """
        payload_outputs = dict(outputs)
        last_result: StageResult | None = None

        for attempt in range(1, self._max_stage_attempts + 1):
            started_at = datetime.now(timezone.utc)
            try:
                result = stage.execute(
                    StageInput(job=job, attempt=attempt, context=context, outputs=payload_outputs)
                )
            except Exception as exc:  # noqa: BLE001 -- a stage failure must never kill the worker
                # Recover the session before anything else: a failure part-way
                # through a database write leaves it unusable, and even reading
                # an attribute off the job would raise until it is rolled back.
                self._discard_uncommitted()
                result = self._result_from_exception(exc)
                retryable = bool(getattr(exc, "retryable", False))
                logger.warning(
                    "report generation stage raised job_id=%s stage=%s attempt=%s retryable=%s error=%s",
                    job.id,
                    stage.stage.value,
                    attempt,
                    retryable,
                    exc,
                    exc_info=not isinstance(exc, ReportingError),
                )
            else:
                retryable = False
                if not result.should_continue and result.status is not StageStatus.WAITING:
                    # A stage that reports failure without raising may still
                    # have left uncommitted work behind; stages commit only on
                    # success, so nothing of value is discarded here.
                    self._discard_uncommitted()

            self._record_stage_execution(job, stage.stage, result, started_at, attempt)
            last_result = result

            if result.should_continue or result.status is StageStatus.WAITING:
                return result
            if not retryable or attempt == self._max_stage_attempts:
                return result

            logger.info(
                "retrying report generation stage job_id=%s stage=%s next_attempt=%s",
                job.id,
                stage.stage.value,
                attempt + 1,
            )

        # Unreachable: the loop always returns on its final attempt.
        return last_result  # type: ignore[return-value]

    @staticmethod
    def _result_from_exception(exc: Exception) -> StageResult:
        return StageResult(
            status=StageStatus.FAILED,
            error_code=type(exc).__name__,
            error_message=str(exc),
        )

    def _record_stage_execution(
        self,
        job: ReportGenerationJob,
        stage: PipelineStage,
        result: StageResult,
        started_at: datetime,
        attempt: int,
    ) -> None:
        completed_at = datetime.now(timezone.utc)
        self._jobs.append_stage_execution(
            job,
            StageExecution(
                stage=stage,
                status=result.status,
                started_at=started_at,
                completed_at=completed_at,
                attempt=attempt,
                error_code=result.error_code,
                error_message=result.error_message,
                artifact_ids=result.artifact_ids,
                messages=result.messages,
            ),
        )
        self._session.commit()
        logger.info(
            "report generation stage finished job_id=%s ecg_record_id=%s stage=%s status=%s "
            "attempt=%s duration_ms=%s artifacts=%s",
            job.id,
            job.ecg_record_id,
            stage.value,
            result.status.value,
            attempt,
            int((completed_at - started_at).total_seconds() * 1000),
            len(result.artifact_ids),
        )

    # ------------------------------------------------------------------
    # Job finalization
    # ------------------------------------------------------------------

    def _complete(self, job: ReportGenerationJob) -> ReportGenerationJob:
        self._transition(
            job,
            JobStatus.COMPLETED,
            progress_percent=100,
            completed_at=datetime.now(timezone.utc),
        )
        self._session.commit()
        logger.info("report generation job completed job_id=%s", job.id)
        return job

    def _fail(self, job: ReportGenerationJob, stage: PipelineStage, result: StageResult) -> None:
        self._transition(
            job,
            JobStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
            failure=JobFailure(
                code=result.error_code or "STAGE_FAILED",
                message=result.error_message or f"Stage {stage.value} failed",
                stage=stage,
            ),
        )
        self._session.commit()
        logger.error(
            "report generation job failed job_id=%s stage=%s error_code=%s error=%s",
            job.id,
            stage.value,
            result.error_code,
            result.error_message,
        )
        self._roll_back_partial_output(job)

    def _suspend(self, job: ReportGenerationJob, stage: PipelineStage, result: StageResult) -> None:
        """Parks a job whose inputs have not arrived yet (Sprint 3.12).

        The job is not failed and no partial report is exposed; it resumes
        from ``WAITING_FOR_SIGNAL_PROCESSING`` when its inputs become
        available.
        """
        self._transition(job, JobStatus.WAITING_FOR_SIGNAL_PROCESSING)
        self._session.commit()
        logger.info(
            "report generation job waiting for inputs job_id=%s stage=%s reason=%s",
            job.id,
            stage.value,
            result.error_message,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _claim(self, job: ReportGenerationJob) -> None:
        """Takes exclusive ownership of a job before executing it.

        The state machine decides whether the move to RUNNING is legal at all;
        the conditional update then decides which of two concurrent runners
        actually performs it.
        """
        current = JobStatus(job.status)
        JobStateMachine.validate(current, JobStatus.RUNNING)
        if not self._jobs.claim(job, expected=current, target=JobStatus.RUNNING):
            raise ConcurrentJobExecutionError(
                f"Report generation job {job.id!r} is already being executed"
            )

    def _roll_back_partial_output(self, job: ReportGenerationJob) -> None:
        """Removes anything a terminated run persisted before it stopped.

        Runs after the job's final state is recorded, so a failure inside the
        rollback cannot leave the job itself in an indeterminate state.
        """
        if self._cleanup is None:
            return
        self._cleanup.clean(job)

    def _discard_uncommitted(self) -> None:
        """Rolls back whatever a failed stage left behind in the session.

        A stage that fails partway through a database write leaves the session
        unusable: every later statement raises until the transaction is rolled
        back. Without this the orchestrator could not record its own failure,
        and the job would be stranded in RUNNING. Rolling back here also
        guarantees a failed stage contributes nothing to the database, since
        stages commit only on success.
        """
        try:
            self._session.rollback()
        except Exception:  # noqa: BLE001 -- recovery must not mask the original failure
            logger.exception("failed to roll back the session after a stage failure")

    def _transition(self, job: ReportGenerationJob, target: JobStatus, **fields: Any) -> None:
        """Moves a job to ``target`` after the state machine approves it."""
        JobStateMachine.validate(JobStatus(job.status), target)
        self._jobs.update_execution_state(job, status=target, **fields)

    def _resume_index(self, job: ReportGenerationJob) -> int:
        """Where execution starts: the parked stage, or the beginning.

        A job that stopped waiting for Signal Processing resumes at the stage
        that parked it; the stages that already completed are not replayed.
        """
        if JobStatus(job.status) is not JobStatus.WAITING_FOR_SIGNAL_PROCESSING or not job.current_stage:
            return 0

        parked_at = PipelineStage(job.current_stage)
        for index, stage in enumerate(self._stages):
            if stage.stage is parked_at:
                return index
        raise PipelineDefinitionError(
            f"Job {job.id!r} is parked at stage {parked_at.value}, which this pipeline does not contain"
        )

    def _is_cancelled(self, job: ReportGenerationJob) -> bool:
        """Re-reads the job so a cancellation issued elsewhere is honoured."""
        self._session.refresh(job)
        return JobStatus(job.status) is JobStatus.CANCELLED

    def _progress_after(self, stage_index: int) -> int:
        """Percentage complete once the stage at ``stage_index`` has finished."""
        return int(round((stage_index + 1) / len(self._stages) * 100))

    def _validate_stage_order(self) -> None:
        """Rejects a pipeline that repeats or reorders the fixed stage sequence.

        A pipeline may omit stages that are not implemented yet; it may never
        run them out of the Sprint 3.8 order.
        """
        declared = list(PipelineStage)
        seen: set[PipelineStage] = set()
        positions: list[int] = []
        for stage in self._stages:
            if stage.stage in seen:
                raise PipelineDefinitionError(
                    f"Stage {stage.stage.value} appears more than once in the pipeline"
                )
            seen.add(stage.stage)
            positions.append(declared.index(stage.stage))
        if positions != sorted(positions):
            raise PipelineDefinitionError(
                "Report generation stages must follow the fixed pipeline order defined by Sprint 3.8"
            )
