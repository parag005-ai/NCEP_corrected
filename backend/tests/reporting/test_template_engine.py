"""Tests for the Template Registry and Template Engine (Sprint 6.11 - 6.18)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.reporting.builders import DetailedReportBuilder, SectionId, SummaryReportBuilder
from app.reporting.constants import PLACEHOLDER_AWAITING_SIGNAL_PROCESSING, ReportType
from app.reporting.context import GenerationContextLoader
from app.reporting.exceptions import TemplateNotFoundError, TemplateRenderingError
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.reporting.templates import (
    DETAILED_REPORT_TEMPLATE,
    SUMMARY_REPORT_TEMPLATE,
    OutputFormat,
    TemplateEngine,
    TemplateRegistry,
    inline_svg,
)

from tests.reporting.conftest import write_canonical_artifacts

GENERATED_AT = datetime(2026, 8, 6, 9, 30, tzinfo=timezone.utc)
SAMPLE_SVG = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<svg xmlns="http://www.w3.org/2000/svg" width="140" height="160" viewBox="0 0 140 160">'
    b'<path class="ecg-trace" d="M0 0L1 1"/></svg>'
)

#: Sample *values* from the specification that must never appear in a generated
#: report. Metric labels and section headings are structure, and do belong.
SAMPLE_CONTENT = (
    "Rajesh Kumar",
    "Priya Sharma",
    "22N-PT-004821",
    "NCEP-26-0718-4521",
    "121 ms",
    "42 ms",
    "16 µV",
    "454 ms",
    "78 bpm",
    "162 ms",
    "412 / 428",
    "96 / 100",
    "0.31 µV",
    "REC-0718-A",
    "EP-Sense ES-200",
    "Palpitations",
)


@pytest.fixture
def context(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = ReportGenerationJobRepository(session).create(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )
    loader = GenerationContextLoader(session, artifacts=ECGArtifactRepository(store=artifact_store))
    return loader.load(job)


@pytest.fixture
def detailed_html(context):
    document = DetailedReportBuilder().build(context)
    rendered = TemplateEngine().render(
        document,
        DETAILED_REPORT_TEMPLATE,
        report_id="grp-test000001",
        generated_at=GENERATED_AT,
        visualization_svg=SAMPLE_SVG,
    )
    return rendered.html


# ---------------------------------------------------------------------------
# Template registry (Sprint 6.12 / 6.13)
# ---------------------------------------------------------------------------


def test_a_template_is_registered_for_each_report_variant():
    registry = TemplateRegistry()

    assert registry.for_report_type(ReportType.DETAILED) is DETAILED_REPORT_TEMPLATE
    assert registry.for_report_type(ReportType.SUMMARY) is SUMMARY_REPORT_TEMPLATE


def test_the_detailed_template_renders_html_and_the_summary_is_frontend_rendered():
    assert DETAILED_REPORT_TEMPLATE.renders_html
    assert DETAILED_REPORT_TEMPLATE.path().is_file()
    assert SUMMARY_REPORT_TEMPLATE.supported_formats == (OutputFormat.STRUCTURED_DATA,)
    assert not SUMMARY_REPORT_TEMPLATE.renders_html


def test_templates_are_versioned_and_addressable():
    registry = TemplateRegistry()

    assert registry.get("ncep-detailed-report").version == DETAILED_REPORT_TEMPLATE.version
    with pytest.raises(TemplateNotFoundError):
        registry.get("does-not-exist")


def test_a_variant_without_a_template_is_refused():
    registry = TemplateRegistry(templates=(SUMMARY_REPORT_TEMPLATE,))

    with pytest.raises(TemplateNotFoundError):
        registry.for_report_type(ReportType.DETAILED)


def test_a_frontend_rendered_template_cannot_be_rendered_to_html(context):
    document = SummaryReportBuilder().build(context)

    with pytest.raises(TemplateNotFoundError, match="does not render HTML"):
        TemplateEngine().render(
            document, SUMMARY_REPORT_TEMPLATE, report_id="grp-1", generated_at=GENERATED_AT
        )


# ---------------------------------------------------------------------------
# SVG embedding
# ---------------------------------------------------------------------------


def test_a_stored_figure_is_prepared_for_embedding():
    inlined = str(inline_svg(SAMPLE_SVG))

    assert not inlined.startswith("<?xml")
    assert inlined.startswith('<svg class="wave-svg"')
    assert 'width="140"' not in inlined and 'height="160"' not in inlined
    assert 'viewBox="0 0 140 160"' in inlined
    assert 'class="ecg-trace"' in inlined  # the drawing itself is untouched


def test_something_that_is_not_an_svg_is_refused():
    with pytest.raises(TemplateRenderingError):
        inline_svg(b"<html></html>")


# ---------------------------------------------------------------------------
# Rendered document structure (canonical specification)
# ---------------------------------------------------------------------------


def test_the_report_has_the_eight_specified_pages(detailed_html):
    assert detailed_html.count('class="report-page"') == 8
    for page in range(1, 9):
        assert f'id="page-{page}-title"' in detailed_html
        assert f">{page} / 8<" in detailed_html


def test_the_specified_page_titles_and_layouts_are_present(detailed_html):
    for title in (
        "Executive Clinical Summary",
        "Recording &amp; Signal Integrity",
        "Standard ECG Assessment",
        "Atrial Electrophysiology",
        "Ventricular Electrophysiology",
        "Repolarization Analysis",
        "Integrated Clinical Assessment",
        "Technical Appendix",
    ):
        assert title in detailed_html
    for layout in (
        "executive-layout",
        "integrity-layout",
        "standard-layout",
        "atrial-layout",
        "ventricular-layout",
        "repolarization-layout",
        "integrated-layout",
        "appendix-layout",
    ):
        assert layout in detailed_html


def test_the_approved_stylesheet_is_inlined(detailed_html):
    assert "<style>" in detailed_html
    assert "--medical-blue: #075e8e;" in detailed_html
    assert ".report-page {" in detailed_html
    assert "@page {" in detailed_html
    assert 'link rel="stylesheet"' not in detailed_html  # self-contained


def test_the_generated_ecg_figure_is_embedded(detailed_html):
    assert 'class="wave-svg"' in detailed_html
    assert 'class="ecg-trace"' in detailed_html


# ---------------------------------------------------------------------------
# Data binding (Sprint 6.14)
# ---------------------------------------------------------------------------


def test_patient_and_recording_data_are_bound_from_the_document(detailed_html, context):
    assert context.patient.name in detailed_html
    assert context.patient.patient_id in detailed_html
    assert context.doctor.name in detailed_html
    assert "grp-test000001" in detailed_html


def test_report_metadata_is_embedded_for_traceability(detailed_html):
    for name, value in (
        ("ncep:report-id", "grp-test000001"),
        ("ncep:report-version", "1"),
        ("ncep:template-id", "ncep-detailed-report"),
        ("ncep:template-version", "2.0.0"),
        ("ncep:pipeline-version", "1.0.0"),
        ("ncep:schema-version", "1.0.0"),
    ):
        assert f'<meta name="{name}" content="{value}">' in detailed_html
    assert 'content="2026-08-06T09:30:00+00:00"' in detailed_html


def test_no_sample_content_from_the_specification_survives(detailed_html):
    """The template is data-driven: none of its sample values may leak."""
    for sample in SAMPLE_CONTENT:
        assert sample not in detailed_html


def test_unavailable_clinical_values_render_an_accurate_reason(detailed_html):
    assert "Clinical result unavailable: approved decision limits are not configured" in detailed_html
    assert PLACEHOLDER_AWAITING_SIGNAL_PROCESSING not in detailed_html
    # The specification's sample impression must be replaced by the placeholder.
    assert "ventricular late-potential criteria in the filtered terminal QRS" not in detailed_html


def test_every_awaited_section_is_still_laid_out(detailed_html):
    """Placeholders preserve the layout rather than removing sections (Sprint 6.16)."""
    for marker in (
        "domain-ledger",
        "measure-table",
        "criteria-list",
        "process-spine",
        "timing-comparison",
        "evidence-ledger",
        "trace-chain",
        "method-provenance",
        "review-checkpoints",
        "signature-grid",
    ):
        assert marker in detailed_html


def test_rendering_is_reproducible(context):
    """Identical document and identity produce identical HTML."""
    document = DetailedReportBuilder().build(context)
    engine = TemplateEngine()
    first = engine.render(
        document, DETAILED_REPORT_TEMPLATE, report_id="grp-1", generated_at=GENERATED_AT
    )
    second = engine.render(
        document, DETAILED_REPORT_TEMPLATE, report_id="grp-1", generated_at=GENERATED_AT
    )

    assert first.html == second.html


def test_a_report_without_a_figure_renders_a_placeholder_instead(context):
    document = DetailedReportBuilder().build(
        context, visualization_unavailable_reason="no lead carries a usable signal"
    )

    html = TemplateEngine().render(
        document, DETAILED_REPORT_TEMPLATE, report_id="grp-2", generated_at=GENERATED_AT
    ).html

    assert "no lead carries a usable signal" in html
    assert 'class="ecg-trace"' not in html
    assert html.count('class="report-page"') == 8  # layout preserved


def test_the_document_drives_the_template_not_the_reverse(context):
    """A section the builder omits degrades to a placeholder, not an error."""
    document = DetailedReportBuilder().build(context)
    trimmed = type(document)(
        report_type=document.report_type,
        title=document.title,
        metadata=document.metadata,
        sections=tuple(s for s in document.sections if s.id is not SectionId.LEAD_QUALITY),
    )

    html = TemplateEngine().render(
        trimmed, DETAILED_REPORT_TEMPLATE, report_id="grp-3", generated_at=GENERATED_AT
    ).html

    assert html.count('class="report-page"') == 8
