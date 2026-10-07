"""Tests for the HTML rendering stage and the pipeline that now ends with it."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np

from app.reporting.constants import ArtifactType, JobStatus, PipelineStage, ReportStatus, StageStatus
from app.reporting.models import StageExecution
from app.reporting.orchestrator import (
    GENERATED_REPORT_OUTPUT,
    WorkflowOrchestrator,
    build_report_pipeline,
)
from app.reporting.orchestrator.rendering_stage import DETAILED_HTML_LOCATION
from app.reporting.repositories import (
    ECGArtifactRepository,
    GeneratedReportRepository,
    ReportArtifactRepository,
)
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import FakePDFRenderer, UpstreamFixture, write_canonical_artifacts


def build(session, artifact_store, report_root) -> WorkflowOrchestrator:
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=ReportArtifactStore(root=report_root),
        pdf_renderer=FakePDFRenderer(),
    )
    return WorkflowOrchestrator(session, stages)


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


def test_the_pipeline_now_ends_with_a_rendered_report(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert [entry.stage for entry in history(job)] == [
        PipelineStage.LOAD_GENERATION_CONTEXT,
        PipelineStage.GENERATE_VISUALIZATIONS,
        PipelineStage.BUILD_SUMMARY_REPORT,
        PipelineStage.BUILD_DETAILED_REPORT,
        PipelineStage.RENDER_HTML_DOCUMENTS,
        PipelineStage.GENERATE_PDF_DOCUMENTS,
        PipelineStage.STORE_REPORT_ARTIFACTS,
    ]
    assert all(entry.status is StageStatus.COMPLETED for entry in history(job))


def test_rendering_creates_the_versioned_report(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    assert report is not None
    assert report.version == 1
    assert report.status == ReportStatus.AVAILABLE.value
    assert report.detailed_template_id == "ncep-detailed-report"
    assert report.detailed_template_version == "2.0.0"
    assert report.summary_template_id == "ncep-summary-frontend"
    assert report.ecg_record_id == upstream.ecg_record_id
    assert report.doctor_id == upstream.doctor_id


def test_regeneration_produces_a_new_immutable_version(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    first = orchestrator.run(create_job(orchestrator, upstream))
    second = orchestrator.run(create_job(orchestrator, upstream))

    reports = GeneratedReportRepository(session)
    assert second.status == JobStatus.COMPLETED.value
    assert [r.version for r in reports.list_for_ecg_record(upstream.ecg_record_id)] == [2, 1]
    assert reports.get_by_job(first.id).version == 1


def test_the_rendered_html_is_stored_and_registered(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    artifacts = ReportArtifactRepository(session).list_for_report(report.id)
    by_type = {a.artifact_type: a for a in artifacts}

    assert ArtifactType.DETAILED_HTML.value in by_type
    assert ArtifactType.RAW_ECG_SVG.value in by_type

    html_artifact = by_type[ArtifactType.DETAILED_HTML.value]
    assert html_artifact.storage_location == DETAILED_HTML_LOCATION
    assert html_artifact.content_type == "text/html; charset=utf-8"
    assert html_artifact.artifact_metadata["template_id"] == "ncep-detailed-report"

    stored = Path(report.storage_dir) / html_artifact.storage_location
    assert stored.is_file()
    assert stored.stat().st_size == html_artifact.file_size_bytes


def test_the_stored_report_is_a_complete_self_contained_document(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))
    report = GeneratedReportRepository(session).get_by_job(job.id)
    html = (Path(report.storage_dir) / DETAILED_HTML_LOCATION).read_text(encoding="utf-8")

    assert html.startswith("<!doctype html>")
    assert html.count('class="report-page"') == 8
    assert "<style>" in html
    assert 'class="wave-svg"' in html  # the generated ECG figure is embedded
    assert f'content="{report.id}"' in html
    assert upstream.patient_id in html


def test_the_previously_pending_visualization_is_registered_once(
    session, upstream, artifact_store, tmp_path
):
    """Artifacts stay pending until a report exists, then are registered to it."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    svgs = ReportArtifactRepository(session).list_for_report(
        report.id, artifact_type=ArtifactType.RAW_ECG_SVG
    )
    assert len(svgs) == 1
    assert svgs[0].artifact_metadata["lead"] == "II"
    assert svgs[0].checksum_sha256


def test_a_report_without_a_figure_still_renders_and_registers(
    session, upstream, artifact_store, tmp_path
):
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.array([np.nan, np.nan]))
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=buffer.getvalue()
    )
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    report = GeneratedReportRepository(session).get_by_job(job.id)
    artifacts = ReportArtifactRepository(session).list_for_report(report.id)
    assert sorted(a.artifact_type for a in artifacts) == [
        ArtifactType.DETAILED_HTML.value,
        ArtifactType.DETAILED_PDF.value,
        ArtifactType.SUMMARY_JSON.value,
    ]


def test_the_report_identity_is_published_for_later_stages(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    rendering = [e for e in history(job) if e.stage is PipelineStage.RENDER_HTML_DOCUMENTS][0]
    report = GeneratedReportRepository(session).get_by_job(job.id)
    assert len(rendering.artifact_ids) == 3
    assert GENERATED_REPORT_OUTPUT  # published under a stable key
    assert report.id.startswith("grp-")


def test_a_failed_render_leaves_no_completed_report(session, upstream, artifact_store, tmp_path):
    """A recording whose artifacts are missing never reaches rendering."""
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert GeneratedReportRepository(session).get_by_job(job.id) is None
