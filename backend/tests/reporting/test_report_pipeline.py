"""End-to-end tests of the pipeline as currently assembled.

Exercises the real stage set driven by the real Workflow Orchestrator against
real persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.reporting.constants import JobStatus, PipelineStage, StageStatus
from app.reporting.context.generation_context import GenerationContext
from app.reporting.models import StageExecution
from app.reporting.orchestrator import StageInput, StageResult, WorkflowOrchestrator, build_report_pipeline
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import FakePDFRenderer, UpstreamFixture, write_canonical_artifacts


@dataclass
class ContextCapturingStage:
    """A downstream stage that records the context the pipeline handed it."""

    stage: PipelineStage = PipelineStage.EVALUATE_CLINICAL_RULES
    received: list[GenerationContext] = field(default_factory=list)

    def execute(self, payload: StageInput) -> StageResult:
        self.received.append(payload.context)
        return StageResult(status=StageStatus.COMPLETED)


def in_pipeline_order(stages):
    """Stages sorted into the fixed pipeline order, so an inserted observer sits
    in its declared slot rather than at the end."""
    declared = list(PipelineStage)
    return sorted(stages, key=lambda stage: declared.index(stage.stage))


def build(session, artifact_store, report_root, *extra_stages) -> WorkflowOrchestrator:
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=ReportArtifactStore(root=report_root),
        pdf_renderer=FakePDFRenderer(),
    )
    return WorkflowOrchestrator(session, in_pipeline_order([*stages, *extra_stages]))


def create_job(orchestrator: WorkflowOrchestrator, upstream: UpstreamFixture):
    return orchestrator.create_job(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )


def test_the_assembled_pipeline_runs_every_implemented_stage(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert job.progress_percent == 100
    entries = [StageExecution.from_dict(entry) for entry in job.stage_history]
    assert [entry.stage for entry in entries] == [
        PipelineStage.LOAD_GENERATION_CONTEXT,
        PipelineStage.GENERATE_VISUALIZATIONS,
        PipelineStage.BUILD_SUMMARY_REPORT,
        PipelineStage.BUILD_DETAILED_REPORT,
        PipelineStage.RENDER_HTML_DOCUMENTS,
        PipelineStage.GENERATE_PDF_DOCUMENTS,
        PipelineStage.STORE_REPORT_ARTIFACTS,
    ]
    assert all(entry.status is StageStatus.COMPLETED for entry in entries)
    assert all(entry.duration_ms is not None for entry in entries)


def test_the_loaded_context_reaches_the_following_stage(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    downstream = ContextCapturingStage()
    orchestrator = build(session, artifact_store, tmp_path / "reports", downstream)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    context = downstream.received[0]
    assert context is not None
    assert context.generation.job_id == job.id
    assert context.ecg.ecg_record_id == upstream.ecg_record_id
    assert context.patient.patient_id == upstream.patient_id
    # Signal Processing (Phase 2) runs against the recording's real waveform.
    assert context.signal_processing.is_available


def test_a_recording_without_artifacts_fails_the_job_at_the_context_stage(
    session, upstream, artifact_store, tmp_path
):
    downstream = ContextCapturingStage()
    orchestrator = build(session, artifact_store, tmp_path / "reports", downstream)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert job.error_code == "ECGArtifactUnavailableError"
    assert downstream.received == []


def test_context_loading_failures_are_not_retried(session, upstream, artifact_store, tmp_path):
    """A missing artifact is permanent, so the stage runs exactly once (Sprint 2.13)."""
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert len(job.stage_history) == 1
