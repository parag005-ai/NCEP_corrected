"""Tests for report composition (Sprint 6.6 - 6.10 / 6.16)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.reporting.builders import (
    Availability,
    DetailedReportBuilder,
    ReportSection,
    SectionId,
    SummaryReportBuilder,
)
from app.reporting.constants import (
    PLACEHOLDER_NOT_AVAILABLE,
    ArtifactType,
    ReportType,
)
from app.reporting.context import GenerationContextLoader
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.repositories.job_repository import ReportGenerationJobRepository

from tests.reporting.conftest import write_canonical_artifacts

RAW_ECG_VISUALIZATION = PendingReportArtifact(
    artifact_type=ArtifactType.RAW_ECG_SVG,
    content_type="image/svg+xml",
    storage_location="visualizations/raw_ecg_lead_II.svg",
    absolute_path="/reports/ecg-1/rgj-1/visualizations/raw_ecg_lead_II.svg",
    file_size_bytes=2048,
    checksum_sha256="c" * 64,
    generated_at=datetime.now(timezone.utc),
    artifact_metadata={
        "visualization_type": "RAW_ECG",
        "lead": "II",
        "window_start_second": 0.0,
        "window_end_second": 10.0,
        "sampling_rate_hz": 1000.0,
    },
)


@pytest.fixture
def context(session, upstream, artifact_store):
    """A Generation Context for a fully ingested recording."""
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


def values_of(section: ReportSection) -> dict[str, str]:
    return {value.label: value.display_value for value in section.values}


# ---------------------------------------------------------------------------
# Document structure (Sprint 6.7 / 6.8 / 6.10)
# ---------------------------------------------------------------------------


def test_the_summary_contains_the_sections_a_clinician_reads_first(context):
    document = SummaryReportBuilder().build(context)

    assert document.report_type is ReportType.SUMMARY
    assert document.section_ids == (
        SectionId.REPORT_HEADER,
        SectionId.PATIENT_INFORMATION,
        SectionId.DOCTOR_INFORMATION,
        SectionId.RECORDING_SUMMARY,
        SectionId.SIGNAL_QUALITY,
        SectionId.RAW_ECG_VISUALIZATION,
        SectionId.RHYTHM_METRICS,
        SectionId.CLINICAL_FLAGS,
        SectionId.INTERPRETATION,
        SectionId.RECOMMENDATIONS,
        SectionId.REPORT_FOOTER,
    )


def test_the_detailed_report_expands_on_the_summary(context):
    summary = SummaryReportBuilder().build(context)
    detailed = DetailedReportBuilder().build(context)

    assert detailed.report_type is ReportType.DETAILED
    assert set(summary.section_ids) <= set(detailed.section_ids)
    assert SectionId.SAECG_PARAMETERS in detailed.section_ids
    assert SectionId.REPOLARIZATION_ANALYSIS in detailed.section_ids
    assert SectionId.CLINICAL_MEASUREMENTS in detailed.section_ids
    assert SectionId.RECOMMENDATIONS in detailed.section_ids


def test_both_variants_open_with_the_header_and_close_with_the_footer(context):
    for document in (SummaryReportBuilder().build(context), DetailedReportBuilder().build(context)):
        assert document.section_ids[0] is SectionId.REPORT_HEADER
        assert document.section_ids[-1] is SectionId.REPORT_FOOTER


def test_a_document_carries_the_traceability_metadata_of_its_generation(context):
    document = DetailedReportBuilder().build(context)

    assert document.metadata.ecg_record_id == context.ecg.ecg_record_id
    assert document.metadata.job_id == context.generation.job_id
    assert document.metadata.report_version == context.generation.report_version
    assert document.metadata.pipeline_version == context.generation.pipeline_version
    assert document.metadata.schema_version == context.generation.schema_version
    assert document.metadata.software_version == context.generation.software_version


# ---------------------------------------------------------------------------
# Consistency between variants (Sprint 2.24)
# ---------------------------------------------------------------------------


def test_both_variants_state_the_same_facts(context):
    """The Detailed report may show more, never something different."""
    summary = SummaryReportBuilder().build(context)
    detailed = DetailedReportBuilder().build(context)

    for section_id in (SectionId.PATIENT_INFORMATION, SectionId.RECORDING_SUMMARY):
        summary_values = values_of(summary.section(section_id))
        detailed_values = values_of(detailed.section(section_id))
        assert summary_values.items() <= detailed_values.items()
        assert len(detailed_values) > len(summary_values)


# ---------------------------------------------------------------------------
# Available data (Phase 1)
# ---------------------------------------------------------------------------


def test_patient_information_is_populated_from_the_context(context):
    section = SummaryReportBuilder().build(context).section(SectionId.PATIENT_INFORMATION)

    assert section.is_available
    assert values_of(section)["Name"] == "Test Patient"
    assert values_of(section)["Patient ID"] == context.patient.patient_id


def test_recording_information_is_populated_from_the_context(context):
    section = DetailedReportBuilder().build(context).section(SectionId.RECORDING_SUMMARY)

    values = values_of(section)
    assert values["Sampling rate"] == "1,000"
    assert values["Duration"] == "10.0"
    assert values["Leads"] == "I, II, V1"
    assert values["Source format"] == "WFDB"


def test_signal_quality_reports_ingestion_measurements(context):
    section = DetailedReportBuilder().build(context).section(SectionId.SIGNAL_QUALITY)

    values = values_of(section)
    assert values["Quality score"] == "0.93"
    assert values["Accepted beats"] == "12"
    assert values["Validation status"] == "PASS"
    assert values["SP preprocessing status"] == context.signal_processing.signal_quality_metrics.payload[
        "preprocessing_status"
    ]
    assert values["QRS QC status"] == context.signal_processing.signal_quality_metrics.payload[
        "qrs_qc_status"
    ]
    assert values["R-peak count"] == str(
        context.signal_processing.signal_quality_metrics.payload["r_peak_count"]
    )


def test_an_absent_optional_value_is_marked_not_invented(context):
    """The fixture patient has no clinical notes; the report must say so."""
    section = DetailedReportBuilder().build(context).section(SectionId.PATIENT_INFORMATION)

    notes = next(value for value in section.values if value.label == "Clinical notes")
    assert not notes.is_available
    assert notes.availability is Availability.NOT_AVAILABLE
    assert notes.display_value == PLACEHOLDER_NOT_AVAILABLE


# ---------------------------------------------------------------------------
# Phase 1 placeholders (Sprint 5.7 / 6.16)
# ---------------------------------------------------------------------------


def test_clinical_measurements_are_copied_from_signal_processing(context):
    section = DetailedReportBuilder().build(context).section(SectionId.CLINICAL_MEASUREMENTS)

    assert section.is_available
    assert section.value("Heart rate").value == str(
        round(context.signal_processing.ecg_parameters.payload["heart_rate_bpm"])
    )


@pytest.mark.parametrize(
    "section_id",
    [SectionId.CLINICAL_FLAGS, SectionId.CLINICAL_FINDINGS, SectionId.INTERPRETATION, SectionId.RECOMMENDATIONS],
)
def test_rule_dependent_sections_are_unavailable_without_inventing_results(context, section_id):
    section = DetailedReportBuilder().build(context).section(section_id)

    assert section is not None
    assert section.availability is Availability.NOT_AVAILABLE
    assert "decision limits are not configured" in section.display_placeholder
    assert all(not value.is_available for value in section.values)


# ---------------------------------------------------------------------------
# Signal Processing (Phase 2): sections now backed by the vendored ECG
# pipeline (Sprint 5.7 Phase 2 -- see app/signal_processing/README.md)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section_id",
    [
        SectionId.RHYTHM_METRICS,
        SectionId.STANDARD_ECG_MEASUREMENTS,
        SectionId.ATRIAL_CRITERIA,
        SectionId.ATRIAL_MEASUREMENTS,
        SectionId.SAECG_PROCESSING,
        SectionId.SAECG_PARAMETERS,
        SectionId.REPOLARIZATION_TIMING,
        SectionId.REPOLARIZATION_ANALYSIS,
    ],
)
def test_signal_processing_measurement_sections_are_populated(context, section_id):
    """These sections now carry real, computed values -- no longer placeholders."""
    section = DetailedReportBuilder().build(context).section(section_id)

    assert section is not None
    assert section.availability is Availability.AVAILABLE
    # At least one value in the section is a real, computed measurement.
    assert any(value.is_available for value in section.values)


def test_fields_no_vendored_module_computes_are_unavailable(context):
    """A populated section can still individually await a specific field --
    e.g. rhythm classification and PR interval require analysis no vendored
    module performs, distinct from metrics that ARE computed (Sprint 5.7 /
    6.16: absent data says so per-field, not just per-section)."""
    rhythm = DetailedReportBuilder().build(context).section(SectionId.RHYTHM_METRICS)

    assert rhythm.value("Rate").is_available
    assert rhythm.value("Rhythm").availability is Availability.NOT_AVAILABLE
    assert rhythm.value("PR").availability is Availability.NOT_AVAILABLE
    assert rhythm.value("Rhythm").display_value == "Not produced by Signal Processing"


def test_no_clinical_value_is_ever_invented(context):
    """Every populated value must trace to the context, never to a default."""
    document = DetailedReportBuilder().build(context)

    # Raw measurements are copied from the SP context, never recomputed.
    clinical_measurements = document.section(SectionId.CLINICAL_MEASUREMENTS)
    assert clinical_measurements.value("Heart rate").value == str(
        round(context.signal_processing.ecg_parameters.payload["heart_rate_bpm"])
    )

    # Rule-dependent output remains absent.
    for section_id in (SectionId.CLINICAL_FLAGS, SectionId.CLINICAL_FINDINGS, SectionId.RECOMMENDATIONS):
        assert not document.section(section_id).is_available

    # Integrated -- every real value must equal what the context actually
    # computed, proving it was read from Signal Processing output, not
    # invented by the builder.
    ecg_parameters = context.signal_processing.ecg_parameters.payload
    rhythm = document.section(SectionId.RHYTHM_METRICS)
    assert rhythm.value("Rate").value == str(round(ecg_parameters["heart_rate_bpm"]))


# ---------------------------------------------------------------------------
# Visualization section (Sprint 4.19)
# ---------------------------------------------------------------------------


def test_the_visualization_section_references_the_stored_figure(context):
    document = DetailedReportBuilder().build(context, visualization=RAW_ECG_VISUALIZATION)
    section = document.section(SectionId.RAW_ECG_VISUALIZATION)

    assert section.is_available
    figure = section.figures[0]
    assert figure.artifact_type is ArtifactType.RAW_ECG_SVG
    assert figure.storage_location == "visualizations/raw_ecg_lead_II.svg"
    assert figure.media_type == "image/svg+xml"
    assert "lead II" in figure.caption
    assert values_of(section)["Lead"] == "II"


def test_both_variants_reference_the_same_figure(context):
    summary = SummaryReportBuilder().build(context, visualization=RAW_ECG_VISUALIZATION)
    detailed = DetailedReportBuilder().build(context, visualization=RAW_ECG_VISUALIZATION)

    assert (
        summary.section(SectionId.RAW_ECG_VISUALIZATION).figures[0].storage_location
        == detailed.section(SectionId.RAW_ECG_VISUALIZATION).figures[0].storage_location
    )


def test_an_undrawable_recording_leaves_an_explained_placeholder(context):
    document = SummaryReportBuilder().build(
        context, visualization_unavailable_reason="no lead carries a usable signal"
    )
    section = document.section(SectionId.RAW_ECG_VISUALIZATION)

    assert not section.is_available
    assert section.figures == ()
    assert section.display_placeholder == "no lead carries a usable signal"


# ---------------------------------------------------------------------------
# Recoverable gaps (Sprint 3.14)
# ---------------------------------------------------------------------------


def test_a_missing_clinician_leaves_the_section_in_place(session, upstream, artifact_store):
    from app.models import ECGRecord, Patient

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.get(ECGRecord, upstream.ecg_record_id).doctor_id = ""
    session.get(Patient, upstream.patient_id).assigned_doctor_id = None
    session.flush()
    job = ReportGenerationJobRepository(session).create(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
    )
    loader = GenerationContextLoader(session, artifacts=ECGArtifactRepository(store=artifact_store))

    document = SummaryReportBuilder().build(loader.load(job))
    section = document.section(SectionId.DOCTOR_INFORMATION)

    assert not section.is_available
    assert "No clinician" in section.display_placeholder


# ---------------------------------------------------------------------------
# Builders emit data, not markup (Sprint 6.15)
# ---------------------------------------------------------------------------


def test_no_built_content_contains_markup(context):
    """Presentation belongs entirely to the Template Engine."""
    document = DetailedReportBuilder().build(context, visualization=RAW_ECG_VISUALIZATION)

    for section in document.sections:
        rendered = [section.title, section.display_placeholder, *section.notes]
        rendered += [value.label for value in section.values]
        rendered += [value.display_value for value in section.values]
        rendered += [figure.caption for figure in section.figures]
        for text in rendered:
            assert "<" not in text and ">" not in text
