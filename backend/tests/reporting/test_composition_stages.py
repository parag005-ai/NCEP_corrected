"""Tests for the report composition stages inside the pipeline."""

from __future__ import annotations

import io

import numpy as np

from app.reporting.builders import SectionId
from app.reporting.constants import JobStatus, PipelineStage, ReportType, StageStatus
from app.reporting.models import StageExecution
from app.reporting.orchestrator import (
    DETAILED_DOCUMENT_OUTPUT,
    SUMMARY_DOCUMENT_OUTPUT,
    WorkflowOrchestrator,
    build_report_pipeline,
)
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import UpstreamFixture, write_canonical_artifacts


class DocumentCapturingStage:
    """A stage standing in for the Template Engine, capturing what was composed."""

    stage = PipelineStage.RENDER_HTML_DOCUMENTS

    def __init__(self) -> None:
        self.received: dict = {}

    def execute(self, payload):
        from app.reporting.orchestrator import StageResult

        self.received[SUMMARY_DOCUMENT_OUTPUT] = payload.outputs.get(
            PipelineStage.BUILD_SUMMARY_REPORT, {}
        ).get(SUMMARY_DOCUMENT_OUTPUT)
        self.received[DETAILED_DOCUMENT_OUTPUT] = payload.outputs.get(
            PipelineStage.BUILD_DETAILED_REPORT, {}
        ).get(DETAILED_DOCUMENT_OUTPUT)
        return StageResult(status=StageStatus.COMPLETED)


#: Composition is observed on its own, with the stages that follow it removed.
POST_COMPOSITION_STAGES = (
    PipelineStage.RENDER_HTML_DOCUMENTS,
    PipelineStage.GENERATE_PDF_DOCUMENTS,
    PipelineStage.STORE_REPORT_ARTIFACTS,
)


def build(session, artifact_store, report_root, *extra_stages) -> WorkflowOrchestrator:
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=ReportArtifactStore(root=report_root),
    )
    composition = [stage for stage in stages if stage.stage not in POST_COMPOSITION_STAGES]
    return WorkflowOrchestrator(session, (*composition, *extra_stages))


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


def test_the_pipeline_composes_both_report_variants(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert [entry.stage for entry in history(job)] == [
        PipelineStage.LOAD_GENERATION_CONTEXT,
        PipelineStage.GENERATE_VISUALIZATIONS,
        PipelineStage.BUILD_SUMMARY_REPORT,
        PipelineStage.BUILD_DETAILED_REPORT,
    ]
    assert all(entry.status is StageStatus.COMPLETED for entry in history(job))


def test_both_documents_reach_the_rendering_stage(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    renderer = DocumentCapturingStage()
    orchestrator = build(session, artifact_store, tmp_path / "reports", renderer)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    summary = renderer.received[SUMMARY_DOCUMENT_OUTPUT]
    detailed = renderer.received[DETAILED_DOCUMENT_OUTPUT]
    assert summary.report_type is ReportType.SUMMARY
    assert detailed.report_type is ReportType.DETAILED
    assert summary.metadata.job_id == job.id


def test_the_rendered_ecg_reaches_both_composed_documents(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    renderer = DocumentCapturingStage()
    orchestrator = build(session, artifact_store, tmp_path / "reports", renderer)

    orchestrator.run(create_job(orchestrator, upstream))

    for document in (
        renderer.received[SUMMARY_DOCUMENT_OUTPUT],
        renderer.received[DETAILED_DOCUMENT_OUTPUT],
    ):
        figures = document.section(SectionId.RAW_ECG_VISUALIZATION).figures
        assert figures[0].storage_location == "visualizations/raw_ecg_lead_II.svg"


def test_composition_continues_when_no_ecg_could_be_drawn(session, upstream, artifact_store, tmp_path):
    """A skipped visualization degrades the section, not the report (Sprint 3.14)."""
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.array([np.nan, np.nan]))
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=buffer.getvalue()
    )
    renderer = DocumentCapturingStage()
    orchestrator = build(session, artifact_store, tmp_path / "reports", renderer)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    section = renderer.received[SUMMARY_DOCUMENT_OUTPUT].section(SectionId.RAW_ECG_VISUALIZATION)
    assert not section.is_available
    assert section.display_placeholder


def test_composition_itself_writes_nothing_to_the_database(session, upstream, artifact_store, tmp_path):
    """The GeneratedReport row is created when the report is rendered, not composed.

    The pipeline is cut short of rendering so composition is observed alone.
    """
    from app.reporting.repositories import GeneratedReportRepository

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert GeneratedReportRepository(session).get_latest_for_ecg_record(upstream.ecg_record_id) is None
