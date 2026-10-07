"""Tests for PDF generation, artifact publication and artifact reuse (Sprint 9)."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest

from app.reporting.constants import (
    ArtifactStatus,
    ArtifactType,
    JobStatus,
    PipelineStage,
    ReportStatus,
    StageStatus,
)
from app.reporting.exceptions import PDFRenderingError
from app.reporting.models import StageExecution
from app.reporting.orchestrator import WorkflowOrchestrator, build_report_pipeline
from app.reporting.orchestrator.pdf_stage import DETAILED_PDF_LOCATION
from app.reporting.orchestrator.rendering_stage import DETAILED_HTML_LOCATION
from app.reporting.renderers import PDF_MAGIC
from app.reporting.repositories import (
    ECGArtifactRepository,
    GeneratedReportRepository,
    ReportArtifactRepository,
)
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import UpstreamFixture, write_canonical_artifacts

MINIMAL_PDF = b"%PDF-1.4\n%stub document\n"


class FakePDFRenderer:
    """A renderer that records the HTML it was given, without a browser."""

    engine = "fake"
    engine_version = "1.0"

    def __init__(self, output: bytes = MINIMAL_PDF, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.seen: list[str] = []

    def render(self, html: str) -> bytes:
        self.seen.append(html)
        if self.error is not None:
            raise self.error
        return self.output


def build(session, artifact_store, report_root, renderer=None) -> WorkflowOrchestrator:
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=ReportArtifactStore(root=report_root),
        pdf_renderer=renderer or FakePDFRenderer(),
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


# ---------------------------------------------------------------------------
# The complete pipeline
# ---------------------------------------------------------------------------


def test_the_pipeline_now_runs_every_specified_stage(session, upstream, artifact_store, tmp_path):
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


# ---------------------------------------------------------------------------
# HTML -> PDF (approved decisions 3 and 4)
# ---------------------------------------------------------------------------


def test_the_pdf_is_rendered_from_the_registered_html(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    renderer = FakePDFRenderer()
    orchestrator = build(session, artifact_store, tmp_path / "reports", renderer)

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    stored_html = (Path(report.storage_dir) / DETAILED_HTML_LOCATION).read_text(encoding="utf-8")
    assert renderer.seen == [stored_html]


def test_the_pdf_records_the_html_it_was_rendered_from(session, upstream, artifact_store, tmp_path):
    """The two representations of a report version are provably consistent."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    artifacts = {a.artifact_type: a for a in ReportArtifactRepository(session).list_for_report(report.id)}
    html = artifacts[ArtifactType.DETAILED_HTML.value]
    pdf = artifacts[ArtifactType.DETAILED_PDF.value]

    assert pdf.artifact_metadata["source_artifact_id"] == html.id
    assert pdf.artifact_metadata["source_checksum_sha256"] == html.checksum_sha256
    assert pdf.artifact_metadata["rendering_engine"] == "fake"
    assert pdf.content_type == "application/pdf"
    assert pdf.storage_location == DETAILED_PDF_LOCATION


def test_the_pdf_is_stored_beside_its_html(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    pdf_path = Path(report.storage_dir) / DETAILED_PDF_LOCATION
    assert pdf_path.is_file()
    assert pdf_path.read_bytes().startswith(PDF_MAGIC)


def test_a_renderer_that_returns_something_other_than_a_pdf_fails_the_job(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(
        session, artifact_store, tmp_path / "reports", FakePDFRenderer(output=b"<html>nope</html>")
    )

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.GENERATE_PDF_DOCUMENTS.value
    assert job.error_code == "PDFRenderingError"


def test_a_rendering_failure_fails_the_job_and_is_not_retried(
    session, upstream, artifact_store, tmp_path
):
    """PDF generation failure is critical (Sprint 9.14), never retried (Sprint 2.13)."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    renderer = FakePDFRenderer(error=PDFRenderingError("engine unavailable"))
    orchestrator = build(session, artifact_store, tmp_path / "reports", renderer)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.error_code == "PDFRenderingError"
    assert len([e for e in history(job) if e.stage is PipelineStage.GENERATE_PDF_DOCUMENTS]) == 1


#: Stages that run after the report HTML exists; excluded when a test needs to
#: interfere with the stored document before they run.
POST_RENDER_STAGES = (PipelineStage.GENERATE_PDF_DOCUMENTS, PipelineStage.STORE_REPORT_ARTIFACTS)


def run_until_rendered(session, artifact_store, report_root, renderer) -> WorkflowOrchestrator:
    """An orchestrator whose pipeline stops once the report HTML is registered."""
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=ReportArtifactStore(root=report_root),
        pdf_renderer=renderer,
    )
    return WorkflowOrchestrator(
        session, [stage for stage in stages if stage.stage not in POST_RENDER_STAGES]
    )


def test_a_tampered_html_document_is_never_rendered(session, upstream, artifact_store, tmp_path):
    """Rendering an HTML that no longer matches its registry entry is refused."""
    from app.reporting.orchestrator import StageInput
    from app.reporting.orchestrator.pdf_stage import GeneratePDFDocumentsStage
    from app.reporting.orchestrator.rendering_stage import GENERATED_REPORT_OUTPUT

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    renderer = FakePDFRenderer()
    orchestrator = run_until_rendered(session, artifact_store, tmp_path / "reports", renderer)
    job = orchestrator.run(create_job(orchestrator, upstream))
    report = GeneratedReportRepository(session).get_by_job(job.id)

    (Path(report.storage_dir) / DETAILED_HTML_LOCATION).write_text("tampered", encoding="utf-8")
    stage = GeneratePDFDocumentsStage(
        session, ReportArtifactStore(root=tmp_path / "reports"), renderer
    )
    result = stage.execute(
        StageInput(
            job=job,
            attempt=1,
            outputs={PipelineStage.RENDER_HTML_DOCUMENTS: {GENERATED_REPORT_OUTPUT: report.id}},
        )
    )

    assert result.status is StageStatus.FAILED
    assert result.error_code == "ArtifactIntegrityError"
    assert renderer.seen == []


def test_verified_artifacts_are_released_and_the_report_published(
    session, upstream, artifact_store, tmp_path
):
    """Only verified artifacts reach AVAILABLE, and the report follows them."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    artifacts = ReportArtifactRepository(session).list_for_report(report.id)

    assert report.status == ReportStatus.AVAILABLE.value
    assert sorted(a.artifact_type for a in artifacts) == [
        ArtifactType.DETAILED_HTML.value,
        ArtifactType.DETAILED_PDF.value,
        ArtifactType.RAW_ECG_SVG.value,
        ArtifactType.SUMMARY_JSON.value,
    ]
    assert all(a.status == ArtifactStatus.AVAILABLE.value for a in artifacts)


def test_publication_walks_each_artifact_along_its_lifecycle(
    session, upstream, artifact_store, tmp_path
):
    """An artifact reaches AVAILABLE only through the declared lifecycle path."""
    from app.reporting.storage import ArtifactLifecycle

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    for artifact in ReportArtifactRepository(session).list_for_report(report.id):
        assert ArtifactStatus(artifact.status) is ArtifactStatus.AVAILABLE
        assert not ArtifactLifecycle.is_final(ArtifactStatus.AVAILABLE)


def test_a_corrupt_artifact_stops_publication(session, upstream, artifact_store, tmp_path):
    from app.reporting.orchestrator import StageInput
    from app.reporting.orchestrator.artifact_stage import StoreReportArtifactsStage
    from app.reporting.orchestrator.rendering_stage import GENERATED_REPORT_OUTPUT

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = run_until_rendered(
        session, artifact_store, tmp_path / "reports", FakePDFRenderer()
    )
    job = orchestrator.run(create_job(orchestrator, upstream))
    report = GeneratedReportRepository(session).get_by_job(job.id)

    (Path(report.storage_dir) / DETAILED_HTML_LOCATION).write_text("tampered", encoding="utf-8")
    result = StoreReportArtifactsStage(session).execute(
        StageInput(
            job=job,
            attempt=1,
            outputs={PipelineStage.RENDER_HTML_DOCUMENTS: {GENERATED_REPORT_OUTPUT: report.id}},
        )
    )

    assert result.status is StageStatus.FAILED
    assert result.error_code == "ArtifactIntegrityError"
    assert GeneratedReportRepository(session).get(report.id).status == ReportStatus.FAILED.value


# ---------------------------------------------------------------------------
# Artifact reuse (Sprint 4.21)
# ---------------------------------------------------------------------------


def test_a_regenerated_report_reuses_the_existing_ecg_figure(
    session, upstream, artifact_store, tmp_path
):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    first = orchestrator.run(create_job(orchestrator, upstream))
    second = orchestrator.run(create_job(orchestrator, upstream))

    reports = GeneratedReportRepository(session)
    artifacts = ReportArtifactRepository(session)
    original = artifacts.list_for_report(
        reports.get_by_job(first.id).id, artifact_type=ArtifactType.RAW_ECG_SVG
    )[0]
    reused = artifacts.list_for_report(
        reports.get_by_job(second.id).id, artifact_type=ArtifactType.RAW_ECG_SVG
    )[0]

    assert reused.id != original.id
    assert reused.checksum_sha256 == original.checksum_sha256
    assert reused.artifact_metadata["reused_from_artifact_id"] == original.id
    message = [
        e for e in history(second) if e.stage is PipelineStage.GENERATE_VISUALIZATIONS
    ][0].messages[0]
    assert "reused" in message


def test_a_reused_figure_is_copied_into_the_new_report(session, upstream, artifact_store, tmp_path):
    """Each report version owns a complete, self-sufficient artifact directory."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    orchestrator.run(create_job(orchestrator, upstream))
    second = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(second.id)
    artifact = ReportArtifactRepository(session).list_for_report(
        report.id, artifact_type=ArtifactType.RAW_ECG_SVG
    )[0]
    assert (Path(report.storage_dir) / artifact.storage_location).is_file()


def test_nothing_is_reused_for_a_different_recording(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    write_canonical_artifacts(artifact_store, "rec-0002")
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    orchestrator.run(create_job(orchestrator, upstream))
    other = orchestrator.create_job(
        ecg_record_id=upstream.other_ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
    )
    other = orchestrator.run(other)

    message = [
        e for e in history(other) if e.stage is PipelineStage.GENERATE_VISUALIZATIONS
    ][0].messages[0]
    assert "rendered" in message


def test_an_undrawable_recording_has_nothing_to_reuse(session, upstream, artifact_store, tmp_path):
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.array([np.nan, np.nan]))
    write_canonical_artifacts(
        artifact_store, upstream.canonical_record_id, waveform_bytes=buffer.getvalue()
    )
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    orchestrator.run(create_job(orchestrator, upstream))
    second = orchestrator.run(create_job(orchestrator, upstream))

    assert second.status == JobStatus.COMPLETED.value
    visualization = [
        e for e in history(second) if e.stage is PipelineStage.GENERATE_VISUALIZATIONS
    ][0]
    assert visualization.status is StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Versioned document generation
# ---------------------------------------------------------------------------


def test_each_version_owns_its_own_documents(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    first = orchestrator.run(create_job(orchestrator, upstream))
    second = orchestrator.run(create_job(orchestrator, upstream))

    reports = GeneratedReportRepository(session)
    v1 = reports.get_by_job(first.id)
    v2 = reports.get_by_job(second.id)

    assert (v1.version, v2.version) == (1, 2)
    assert v1.storage_dir != v2.storage_dir
    for report in (v1, v2):
        assert (Path(report.storage_dir) / DETAILED_HTML_LOCATION).is_file()
        assert (Path(report.storage_dir) / DETAILED_PDF_LOCATION).is_file()
        assert report.status == ReportStatus.AVAILABLE.value


def test_an_earlier_version_is_untouched_by_a_later_one(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    first = orchestrator.run(create_job(orchestrator, upstream))
    v1 = GeneratedReportRepository(session).get_by_job(first.id)
    before = (Path(v1.storage_dir) / DETAILED_PDF_LOCATION).read_bytes()

    orchestrator.run(create_job(orchestrator, upstream))

    assert (Path(v1.storage_dir) / DETAILED_PDF_LOCATION).read_bytes() == before
    assert v1.version == 1


# ---------------------------------------------------------------------------
# The real rendering engine
# ---------------------------------------------------------------------------


def test_chromium_renders_the_report_to_a_paginated_pdf(session, upstream, artifact_store, tmp_path):
    """The approved layout paginates to the eight specified A4 pages."""
    import re

    from app.reporting.renderers import ChromiumPDFRenderer

    playwright = pytest.importorskip("playwright.sync_api")
    try:
        with playwright.sync_playwright() as p:
            p.chromium.launch().close()
    except Exception:  # noqa: BLE001 - the browser binary is a deployment concern
        pytest.skip("Chromium browser is not installed")

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports", ChromiumPDFRenderer())

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    report = GeneratedReportRepository(session).get_by_job(job.id)
    pdf = (Path(report.storage_dir) / DETAILED_PDF_LOCATION).read_bytes()
    assert pdf.startswith(PDF_MAGIC)
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 8
