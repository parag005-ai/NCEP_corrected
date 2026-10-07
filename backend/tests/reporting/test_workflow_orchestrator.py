"""Tests for the Workflow Orchestrator (Sprint 3.5 / 3.11-3.16 / 10.7)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from sqlalchemy.orm import Session

from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    JobStatus,
    PipelineStage,
    StageStatus,
)
from app.reporting.exceptions import (
    InvalidJobTransitionError,
    PipelineDefinitionError,
    ReportingError,
    TransientReportingError,
)
from app.reporting.models import StageExecution
from app.reporting.orchestrator import StageInput, StageResult, WorkflowOrchestrator

from tests.reporting.conftest import UpstreamFixture


class _StorageTimeout(TransientReportingError):
    """A transient infrastructure failure a stage may recover from."""


class _CorruptTemplate(ReportingError):
    """A permanent failure that must never be retried."""


@dataclass
class FakeStage:
    """A pipeline stage whose behaviour each test dictates."""

    stage: PipelineStage
    result: StageResult | None = None
    raises: list[Exception | None] = field(default_factory=list)
    seen: list[StageInput] = field(default_factory=list)
    on_execute: object = None

    def execute(self, payload: StageInput) -> StageResult:
        self.seen.append(payload)
        if self.on_execute is not None:
            self.on_execute(payload)
        if self.raises:
            error = self.raises.pop(0)
            if error is not None:
                raise error
        return self.result or StageResult(status=StageStatus.COMPLETED)

    @property
    def call_count(self) -> int:
        return len(self.seen)


def build_orchestrator(session: Session, *stages: FakeStage, **kwargs) -> WorkflowOrchestrator:
    return WorkflowOrchestrator(session, stages, **kwargs)


def create_job(orchestrator: WorkflowOrchestrator, upstream: UpstreamFixture):
    return orchestrator.create_job(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )


def history(job) -> list[StageExecution]:
    return [StageExecution.from_dict(entry) for entry in job.stage_history]


# ---------------------------------------------------------------------------
# Job creation
# ---------------------------------------------------------------------------


def test_a_created_job_is_queued_for_execution(session, upstream):
    orchestrator = build_orchestrator(session, FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT))

    job = create_job(orchestrator, upstream)

    assert job.status == JobStatus.QUEUED.value
    assert job.pipeline_version == REPORT_PIPELINE_VERSION
    assert job.progress_percent == 0
    assert job.started_at is None


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------


def test_a_completed_run_walks_every_stage_and_finalizes_the_job(session, upstream):
    first = FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT)
    second = FakeStage(PipelineStage.GENERATE_VISUALIZATIONS)
    orchestrator = build_orchestrator(session, first, second)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert job.progress_percent == 100
    assert job.started_at is not None and job.completed_at is not None
    assert job.attempt_count == 1
    assert first.call_count == 1 and second.call_count == 1
    assert [entry.stage for entry in history(job)] == [
        PipelineStage.LOAD_GENERATION_CONTEXT,
        PipelineStage.GENERATE_VISUALIZATIONS,
    ]
    assert all(entry.status is StageStatus.COMPLETED for entry in history(job))


def test_progress_is_updated_after_every_stage(session, upstream):
    observed = []
    first = FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT)
    second = FakeStage(PipelineStage.GENERATE_VISUALIZATIONS)
    second.on_execute = lambda payload: observed.append(payload.job.progress_percent)
    orchestrator = build_orchestrator(session, first, second)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert observed == [50]
    assert job.progress_percent == 100


def test_a_stage_receives_the_outputs_published_by_earlier_stages(session, upstream):
    first = FakeStage(
        PipelineStage.LOAD_GENERATION_CONTEXT,
        result=StageResult(status=StageStatus.COMPLETED, outputs={"lead": "II"}),
    )
    second = FakeStage(PipelineStage.GENERATE_VISUALIZATIONS)
    orchestrator = build_orchestrator(session, first, second)

    orchestrator.run(create_job(orchestrator, upstream))

    published = second.seen[0].outputs[PipelineStage.LOAD_GENERATION_CONTEXT]
    assert published["lead"] == "II"
    with pytest.raises(TypeError):
        published["lead"] = "V1"


def test_degraded_stages_do_not_stop_the_pipeline(session, upstream):
    """Skipped and partially successful stages continue with placeholders (Sprint 3.14)."""
    first = FakeStage(
        PipelineStage.EVALUATE_CLINICAL_RULES, result=StageResult(status=StageStatus.SKIPPED)
    )
    second = FakeStage(
        PipelineStage.GENERATE_NARRATIVE, result=StageResult(status=StageStatus.PARTIAL_SUCCESS)
    )
    third = FakeStage(PipelineStage.BUILD_SUMMARY_REPORT)
    orchestrator = build_orchestrator(session, first, second, third)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert third.call_count == 1


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_a_failed_stage_fails_the_job_and_stops_the_pipeline(session, upstream):
    failing = FakeStage(
        PipelineStage.LOAD_GENERATION_CONTEXT,
        result=StageResult(
            status=StageStatus.FAILED,
            error_code="ECGArtifactUnavailableError",
            error_message="waveform.npz is missing",
        ),
    )
    later = FakeStage(PipelineStage.GENERATE_VISUALIZATIONS)
    orchestrator = build_orchestrator(session, failing, later)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert job.error_code == "ECGArtifactUnavailableError"
    assert job.error_message == "waveform.npz is missing"
    assert job.completed_at is not None
    assert later.call_count == 0


def test_an_exception_raised_by_a_stage_is_recorded_not_propagated(session, upstream):
    failing = FakeStage(PipelineStage.RENDER_HTML_DOCUMENTS, raises=[_CorruptTemplate("template is invalid")])
    orchestrator = build_orchestrator(session, failing)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.error_code == "_CorruptTemplate"
    assert job.error_message == "template is invalid"
    assert history(job)[-1].status is StageStatus.FAILED


def test_an_unexpected_exception_does_not_escape_the_orchestrator(session, upstream):
    failing = FakeStage(PipelineStage.GENERATE_PDF_DOCUMENTS, raises=[RuntimeError("renderer crashed")])
    orchestrator = build_orchestrator(session, failing)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.error_code == "RuntimeError"


# ---------------------------------------------------------------------------
# Retry policy (Sprint 2.13 / 3.16)
# ---------------------------------------------------------------------------


def test_a_transient_failure_is_retried_and_can_succeed(session, upstream):
    flaky = FakeStage(PipelineStage.STORE_REPORT_ARTIFACTS, raises=[_StorageTimeout("storage busy"), None])
    orchestrator = build_orchestrator(session, flaky)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert flaky.call_count == 2
    attempts = history(job)
    assert [(entry.attempt, entry.status) for entry in attempts] == [
        (1, StageStatus.FAILED),
        (2, StageStatus.COMPLETED),
    ]


def test_retries_are_bounded_and_the_job_then_fails(session, upstream):
    always_failing = FakeStage(
        PipelineStage.STORE_REPORT_ARTIFACTS,
        raises=[_StorageTimeout("storage down")] * 5,
    )
    orchestrator = build_orchestrator(session, always_failing, max_stage_attempts=3)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert always_failing.call_count == 3
    assert [entry.attempt for entry in history(job)] == [1, 2, 3]


def test_a_permanent_failure_is_never_retried(session, upstream):
    failing = FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT, raises=[_CorruptTemplate("invalid context")] * 5)
    orchestrator = build_orchestrator(session, failing, max_stage_attempts=3)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert failing.call_count == 1


# ---------------------------------------------------------------------------
# Waiting for Signal Processing (Sprint 3.12)
# ---------------------------------------------------------------------------


def test_a_waiting_stage_parks_the_job_without_failing_it(session, upstream):
    waiting = FakeStage(
        PipelineStage.EVALUATE_CLINICAL_RULES,
        result=StageResult(status=StageStatus.WAITING, error_message="signal processing pending"),
    )
    later = FakeStage(PipelineStage.BUILD_SUMMARY_REPORT)
    orchestrator = build_orchestrator(session, waiting, later)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.WAITING_FOR_SIGNAL_PROCESSING.value
    assert job.completed_at is None
    assert job.error_code is None
    assert later.call_count == 0


def test_a_parked_job_resumes_at_the_stage_that_waited(session, upstream):
    """Stages that already succeeded are not replayed on resume."""
    first = FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT)
    waiting = FakeStage(
        PipelineStage.EVALUATE_CLINICAL_RULES,
        result=StageResult(status=StageStatus.WAITING),
    )
    last = FakeStage(PipelineStage.BUILD_SUMMARY_REPORT)
    orchestrator = build_orchestrator(session, first, waiting, last)

    job = orchestrator.run(create_job(orchestrator, upstream))
    assert job.status == JobStatus.WAITING_FOR_SIGNAL_PROCESSING.value
    assert job.current_stage == PipelineStage.EVALUATE_CLINICAL_RULES.value

    waiting.result = StageResult(status=StageStatus.COMPLETED)
    job = orchestrator.run(job)

    assert job.status == JobStatus.COMPLETED.value
    assert job.attempt_count == 2
    assert first.call_count == 1  # not replayed
    assert waiting.call_count == 2
    assert last.call_count == 1


def test_resuming_preserves_the_original_start_time(session, upstream):
    waiting = FakeStage(
        PipelineStage.EVALUATE_CLINICAL_RULES, result=StageResult(status=StageStatus.WAITING)
    )
    orchestrator = build_orchestrator(session, waiting)
    job = orchestrator.run(create_job(orchestrator, upstream))
    started_at = job.started_at

    waiting.result = StageResult(status=StageStatus.COMPLETED)
    job = orchestrator.run(job)

    assert job.started_at == started_at


def test_a_job_parked_at_a_stage_the_pipeline_no_longer_has_is_refused(session, upstream):
    waiting = FakeStage(
        PipelineStage.EVALUATE_CLINICAL_RULES, result=StageResult(status=StageStatus.WAITING)
    )
    job = build_orchestrator(session, waiting).run(create_job(build_orchestrator(session, waiting), upstream))

    reduced = build_orchestrator(session, FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT))
    with pytest.raises(PipelineDefinitionError, match="does not contain"):
        reduced.run(job)


# ---------------------------------------------------------------------------
# Cancellation (Sprint 3.12)
# ---------------------------------------------------------------------------


def test_a_queued_job_can_be_cancelled_and_then_never_runs(session, upstream):
    orchestrator = build_orchestrator(session, FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT))
    job = create_job(orchestrator, upstream)

    orchestrator.cancel(job)

    assert job.status == JobStatus.CANCELLED.value
    with pytest.raises(InvalidJobTransitionError):
        orchestrator.run(job)


def test_a_running_job_stops_at_the_next_stage_boundary_once_cancelled(session, upstream):
    first = FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT)
    second = FakeStage(PipelineStage.GENERATE_VISUALIZATIONS)
    orchestrator = build_orchestrator(session, first, second)
    first.on_execute = lambda payload: None

    job = create_job(orchestrator, upstream)
    first.on_execute = lambda payload: orchestrator.cancel(payload.job)
    job = orchestrator.run(job)

    assert job.status == JobStatus.CANCELLED.value
    assert first.call_count == 1
    assert second.call_count == 0


# ---------------------------------------------------------------------------
# Pipeline definition (Sprint 3.8)
# ---------------------------------------------------------------------------


def test_stages_may_not_run_out_of_the_fixed_order(session):
    with pytest.raises(PipelineDefinitionError, match="fixed pipeline order"):
        build_orchestrator(
            session,
            FakeStage(PipelineStage.GENERATE_PDF_DOCUMENTS),
            FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT),
        )


def test_a_stage_may_not_appear_twice(session):
    with pytest.raises(PipelineDefinitionError, match="more than once"):
        build_orchestrator(
            session,
            FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT),
            FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT),
        )


def test_a_pipeline_may_omit_stages_that_are_not_implemented_yet(session, upstream):
    """Later increments append stages; the pipeline stays valid meanwhile."""
    orchestrator = build_orchestrator(
        session,
        FakeStage(PipelineStage.LOAD_GENERATION_CONTEXT),
        FakeStage(PipelineStage.STORE_REPORT_ARTIFACTS),
    )

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
