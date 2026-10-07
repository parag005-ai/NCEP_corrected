"""Tests for the visualization pipeline stage and its place in the pipeline."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np

from app.reporting.constants import ArtifactType, JobStatus, PipelineStage, StageStatus
from app.reporting.models import StageExecution
from app.reporting.orchestrator import (
    RAW_ECG_ARTIFACT_OUTPUT,
    VISUALIZATION_UNAVAILABLE_OUTPUT,
    StageInput,
    StageResult,
    WorkflowOrchestrator,
    build_report_pipeline,
)
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import FakePDFRenderer, UpstreamFixture, write_canonical_artifacts


@dataclass
class CapturingStage:
    """A downstream stage that records what the visualization stage published."""

    stage: PipelineStage = PipelineStage.EVALUATE_CLINICAL_RULES
    received: dict = field(default_factory=dict)

    def execute(self, payload: StageInput) -> StageResult:
        self.received.update(payload.outputs.get(PipelineStage.GENERATE_VISUALIZATIONS, {}))
        return StageResult(status=StageStatus.COMPLETED)


def in_pipeline_order(stages):
    """Stages sorted into the fixed pipeline order, so an inserted observer sits
    in its declared slot rather than at the end."""
    declared = list(PipelineStage)
    return sorted(stages, key=lambda stage: declared.index(stage.stage))


def build(session, artifact_store, report_store, *extra_stages) -> WorkflowOrchestrator:
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=report_store,
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


def history(job) -> list[StageExecution]:
    return [StageExecution.from_dict(entry) for entry in job.stage_history]


def test_the_stage_publishes_the_stored_visualization_for_later_stages(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    downstream = CapturingStage()
    orchestrator = build(session, artifact_store, ReportArtifactStore(root=tmp_path / "reports"), downstream)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    artifact = downstream.received[RAW_ECG_ARTIFACT_OUTPUT]
    assert artifact.artifact_type is ArtifactType.RAW_ECG_SVG
    assert artifact.artifact_metadata["lead"] == "II"
    assert artifact.checksum_sha256


def test_an_undrawable_recording_skips_the_stage_without_failing_the_job(
    session, upstream, artifact_store, tmp_path
):
    """No fabricated image; the report section will carry a placeholder (Sprint 4.14)."""
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.array([np.nan, np.nan]))
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=buffer.getvalue()
    )
    downstream = CapturingStage()
    orchestrator = build(session, artifact_store, ReportArtifactStore(root=tmp_path / "reports"), downstream)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    visualization = [e for e in history(job) if e.stage is PipelineStage.GENERATE_VISUALIZATIONS][0]
    assert visualization.status is StageStatus.SKIPPED
    assert "unavailable" in visualization.messages[0]
    assert RAW_ECG_ARTIFACT_OUTPUT not in downstream.received
    assert downstream.received[VISUALIZATION_UNAVAILABLE_OUTPUT]


def test_a_corrupt_waveform_fails_the_job_at_the_visualization_stage(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=b"not an npz archive"
    )
    orchestrator = build(session, artifact_store, ReportArtifactStore(root=tmp_path / "reports"))

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.GENERATE_VISUALIZATIONS.value
    assert job.error_code == "WaveformReadError"


def test_a_corrupt_waveform_is_not_retried(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=b"not an npz archive"
    )
    orchestrator = build(session, artifact_store, ReportArtifactStore(root=tmp_path / "reports"))

    job = orchestrator.run(create_job(orchestrator, upstream))

    visualization_attempts = [
        entry for entry in history(job) if entry.stage is PipelineStage.GENERATE_VISUALIZATIONS
    ]
    assert len(visualization_attempts) == 1
